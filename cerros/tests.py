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


class AdminSecurityTests(TestCase):
    """Failed admin logins are limited per user and IP (django-axes)."""

    LOGIN = "/admin/login/?next=/admin/"

    @classmethod
    def setUpTestData(cls):
        from cerros.models import CustomUser

        cls.user = CustomUser.objects.create_superuser("editor@example.com", "clave-correcta-123")

    def login(self, password, **extra):
        return self.client.post(
            self.LOGIN, {"username": "editor@example.com", "password": password}, **extra
        )

    def test_blocked_after_five_failures_even_with_right_password(self):
        for _ in range(4):
            self.assertEqual(self.login("mala").status_code, 200)  # form with error
        self.assertEqual(self.login("mala").status_code, 429)  # 5th: blocked
        response = self.login("clave-correcta-123")
        self.assertEqual(response.status_code, 429)
        self.assertContains(response, "Acceso bloqueado", status_code=429)

    def test_other_ip_is_not_blocked(self):
        for _ in range(5):
            self.login("mala", HTTP_X_FORWARDED_FOR="203.0.113.7")
        self.assertEqual(self.login("mala", HTTP_X_FORWARDED_FOR="203.0.113.7").status_code, 429)
        ok = self.login("clave-correcta-123", HTTP_X_FORWARDED_FOR="198.51.100.20")
        self.assertEqual(ok.status_code, 302)

    def test_success_resets_the_count(self):
        for _ in range(4):
            self.login("mala")
        self.assertEqual(self.login("clave-correcta-123").status_code, 302)
        self.client.logout()
        for _ in range(4):
            self.login("mala")
        self.assertEqual(self.login("clave-correcta-123").status_code, 302)

    def test_admin_in_spanish_and_chilean_time(self):
        from django.conf import settings

        self.assertEqual(settings.TIME_ZONE, "America/Santiago")
        self.assertContains(self.client.get(self.LOGIN), "Contraseña")


class SecurityHelpersTests(TestCase):
    def request(self, remote, forwarded=None):
        from django.test import RequestFactory

        extra = {"REMOTE_ADDR": remote}
        if forwarded is not None:
            extra["HTTP_X_FORWARDED_FOR"] = forwarded
        return RequestFactory().get("/", **extra)

    def test_client_ip(self):
        from adeback.security import client_ip

        # Behind nginx: the last address is the one nginx saw.
        self.assertEqual(client_ip(self.request("127.0.0.1", "1.1.1.1, 203.0.113.7")), "203.0.113.7")
        self.assertEqual(client_ip(self.request("", "203.0.113.7")), "203.0.113.7")  # unix socket
        # Straight from the internet: the header is ignored (could be made up).
        self.assertEqual(client_ip(self.request("198.51.100.1", "203.0.113.7")), "198.51.100.1")
        self.assertEqual(client_ip(self.request("127.0.0.1")), "127.0.0.1")

    def test_https_origins(self):
        from adeback.security import https_origins

        self.assertEqual(
            https_origins(["andinismodeescritorio.cl", ".www.andinismodeescritorio.cl", "localhost", ""]),
            ["https://andinismodeescritorio.cl", "https://www.andinismodeescritorio.cl"],
        )

    def test_api_ignores_login_headers(self):
        """The public API doesn't try to log anyone in (no 401 on a bad header)."""
        response = self.client.get("/djangoapi/countries/", HTTP_AUTHORIZATION="Basic Zm9vOmJhcg==")
        self.assertEqual(response.status_code, 200)


class UnknownDateTests(TestCase):
    """Ascents without a date (they used to be stored as 0001-01-01)."""

    def setUp(self):
        prefix = MountainPrefix.objects.create(prefix="Cerro")
        self.mountain = Mountain.objects.create(prefix=prefix, name="Sin Fecha")
        self.route = Route.objects.create(name="Normal", mountain=self.mountain)

    def test_placeholder_dates_become_empty(self):
        import importlib

        from django.apps import apps

        old = Ascent.objects.create(name="Comodín", route=self.route, date=datetime.date(1, 1, 1))
        real = Ascent.objects.create(name="Real", route=self.route, date=datetime.date(1950, 2, 1))
        migration = importlib.import_module("cerros.migrations.0030_ascent_unknown_dates")
        migration.clear_placeholder_dates(apps, None)
        old.refresh_from_db()
        real.refresh_from_db()
        self.assertIsNone(old.date)
        self.assertEqual(real.date, datetime.date(1950, 2, 1))

    def test_undated_ascent_is_not_the_first_one(self):
        Ascent.objects.create(name="Sin fecha", route=self.route, date=None)
        dated = Ascent.objects.create(name="Con fecha", route=self.route, date=datetime.date(1960, 1, 1))
        self.mountain.refresh_from_db()
        self.route.refresh_from_db()
        self.assertEqual(self.mountain.first_absolute, dated)
        self.assertEqual(self.route.first_ascent, dated)

    def test_site_works_with_undated_ascents(self):
        ascent = Ascent.objects.create(name="Sin fecha", route=self.route, date=None)
        self.assertIn("sin fecha", str(ascent))
        self.assertIsNone(ascent.date_tostring())
        self.assertEqual(self.route.first_ascent_year(), "")
        for url in [f"/djangoapi/ascent/{ascent.pk}/", "/djangoapi/ascent/table/",
                    f"/djangoapi/mountain/{self.mountain.pk}/", f"/djangoapi/mountain/{self.mountain.pk}/ascents/",
                    f"/djangoapi/route/{self.route.pk}/", "/djangoapi/route/table/"]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
        self.assertIsNone(self.client.get(f"/djangoapi/ascent/{ascent.pk}/").json()["date_tostr"])


class GeoTests(TestCase):
    """Country and region from coordinates (cerros/geo.py)."""

    def test_known_places(self):
        from cerros import geo

        aconcagua = geo.suggest(-32.6532, -70.0109)
        self.assertEqual((aconcagua.place.country, aconcagua.place.region), ("Argentina", "Mendoza"))
        self.assertTrue(aconcagua.confident)

        plomo = geo.suggest(-33.2364, -70.2133)
        self.assertEqual(plomo.place.country, "Chile")
        self.assertIn("Metropolitana", plomo.place.region)
        self.assertTrue(plomo.confident)

        # Tupungato is on the border: never decided by the map.
        tupungato = geo.suggest(-33.3586, -69.7703)
        self.assertFalse(tupungato.confident)
        self.assertLess(tupungato.distance, 500)
        self.assertEqual(tupungato.limit, "Chile – Argentina")
        self.assertIn("Chile", [p.country for p in tupungato.across])

        self.assertIsNone(geo.suggest(-33.5, -76.0).place)  # Pacific Ocean

    def test_margin(self):
        from cerros import geo

        plomo = geo.suggest(-33.2364, -70.2133, margin=10_000)
        self.assertFalse(plomo.confident)  # ~6 km from the Valparaíso limit

    def test_names(self):
        from cerros import geo

        self.assertTrue(geo.same_name("Metropolitana", "Región Metropolitana de Santiago"))
        self.assertTrue(geo.same_name("Biobío", "Región del Bío-Bío"))
        self.assertTrue(geo.same_name("O'Higgins", "Región del Libertador Bernardo O'Higgins"))
        self.assertTrue(geo.same_name("Aysén", "Región de Aysén del Gral.Ibañez del Campo"))
        self.assertFalse(geo.same_name("Los Ríos", "Región de Los Lagos"))


class LocationTests(TestCase):
    """Assigning and checking country/region (cerros/location.py, asignar_ubicacion)."""

    @classmethod
    def setUpTestData(cls):
        from cerros.models import Country, Region

        cls.chile = Country.objects.create(name="Chile")
        cls.argentina = Country.objects.create(name="Argentina")
        cls.rm = Region.objects.create(name="Metropolitana", country=cls.chile)
        cls.valpo = Region.objects.create(name="Valparaíso", country=cls.chile)
        cls.mendoza = Region.objects.create(name="Mendoza", country=cls.argentina)
        cls.prefix = MountainPrefix.objects.create(prefix="Cerro")

    def mountain(self, name, lat, lon, countries=(), regions=()):
        m = Mountain.objects.create(prefix=self.prefix, name=name, latitude=lat, longitude=lon)
        m.countries.set(countries)
        m.regions.set(regions)
        return m

    def run_command(self, *args):
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "out.csv")
            out = StringIO()
            call_command("asignar_ubicacion", *args, "--csv", path, stdout=out)
            with open(path, encoding="utf-8-sig") as fh:
                return out.getvalue(), fh.read()

    def test_far_from_limits_is_assigned_and_marked(self):
        plomo = self.mountain("Plomo", -33.2364, -70.2133)
        aconcagua = self.mountain("Aconcagua", -32.6532, -70.0109)
        self.run_command()
        for m, country, region in [(plomo, self.chile, self.rm), (aconcagua, self.argentina, self.mendoza)]:
            m.refresh_from_db()
            self.assertEqual(list(m.countries.all()), [country])
            self.assertEqual(list(m.regions.all()), [region])
            self.assertEqual(m.location_status, Mountain.LOCATION_AUTO)
        # A second run keeps the mark.
        self.run_command()
        plomo.refresh_from_db()
        self.assertEqual(plomo.location_status, Mountain.LOCATION_AUTO)

    def test_near_a_limit_is_only_suggested(self):
        tupungato = self.mountain("Tupungato", -33.3586, -69.7703)
        self.run_command()
        tupungato.refresh_from_db()
        self.assertEqual(tupungato.countries.count(), 0)
        self.assertEqual(tupungato.location_status, Mountain.LOCATION_TO_REVIEW)
        self.assertEqual(tupungato.suggested_country, self.argentina)
        self.assertEqual(tupungato.suggested_region, self.mendoza)
        self.assertIn("Chile – Argentina", tupungato.location_note)
        self.assertLess(tupungato.border_distance, 500)

    def test_loaded_data_is_never_changed(self):
        right = self.mountain("Bien", -33.2364, -70.2133, [self.chile], [self.rm])
        wrong = self.mountain("Mal", -32.6532, -70.0109, [self.chile], [self.rm])  # Aconcagua as Chile
        border = self.mountain("Frontera", -33.3586, -69.7703, [self.chile], [self.rm])  # either side is fine
        self.run_command()
        for m in (right, wrong, border):
            m.refresh_from_db()
            self.assertEqual(list(m.countries.all()), [self.chile])
        self.assertEqual(right.location_status, Mountain.LOCATION_MATCH)
        self.assertEqual(wrong.location_status, Mountain.LOCATION_MISMATCH)
        self.assertEqual(border.location_status, Mountain.LOCATION_MATCH)

    def test_missing_region_is_completed(self):
        m = self.mountain("Solo país", -33.2364, -70.2133, [self.chile])
        self.run_command()
        m.refresh_from_db()
        self.assertEqual(list(m.regions.all()), [self.rm])

    def test_dry_run_writes_nothing(self):
        m = self.mountain("Plomo", -33.2364, -70.2133)
        sin = Mountain.objects.create(prefix=self.prefix, name="Sin coordenadas")
        out, csv_text = self.run_command("--dry-run")
        m.refresh_from_db()
        self.assertEqual(m.countries.count(), 0)
        self.assertEqual(m.location_status, Mountain.LOCATION_UNCHECKED)
        self.assertIn("Se asignarían país/región a 1", out)
        self.assertIn("Plomo", csv_text)
        self.assertIn("Sin coordenadas", csv_text)

    def test_reviewed_is_kept(self):
        m = self.mountain("Revisado", -32.6532, -70.0109, [self.chile], [self.rm])
        Mountain.objects.filter(pk=m.pk).update(location_status=Mountain.LOCATION_REVIEWED)
        self.run_command()
        m.refresh_from_db()
        self.assertEqual(m.location_status, Mountain.LOCATION_REVIEWED)


class LocationAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from cerros.models import Country, CustomUser, Region

        cls.user = CustomUser.objects.create_superuser("editor@example.com", "clave-correcta-123")
        cls.chile = Country.objects.create(name="Chile")
        cls.rm = Region.objects.create(name="Metropolitana", country=cls.chile)
        cls.prefix = MountainPrefix.objects.create(prefix="Cerro")

    def setUp(self):
        self.client.force_login(self.user)

    def test_panel_filters_and_reviewing(self):
        from cerros import location

        m = Mountain.objects.create(prefix=self.prefix, name="Tupungato", latitude=-33.3586, longitude=-69.7703)
        location.check_one(m)
        page = self.client.get(f"/admin/cerros/mountain/{m.pk}/change/")
        self.assertContains(page, "Por completar: cerca de un límite")
        self.assertContains(page, "Chile – Argentina")

        listing = self.client.get("/admin/cerros/mountain/", {"location_status__exact": Mountain.LOCATION_TO_REVIEW})
        self.assertContains(listing, "Tupungato")
        self.assertContains(self.client.get("/admin/cerros/mountain/", {"pais": "sin"}), "Tupungato")
        self.assertNotContains(self.client.get("/admin/cerros/mountain/", {"pais": "con"}), "Tupungato")

        # The editor sets country and region by hand: marked as reviewed.
        data = {
            "prefix": self.prefix.pk, "name": "Tupungato", "latitude": "-33.358600", "longitude": "-69.770300",
            "countries": [self.chile.pk], "regions": [self.rm.pk], "main_altitude_source": 0,
            "location_status": Mountain.LOCATION_TO_REVIEW, "_save": "Guardar",
        }
        response = self.client.post(f"/admin/cerros/mountain/{m.pk}/change/", data)
        self.assertEqual(response.status_code, 302, getattr(response, "context", None) and response.context["adminform"].form.errors)
        m.refresh_from_db()
        self.assertEqual(m.location_status, Mountain.LOCATION_REVIEWED)

    def test_new_mountain_is_checked_on_save(self):
        data = {
            "prefix": self.prefix.pk, "name": "Nuevo", "latitude": "-33.236400", "longitude": "-70.213300",
            "main_altitude_source": 0, "location_status": Mountain.LOCATION_UNCHECKED, "_save": "Guardar",
        }
        response = self.client.post("/admin/cerros/mountain/add/", data)
        self.assertEqual(response.status_code, 302, getattr(response, "context", None) and response.context["adminform"].form.errors)
        m = Mountain.objects.get(name="Nuevo")
        self.assertEqual(m.location_status, Mountain.LOCATION_AUTO)
        self.assertEqual(list(m.countries.all()), [self.chile])

    def test_ascent_filter_without_date(self):
        mountain = Mountain.objects.create(prefix=self.prefix, name="X")
        route = Route.objects.create(name="R", mountain=mountain)
        Ascent.objects.create(name="Undated one", route=route, date=None)
        Ascent.objects.create(name="Dated one", route=route, date=datetime.date(1950, 1, 1))
        page = self.client.get("/admin/cerros/ascent/", {"fecha": "sin"})
        self.assertContains(page, "Undated one")
        self.assertNotContains(page, "Dated one")
