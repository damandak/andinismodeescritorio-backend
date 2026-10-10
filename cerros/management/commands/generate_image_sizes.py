"""
Create the thumbnail sizes (cover, small, medium) and record the size of
every photo that is missing any of them.

    python manage.py generate_image_sizes --dry-run     # how many need work
    python manage.py generate_image_sizes               # do it
    python manage.py generate_image_sizes --force       # redo all of them
    python manage.py generate_image_sizes --list-orphans

Run it once after deploying the migration that adds the "medium" size. It is
safe to stop and run again: photos already done are skipped.

--list-orphans only lists files in media/images that no Image record uses
(old thumbnails left behind by earlier versions) and their total size. It
deletes nothing.
"""
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from cerros.models import Image

FILE_FIELDS = ("image", "tb_item_cover", "tb_small", "tb_medium")


class Command(BaseCommand):
    help = "Generate missing thumbnail sizes for existing photos."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Only count, change nothing.")
        parser.add_argument("--force", action="store_true", help="Regenerate every photo.")
        parser.add_argument(
            "--list-orphans", action="store_true", help="List unused files in media/images."
        )

    def handle(self, *args, dry_run=False, force=False, list_orphans=False, **options):
        if list_orphans:
            return self.list_orphans()

        done = skipped = failed = 0
        todo = [img for img in Image.objects.order_by("pk") if force or img.missing_variants()]
        self.stdout.write(f"{len(todo)} de {Image.objects.count()} fotos necesitan tamaños nuevos.")
        if dry_run:
            return

        for img in todo:
            if not img.image or not img.image.storage.exists(img.image.name):
                skipped += 1
                self.stderr.write(f"  Imagen {img.pk} ({img}): falta el archivo original, se omite.")
                continue
            try:
                img.generate_variants()
                img.save(update_fields=["tb_item_cover", "tb_small", "tb_medium", "width", "height"])
                done += 1
                self.stdout.write(f"  {img.pk} {img}: {img.width}x{img.height}")
            except Exception as exc:  # keep going with the rest
                failed += 1
                self.stderr.write(f"  Imagen {img.pk} ({img}): error: {exc}")

        self.stdout.write(self.style.SUCCESS(
            f"Listo: {done} generadas, {skipped} sin archivo original, {failed} con error."
        ))

    def list_orphans(self):
        folder = os.path.join(settings.MEDIA_ROOT, "images")
        used = set()
        for row in Image.objects.values_list(*FILE_FIELDS):
            used.update(os.path.basename(name) for name in row if name)
        orphans = [
            name for name in sorted(os.listdir(folder))
            if os.path.isfile(os.path.join(folder, name)) and name not in used
        ]
        total = sum(os.path.getsize(os.path.join(folder, n)) for n in orphans)
        for name in orphans:
            self.stdout.write(f"  {name}")
        self.stdout.write(
            f"{len(orphans)} archivos sin uso en {folder}, {total / 1_048_576:.1f} MB. "
            "No se borró nada."
        )
