"""
Country and region of each mountain according to its coordinates.

    python manage.py asignar_ubicacion --dry-run    # see what it would do (writes nothing)
    python manage.py asignar_ubicacion              # apply

Mountains at least 2 km (--margen) from every limit and with no country/region
get them assigned ("Asignada por coordenadas"). Nearer ones are left
"Por completar: cerca de un límite", with the suggestion in their admin page.
Data already loaded is never changed, only compared ("Coincide" / "No calza").
Rules in cerros/location.py, maps in cerros/geo.py.

A CSV with every mountain (opens in Excel) is written in both modes.
"""
import csv
from collections import Counter
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from cerros import geo
from cerros.location import Lookups, apply, evaluate
from cerros.models import Mountain


class Command(BaseCommand):
    help = "Asigna país y región por coordenadas a los cerros que no los tienen (lejos de los límites)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Muestra lo que haría, sin escribir.")
        parser.add_argument(
            "--margen", type=int, default=geo.DEFAULT_MARGIN,
            help="Distancia mínima a cualquier límite, en metros, para asignar sola (por defecto 2000).",
        )
        parser.add_argument("--csv", dest="csv_path", default=None, help="Archivo CSV de salida (por defecto ubicacion-AAAA-MM-DD.csv).")
        parser.add_argument(
            "--rehacer-revisados", action="store_true",
            help="Recalcula también los marcados «Revisada a mano» (sin cambiar su país ni región).",
        )

    def handle(self, *args, dry_run=False, margen=geo.DEFAULT_MARGIN, csv_path=None, rehacer_revisados=False, **options):
        path = csv_path or f"ubicacion-{date.today().isoformat()}.csv"
        lookups = Lookups()
        labels = dict(Mountain.LOCATION_STATUS_CHOICES)
        counts = Counter()
        assigned = 0
        rows = []

        mountains = (
            Mountain.objects.select_related("prefix")
            .prefetch_related("countries", "regions")
            .order_by("pk")
        )
        with transaction.atomic():
            for mountain in mountains:
                result = evaluate(mountain, margen, lookups, keep_reviewed=not rehacer_revisados)
                counts[result.status] += 1
                added = [x.name for x in (result.add_country, result.add_region) if x is not None]
                assigned += bool(added)
                if not dry_run:
                    apply(mountain, result)
                rows.append([
                    mountain.pk, str(mountain), mountain.latitude, mountain.longitude, labels[result.status],
                    ", ".join(c.name for c in mountain.countries.all()),
                    ", ".join(r.name for r in mountain.regions.all()),
                    getattr(result.suggested_country, "name", ""), getattr(result.suggested_region, "name", ""),
                    result.distance if result.distance is not None else "", " + ".join(added), result.note,
                ])

        with open(path, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.writer(fh, delimiter=";")
            writer.writerow([
                "id", "cerro", "latitud", "longitud", "estado", "país cargado antes", "región cargada antes",
                "país sugerido", "región sugerida", "distancia al límite (m)",
                "asignado ahora" if not dry_run else "se asignaría", "detalle",
            ])
            writer.writerows(rows)

        verb = "Se asignarían" if dry_run else "Se asignaron"
        self.stdout.write(f"{len(rows)} cerros revisados con margen de {margen} m. {verb} país/región a {assigned}.")
        for status, label in Mountain.LOCATION_STATUS_CHOICES:
            if counts[status]:
                self.stdout.write(f"  {label}: {counts[status]}")
        self.stdout.write(f"Detalle en {path}" + (" (nada se escribió en la base)." if dry_run else "."))
