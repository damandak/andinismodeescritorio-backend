"""
Keep derived fields in sync when ascents or routes change.

Before this, first ascents, "ascended" and andinist counters were only
recalculated when the mountain, route or andinist itself was saved, so a new
or edited ascent left them stale (e.g. a mountain showing "No registrado"
with a first ascent on record).
"""
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_delete, pre_save
from django.dispatch import receiver

from .derived import refresh_andinists, refresh_mountain, refresh_route
from .models import Ascent, Route


def _route_ids_and_mountain(route_id):
    mountain_id = (
        Route.objects.filter(pk=route_id).values_list("mountain_id", flat=True).first()
    )
    return route_id, mountain_id


def _refresh_for_route(route_id):
    if route_id is None:
        return
    route_id, mountain_id = _route_ids_and_mountain(route_id)
    refresh_route(route_id)
    if mountain_id is not None:
        refresh_mountain(mountain_id)


# --- Ascent -------------------------------------------------------------

@receiver(pre_save, sender=Ascent)
def ascent_remember_old_route(sender, instance, **kwargs):
    instance._old_route_id = (
        Ascent.objects.filter(pk=instance.pk).values_list("route_id", flat=True).first()
        if instance.pk
        else None
    )


@receiver(post_save, sender=Ascent)
def ascent_saved(sender, instance, raw=False, **kwargs):
    if raw:  # loaddata
        return
    _refresh_for_route(instance.route_id)
    old_route_id = getattr(instance, "_old_route_id", None)
    if old_route_id and old_route_id != instance.route_id:
        _refresh_for_route(old_route_id)
    # Flags (first ascent / new route) may have changed.
    refresh_andinists(instance.andinists.values_list("pk", flat=True))


@receiver(pre_delete, sender=Ascent)
def ascent_remember_relations(sender, instance, **kwargs):
    instance._andinist_ids = list(instance.andinists.values_list("pk", flat=True))
    instance._mountain_id = (
        Route.objects.filter(pk=instance.route_id)
        .values_list("mountain_id", flat=True)
        .first()
    )


@receiver(post_delete, sender=Ascent)
def ascent_deleted(sender, instance, **kwargs):
    refresh_route(instance.route_id)
    mountain_id = getattr(instance, "_mountain_id", None)
    if mountain_id is not None:
        refresh_mountain(mountain_id)
    refresh_andinists(getattr(instance, "_andinist_ids", []))


@receiver(m2m_changed, sender=Ascent.andinists.through)
def ascent_andinists_changed(sender, instance, action, reverse, pk_set, **kwargs):
    if action == "pre_clear":
        if reverse:  # andinist.ascent_set.clear()
            instance._cleared_ids = [instance.pk]
        else:
            instance._cleared_ids = list(instance.andinists.values_list("pk", flat=True))
        return
    if action not in ("post_add", "post_remove", "post_clear"):
        return
    if reverse:
        # instance is an Andinist; its own counters changed.
        refresh_andinists([instance.pk])
    elif action == "post_clear":
        refresh_andinists(getattr(instance, "_cleared_ids", []))
    else:
        refresh_andinists(pk_set or [])


# --- Route --------------------------------------------------------------

@receiver(pre_save, sender=Route)
def route_remember_old_mountain(sender, instance, **kwargs):
    instance._old_mountain_id = (
        Route.objects.filter(pk=instance.pk).values_list("mountain_id", flat=True).first()
        if instance.pk
        else None
    )


@receiver(post_save, sender=Route)
def route_saved(sender, instance, raw=False, **kwargs):
    if raw:
        return
    if instance.mountain_id is not None:
        refresh_mountain(instance.mountain_id)
    old_mountain_id = getattr(instance, "_old_mountain_id", None)
    if old_mountain_id and old_mountain_id != instance.mountain_id:
        refresh_mountain(old_mountain_id)


@receiver(post_delete, sender=Route)
def route_deleted(sender, instance, **kwargs):
    if instance.mountain_id is not None:
        refresh_mountain(instance.mountain_id)
