from django.db import models
from .routes import Route
from .andinists import Andinist
from .references import Referenceable

class Ascent(Referenceable):
  # Date with partial-date or full-date truncated
  name = models.CharField(max_length=255)
  route = models.ForeignKey(Route, on_delete=models.CASCADE)
  completed = models.BooleanField(default=True)
  andinists = models.ManyToManyField(Andinist, blank=True)
  support_andinists = models.ManyToManyField(Andinist, related_name='support_andinists', blank=True)
  is_first_ascent = models.BooleanField(default=False)
  new_route = models.BooleanField(default=False)
  
  # Save date with optional day and optional month
  date = models.DateField(null=True, blank=True)
  YEAR = 0
  MONTHYEAR = 1
  DAYMONTHYEAR = 2
  DATE_FORMAT_CHOICES = (
    (YEAR, 'Year'),
    (MONTHYEAR, 'Month and Year'),
    (DAYMONTHYEAR, 'Day, Month and Year'),
  )
  date_format = models.IntegerField(choices=DATE_FORMAT_CHOICES, default=DAYMONTHYEAR)
  
  main_image = models.ForeignKey('Image', on_delete=models.SET_NULL, null=True, blank=True, related_name='ascent_main_image')
  image_set = models.ManyToManyField('Image', blank=True)

  class Meta:
    verbose_name = "Ascenso"
    verbose_name_plural = "Ascensos"
    ordering = ['date']

  def __str__(self):
    return self.date_tostring() + " - " + str(self.route.mountain) + " - " + self.route.name + " - " + self.name

  def date_tostring(self):
    if self.date_format == self.YEAR:
      return self.date.strftime("%Y") + "-xx-xx"
    elif self.date_format == self.MONTHYEAR:
      return self.date.strftime("%Y-%m") + "-xx"
    else:
      return self.date.strftime("%Y-%m-%d")