"""Proposals from the site: the form for a record, sending one, and the
user's own proposals (/djangoapi/proposals/..., /djangoapi/me/proposals/...).
Review happens in the admin (cerros/admin.py)."""
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from cerros import proposals as P
from cerros.models import Proposal

from .account_views import AccountView

SLUGS = {"cerro": Proposal.MOUNTAIN, "ruta": Proposal.ROUTE, "ascenso": Proposal.ASCENT, "andinista": Proposal.ANDINIST}
SLUG_OF = {v: k for k, v in SLUGS.items()}


def _kind(slug):
    if slug not in SLUGS:
        from django.http import Http404

        raise Http404
    return SLUGS[slug]


class ProposalFormView(APIView):
    """GET /djangoapi/proposals/form/<cerro|ruta|ascenso|andinista>/<id|nuevo>/"""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, slug, target):
        kind = _kind(slug)
        model = P.MODELS[kind]
        if target == "nuevo":
            if kind not in P.CAN_CREATE:
                return Response({"detail": "No se pueden proponer fichas nuevas de este tipo."}, status=404)
            obj = model()
        else:
            obj = get_object_or_404(model, pk=target)
        return Response({
            "model": slug,
            "id": obj.pk,
            "title": str(obj) if obj.pk else "Cerro nuevo",
            "fields": P.describe(kind, obj),
        })


def _proposal_json(p, detail=False):
    data = {
        "id": p.pk,
        "model": SLUG_OF[p.target_model],
        "target_id": p.target_id,
        "title": p.target_label,
        "creates": p.creates,
        "status": p.status,
        "status_label": p.get_status_display(),
        "editor_message": p.editor_message,
        "created_at": p.created_at,
        "changes": [
            {"label": P.LABELS.get(k, k), "value": P.display(p.target_model, k, v, p.changes)}
            for k, v in p.changes.items() if k != "date_format"
        ],
    }
    if detail:
        from cerros.models import Andinist

        data.update({"values": p.changes, "source": p.source, "comment": p.comment})
        # Names for the andinists chosen with the search box.
        for name in P.SEARCHED & set(p.changes):
            found = {a.pk: str(a) for a in Andinist.objects.filter(pk__in=p.changes[name] or [])}
            data["values"] = {**data["values"], name: [{"id": pk, "name": found.get(pk, f"#{pk}")} for pk in p.changes[name]]}
    return data


class ProposalCreateView(AccountView):
    """POST /djangoapi/proposals/ {model, target_id|null, changes, source, comment}"""

    def post(self, request):
        from allauth.account.models import EmailAddress

        if not EmailAddress.objects.filter(user=request.user, verified=True).exists():
            return Response({"": ["Confirma tu correo antes de proponer cambios."]}, status=403)
        kind = SLUGS.get(request.data.get("model"))
        if kind is None:
            return Response({"": ["Tipo de ficha desconocido."]}, status=400)
        source = P.clean_text(request.data.get("source"), 1000)
        if not source:
            return Response({"source": ["Indica la fuente de esta información."]}, status=400)
        target_id = request.data.get("target_id")
        try:
            P.check_limits(request.user)
            changes, original, label = P.prepare(kind, int(target_id) if target_id else None, request.data.get("changes"))
        except P.ProposalError as error:
            return Response(error.errors, status=400)
        except (TypeError, ValueError):
            return Response({"": ["Datos inválidos."]}, status=400)
        proposal = Proposal.objects.create(
            author=request.user, target_model=kind, target_id=int(target_id) if target_id else None,
            creates=not target_id, target_label=label[:255], changes=changes, original=original,
            source=source, comment=P.clean_text(request.data.get("comment"), 2000),
        )
        return Response(_proposal_json(proposal), status=201)


class MyProposalsView(AccountView):
    """GET /djangoapi/me/proposals/"""

    def get(self, request):
        items = request.user.proposals.exclude(status=Proposal.WITHDRAWN).order_by("-created_at")[:100]
        return Response([_proposal_json(p) for p in items])


class MyProposalView(AccountView):
    """GET / PATCH (edit and send again, when more information was asked) /
    DELETE (withdraw) /djangoapi/me/proposals/<id>/"""

    def get_object(self, request, pk):
        return get_object_or_404(request.user.proposals, pk=pk)

    def get(self, request, pk):
        return Response(_proposal_json(self.get_object(request, pk), detail=True))

    def patch(self, request, pk):
        proposal = self.get_object(request, pk)
        if proposal.status not in Proposal.OPEN:
            return Response({"": ["Esta propuesta ya fue revisada."]}, status=400)
        source = P.clean_text(request.data.get("source", proposal.source), 1000)
        if not source:
            return Response({"source": ["Indica la fuente de esta información."]}, status=400)
        try:
            changes, original, label = P.prepare(
                proposal.target_model, None if proposal.creates else proposal.target_id, request.data.get("changes")
            )
        except P.ProposalError as error:
            return Response(error.errors, status=400)
        proposal.changes, proposal.original, proposal.target_label = changes, original, label[:255]
        proposal.source = source
        proposal.comment = P.clean_text(request.data.get("comment", proposal.comment), 2000)
        proposal.status = Proposal.PENDING
        proposal.save()
        return Response(_proposal_json(proposal, detail=True))

    def delete(self, request, pk):
        proposal = self.get_object(request, pk)
        if proposal.status in Proposal.OPEN:
            proposal.status = Proposal.WITHDRAWN
            proposal.save(update_fields=["status", "updated_at"])
        return Response(status=204)
