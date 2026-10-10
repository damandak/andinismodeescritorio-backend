"""Ascents dated 0001-01-01 (or any date in year 1) meant "unknown date": it was
the only way to save an ascent without a date, because the site broke on empty
dates. They become empty dates now that the site handles them.

As 0001 they counted as the oldest ascent of their route and mountain, so they
could be taken as the first ascent. After migrating, recalculate with:
    python manage.py assign_first_ascents --dry-run   (see what changes)
    python manage.py assign_first_ascents
Not reversible (which ascents had 0001 is not kept): restore the backup if needed.
"""
from django.db import migrations


def clear_placeholder_dates(apps, schema_editor):
    Ascent = apps.get_model("cerros", "Ascent")
    count = Ascent.objects.filter(date__year=1).update(date=None)
    if count:
        print(f"\n    {count} ascensos con fecha 0001 quedaron sin fecha.", end="")


class Migration(migrations.Migration):
    dependencies = [("cerros", "0029_image_medium_and_size")]
    operations = [migrations.RunPython(clear_placeholder_dates, migrations.RunPython.noop)]
