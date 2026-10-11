from django import forms
from django.utils import timezone


def clean_public_name(value):
    """Plain text, one line, no control characters."""
    value = " ".join((value or "").split())
    value = "".join(ch for ch in value if ch.isprintable())
    if len(value) < 2:
        raise forms.ValidationError("Escribe tu nombre (al menos 2 letras).")
    return value[:80]


class SignupForm(forms.Form):
    """Extra fields of the site's signup (used by allauth, ACCOUNT_SIGNUP_FORM_CLASS)."""

    public_name = forms.CharField(
        label="Nombre público", max_length=80,
        help_text="Así aparecerás junto a tus aportes.",
    )
    accept_privacy = forms.BooleanField(
        label="Acepto la política de privacidad", required=True,
        error_messages={"required": "Debes aceptar la política de privacidad."},
    )

    # Invisible in the site's form: people leave it empty, spam bots fill it.
    website = forms.CharField(required=False)

    def clean_public_name(self):
        return clean_public_name(self.cleaned_data.get("public_name"))

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("No se pudo crear la cuenta.")
        return ""

    def signup(self, request, user):
        user.public_name = self.cleaned_data["public_name"]
        user.privacy_accepted_at = timezone.now()
        user.save(update_fields=["public_name", "privacy_accepted_at"])
