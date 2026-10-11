"""Roles. "Editores": staff who curate the data in the admin (everything in
the "cerros" app except user accounts). Administrators are superusers.

Kept up to date after every `migrate` (cerros/apps.py), so new models get
their permissions automatically."""

EDITORS = "Editores"
EXCLUDED_MODELS = {"customuser"}


def ensure_roles(**kwargs):
    from django.contrib.auth.models import Group, Permission

    group, _ = Group.objects.get_or_create(name=EDITORS)
    perms = Permission.objects.filter(content_type__app_label="cerros").exclude(
        content_type__model__in=EXCLUDED_MODELS
    )
    group.permissions.set(perms)
