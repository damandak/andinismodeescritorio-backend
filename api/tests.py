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


class MountainTableTests(TestCase):
    def test_search_results_include_ascended(self):
        """The /cerros table shows "Ascendido" also while searching."""
        prefix = MountainPrefix.objects.create(prefix="Cerro")
        Mountain.objects.create(prefix=prefix, name="Plomo")

        for params in ({}, {"search": "plomo"}):
            with self.subTest(params=params):
                row = self.client.get("/djangoapi/mountains/", params).json()["results"][0]
                self.assertIn("ascended", row)


class ImagesBatchTests(TestCase):
    def test_several_images_in_one_request(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from io import BytesIO
        from PIL import Image as PILImage
        from django.test import override_settings
        import tempfile

        from cerros.models import Image

        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            def photo(name):
                buf = BytesIO()
                PILImage.new("RGB", (40, 30), "white").save(buf, "JPEG")
                return Image.objects.create(
                    name=name, image=SimpleUploadedFile(f"{name}.jpg", buf.getvalue())
                )

            a, b = photo("a"), photo("b")
            with self.assertNumQueries(1):
                data = self.client.get("/djangoapi/images/", {"ids": f"{b.pk},{a.pk},999999,x"}).json()
            self.assertEqual([r["id"] for r in data["results"]], [a.pk, b.pk])
            self.assertIn("tb_item_cover", data["results"][0])

            empty = self.client.get("/djangoapi/images/").json()
            self.assertEqual(empty["results"], [])


class AccountTests(TestCase):
    """Signup, login, profile and andinist claims through the site's JSON API,
    with CSRF checks on (as the browser does it)."""

    API = "/djangoapi/_allauth/browser/v1"

    def setUp(self):
        from django.core.cache import cache
        from django.test import Client

        cache.clear()  # allauth's rate limits (e.g. one confirmation email per address every 3 min)
        self.c = Client(enforce_csrf_checks=True)
        self.c.get(self.API + "/auth/session")  # sets the CSRF cookie

    def send(self, method, url, data=None):
        import json

        return getattr(self.c, method)(
            url, json.dumps(data or {}), content_type="application/json",
            HTTP_X_CSRFTOKEN=self.c.cookies["csrftoken"].value,
        )

    def signup(self, **extra):
        data = {"email": "ana@example.com", "password": "una-clave-larga-123",
                "public_name": "Ana Pérez", "accept_privacy": True, **extra}
        return self.send("post", self.API + "/auth/signup", data)

    def test_signup_login_logout(self):
        from django.core import mail

        from cerros.models import CustomUser

        with self.captureOnCommitCallbacks(execute=True):  # emails go out on commit
            response = self.signup(public_name="  Ana   Pérez ")
        self.assertEqual(response.status_code, 200, response.content)
        user = CustomUser.objects.get(email="ana@example.com")
        self.assertEqual(user.public_name, "Ana Pérez")
        self.assertIsNotNone(user.privacy_accepted_at)
        # Confirmation email in Spanish, with a link to the site.
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("https://www.andinismodeescritorio.cl/confirmar-email/", mail.outbox[0].body)
        self.assertIn("Ana Pérez", mail.outbox[0].body)

        me = self.c.get("/djangoapi/me/").json()
        self.assertEqual(me["public_name"], "Ana Pérez")
        self.assertFalse(me["email_verified"])

        self.assertEqual(self.send("delete", self.API + "/auth/session").status_code, 401)  # logged out
        self.assertEqual(self.c.get("/djangoapi/me/").status_code, 403)
        login = self.send("post", self.API + "/auth/login", {"email": "ana@example.com", "password": "una-clave-larga-123"})
        self.assertEqual(login.status_code, 200)
        self.assertEqual(self.c.get("/djangoapi/me/").status_code, 200)

    def test_signup_requires_name_and_privacy(self):
        from cerros.models import CustomUser

        response = self.signup(public_name="", accept_privacy=False)
        self.assertEqual(response.status_code, 400)
        params = {e["param"] for e in response.json()["errors"]}
        self.assertEqual(params, {"public_name", "accept_privacy"})
        self.assertFalse(CustomUser.objects.exists())

    def test_honeypot_creates_no_account(self):
        from cerros.models import CustomUser

        response = self.signup(website="http://spam.example")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(CustomUser.objects.exists())

    def test_password_reset_link_goes_to_the_site(self):
        from django.core import mail

        from cerros.models import CustomUser

        CustomUser.objects.create_user("ana@example.com", "una-clave-larga-123")
        self.send("post", self.API + "/auth/password/request", {"email": "ana@example.com"})
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("https://www.andinismodeescritorio.cl/recuperar-clave/", mail.outbox[0].body)

    def test_csrf_is_required(self):
        import json

        from django.test import Client

        response = Client(enforce_csrf_checks=True).post(
            self.API + "/auth/login", json.dumps({"email": "a@example.com", "password": "x"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_public_name_and_claim(self):
        from cerros.models import AndinistClaim

        self.signup()
        bad = self.send("patch", "/djangoapi/me/", {"public_name": "x"})
        self.assertEqual(bad.status_code, 400)
        ok = self.send("patch", "/djangoapi/me/", {"public_name": "Ana P."})
        self.assertEqual(ok.json()["public_name"], "Ana P.")

        brandt = Andinist.objects.create(name="Gustavo", surname="Brandt")
        unverified = self.send("post", "/djangoapi/me/claim/", {"andinist": brandt.pk})
        self.assertEqual(unverified.status_code, 400)  # confirm the email first
        from allauth.account.models import EmailAddress

        EmailAddress.objects.filter(email="ana@example.com").update(verified=True)
        claim = self.send("post", "/djangoapi/me/claim/", {"andinist": brandt.pk, "message": "Soy yo"})
        self.assertEqual(claim.status_code, 201, claim.content)
        self.assertTrue(claim.json()["claim"]["pending"])
        again = self.send("post", "/djangoapi/me/claim/", {"andinist": brandt.pk})
        self.assertEqual(again.status_code, 400)
        self.assertEqual(AndinistClaim.objects.count(), 1)
        self.send("delete", "/djangoapi/me/claim/")
        self.assertEqual(AndinistClaim.objects.count(), 0)


class AccountAdminTests(TestCase):
    def test_editor_role_and_claim_approval(self):
        from django.contrib.auth.models import Group

        from cerros.models import AndinistClaim, CustomUser

        editors = Group.objects.get(name="Editores")  # created by migrate
        self.assertTrue(editors.permissions.filter(codename="change_mountain").exists())
        self.assertFalse(editors.permissions.filter(codename="change_customuser").exists())

        admin = CustomUser.objects.create_superuser("admin@example.com", "clave-correcta-123")
        ana = CustomUser.objects.create_user("ana@example.com", "una-clave-larga-123")
        brandt = Andinist.objects.create(name="Gustavo", surname="Brandt")
        claim = AndinistClaim.objects.create(user=ana, andinist=brandt)

        self.client.force_login(admin)
        response = self.client.post("/admin/cerros/andinistclaim/", {
            "action": "approve", "_selected_action": [claim.pk],
        })
        self.assertEqual(response.status_code, 302)
        ana.refresh_from_db()
        claim.refresh_from_db()
        self.assertEqual(ana.andinist, brandt)
        self.assertEqual(claim.status, AndinistClaim.APPROVED)
        self.assertEqual(claim.reviewed_by, admin)

        # The admin can create a user with a password.
        response = self.client.post("/admin/cerros/customuser/add/", {
            "email": "nuevo@example.com", "public_name": "Nuevo", "password1": "otra-clave-larga-456",
            "password2": "otra-clave-larga-456", "usable_password": "true", "_save": "Guardar",
        })
        self.assertEqual(response.status_code, 302, response.content[:500])
        self.assertTrue(CustomUser.objects.get(email="nuevo@example.com").check_password("otra-clave-larga-456"))

    def test_deleting_an_andinist_keeps_the_account(self):
        from cerros.models import CustomUser

        brandt = Andinist.objects.create(name="Gustavo", surname="Brandt")
        ana = CustomUser.objects.create_user("ana@example.com", "x")
        ana.andinist = brandt
        ana.save()
        brandt.delete()
        self.assertTrue(CustomUser.objects.filter(email="ana@example.com").exists())


class ProposalTests(TestCase):
    """Users propose changes from the site; editors review them in the admin;
    approved ones are applied, credited and recorded in the internal history."""

    @classmethod
    def setUpTestData(cls):
        from allauth.account.models import EmailAddress

        from cerros.models import Country, CustomUser

        cls.cerro = MountainPrefix.objects.create(prefix="Cerro")
        cls.chile = Country.objects.create(name="Chile")
        cls.plomo = Mountain.objects.create(prefix=cls.cerro, name="El Plomo", altitude_igm=5424,
                                            latitude="-33.236155", longitude="-70.214494")
        cls.route = Route.objects.create(name="Normal", mountain=cls.plomo)
        cls.brandt = Andinist.objects.create(name="Gustavo", surname="Brandt")
        cls.luck = Andinist.objects.create(name="Rodolfo", surname="Luck")
        cls.ascent = Ascent.objects.create(name="Primera", route=cls.route, date=datetime.date(1896, 1, 1),
                                           date_format=Ascent.YEAR)
        cls.ascent.andinists.add(cls.brandt)
        cls.ana = CustomUser.objects.create_user("ana@example.com", "una-clave-larga-123")
        cls.ana.public_name = "Ana Pérez"
        cls.ana.save()
        EmailAddress.objects.create(user=cls.ana, email=cls.ana.email, verified=True, primary=True)
        cls.unverified = CustomUser.objects.create_user("beto@example.com", "una-clave-larga-123")
        cls.editor = CustomUser.objects.create_superuser("editor@example.com", "clave-correcta-123")

    def send(self, method, url, data=None):
        import json

        return getattr(self.client, method)(url, json.dumps(data or {}), content_type="application/json")

    def propose(self, model="cerro", target_id="plomo", changes=None, source="Carta IGM", **extra):
        target_id = self.plomo.pk if target_id == "plomo" else target_id
        return self.send("post", "/djangoapi/proposals/", {
            "model": model, "target_id": target_id, "changes": changes or {}, "source": source, **extra,
        })

    def review(self, proposal, action, message="", **values):
        data = {"action": action, "editor_message": message}
        data.update({f"v-{k}": v for k, v in values.items()})
        self.client.force_login(self.editor)
        return self.client.post(f"/admin/cerros/proposal/{proposal.pk}/change/", data)

    def test_form_description_is_public(self):
        response = self.client.get(f"/djangoapi/proposals/form/cerro/{self.plomo.pk}/")
        self.assertEqual(response.status_code, 200)
        fields = {f["name"]: f for f in response.json()["fields"]}
        self.assertEqual(fields["altitude_igm"]["value"], 5424)
        self.assertEqual(fields["latitude"]["type"], "decimal")
        self.assertEqual(fields["countries"]["type"], "multi")
        self.assertEqual(self.client.get("/djangoapi/proposals/form/cerro/nuevo/").json()["title"], "Cerro nuevo")
        self.assertEqual(self.client.get("/djangoapi/proposals/form/ruta/nuevo/").status_code, 404)
        asc = self.client.get(f"/djangoapi/proposals/form/ascenso/{self.ascent.pk}/").json()["fields"]
        date = next(f for f in asc if f["name"] == "date")
        self.assertEqual(date, {**date, "type": "partial_date", "value": {"date": "1896-01-01", "format": Ascent.YEAR}})
        cordada = next(f for f in asc if f["name"] == "andinists")
        self.assertEqual(cordada["value"], [{"id": self.brandt.pk, "name": "Gustavo Brandt"}])

    def test_who_can_propose(self):
        self.assertEqual(self.propose(changes={"altitude_igm": 5430}).status_code, 403)  # anonymous
        self.client.force_login(self.unverified)
        response = self.propose(changes={"altitude_igm": 5430})
        self.assertEqual(response.status_code, 403)
        self.assertIn("Confirma tu correo", response.json()[""][0])

    def test_validation(self):
        from cerros.models import Proposal

        self.client.force_login(self.ana)
        cases = [
            ({"altitude_igm": 5424}, "", "No cambiaste ningún dato."),  # same value
            ({"altitude_igm": "alto"}, "altitude_igm", None),
            ({"ascended": True}, "", "Campos no permitidos: ascended."),
            ({"main_altitude_source": 9}, "main_altitude_source", None),
        ]
        for changes, key, message in cases:
            with self.subTest(changes=changes):
                response = self.propose(changes=changes)
                self.assertEqual(response.status_code, 400, response.content)
                self.assertIn(key, response.json())
                if message:
                    self.assertEqual(response.json()[key], [message])
        self.assertEqual(self.propose(changes={"altitude_igm": 5430}, source="  ").json(),
                         {"source": ["Indica la fuente de esta información."]})
        self.assertEqual(Proposal.objects.count(), 0)

        # Only what changes is kept; extra decimals are rounded; the original is remembered.
        response = self.propose(changes={"altitude_igm": 5430, "name": "El Plomo", "latitude": "-33.23615549"})
        self.assertEqual(response.status_code, 201, response.content)
        proposal = Proposal.objects.get()
        self.assertEqual(proposal.changes, {"altitude_igm": 5430})  # latitude rounds to the same value
        self.assertEqual(proposal.original, {"altitude_igm": 5424})
        self.assertEqual(proposal.target_label, "Cerro El Plomo")

    def test_limits(self):
        from cerros import proposals as P

        self.client.force_login(self.ana)
        for i in range(P.MAX_OPEN):
            self.assertEqual(self.propose(changes={"altitude_igm": 5000 + i}).status_code, 201)
        response = self.propose(changes={"altitude_igm": 4000})
        self.assertEqual(response.status_code, 400)
        self.assertIn("esperando revisión", response.json()[""][0])

    def test_approve_with_adjustment(self):
        from django.core import mail

        from cerros.models import Proposal

        self.client.force_login(self.ana)
        self.propose(changes={"altitude_igm": 5430, "countries": [self.chile.pk]}, comment="Carta nueva")
        proposal = Proposal.objects.get()
        response = self.review(proposal, "approve", "Usé 5428.", altitude_igm=5428, countries=[self.chile.pk])
        self.assertEqual(response.status_code, 302, response.content[:2000])
        self.plomo.refresh_from_db()
        proposal.refresh_from_db()
        self.assertEqual(self.plomo.altitude_igm, 5428)
        self.assertEqual(self.plomo.altitude, 5428)
        self.assertEqual(list(self.plomo.countries.all()), [self.chile])
        self.assertEqual(self.plomo.location_status, Mountain.LOCATION_REVIEWED)
        self.assertEqual(proposal.status, Proposal.APPROVED)
        self.assertEqual(proposal.applied, {"altitude_igm": 5428, "countries": [self.chile.pk]})
        self.assertEqual(proposal.reviewed_by, self.editor)
        # Internal history: who approved it and why.
        last = self.plomo.history.first()
        self.assertEqual(last.history_user, self.editor)
        self.assertEqual(last.history_change_reason, f"Propuesta #{proposal.pk} de Ana Pérez")
        # The author is told, with the editor's message, and credited on the record.
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("fue aprobada", mail.outbox[0].subject)
        self.assertIn("Usé 5428.", mail.outbox[0].body)
        data = self.client.get(f"/djangoapi/mountain/{self.plomo.pk}/").json()
        self.assertEqual(data["contributors"], ["Ana Pérez"])

    def test_ask_for_information_resend_and_withdraw(self):
        from django.core import mail

        from cerros.models import Proposal

        self.client.force_login(self.ana)
        self.propose("ascenso", self.ascent.pk, {"date": "1896-02-10", "date_format": Ascent.MONTHYEAR,
                                                 "andinists": [self.brandt.pk, self.luck.pk]})
        proposal = Proposal.objects.get()
        self.assertEqual(proposal.changes["date"], "1896-02-10")
        response = self.review(proposal, "needs_info")  # a message is required
        self.assertContains(response, "Escribe qué información falta")
        response = self.review(proposal, "needs_info", "¿Qué página de la revista?")
        self.assertEqual(response.status_code, 302)
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, Proposal.NEEDS_INFO)
        self.assertIn("¿Qué página de la revista?", mail.outbox[0].body)
        self.assertEqual(self.ascent.date, datetime.date(1896, 1, 1))  # nothing applied

        self.client.force_login(self.ana)
        mine = self.client.get("/djangoapi/me/proposals/").json()
        self.assertEqual(mine[0]["status"], Proposal.NEEDS_INFO)
        self.assertEqual(mine[0]["editor_message"], "¿Qué página de la revista?")
        self.assertIn({"label": "Fecha", "value": "02/1896"}, mine[0]["changes"])
        detail = self.client.get(f"/djangoapi/me/proposals/{proposal.pk}/").json()
        self.assertEqual(detail["values"]["andinists"], [{"id": self.brandt.pk, "name": "Gustavo Brandt"},
                                                         {"id": self.luck.pk, "name": "Rodolfo Luck"}])
        response = self.send("patch", f"/djangoapi/me/proposals/{proposal.pk}/", {
            "changes": {"date": "1896-02-10", "date_format": Ascent.MONTHYEAR, "andinists": [self.brandt.pk, self.luck.pk]},
            "source": "Revista Andina nº 12, p. 40",
        })
        self.assertEqual(response.status_code, 200, response.content)
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, Proposal.PENDING)
        self.assertEqual(proposal.source, "Revista Andina nº 12, p. 40")

        self.assertEqual(self.client.delete(f"/djangoapi/me/proposals/{proposal.pk}/").status_code, 204)
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, Proposal.WITHDRAWN)
        self.assertEqual(self.client.get("/djangoapi/me/proposals/").json(), [])
        # Someone else's proposal is not found.
        self.client.force_login(self.unverified)
        self.assertEqual(self.client.get(f"/djangoapi/me/proposals/{proposal.pk}/").status_code, 404)

    def test_approve_ascent_date_and_party(self):
        from cerros.models import Proposal

        self.client.force_login(self.ana)
        self.propose("ascenso", self.ascent.pk, {"date": "1896-02-10", "date_format": Ascent.MONTHYEAR,
                                                 "andinists": [self.brandt.pk, self.luck.pk]})
        proposal = Proposal.objects.get()
        response = self.review(proposal, "approve", date="1896-02-10", date_format=Ascent.MONTHYEAR,
                               andinists=[self.brandt.pk, self.luck.pk])
        self.assertEqual(response.status_code, 302, response.content[:3000])
        self.ascent.refresh_from_db()
        self.assertEqual((self.ascent.date, self.ascent.date_format), (datetime.date(1896, 2, 10), Ascent.MONTHYEAR))
        self.assertEqual(set(self.ascent.andinists.all()), {self.brandt, self.luck})

    def test_reject(self):
        from cerros.models import Proposal

        self.client.force_login(self.ana)
        self.propose(changes={"altitude_igm": 6000})
        proposal = Proposal.objects.get()
        self.assertEqual(self.review(proposal, "reject", "Sin fuente fiable.").status_code, 302)
        proposal.refresh_from_db()
        self.plomo.refresh_from_db()
        self.assertEqual((proposal.status, proposal.editor_message), (Proposal.REJECTED, "Sin fuente fiable."))
        self.assertEqual(self.plomo.altitude_igm, 5424)
        # A reviewed proposal can no longer be changed.
        self.client.force_login(self.ana)
        response = self.send("patch", f"/djangoapi/me/proposals/{proposal.pk}/", {"changes": {"altitude_igm": 6001}})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get(f"/djangoapi/mountain/{self.plomo.pk}/").json()["contributors"], [])

    def test_new_mountain(self):
        from cerros import proposals as P
        from cerros.models import Proposal

        self.client.force_login(self.ana)
        response = self.propose(target_id=None, changes={"name": "Nuevo"})
        self.assertEqual(response.json(), {"prefix": ["Este dato es obligatorio."]})
        response = self.propose(target_id=None, changes={
            "prefix": self.cerro.pk, "name": "Plomito", "altitude_gps": 4100,
            "latitude": "-33.240", "longitude": "-70.220",
        })
        self.assertEqual(response.status_code, 201, response.content)
        proposal = Proposal.objects.get()
        self.assertTrue(proposal.creates)
        self.assertEqual(proposal.changes["main_altitude_source"], Mountain.GPS)  # the altitude given
        # The editor is warned about El Plomo, 0.6 km away.
        self.assertEqual([m.name for m in P.similar_mountains(proposal)], ["El Plomo"])
        self.client.force_login(self.editor)
        self.assertContains(self.client.get(f"/admin/cerros/proposal/{proposal.pk}/change/"), "¿Ya existe?")
        response = self.review(proposal, "approve", prefix=self.cerro.pk, name="Plomito", altitude_gps=4100,
                               latitude="-33.240000", longitude="-70.220000", main_altitude_source=Mountain.GPS)
        self.assertEqual(response.status_code, 302, response.content[:3000])
        proposal.refresh_from_db()
        new = Mountain.objects.get(name="Plomito")
        self.assertEqual((proposal.target_id, new.altitude), (new.pk, 4100))
        self.assertEqual(self.client.get(f"/djangoapi/mountain/{new.pk}/").json()["contributors"], ["Ana Pérez"])

    def test_direct_admin_edits_are_in_the_history(self):
        self.client.force_login(self.editor)
        response = self.client.post(f"/admin/cerros/andinist/{self.luck.pk}/change/", {
            "name": "Rodolfo", "surname": "Lück", "ascent_count": 0, "new_routes_count": 0, "first_ascent_count": 0,
        })
        self.assertEqual(response.status_code, 302, response.content[:3000])
        self.luck.refresh_from_db()
        self.assertEqual(self.luck.surname, "Lück")
        last = self.luck.history.first()
        self.assertEqual((last.history_user, last.surname, last.history_type), (self.editor, "Lück", "~"))
        self.assertContains(self.client.get(f"/admin/cerros/andinist/{self.luck.pk}/history/"), "Lück")

    def test_history_from_the_other_side_of_a_many_to_many(self):
        before = self.ascent.history.count()
        self.luck.ascent_set.add(self.ascent)  # adding from the andinist
        self.assertEqual(self.ascent.history.count(), before + 1)
        last = self.ascent.history.first()
        self.assertEqual({a.andinist_id for a in last.andinists.all()}, {self.brandt.pk, self.luck.pk})
