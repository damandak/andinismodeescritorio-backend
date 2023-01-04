# Generated by Django 4.1.3 on 2023-01-03 18:22

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cerros', '0022_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='andinist',
            name='image_set',
            field=models.ManyToManyField(blank=True, to='cerros.image'),
        ),
        migrations.AddField(
            model_name='andinist',
            name='main_image',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='andinist_main_image', to='cerros.image'),
        ),
        migrations.AddField(
            model_name='ascent',
            name='image_set',
            field=models.ManyToManyField(blank=True, to='cerros.image'),
        ),
        migrations.AddField(
            model_name='ascent',
            name='main_image',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ascent_main_image', to='cerros.image'),
        ),
        migrations.AddField(
            model_name='mountain',
            name='image_set',
            field=models.ManyToManyField(blank=True, to='cerros.image'),
        ),
        migrations.AddField(
            model_name='mountain',
            name='main_image',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='mtn_main_image', to='cerros.image'),
        ),
        migrations.AddField(
            model_name='route',
            name='image_set',
            field=models.ManyToManyField(blank=True, to='cerros.image'),
        ),
        migrations.AddField(
            model_name='route',
            name='main_image',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='route_main_image', to='cerros.image'),
        ),
    ]