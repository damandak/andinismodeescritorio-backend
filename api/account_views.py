"""The signed-in user's own data: /djangoapi/me/ and /djangoapi/me/claim/.

Login, signup, logout and passwords are allauth's API under
/djangoapi/_allauth/browser/v1/ (see adeback/settings.py)."""
from django.db import transaction
from rest_framework import serializers, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from cerros.forms import clean_public_name
from cerros.models import Andinist, AndinistClaim


def _andinist(a):
    return {"id": a.pk, "name": " ".join(filter(None, [a.name, a.surname]))} if a else None


def _me(user):
    from allauth.account.models import EmailAddress

    claim = user.andinist_claims.select_related("andinist").exclude(status=AndinistClaim.APPROVED).first()
    return {
        "email": user.email,
        "public_name": user.public_name,
        "email_verified": EmailAddress.objects.filter(user=user, verified=True).exists(),
        "andinist": _andinist(user.andinist),
        "claim": {
            "andinist": _andinist(claim.andinist),
            "status": claim.get_status_display(),
            "pending": claim.status == AndinistClaim.PENDING,
            "created_at": claim.created_at,
        } if claim else None,
        "is_editor": user.is_staff,
    }


class AccountView(APIView):
    authentication_classes = [SessionAuthentication]  # with CSRF checks
    permission_classes = [IsAuthenticated]


class MeView(AccountView):
    """GET: my data. PATCH {"public_name": "..."}: change my public name."""

    def get(self, request):
        return Response(_me(request.user))

    def patch(self, request):
        try:
            name = clean_public_name(request.data.get("public_name"))
        except Exception as error:  # forms.ValidationError
            return Response({"public_name": list(getattr(error, "messages", [str(error)]))}, status=400)
        request.user.public_name = name
        request.user.save(update_fields=["public_name"])
        return Response(_me(request.user))


class ClaimInput(serializers.Serializer):
    andinist = serializers.PrimaryKeyRelatedField(queryset=Andinist.objects.all())
    message = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")


class ClaimView(AccountView):
    """POST {"andinist": id, "message": "..."}: ask to be linked to an andinist.
    DELETE: withdraw my pending request."""

    def post(self, request):
        data = ClaimInput(data=request.data)
        data.is_valid(raise_exception=True)
        andinist = data.validated_data["andinist"]
        user = request.user
        from allauth.account.models import EmailAddress

        if not EmailAddress.objects.filter(user=user, verified=True).exists():
            return Response({"detail": "Confirma tu correo antes de vincular tu perfil."}, status=400)
        with transaction.atomic():
            if user.andinist_id:
                return Response({"detail": "Tu cuenta ya está vinculada a un andinista."}, status=400)
            if user.andinist_claims.filter(status=AndinistClaim.PENDING).exists():
                return Response({"detail": "Ya tienes una solicitud pendiente."}, status=400)
            if andinist.customuser_set.exists():
                return Response({"detail": "Ese perfil ya está vinculado a otra cuenta."}, status=400)
            AndinistClaim.objects.create(user=user, andinist=andinist, message=data.validated_data["message"].strip())
        return Response(_me(user), status=status.HTTP_201_CREATED)

    def delete(self, request):
        request.user.andinist_claims.filter(status=AndinistClaim.PENDING).delete()
        return Response(_me(request.user))
