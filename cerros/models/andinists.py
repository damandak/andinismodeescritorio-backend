from django.db import models
from .base import BaseModel
from .geography import Country
from .references import Referenceable
from django.apps import apps

class Club(Referenceable):
    name = models.CharField(max_length=255)
    shortname = models.CharField(max_length=255)
    founded_date = models.DateField(null=True, blank=True)
    country = models.CharField(max_length=255, null=True, blank=True)
    region = models.CharField(max_length=255, null=True, blank=True)
    external_link = models.URLField(null=True, blank=True)
    #logo = models.ImageField(upload_to='clubs', null=True, blank=True)
    #cover_image = models.ForeignKey('ImageUpload', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Club"
        verbose_name_plural = "Clubes"

class Andinist(Referenceable):
    name = models.CharField(max_length=255, blank=True, null=True)
    surname = models.CharField(max_length=255, blank=True, null=True)
    clubs = models.ManyToManyField(Club, blank=True)
    nationalities = models.ManyToManyField(Country, blank=True)
    gender = models.CharField(max_length=255, blank=True, null=True)

    ascent_count = models.IntegerField(default=0)
    new_routes_count = models.IntegerField(default=0)
    first_ascent_count = models.IntegerField(default=0)

    main_image = models.ForeignKey('Image', on_delete=models.SET_NULL, null=True, blank=True, related_name='andinist_main_image')
    image_set = models.ManyToManyField('Image', blank=True)
    
    def __str__(self):
        if self.name and self.surname:
            return self.name + ' ' + self.surname
        elif self.name:
            return self.name
        elif self.surname:
            return self.surname
        else:
            return 'Andinista sin nombre'

    class Meta:
        verbose_name = "Andinista"
        verbose_name_plural = "Andinistas"
        ordering = ['surname', 'name']

    def get_ascent_count(self):
        ascents_count = apps.get_model(app_label='cerros', model_name='Ascent').objects.filter(andinists=self).count()
        return ascents_count

    def get_new_routes_count(self):
        new_routes = apps.get_model(app_label='cerros', model_name='Ascent').objects.filter(andinists=self)
        new_routes_count = 0
        for new_route in new_routes:
            if new_route.new_route:
                new_routes_count += 1
        return new_routes_count

    def get_first_ascent_count(self):
        first_ascents = apps.get_model(app_label='cerros', model_name='Ascent').objects.filter(andinists=self)
        first_ascent_count = 0
        for first_ascent in first_ascents:
            if first_ascent.is_first_ascent:
                first_ascent_count += 1
        return first_ascent_count

    def save(self, *args, **kwargs):
        self.ascent_count = self.get_ascent_count()
        self.new_routes_count = self.get_new_routes_count()
        self.first_ascent_count = self.get_first_ascent_count()
        super(Andinist, self).save(*args, **kwargs)