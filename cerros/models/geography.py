from django.db import models
from .base import BaseModel
from .references import Referenceable

class Country(BaseModel):
  name = models.CharField(max_length=255)

  def __str__(self):
      return self.name

  class Meta:
    verbose_name = "País"
    verbose_name_plural = "Países"
    ordering = ['name']

class Region(BaseModel):
  name = models.CharField(max_length=255)
  country = models.ForeignKey(Country, on_delete=models.CASCADE)

  def __str__(self):
      return self.name

  class Meta:
    verbose_name = "Región"
    verbose_name_plural = "Regiones"
    ordering = ['name']

class MountainGroup(Referenceable):
  name = models.CharField(max_length=255)
  GROUP_TYPE_CHOICES = (
      (0, 'Cordón Montañoso'),
      (1, 'Valle'),
      (2, 'Macizo'),
      (3, 'Zona'),
  )
  group_type = models.IntegerField(choices=GROUP_TYPE_CHOICES)
  # Método para obtener longitud y latitud centro de masa de un grupo

  def __str__(self):
    # GROUP TYPE IN STRING
    return self.GROUP_TYPE_CHOICES[self.group_type][1] + " " + self.name
  
  class Meta:
    verbose_name = "Grupo de Montañas"
    verbose_name_plural = "Grupos de Montañas"
    ordering = ['group_type', 'name']
