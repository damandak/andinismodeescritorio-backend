"""Internal change history (django-simple-history), viewable in the admin
("Historial" on each record). Not shown on the site."""
from simple_history import models as simple_history


class HistoricalRecords(simple_history.HistoricalRecords):
    """simple_history's HistoricalRecords, fixed for changes made from the
    other side of a many-to-many (e.g. `andinist.ascent_set.add(ascent)`):
    the change is recorded on each affected ascent, instead of failing while
    trying to record the andinist with the ascent's settings."""

    def m2m_changed(self, instance, action, attr, pk_set, reverse, model=None, **kwargs):
        if not reverse:
            return super().m2m_changed(instance, action, attr, pk_set, reverse, **kwargs)
        if action in ("post_add", "post_remove") and pk_set and model is not None:
            for obj in model.objects.filter(pk__in=pk_set):
                super().m2m_changed(obj, action, attr, pk_set, False, **kwargs)
        # post_clear from the other side: the ascents affected are no longer known.
