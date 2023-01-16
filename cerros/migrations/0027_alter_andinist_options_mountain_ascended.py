# Generated by Django 4.1.3 on 2023-01-10 17:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cerros', '0026_alter_image_author'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='andinist',
            options={'ordering': ['surname', 'name'], 'verbose_name': 'Andinista', 'verbose_name_plural': 'Andinistas'},
        ),
        migrations.AddField(
            model_name='mountain',
            name='ascended',
            field=models.BooleanField(default=False),
        ),
    ]