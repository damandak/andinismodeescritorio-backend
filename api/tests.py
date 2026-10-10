import datetime

from django.test import TestCase

from cerros.models import Andinist, Ascent, Mountain, MountainPrefix, Route


class SearchTests(TestCase):
    """Search ignores accents and case, and every word must match some field."""

    @classmethod
    def setUpTestData(cls):
        cerro = MountainPrefix.objects.create(prefix="Cerro")
        volcan = MountainPrefix.objects.create(prefix="Volcán")
        cls.plomo = Mountain.objects.create(prefix=cerro, name="El Plomo", altitude_igm=5424)
        cls.sanjose = Mountain.objects.create(prefix=volcan, name="San José", altitude_igm=5856)
        route = Route.objects.create(name="Glaciar Iver", mountain=cls.plomo)
        ascent = Ascent.objects.create(name="Primera", route=route, date=datetime.date(1945, 1, 1))
        ascent.andinists.add(Andinist.objects.create(name="Héctor", surname="Palominos"))

    def names(self, url, search):
        response = self.client.get(url, {"search": search})
        self.assertEqual(response.status_code, 200)
        return [r.get("name") or r.get("fullname") for r in response.json()["results"]]

    def test_accents_and_case_are_ignored(self):
        for term in ["Volcán", "volcan", "VOLCAN", "José", "jose"]:
            with self.subTest(term=term):
                self.assertEqual(self.names("/djangoapi/mountains/", term), ["San José"])

    def test_prefix_and_name_together(self):
        self.assertEqual(self.names("/djangoapi/mountains/", "Cerro El Plomo"), ["El Plomo"])

    def test_every_word_must_match(self):
        self.assertEqual(self.names("/djangoapi/mountains/", "Cerro San José"), [])

    def test_numbers_still_match(self):
        self.assertEqual(self.names("/djangoapi/mountains/", "5424"), ["El Plomo"])

    def test_tables(self):
        self.assertEqual(self.names("/djangoapi/route/table/", "plomo glaciar"), ["Glaciar Iver"])
        self.assertEqual(self.names("/djangoapi/ascent/table/", "hector 1945"), ["Primera"])
        self.assertEqual(self.names("/djangoapi/andinist/table/", "HECTOR"), ["Héctor Palominos"])


class NomenclaturaTests(TestCase):
    """/mountain/<id>/nomenclatura/ returns the summit linked to that mountain."""

    @classmethod
    def setUpTestData(cls):
        from cerros.models import IGMMap, NomenclaturaSummit

        igm = IGMMap.objects.create(name="Juncal", file_id="x")
        cls.decoy = NomenclaturaSummit.objects.create(
            pk=5000, id_nomenclatura="A", cod_revision="1", name="Otro cerro", igm_rectangle=igm
        )
        cls.summit = NomenclaturaSummit.objects.create(
            id_nomenclatura="B", cod_revision="1", name="Cerro Correcto", igm_rectangle=igm
        )
        prefix = MountainPrefix.objects.create(prefix="Cerro")
        # Same id as the decoy summit, linked to the other one.
        cls.linked = Mountain.objects.create(
            pk=cls.decoy.pk, prefix=prefix, name="Correcto", nomenclatura_mountain=cls.summit
        )
        cls.unlinked = Mountain.objects.create(prefix=prefix, name="Sin vínculo")

    def test_returns_the_linked_summit(self):
        response = self.client.get(f"/djangoapi/mountain/{self.linked.pk}/nomenclatura/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "Cerro Correcto")
        self.assertEqual(response.json()["igm_rectangle_name"], "Juncal")

    def test_404_when_not_linked_or_missing(self):
        for pk in (self.unlinked.pk, 999999):
            response = self.client.get(f"/djangoapi/mountain/{pk}/nomenclatura/")
            self.assertEqual(response.status_code, 404)


class ApiRobustnessTests(TestCase):
    """Lists are complete, bad parameters don't produce 500s."""

    @classmethod
    def setUpTestData(cls):
        prefix = MountainPrefix.objects.create(prefix="Cerro")
        cls.mountain = Mountain.objects.create(prefix=prefix, name="Grande", altitude_igm=5000)
        Mountain.objects.create(prefix=prefix, name="Sin altura")
        Mountain.objects.create(prefix=prefix, name="Chico", altitude_igm=3000)
        for i in range(12):
            Route.objects.create(name=f"Ruta {i:02d}", mountain=cls.mountain)
        route = Route.objects.get(name="Ruta 00")
        first = Ascent.objects.create(
            name="Primera ascensión", route=route, date=datetime.date(1910, 1, 20)
        )
        first.andinists.add(Andinist.objects.create(name="Federico", surname="Reichert"))

    def test_short_lists_are_not_cut_at_ten(self):
        data = self.client.get(f"/djangoapi/mountain/{self.mountain.pk}/routes/").json()
        self.assertEqual(data["count"], 12)
        self.assertEqual(len(data["results"]), 12)

    def test_invalid_ordering_is_ignored(self):
        response = self.client.get("/djangoapi/mountains/", {"ordering": "campo_inexistente"})
        self.assertEqual(response.status_code, 200)
        response = self.client.get("/djangoapi/mountains/", {"ordering": "image_set__author__surname"})
        self.assertEqual(response.status_code, 200)

    def test_empty_altitude_sorts_last_both_ways(self):
        for ordering, expected in [("-altitude", ["Grande", "Chico", "Sin altura"]),
                                   ("altitude", ["Chico", "Grande", "Sin altura"])]:
            data = self.client.get("/djangoapi/mountains/", {"ordering": ordering}).json()
            self.assertEqual([m["name"] for m in data["results"]], expected)

    def test_missing_records_give_404(self):
        for url in ["/djangoapi/mountain/999999/references/",
                    "/djangoapi/route/999999/references/",
                    "/djangoapi/ascent/999999/references/",
                    "/djangoapi/andinist/999999/references/",
                    "/djangoapi/mountains/?nearby=999999",
                    "/djangoapi/mountains/?nearby=abc"]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_mountain_includes_first_ascent_name(self):
        data = self.client.get(f"/djangoapi/mountain/{self.mountain.pk}/").json()
        self.assertEqual(data["first_absolute_name"], "Primera ascensión")
        self.assertEqual(data["first_absolute_team"][0][1], "Federico Reichert")


class SitemapTests(TestCase):
    def test_lists_public_ids(self):
        prefix = MountainPrefix.objects.create(prefix="Cerro")
        mountain = Mountain.objects.create(prefix=prefix, name="Plomo")
        route = Route.objects.create(name="Normal", mountain=mountain)
        ascent = Ascent.objects.create(name="Primera", route=route, date=datetime.date(1910, 1, 1))
        climber = Andinist.objects.create(name="Con", surname="Ascensos")
        ascent.andinists.add(climber)
        Andinist.objects.create(name="Sin", surname="Ascensos")

        data = self.client.get("/djangoapi/sitemap/").json()

        self.assertEqual(data["mountains"], [mountain.pk])
        self.assertEqual(data["routes"], [route.pk])
        self.assertEqual(data["ascents"], [ascent.pk])
        self.assertEqual(data["andinists"], [climber.pk])


class MapListTests(TestCase):
    def test_full_list_is_cacheable_and_nearby_has_ascended(self):
        prefix = MountainPrefix.objects.create(prefix="Cerro")
        a = Mountain.objects.create(prefix=prefix, name="A", latitude=-33.0, longitude=-70.0)
        Mountain.objects.create(prefix=prefix, name="B", latitude=-33.01, longitude=-70.01)

        full = self.client.get("/djangoapi/mountains/", {"no_pagination": ""})
        self.assertEqual(full["Cache-Control"], "public, max-age=600")

        paged = self.client.get("/djangoapi/mountains/")
        self.assertNotIn("max-age", paged.get("Cache-Control", ""))

        nearby = self.client.get("/djangoapi/mountains/", {"nearby": a.pk, "no_pagination": ""}).json()
        self.assertEqual([m["name"] for m in nearby], ["B"])
        self.assertIn("ascended", nearby[0])
