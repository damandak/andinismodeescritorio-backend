from django.db import models
from .base import BaseModel
from .mountains import Mountain
from .references import Referenceable
from django.apps import apps


class Route(Referenceable):
  parent_route = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
  name = models.CharField(max_length=255)
  mountain = models.ForeignKey(Mountain, on_delete=models.CASCADE, null=True, blank=True) 
  summit = models.BooleanField(default=True) # If the route ends in a summit
  ascended = models.BooleanField(default=True) # If the route has been ascended
  unregistered_non_sport_ascent = models.BooleanField(default=False) # If the route has been ascended by miners, arrieros, indigenous groups, etc
  unregistered_sport_ascent = models.BooleanField(default=False) # If the route has been ascended by andinists but there is no record of it

  ## GRADUATION
  # ALPINE GRADE
  F = 0
  PD_LOWER = 1
  PD = 2
  PD_UPPER = 3
  AD_LOWER = 4
  AD = 5
  AD_UPPER = 6
  D_LOWER = 7
  D = 8
  D_UPPER = 9
  ED_LOWER = 10
  ED = 11
  ED_UPPER = 12
  EDX = 13
  ALPINE_GRADE_CHOICES = (
    (F, 'F'),
    (PD_LOWER, 'PD-'),
    (PD, 'PD'),
    (PD_UPPER, 'PD+'),
    (AD_LOWER, 'AD-'),
    (AD, 'AD'),
    (AD_UPPER, 'AD+'),
    (D_LOWER, 'D-'),
    (D, 'D'),
    (D_UPPER, 'D+'),
    (ED_LOWER, 'ED-'),
    (ED, 'ED'),
    (ED_UPPER, 'ED+'),
    (EDX, 'EDx'),
  )
  alpine_grade = models.IntegerField(choices=ALPINE_GRADE_CHOICES, default=F) # Alpine Grade

  # AID GRADE
  A0 = 0
  A1 = 1
  A2 = 2
  A3 = 3
  A4 = 4
  A5 = 5
  AID_CLIMBING_GRADE_CHOICES = (
    (A0, 'A0'),
    (A1, 'A1'),
    (A2, 'A2'),
    (A3, 'A3'),
    (A4, 'A4'),
    (A5, 'A5'),
  )
  aid_climbing_grade = models.IntegerField(choices=AID_CLIMBING_GRADE_CHOICES, null=True, blank=True) # Aid Climbing Grade

  # ICE GRADE
  WI1 = 0
  WI2 = 1
  WI3 = 2
  WI4 = 3
  WI5 = 4
  WI6 = 5
  WI7 = 6
  ICE_CLIMBING_GRADE_CHOICES = (
    (WI1, 'WI1'),
    (WI2, 'WI2'),
    (WI3, 'WI3'),
    (WI4, 'WI4'),
    (WI5, 'WI5'),
    (WI6, 'WI6'),
    (WI7, 'WI7'),
  )
  ice_climbing_grade = models.IntegerField(choices=ICE_CLIMBING_GRADE_CHOICES, null=True, blank=True) # Ice Climbing Grade

  # ROCK GRADE (FRENCH)
  ThreeA = 0
  FourA = 1
  FourB = 2
  FourC = 3
  FiveA = 4
  FiveB = 5
  FiveC = 6
  SixA = 7
  SixB = 8
  SixC = 9
  SevenA = 10
  SevenB = 11
  SevenC = 12
  EightA = 13
  EightB = 14
  EightC = 15
  NineA = 16
  NineB = 17
  NineC = 18
  ROCK_CLIMBING_GRADE_CHOICES = (
    (ThreeA, '3A'),
    (FourA, '4A'),
    (FourB, '4B'),
    (FourC, '4C'),
    (FiveA, '5A'),
    (FiveB, '5B'),
    (FiveC, '5C'),
    (SixA, '6A'),
    (SixB, '6B'),
    (SixC, '6C'),
    (SevenA, '7A'),
    (SevenB, '7B'),
    (SevenC, '7C'),
    (EightA, '8A'),
    (EightB, '8B'),
    (EightC, '8C'),
    (NineA, '9A'),
    (NineB, '9B'),
    (NineC, '9C'),
  )
  rock_climbing_grade = models.IntegerField(choices=ROCK_CLIMBING_GRADE_CHOICES, null=True, blank=True) # Rock Climbing Grade

  description = models.TextField(null=True, blank=True)
  notes = models.TextField(null=True, blank=True)
  gpx = models.FileField(upload_to='gpx', null=True, blank=True)
  kml = models.FileField(upload_to='kml', null=True, blank=True)
  first_ascent = models.ForeignKey('Ascent', on_delete=models.SET_NULL, null=True, blank=True, related_name='first_ascent')

  main_image = models.ForeignKey('Image', on_delete=models.SET_NULL, null=True, blank=True, related_name='route_main_image')
  image_set = models.ManyToManyField('Image', blank=True)

  class Meta:
    verbose_name = "Ruta"
    verbose_name_plural = "Rutas"

  def __str__(self):
    return str(self.mountain) + " - " + self.name

  def first_ascent_year(self):
    if self.first_ascent:
      return self.first_ascent.date.year
    return ""

  def get_first_ascent(self):
    if self.unregistered_sport_ascent:
      return None
    ascents = apps.get_model(app_label='cerros', model_name='Ascent').objects.filter(route=self).order_by('-date')
    if not ascents:
      return None
    temp_ascent = ascents.first()
    for ascent in ascents:
      temp_ascent = ascent
      if ascent.new_route:
        return ascent
    return temp_ascent

  def save(self, *args, **kwargs):
    self.first_ascent = self.get_first_ascent()
    super(Route, self).save(*args, **kwargs)