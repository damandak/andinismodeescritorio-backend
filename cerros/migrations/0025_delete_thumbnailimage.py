# Generated by Django 4.1.3 on 2023-01-04 00:03

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cerros', '0024_image_tb_item_cover_image_tb_small_thumbnailimage'),
    ]

    operations = [
        migrations.DeleteModel(
            name='ThumbnailImage',
        ),
    ]
