from django.db import models

from .base import BaseModel
from .nomenclatura import NomenclaturaSummit
from .geography import Country, Region, MountainGroup
from .references import Referenceable
from django.apps import apps

class MountainPrefix(BaseModel):
  prefix = models.CharField(max_length=15, unique=True, blank=True, null=True)

  class Meta:
    verbose_name = "Prefijo de montaña"
    verbose_name_plural = "Prefijos de montaña"
  
  def __str__(self):
    return self.prefix

class Mountain(Referenceable):
  prefix = models.ForeignKey(MountainPrefix, on_delete=models.CASCADE)
  name = models.CharField(max_length=255)

  # Ubicación geográfica en WGS84
  latitude = models.DecimalField(max_digits=10, decimal_places=6, blank=True, null=True)
  longitude = models.DecimalField(max_digits=10, decimal_places=6, blank=True, null=True)

  # Altura
  altitude = models.IntegerField(blank=True, null=True)
  altitude_igm = models.IntegerField(blank=True, null=True) # Only if there are multiple sources
  altitude_arg = models.IntegerField(blank=True, null=True) # Only if there are multiple sources
  altitude_gps = models.IntegerField(blank=True, null=True) # Only if there are multiple sources
  IGM = 0
  ARG = 1
  GPS = 2
  MAIN_ALTITUDE_SOURCE_CHOICES = (
    (IGM, 'IGM Chile'),
    (ARG, 'Argentina'),
    (GPS, 'GPS'),
  )
  main_altitude_source = models.IntegerField(choices=MAIN_ALTITUDE_SOURCE_CHOICES, default=IGM)

  # Relationships
  parent_mountain = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
  nomenclatura_mountain = models.ForeignKey(NomenclaturaSummit, on_delete=models.CASCADE, null=True, blank=True)
  ref_ahb = models.CharField(max_length=255, null=True, blank=True)
  ref_wikiexplora = models.CharField(max_length=255, null=True, blank=True)
  countries = models.ManyToManyField(Country, blank=True)
  regions = models.ManyToManyField(Region, blank=True)
  mountain_group = models.ManyToManyField(MountainGroup, blank=True)
  first_absolute = models.ForeignKey('Ascent', on_delete=models.SET_NULL, null=True, blank=True, related_name='first_absolute')
  unregistered_sport_ascent = models.BooleanField(default=False)
  unregistered_non_sport_ascent = models.BooleanField(default=False)

  main_image = models.ForeignKey('Image', on_delete=models.SET_NULL, null=True, blank=True, related_name='mtn_main_image')
  image_set = models.ManyToManyField('Image', blank=True)

  def __str__(self):
      return self.prefix.prefix + " " + self.name

  def save(self, *args, **kwargs):
    # when changing main_altitude_source, update altitude field
    if self.main_altitude_source == self.IGM:
      self.altitude = self.altitude_igm
    elif self.main_altitude_source == self.ARG:
      self.altitude = self.altitude_arg
    elif self.main_altitude_source == self.GPS:
      self.altitude = self.altitude_gps
    super(Mountain, self).save(*args, **kwargs)

  def get_first_ascent(self):
    if self.unregistered_sport_ascent:
      return None
    ascents = apps.get_model(app_label='cerros', model_name='Ascent').objects.filter(route__mountain=self).order_by('-date')
    if not ascents:
      return None
    temp_ascent = ascents.first()
    for ascent in ascents:
      temp_ascent = ascent
      if ascent.is_first_ascent:
        return ascent
    return temp_ascent

  def save(self, *args, **kwargs):
    self.first_absolute = self.get_first_ascent()
    if self.main_image:
      if self.main_image not in self.image_set.all():
        self.image_set.add(self.main_image)
    super(Mountain, self).save(*args, **kwargs)

  class Meta:
    verbose_name = "Montaña"
    verbose_name_plural = "Montañas"
    ## REVISAR ESTO, SERÁ EL ORDEN IDEAL?
    ordering = ['id']
    