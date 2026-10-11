"""Changes proposed by users (cerros.models.Proposal): which fields can be
proposed, how they are validated, shown to the editor and applied.

Validation and application go through a Django ModelForm with only the
proposed fields, so the same rules as the admin apply (choices, number
formats, related records that exist...). Applying saves the record normally:
derived fields (first ascents...) are recalculated by the usual signals, and
the internal history (simple_history) records "Propuesta #N de <autor>".
"""
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.forms import modelform_factory
from django.utils import timezone

from cerros.models import Andinist, Ascent, Mountain, Proposal, Route

MODELS = {
    Proposal.MOUNTAIN: Mountain,
    Proposal.ROUTE: Route,
    Proposal.ASCENT: Ascent,
    Proposal.ANDINIST: Andinist,
}

# Fields a user can propose, in the order they are shown.
FIELDS = {
    Proposal.MOUNTAIN: [
        "prefix", "name", "altitude_igm", "altitude_arg", "altitude_gps", "main_altitude_source",
        "latitude", "longitude", "countries", "regions", "mountain_group",
        "unregistered_sport_ascent", "unregistered_non_sport_ascent", "ref_ahb", "ref_wikiexplora",
    ],
    Proposal.ROUTE: [
        "name", "summit", "alpine_grade", "rock_climbing_grade", "ice_climbing_grade", "aid_climbing_grade",
        "description", "notes", "unregistered_sport_ascent", "unregistered_non_sport_ascent",
    ],
    Proposal.ASCENT: [
        "name", "date", "date_format", "completed", "andinists", "support_andinists", "is_first_ascent", "new_route",
    ],
    Proposal.ANDINIST: ["name", "surname", "nationalities", "clubs"],
}
CAN_CREATE = {Proposal.MOUNTAIN}
REQUIRED_FOR_NEW = {Proposal.MOUNTAIN: ["prefix", "name"]}
SEARCHED = {"andinists", "support_andinists"}  # too many options: chosen with a search box

LABELS = {
    "prefix": "Prefijo", "name": "Nombre", "surname": "Apellido",
    "altitude_igm": "Altitud IGM Chile (m)", "altitude_arg": "Altitud IGN Argentina (m)",
    "altitude_gps": "Altitud GPS (m)", "main_altitude_source": "Altitud principal según",
    "latitude": "Latitud", "longitude": "Longitud",
    "countries": "Países", "regions": "Regiones", "mountain_group": "Sectores",
    "unregistered_sport_ascent": "Tiene ascensos deportivos sin registro",
    "unregistered_non_sport_ascent": "Tiene ascensos no deportivos (arrieros, mineros, pueblos originarios)",
    "ref_ahb": "Andeshandbook (enlace)", "ref_wikiexplora": "Wikiexplora (enlace)",
    "summit": "Llega a la cumbre", "alpine_grade": "Grado alpino", "rock_climbing_grade": "Grado en roca",
    "ice_climbing_grade": "Grado en hielo", "aid_climbing_grade": "Grado en artificial",
    "description": "Descripción", "notes": "Notas",
    "date": "Fecha", "date_format": "Precisión de la fecha", "completed": "Completado (llegó al objetivo)",
    "andinists": "Cordada", "support_andinists": "Apoyo", "is_first_ascent": "Primera ascensión",
    "new_route": "Ruta nueva", "nationalities": "Nacionalidades", "clubs": "Clubes",
}
HELP = {
    "latitude": "En grados decimales (WGS84), negativa al sur. Ej.: -33.236155",
    "longitude": "En grados decimales (WGS84), negativa al oeste. Ej.: -70.214494",
    "main_altitude_source": "Cuál de las altitudes se muestra. En un cerro nuevo con una sola altitud, se usa esa.",
}

MAX_OPEN = 10  # pending proposals per person
MAX_PER_DAY = 20

PUBLIC_PATHS = {
    Proposal.MOUNTAIN: "/cerros/{}", Proposal.ROUTE: "/rutas/{}",
    Proposal.ASCENT: "/ascensos/{}", Proposal.ANDINIST: "/andinistas/{}",
}


class ProposalError(Exception):
    def __init__(self, errors):
        super().__init__(errors)
        self.errors = errors  # {field or "": [messages]}


def model_field(kind, name):
    return MODELS[kind]._meta.get_field(name)


def clean_text(value, max_length):
    """Plain text: no control characters (line breaks are kept), trimmed."""
    text = "".join(ch for ch in str(value or "") if ch.isprintable() or ch in "\n\t").strip()
    return text[:max_length]


# --- Values: stored as JSON, shown to people -----------------------------------

def serialize(field, value):
    """A field's value as JSON: ids for related records, text for numbers and dates."""
    if field.many_to_many:
        items = value.all() if hasattr(value, "all") else (value or [])
        return sorted(item.pk if hasattr(item, "pk") else int(item) for item in items)
    if field.many_to_one:
        return getattr(value, "pk", value)
    if value is None or value == "":
        return None
    if field.get_internal_type() == "DecimalField":
        return f"{value:.{field.decimal_places}f}"
    if field.get_internal_type() == "DateField":
        return value.isoformat()
    return value


def current_values(kind, obj, fields):
    values = {}
    for name in fields:
        field = model_field(kind, name)
        if field.many_to_many:
            values[name] = serialize(field, getattr(obj, name).all() if obj.pk else [])
        else:
            values[name] = serialize(field, getattr(obj, field.attname if field.many_to_one else name))
    return values


DATE_FORMATS = {Ascent.YEAR: "Solo el año", Ascent.MONTHYEAR: "Mes y año", Ascent.DAYMONTHYEAR: "Día, mes y año"}


def partial_date(iso, date_format):
    """"1965", "02/1965" or "10/02/1965", as precise as the date is known."""
    if not iso:
        return "—"
    year, month, day = iso.split("-")
    if date_format == Ascent.YEAR:
        return year
    if date_format == Ascent.MONTHYEAR:
        return f"{month}/{year}"
    return f"{day}/{month}/{year}"


def display(kind, name, value, values=None):
    """How a value reads for a person: names instead of ids, labels for choices.
    `values` (the other values of the same set) gives a date its precision."""
    field = model_field(kind, name)
    if name == "date" and values is not None and value:
        return partial_date(value, values.get("date_format"))
    if name == "date_format" and value is not None:
        return DATE_FORMATS.get(value, str(value))
    if value in (None, "", []):
        return "—"
    if field.many_to_many:
        model = field.related_model
        names = {o.pk: str(o) for o in model.objects.filter(pk__in=value)}
        return ", ".join(names.get(pk, f"#{pk} (no existe)") for pk in value)
    if field.many_to_one:
        obj = field.related_model.objects.filter(pk=value).first()
        return str(obj) if obj else f"#{value} (no existe)"
    if field.choices:
        return dict(field.flatchoices).get(value, str(value))
    if isinstance(value, bool):
        return "Sí" if value else "No"
    return str(value)


# --- Validation ---------------------------------------------------------------

def _form_data(kind, values):
    data = {}
    for name, value in values.items():
        field = model_field(kind, name)
        if field.many_to_many:
            data[name] = [str(v) for v in (value or [])]
        elif isinstance(value, bool):
            data[name] = "on" if value else ""
        else:
            data[name] = "" if value is None else str(value)
    return data


def build_form(kind, values, instance):
    form_class = modelform_factory(MODELS[kind], fields=list(values.keys()))
    return form_class(data=_form_data(kind, values), instance=instance)


def _form_errors(form):
    return {name: [str(e) for e in errors] for name, errors in form.errors.items()}


def prepare(kind, target_id, raw_changes):
    """Validate proposed values. Returns (changes, original, label) with only
    the fields that really change; raises ProposalError."""
    if kind not in MODELS:
        raise ProposalError({"": ["Tipo de ficha desconocido."]})
    creating = target_id is None
    if creating and kind not in CAN_CREATE:
        raise ProposalError({"": ["No se pueden proponer fichas nuevas de este tipo."]})
    if not isinstance(raw_changes, dict) or not raw_changes:
        raise ProposalError({"": ["No cambiaste ningún dato."]})
    unknown = set(raw_changes) - set(FIELDS[kind])
    if unknown:
        raise ProposalError({"": [f"Campos no permitidos: {', '.join(sorted(unknown))}."]})

    model = MODELS[kind]
    if creating:
        obj = model()
        missing = [f for f in REQUIRED_FOR_NEW.get(kind, []) if raw_changes.get(f) in (None, "", [])]
        if missing:
            raise ProposalError({f: ["Este dato es obligatorio."] for f in missing})
    else:
        obj = model.objects.filter(pk=target_id).first()
        if obj is None:
            raise ProposalError({"": ["La ficha no existe."]})

    values = dict(raw_changes)
    if creating and kind == Proposal.MOUNTAIN and "main_altitude_source" not in values:
        # The main altitude is the one given (IGM, then IGN, then GPS).
        for name, source in (("altitude_igm", Mountain.IGM), ("altitude_arg", Mountain.ARG), ("altitude_gps", Mountain.GPS)):
            if values.get(name) not in (None, ""):
                values["main_altitude_source"] = source
                break
    # A date only makes sense with its precision, and the other way around.
    if kind == Proposal.ASCENT and ("date" in values or "date_format" in values):
        values.setdefault("date", serialize(model_field(kind, "date"), obj.date))
        values.setdefault("date_format", obj.date_format)
    for name, value in list(values.items()):
        field = model_field(kind, name)
        if field.get_internal_type() == "DecimalField" and value not in (None, ""):
            # Coordinates with more decimals than stored: rounded, not refused.
            from decimal import Decimal, InvalidOperation

            try:
                values[name] = str(round(Decimal(str(value).replace(",", ".")), field.decimal_places))
            except InvalidOperation:
                pass  # the form reports it
        elif field.get_internal_type() == "TextField":
            values[name] = clean_text(value, 5000)
        elif field.get_internal_type() == "CharField" and value is not None:
            values[name] = clean_text(value, field.max_length or 255)

    original_all = current_values(kind, obj, values.keys())
    form = build_form(kind, values, model.objects.get(pk=obj.pk) if obj.pk else model())
    if not form.is_valid():
        raise ProposalError(_form_errors(form))
    normalized = {name: serialize(model_field(kind, name), form.cleaned_data[name]) for name in values}
    changes = {k: v for k, v in normalized.items() if creating or v != original_all[k]}
    if kind == Proposal.ASCENT and ("date" in changes or "date_format" in changes):
        changes["date"], changes["date_format"] = normalized["date"], normalized["date_format"]
    if not changes:
        raise ProposalError({"": ["No cambiaste ningún dato."]})
    original = {} if creating else {k: original_all[k] for k in changes}
    label = str(obj) if obj.pk else _new_label(kind, changes)
    return changes, original, label


def _new_label(kind, changes):
    if kind == Proposal.MOUNTAIN:
        from cerros.models import MountainPrefix

        prefix = MountainPrefix.objects.filter(pk=changes.get("prefix")).first()
        return f"{prefix or ''} {changes.get('name', '')}".strip()
    return changes.get("name", "")


def check_limits(user):
    if user.proposals.filter(status__in=Proposal.OPEN).count() >= MAX_OPEN:
        raise ProposalError({"": [f"Tienes {MAX_OPEN} propuestas esperando revisión. Espera a que se revisen."]})
    since = timezone.now() - timedelta(days=1)
    if user.proposals.filter(created_at__gte=since).count() >= MAX_PER_DAY:
        raise ProposalError({"": ["Llegaste al límite de propuestas por hoy. Vuelve mañana."]})


# --- Review --------------------------------------------------------------------

def rows(proposal):
    """For the review screen: one row per field with current, original and proposed values."""
    kind = proposal.target_model
    obj = None
    if proposal.target_id and not proposal.creates:
        obj = MODELS[kind].objects.filter(pk=proposal.target_id).first()
    now = current_values(kind, obj, set(proposal.changes) | {"date_format"} & set(FIELDS[kind])) if obj else {}
    original_all = {**now, **proposal.original}
    result = []
    for name in FIELDS[kind]:
        if name not in proposal.changes:
            continue
        original = proposal.original.get(name)
        current = now.get(name)
        result.append({
            "name": name,
            "label": LABELS.get(name, name),
            "current": display(kind, name, current, now) if obj else "—",
            "proposed": display(kind, name, proposal.changes[name], proposal.changes),
            "changed_since": bool(obj) and name in proposal.original and current != original,
            "original": display(kind, name, original, original_all),
        })
    return result


def apply(proposal, editor, values=None, message=""):
    """Apply an approved proposal (with the editor's adjusted values, if any,
    and an optional message for the author). Returns the saved record; raises
    ProposalError if the values are invalid."""
    from cerros import location

    kind = proposal.target_model
    model = MODELS[kind]
    values = dict(values if values is not None else proposal.changes)
    with transaction.atomic():
        obj = model() if proposal.creates else model.objects.select_for_update().get(pk=proposal.target_id)
        form = build_form(kind, values, obj)
        if not form.is_valid():
            raise ProposalError(_form_errors(form))
        obj = form.save(commit=False)
        author = proposal.author.public_name or proposal.author.email
        obj._change_reason = f"Propuesta #{proposal.pk} de {author}"
        obj.save()
        form.save_m2m()
        applied = {name: serialize(model_field(kind, name), form.cleaned_data[name]) for name in values}
        proposal.applied = applied if applied != proposal.changes else None
        proposal.status = Proposal.APPROVED
        proposal.editor_message = clean_text(message, 2000)
        proposal.reviewed_by = editor
        proposal.reviewed_at = timezone.now()
        proposal.target_id = obj.pk
        proposal.target_label = str(obj)[:255]
        proposal.save()

    if kind == Proposal.MOUNTAIN:
        changed = set(values)
        if changed & {"countries", "regions"}:
            location.check_one(obj)
            Mountain.objects.filter(pk=obj.pk).update(location_status=Mountain.LOCATION_REVIEWED)
        elif proposal.creates or changed & {"latitude", "longitude"}:
            location.check_one(obj)
    notify(proposal)
    return obj


def close(proposal, editor, status, message):
    """Ask for more information or reject."""
    proposal.status = status
    proposal.editor_message = clean_text(message, 2000)
    proposal.reviewed_by = editor
    proposal.reviewed_at = timezone.now()
    proposal.save()
    notify(proposal)


def contributors(kind, target_id):
    """Public names of the people whose proposals for this record were approved."""
    names = []
    approved = (
        Proposal.objects.filter(target_model=kind, target_id=target_id, status=Proposal.APPROVED)
        .select_related("author").order_by("reviewed_at")
    )
    for proposal in approved:
        name = proposal.author.public_name
        if name and name not in names:
            names.append(name)
    return names


def public_url(proposal):
    path = PUBLIC_PATHS[proposal.target_model].format(proposal.target_id) if proposal.target_id else ""
    return settings.FRONTEND_URL + path if path else ""


def notify(proposal):
    """Email the author when their proposal is resolved (if email is set up)."""
    email = proposal.author.email
    if not email:
        return
    label = proposal.target_label
    account = settings.FRONTEND_URL + "/mi-cuenta"
    if proposal.status == Proposal.APPROVED:
        subject = "Tu propuesta fue aprobada"
        note = f"\n\nMensaje del editor: {proposal.editor_message}" if proposal.editor_message else ""
        body = (f"Tu propuesta para «{label}» fue aprobada y ya está publicada. ¡Gracias por tu aporte!{note}"
                f"\n\n{public_url(proposal)}")
    elif proposal.status == Proposal.NEEDS_INFO:
        subject = "Tu propuesta necesita más información"
        body = (f"Un editor revisó tu propuesta para «{label}» y necesita más información:\n\n"
                f"{proposal.editor_message}\n\nPuedes editarla y reenviarla desde Mi cuenta:\n{account}")
    elif proposal.status == Proposal.REJECTED:
        subject = "Tu propuesta no fue aprobada"
        reason = f"\n\nMotivo: {proposal.editor_message}" if proposal.editor_message else ""
        body = f"Tu propuesta para «{label}» no fue aprobada.{reason}\n\nGracias de todas formas por tu interés."
    else:
        return
    name = proposal.author.public_name
    greeting = f"Hola{', ' + name if name else ''}:\n\n"
    send_mail(
        settings.ACCOUNT_EMAIL_SUBJECT_PREFIX + subject,
        greeting + body + "\n\n—\nAndinismo de Escritorio\n" + settings.FRONTEND_URL,
        None, [email], fail_silently=True,
    )


# --- Form description for the site -------------------------------------------

def describe(kind, obj):
    """Fields of the proposal form, with their current values (for the site)."""
    fields = []
    for name in FIELDS[kind]:
        if name == "date_format":
            continue  # shown together with the date
        field = model_field(kind, name)
        item = {"name": name, "label": LABELS.get(name, name), "help": HELP.get(name, "")}
        if field.many_to_many:
            value = serialize(field, getattr(obj, name).all()) if obj.pk else []
        else:  # a new record shows the field's default (e.g. altitude source IGM)
            value = serialize(field, getattr(obj, field.attname if field.many_to_one else name))
        if name in SEARCHED:
            item["type"] = "people"
            item["value"] = [{"id": a.pk, "name": str(a)} for a in field.related_model.objects.filter(pk__in=value)]
        elif field.many_to_many:
            item["type"] = "multi"
            item["options"] = [{"value": o.pk, "label": str(o)} for o in field.related_model.objects.all()]
            item["value"] = value
        elif field.many_to_one:
            item["type"] = "choice"
            item["options"] = [{"value": o.pk, "label": str(o)} for o in field.related_model.objects.all()]
            item["value"] = value
        elif field.choices:
            item["type"] = "choice"
            item["options"] = [{"value": v, "label": str(l)} for v, l in field.flatchoices]
            item["value"] = value
        else:
            internal = field.get_internal_type()
            item["type"] = {
                "BooleanField": "boolean", "DecimalField": "decimal", "IntegerField": "integer",
                "TextField": "textarea", "DateField": "partial_date",
            }.get(internal, "text")
            if internal == "DateField":
                item["value"] = {"date": value, "format": obj.date_format if obj.pk else Ascent.DAYMONTHYEAR}
            else:
                item["value"] = value
            if getattr(field, "max_length", None):
                item["max_length"] = field.max_length
        item["required"] = name in REQUIRED_FOR_NEW.get(kind, []) or (
            not field.blank and not field.has_default() and item["type"] != "boolean"
        )
        item["empty"] = field.null or field.blank
        fields.append(item)
    return fields


def similar_mountains(proposal, km=2.0):
    """For a proposed new mountain: existing ones with a similar name or less
    than `km` away, so the editor can spot duplicates."""
    import math

    from django.db.models import Q

    changes = proposal.changes
    name = (changes.get("name") or "").strip()
    query = Q(pk__in=[])
    if len(name) >= 3:
        query |= Q(name__icontains=name)
    lat, lon = changes.get("latitude"), changes.get("longitude")
    if lat not in (None, "") and lon not in (None, ""):
        lat, lon = float(lat), float(lon)
        dlat = km / 111.32
        dlon = dlat / max(math.cos(math.radians(lat)), 0.01)
        query |= Q(latitude__range=(lat - dlat, lat + dlat), longitude__range=(lon - dlon, lon + dlon))
    found = []
    for mountain in Mountain.objects.filter(query).select_related("prefix")[:15]:
        mountain.km = None
        if lat not in (None, "") and mountain.latitude is not None and mountain.longitude is not None:
            dy = (float(mountain.latitude) - lat) * 111.32
            dx = (float(mountain.longitude) - lon) * 111.32 * math.cos(math.radians(lat))
            mountain.km = math.hypot(dx, dy)
        mountain.main_altitude = mountain.altitude
        found.append(mountain)
    return sorted(found, key=lambda m: (m.km is None, m.km or 0))
