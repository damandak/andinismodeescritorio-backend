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
