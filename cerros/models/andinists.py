from django.db import models
from .base import BaseModel
from .geography import Country
from .references import Referenceable

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

    def save(self, *args, **kwargs):
        from cerros.derived import compute_andinist_counts
        for field, value in compute_andinist_counts(self).items():
            setattr(self, field, value)
        super(Andinist, self).save(*args, **kwargs)