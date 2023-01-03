from django.db import models
from .base import BaseModel

class Image(BaseModel):
  name = models.CharField(max_length=255)
  image = models.ImageField(upload_to='images')
  date_captured = models.DateField(null=True, blank=True)
  location = models.CharField(max_length=255, null=True, blank=True)
  description = models.TextField(null=True, blank=True)
  author = models.ForeignKey('cerros.CustomUser', on_delete=models.CASCADE, related_name='images')

  def __str__(self):
    return self.name
