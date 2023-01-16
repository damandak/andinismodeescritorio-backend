# Generated by Django 4.1.3 on 2023-01-16 01:47

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cerros', '0027_alter_andinist_options_mountain_ascended'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='country',
            options={'ordering': ['name'], 'verbose_name': 'País', 'verbose_name_plural': 'Países'},
        ),
        migrations.AlterModelOptions(
            name='mountaingroup',
            options={'ordering': ['group_type', 'name'], 'verbose_name': 'Grupo de Montañas', 'verbose_name_plural': 'Grupos de Montañas'},
        ),
        migrations.AlterModelOptions(
            name='mountainprefix',
            options={'ordering': ['prefix'], 'verbose_name': 'Prefijo de montaña', 'verbose_name_plural': 'Prefijos de montaña'},
        ),
        migrations.AlterModelOptions(
            name='region',
            options={'ordering': ['name'], 'verbose_name': 'Región', 'verbose_name_plural': 'Regiones'},
        ),
    ]
