# Generated by Django 4.1.3 on 2022-11-25 01:59

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Country',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=255)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='IGMMap',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=255)),
                ('file_id', models.CharField(max_length=255)),
            ],
            options={
                'verbose_name': 'Carta IGM',
                'verbose_name_plural': 'Cartas IGM',
            },
        ),
        migrations.CreateModel(
            name='MountainGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=255)),
                ('group_type', models.IntegerField(choices=[(0, 'Cordón Montañoso'), (1, 'Valle'), (2, 'Macizo'), (3, 'Zona')])),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='MountainPrefix',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('prefix', models.CharField(max_length=15)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Region',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=255)),
                ('country', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cerros.country')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='NomenclaturaSummit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id_nomenclatura', models.IntegerField()),
                ('cod_revision', models.IntegerField()),
                ('name', models.CharField(max_length=255)),
                ('altitude_igm', models.IntegerField()),
                ('latitude', models.DecimalField(decimal_places=6, max_digits=10)),
                ('longitude', models.DecimalField(decimal_places=6, max_digits=10)),
                ('observations', models.TextField(blank=True, null=True)),
                ('comment', models.TextField(blank=True, null=True)),
                ('igm_rectangle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cerros.igmmap')),
            ],
            options={
                'verbose_name': 'Cumbre Nomenclatura',
                'verbose_name_plural': 'Cumbres Nomenclatura',
            },
        ),
        migrations.CreateModel(
            name='Mountain',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=255)),
                ('latitude', models.DecimalField(decimal_places=6, max_digits=10)),
                ('longitude', models.DecimalField(decimal_places=6, max_digits=10)),
                ('altitude', models.IntegerField()),
                ('altitude_igm', models.IntegerField(blank=True, null=True)),
                ('altitude_arg', models.IntegerField(blank=True, null=True)),
                ('altitude_gps', models.IntegerField(blank=True, null=True)),
                ('main_altitude_source', models.IntegerField(choices=[(0, 'IGM Chile'), (1, 'Argentina'), (2, 'GPS')], default=0)),
                ('ref_ahb', models.CharField(blank=True, max_length=255, null=True)),
                ('ref_wikiexplora', models.CharField(blank=True, max_length=255, null=True)),
                ('country', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cerros.country')),
                ('mountain_group', models.ManyToManyField(blank=True, to='cerros.mountaingroup')),
                ('nomenclatura_mountain', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cerros.nomenclaturasummit')),
                ('parent_mountain', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cerros.mountain')),
                ('prefix', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cerros.mountainprefix')),
                ('region', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cerros.region')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
