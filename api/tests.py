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
