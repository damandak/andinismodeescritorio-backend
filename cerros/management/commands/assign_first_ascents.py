"""
Recalculate every derived field that depends on ascents.

    python manage.py assign_first_ascents --dry-run   # show what would change
    python manage.py assign_first_ascents             # apply the changes

Run it once after deploying the signals in cerros/signals.py, to fix the
values that went stale before them. It is safe to run again at any time.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from cerros.derived import (
    compute_andinist_counts,
    compute_mountain_ascended,
    compute_mountain_first_ascent,
    compute_route_first_ascent,
)
from cerros.models import Andinist, Mountain, Route


def _id(obj):
    return obj.pk if obj is not None else None


class Command(BaseCommand):
    help = "Recalculate first ascents, 'ascended' and andinist counters from the ascents."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List the changes without writing them.",
        )

    def handle(self, *args, dry_run=False, **options):
        self.verbosity = options.get("verbosity", 1)
        changes = {"routes": 0, "mountains": 0, "andinists": 0}

        with transaction.atomic():
            for route in Route.objects.select_related("mountain__prefix").iterator():
                new_first = _id(compute_route_first_ascent(route))
                if new_first != route.first_ascent_id:
                    changes["routes"] += 1
                    self._report(dry_run, f"Ruta {route.pk} ({route}): primer ascenso {route.first_ascent_id} -> {new_first}")
                    if not dry_run:
                        Route.objects.filter(pk=route.pk).update(first_ascent_id=new_first)

            for mountain in Mountain.objects.select_related("prefix").iterator():
                new_first = _id(compute_mountain_first_ascent(mountain))
                new_ascended = compute_mountain_ascended(mountain)
                if new_first != mountain.first_absolute_id or new_ascended != mountain.ascended:
                    changes["mountains"] += 1
                    self._report(
                        dry_run,
                        f"Cerro {mountain.pk} ({mountain}): primer ascenso "
                        f"{mountain.first_absolute_id} -> {new_first}, "
                        f"ascendido {mountain.ascended} -> {new_ascended}",
                    )
                    if not dry_run:
                        Mountain.objects.filter(pk=mountain.pk).update(
                            first_absolute_id=new_first, ascended=new_ascended
                        )

            for andinist in Andinist.objects.iterator():
                counts = compute_andinist_counts(andinist)
                current = {field: getattr(andinist, field) for field in counts}
                if counts != current:
                    changes["andinists"] += 1
                    self._report(dry_run, f"Andinista {andinist.pk} ({andinist}): {current} -> {counts}")
                    if not dry_run:
                        Andinist.objects.filter(pk=andinist.pk).update(**counts)

        verb = "Cambiarían" if dry_run else "Actualizados"
        self.stdout.write(self.style.SUCCESS(
            f"{verb}: {changes['routes']} rutas, {changes['mountains']} cerros, "
            f"{changes['andinists']} andinistas."
        ))

    def _report(self, dry_run, line):
        if dry_run or self.verbosity > 1:
            self.stdout.write(line)
