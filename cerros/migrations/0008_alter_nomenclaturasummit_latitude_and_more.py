# Generated by Django 4.1.3 on 2022-12-13 16:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cerros', '0007_andinist_gender_alter_route_ascended'),
    ]

    operations = [
        migrations.AlterField(
            model_name='nomenclaturasummit',
            name='latitude',
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name='nomenclaturasummit',
            name='longitude',
            field=models.CharField(max_length=255),
        ),
    ]
