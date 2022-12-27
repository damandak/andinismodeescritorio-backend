from django.db import models
from .base import BaseModel

class Reference(BaseModel):
  publication_name = models.CharField(max_length=255)
  publication_edition = models.CharField(max_length=255, null=True, blank=True)
  publication_year = models.IntegerField(null=True, blank=True)
  title = models.CharField(max_length=255)
  author = models.CharField(max_length=255, null=True, blank=True)
  page = models.CharField(max_length=255, null=True, blank=True)
  url = models.URLField(null=True, blank=True)

  def __str__(self):
    result = self.publication_name
    if self.publication_edition:
      result += ' ' + self.publication_edition
    if self.publication_year:
      result += ', ' + str(self.publication_year)
    if self.title:
      result += ' - ' + self.title
    if self.author:
      result += ' - ' + self.author
    if result == "" and self.title:
      result = self.title
    if result == "" and self.url:
      result = self.url
    return result
  
  class Meta:
    verbose_name = "Referencia"
    verbose_name_plural = "Referencias"
    ordering = ['publication_name', 'publication_edition', 'publication_year', 'title', 'author', 'page', 'url']

class Referenceable(models.Model):
  references = models.ManyToManyField(Reference, blank=True)

  class Meta:
    abstract = True
    verbose_name = "Referenciable"
    verbose_name_plural = "Referenciables"
