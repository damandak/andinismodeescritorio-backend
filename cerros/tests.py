import datetime
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from cerros.models import Andinist, Ascent, Mountain, MountainPrefix, Route


class DerivedFieldsTests(TestCase):
    """First ascents, 'ascended' and andinist counters follow the ascents."""

    def setUp(self):
        prefix = MountainPrefix.objects.create(prefix="Punta")
        self.mountain = Mountain.objects.create(prefix=prefix, name="Patricia")
        self.route = Route.objects.create(name="Glaciar Juncal Sur", mountain=self.mountain)
        self.palominos = Andinist.objects.create(name="Héctor", surname="Palominos")
        self.gomez = Andinist.objects.create(name="Miguel", surname="Gómez")

    def refresh(self):
        self.mountain.refresh_from_db()
        self.route.refresh_from_db()
        self.palominos.refresh_from_db()
        self.gomez.refresh_from_db()

    def ascent(self, year, **kwargs):
        return Ascent.objects.create(
            name=f"Ascenso {year}", route=self.route, date=datetime.date(year, 1, 1), **kwargs
        )

    def test_new_ascent_updates_mountain_and_route(self):
        self.assertIsNone(self.mountain.first_absolute)
        self.assertFalse(self.mountain.ascended)

        first = self.ascent(1963)
        self.refresh()

        self.assertEqual(self.mountain.first_absolute, first)
        self.assertTrue(self.mountain.ascended)
        self.assertEqual(self.route.first_ascent, first)

    def test_oldest_wins_unless_one_is_flagged(self):
        self.ascent(2023)
        older = self.ascent(1963)
        self.refresh()
        self.assertEqual(self.mountain.first_absolute, older)

        flagged = self.ascent(1990, is_first_ascent=True, new_route=True)
        self.refresh()
        self.assertEqual(self.mountain.first_absolute, flagged)
        self.assertEqual(self.route.first_ascent, flagged)

    def test_failed_attempts_are_not_first_ascents(self):
        self.ascent(1950, completed=False)
        self.refresh()
        self.assertIsNone(self.mountain.first_absolute)
        self.assertFalse(self.mountain.ascended)

    def test_deleting_the_only_ascent_resets_fields(self):
        only = self.ascent(1963)
        only.andinists.add(self.palominos)
        only.delete()
        self.refresh()

        self.assertIsNone(self.mountain.first_absolute)
        self.assertFalse(self.mountain.ascended)
        self.assertIsNone(self.route.first_ascent)
        self.assertEqual(self.palominos.ascent_count, 0)

    def test_moving_an_ascent_updates_both_routes(self):
        other_route = Route.objects.create(name="Otra", mountain=self.mountain)
        moved = self.ascent(1963)
        moved.route = other_route
        moved.save()
        self.refresh()
        other_route.refresh_from_db()

        self.assertIsNone(self.route.first_ascent)
        self.assertEqual(other_route.first_ascent, moved)
        self.assertEqual(self.mountain.first_absolute, moved)

    def test_andinist_counters_follow_team_changes(self):
        first = self.ascent(1963, is_first_ascent=True)
        first.andinists.add(self.palominos, self.gomez)
        self.refresh()
        self.assertEqual(self.palominos.ascent_count, 1)
        self.assertEqual(self.palominos.first_ascent_count, 1)

        first.andinists.remove(self.gomez)
        self.refresh()
        self.assertEqual(self.gomez.ascent_count, 0)

        first.andinists.clear()
        self.refresh()
        self.assertEqual(self.palominos.ascent_count, 0)

        # Reverse side: andinist.ascent_set
        self.gomez.ascent_set.add(first)
        self.refresh()
        self.assertEqual(self.gomez.first_ascent_count, 1)

    def test_editing_flags_updates_counters(self):
        a = self.ascent(1963)
        a.andinists.add(self.palominos)
        a.new_route = True
        a.save()
        self.refresh()
        self.assertEqual(self.palominos.new_routes_count, 1)

    def test_unregistered_sport_ascent_means_no_known_first(self):
        self.ascent(1963)
        self.mountain.unregistered_sport_ascent = True
        self.mountain.save()
        self.refresh()
        self.assertIsNone(self.mountain.first_absolute)
        self.assertTrue(self.mountain.ascended)

    def test_saving_mountain_keeps_altitude_when_source_is_empty(self):
        self.mountain.altitude = 4450
        self.mountain.main_altitude_source = Mountain.IGM  # altitude_igm is empty
        self.mountain.save()
        self.mountain.refresh_from_db()
        self.assertEqual(self.mountain.altitude, 4450)

    def test_recalculation_command_fixes_stale_rows(self):
        first = self.ascent(1963)
        first.andinists.add(self.palominos)
        # Simulate data saved before the signals existed.
        Mountain.objects.filter(pk=self.mountain.pk).update(first_absolute=None, ascended=False)
        Route.objects.filter(pk=self.route.pk).update(first_ascent=None)
        Andinist.objects.filter(pk=self.palominos.pk).update(ascent_count=0)

        out = StringIO()
        call_command("assign_first_ascents", "--dry-run", stdout=out)
        self.assertIn("1 rutas, 1 cerros, 1 andinistas", out.getvalue())
        self.refresh()
        self.assertIsNone(self.mountain.first_absolute)  # dry run wrote nothing

        call_command("assign_first_ascents", stdout=StringIO())
        self.refresh()
        self.assertEqual(self.mountain.first_absolute, first)
        self.assertTrue(self.mountain.ascended)
        self.assertEqual(self.route.first_ascent, first)
        self.assertEqual(self.palominos.ascent_count, 1)


import os
import shutil
import tempfile
from io import BytesIO

from django.core.files.base import ContentFile
from django.test import override_settings
from PIL import Image as PILImage

from cerros.models import Image


def _jpeg(size, color=(90, 120, 150), orientation=None):
    buffer = BytesIO()
    img = PILImage.new("RGB", size, color)
    exif = PILImage.Exif()
    if orientation:
        exif[0x0112] = orientation
    img.save(buffer, "JPEG", exif=exif.tobytes())
    return buffer.getvalue()


def _png_transparent(size):
    buffer = BytesIO()
    PILImage.new("RGBA", size, (255, 0, 0, 0)).save(buffer, "PNG")
    return buffer.getvalue()


class ImageVariantsTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media)
        self.override.enable()

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media, ignore_errors=True)

    def make(self, data, name="foto.jpg"):
        img = Image(name="Foto")
        img.image.save(name, ContentFile(data), save=False)
        img.save()
        return img

    def size(self, field_file):
        with PILImage.open(field_file.path) as im:
            return im.size

    def files(self):
        return sorted(os.listdir(os.path.join(self.media, "images")))

    def test_sizes_of_each_variant(self):
        img = self.make(_jpeg((3000, 2000)))
        self.assertEqual((img.width, img.height), (3000, 2000))
        self.assertEqual(self.size(img.tb_item_cover), (600, 400))
        self.assertEqual(self.size(img.tb_small)[1], 100)
        self.assertEqual(self.size(img.tb_medium), (1600, 1067))

    def test_phone_photo_is_rotated(self):
        # Stored 3000x2000 with "rotate 90°" in EXIF: displayed portrait.
        img = self.make(_jpeg((3000, 2000), orientation=6))
        self.assertEqual((img.width, img.height), (2000, 3000))
        w, h = self.size(img.tb_medium)
        self.assertLess(w, h)

    def test_transparent_png_works(self):
        img = self.make(_png_transparent((800, 600)), name="logo.png")
        with PILImage.open(img.tb_item_cover.path) as im:
            self.assertEqual(im.mode, "RGB")
            self.assertEqual(im.getpixel((5, 5)), (255, 255, 255))

    def test_saving_again_does_not_regenerate(self):
        img = self.make(_jpeg((1200, 800)))
        before = self.files()
        img = Image.objects.get(pk=img.pk)
        img.description = "Otra descripción"
        img.save()
        self.assertEqual(self.files(), before)

    def test_replacing_the_photo_removes_old_thumbnails(self):
        img = self.make(_jpeg((1200, 800)))
        old_cover = img.tb_item_cover.name
        img = Image.objects.get(pk=img.pk)
        img.image.save("nueva.jpg", ContentFile(_jpeg((900, 900))), save=False)
        img.save()
        self.assertNotIn(os.path.basename(old_cover), self.files())
        self.assertEqual((img.width, img.height), (900, 900))

    def test_delete_keeps_original_removes_thumbnails(self):
        img = self.make(_jpeg((1200, 800)))
        original = os.path.basename(img.image.name)
        img.delete()
        self.assertEqual(self.files(), [original])

    def test_command_fills_missing_sizes(self):
        img = self.make(_jpeg((1200, 800)))
        Image.objects.filter(pk=img.pk).update(tb_medium=None, width=None, height=None)
        out = StringIO()
        call_command("generate_image_sizes", "--dry-run", stdout=out)
        self.assertIn("1 de 1", out.getvalue())
        call_command("generate_image_sizes", stdout=StringIO())
        img.refresh_from_db()
        self.assertTrue(img.tb_medium)
        self.assertEqual((img.width, img.height), (1200, 800))
