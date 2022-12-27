from django.db import models
from .base import BaseModel

class IGMMap(BaseModel):
  name = models.CharField(max_length=255)
  file_id = models.CharField(max_length=255)

  class Meta:
    verbose_name = "Carta IGM"
    verbose_name_plural = "Cartas IGM"

class NomenclaturaSummit(BaseModel):
  id_nomenclatura = models.CharField(max_length=255)
  cod_revision = models.CharField(max_length=255)
  name = models.CharField(max_length=255)
  altitude_igm = models.CharField(max_length=100, null=True, blank=True)
  latitude = models.CharField(max_length=255, null=True, blank=True)
  longitude = models.CharField(max_length=255, null=True, blank=True)
  observations = models.TextField(null=True, blank=True)
  comment = models.TextField(null=True, blank=True)
  igm_rectangle = models.ForeignKey(IGMMap, on_delete=models.CASCADE)

  def __str__(self):
    return self.id_nomenclatura + " - " + self.name

  class Meta:
    verbose_name = "Cumbre Nomenclatura"
    verbose_name_plural = "Cumbres Nomenclatura"