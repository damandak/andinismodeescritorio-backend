from django.db import models
from .base import BaseModel

class Image(BaseModel):
  name = models.CharField(max_length=255)
  image = models.ImageField(upload_to='images')
  date_captured = models.DateField(null=True, blank=True)

  def __str__(self):
    return self.name
