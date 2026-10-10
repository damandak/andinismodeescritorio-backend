"""A mountain's country and region according to its coordinates.

`evaluate()` works out what to do without writing anything (that's what
`asignar_ubicacion --dry-run` shows); `apply()` writes it. Rules:

- No country and no region: if the mountain is at least `margin` metres from
  every limit, both are assigned ("Asignada por coordenadas"). If it's nearer,
  nothing is assigned and it's left "Por completar: cerca de un límite", with
  the suggestion shown in its admin page.
- Only one of the two loaded: the missing one is completed the same way.
- Data already loaded is never changed. It's compared with the coordinates:
  "Coincide" or "No calza" (near a limit, either side counts as matching).
- "Revisada a mano" is kept unless asked otherwise, and "Asignada por
  coordenadas" stays while the data still matches.
"""
from dataclasses import dataclass, field

from cerros import geo


@dataclass
class Result:
    status: int
    note: str = ""
    distance: int | None = None
    suggested_country: object = None
    suggested_region: object = None
    add_country: object = None  # to assign
    add_region: object = None
    across: list = field(default_factory=list)


class Lookups:
    """Countries and regions of the database, loaded once per run."""

    def __init__(self):
        from cerros.models import Country, Region

        self.countries = list(Country.objects.all())
        self.regions = list(Region.objects.all())

    def find(self, place):
        return geo.find_in_database(place, self.countries, self.regions)


def evaluate(mountain, margin=geo.DEFAULT_MARGIN, lookups=None, keep_reviewed=True):
    from cerros.models import Mountain as M

    if mountain.latitude is None or mountain.longitude is None:
        return Result(M.LOCATION_NO_COORDINATES, note="Sin coordenadas.")

    lookups = lookups or Lookups()
    s = geo.suggest(mountain.latitude, mountain.longitude, margin)
    if s.place is None:
        return Result(M.LOCATION_OUTSIDE, note=s.describe())

    country, region = lookups.find(s.place)
    notes = [s.describe()]
    if country is None:
        notes.append(f"El país «{s.place.country}» no está en la base.")
    elif region is None:
        notes.append(f"La región «{s.place.region}» no está en la base (o el nombre no coincide).")
    if not s.confident and s.across:
        others = "; ".join(f"{p.country}, {p.region}" for p in s.across)
        notes.append(f"Cerca también de: {others}.")
    result = Result(
        M.LOCATION_MATCH, note=" ".join(notes), distance=s.distance,
        suggested_country=country, suggested_region=region, across=s.across,
    )

    if keep_reviewed and mountain.location_status == M.LOCATION_REVIEWED:
        result.status = M.LOCATION_REVIEWED
        return result

    loaded_countries = list(mountain.countries.all()) if mountain.pk else []
    loaded_regions = list(mountain.regions.all()) if mountain.pk else []

    # Near a limit, the other side is also a plausible answer.
    plausible = [s.place] + ([] if s.confident else s.across)
    country_ok = not loaded_countries or any(
        geo.name_key(c.name) == geo.name_key(p.country) for c in loaded_countries for p in plausible
    )
    region_ok = not loaded_regions or any(
        geo.same_name(r.name, p.region) for r in loaded_regions for p in plausible
    )
    if not (country_ok and region_ok):
        result.status = M.LOCATION_MISMATCH
        return result

    missing_country = not loaded_countries
    missing_region = not loaded_regions
    if not (missing_country or missing_region):
        # Assigned by this method earlier: keep saying so.
        result.status = M.LOCATION_AUTO if mountain.location_status == M.LOCATION_AUTO else M.LOCATION_MATCH
        return result

    can_complete = s.confident and (not missing_country or country) and (not missing_region or region)
    if can_complete:
        result.status = M.LOCATION_AUTO
        result.add_country = country if missing_country else None
        result.add_region = region if missing_region else None
    else:
        result.status = M.LOCATION_TO_REVIEW
    return result


def apply(mountain, result):
    """Save the result (and assign the country/region it decided to add)."""
    from cerros.models import Mountain

    if result.add_country is not None:
        mountain.countries.add(result.add_country)
    if result.add_region is not None:
        mountain.regions.add(result.add_region)
    # .update(): no save() side effects, no signals.
    Mountain.objects.filter(pk=mountain.pk).update(
        location_status=result.status,
        location_note=result.note[:500],
        border_distance=result.distance,
        suggested_country=result.suggested_country,
        suggested_region=result.suggested_region,
    )


def check_one(mountain, margin=geo.DEFAULT_MARGIN):
    """Evaluate and save a single mountain (used by the admin when saving).
    The maps are released afterwards so the web process doesn't keep them."""
    try:
        result = evaluate(mountain, margin)
        apply(mountain, result)
        return result
    finally:
        geo.release_maps()
