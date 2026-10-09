"""
Derived (denormalized) fields that depend on ascents.

These values are stored on Mountain, Route and Andinist so the API can list
and sort them cheaply, but they must be recalculated whenever an ascent is
created, edited or deleted. The compute_* functions hold the rules; the
refresh_* functions write the result with a queryset .update(), so they do
not call save() and do not trigger any other signal.

Rules
- A mountain's first ascent (first_absolute) is the oldest completed ascent
  marked "is_first_ascent" on any of its routes; if none is marked, the
  oldest completed ascent. None if the mountain has an unregistered sport
  ascent (someone climbed it before the first one we have on record).
- A route's first ascent is the oldest completed ascent marked "new_route";
  if none is marked, the oldest completed ascent. Same unregistered rule.
- Ascents without a date sort after dated ones.
- A mountain is "ascended" if it has an unregistered ascent (sport or not)
  or at least one completed ascent.
- Andinist counters count the ascents they are listed in (not as support).
"""
from django.apps import apps
from django.db.models import F


def _ascent_model():
    return apps.get_model("cerros", "Ascent")


def _oldest_first(qs):
    return qs.order_by(F("date").asc(nulls_last=True), "id")


def compute_mountain_first_ascent(mountain):
    if mountain.pk is None or mountain.unregistered_sport_ascent:
        return None
    done = _ascent_model().objects.filter(route__mountain=mountain, completed=True)
    flagged = _oldest_first(done.filter(is_first_ascent=True)).first()
    return flagged or _oldest_first(done).first()


def compute_mountain_ascended(mountain):
    if mountain.unregistered_sport_ascent or mountain.unregistered_non_sport_ascent:
        return True
    if mountain.pk is None:
        return False
    return (
        _ascent_model()
        .objects.filter(route__mountain=mountain, completed=True)
        .exists()
    )


def compute_route_first_ascent(route):
    if route.pk is None or route.unregistered_sport_ascent:
        return None
    done = _ascent_model().objects.filter(route=route, completed=True)
    flagged = _oldest_first(done.filter(new_route=True)).first()
    return flagged or _oldest_first(done).first()


def compute_andinist_counts(andinist):
    if andinist.pk is None:
        return {"ascent_count": 0, "new_routes_count": 0, "first_ascent_count": 0}
    ascents = _ascent_model().objects.filter(andinists=andinist)
    return {
        "ascent_count": ascents.count(),
        "new_routes_count": ascents.filter(new_route=True).count(),
        "first_ascent_count": ascents.filter(is_first_ascent=True).count(),
    }


def refresh_mountain(mountain_id):
    Mountain = apps.get_model("cerros", "Mountain")
    mountain = Mountain.objects.filter(pk=mountain_id).first()
    if mountain is None:
        return
    first = compute_mountain_first_ascent(mountain)
    Mountain.objects.filter(pk=mountain_id).update(
        first_absolute=first,
        ascended=compute_mountain_ascended(mountain),
    )


def refresh_route(route_id):
    Route = apps.get_model("cerros", "Route")
    route = Route.objects.filter(pk=route_id).first()
    if route is None:
        return
    Route.objects.filter(pk=route_id).update(
        first_ascent=compute_route_first_ascent(route)
    )


def refresh_andinists(andinist_ids):
    Andinist = apps.get_model("cerros", "Andinist")
    for andinist in Andinist.objects.filter(pk__in=set(andinist_ids)):
        Andinist.objects.filter(pk=andinist.pk).update(
            **compute_andinist_counts(andinist)
        )
