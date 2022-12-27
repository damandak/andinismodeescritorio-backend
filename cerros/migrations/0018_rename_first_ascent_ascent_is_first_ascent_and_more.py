# Generated by Django 4.1.3 on 2022-12-19 12:48

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cerros', '0017_alter_ascent_options_alter_mountain_options_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='ascent',
            old_name='first_ascent',
            new_name='is_first_ascent',
        ),
        migrations.AddField(
            model_name='route',
            name='first_ascent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='first_ascent', to='cerros.ascent'),
        ),
    ]
