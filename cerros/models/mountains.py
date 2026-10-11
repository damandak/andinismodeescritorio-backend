from django.db import models
from .history import HistoricalRecords

from .base import BaseModel
from .nomenclatura import NomenclaturaSummit
from .geography import Country, Region, MountainGroup
from .references import Referenceable

class MountainPrefix(BaseModel):
  prefix = models.CharField(max_length=15, unique=True, blank=True, null=True)

  class Meta:
    verbose_name = "Prefijo de montaña"
    verbose_name_plural = "Prefijos de montaña"
    ordering = ['prefix']
  
  def __str__(self):
    return self.prefix

class Mountain(Referenceable):
  prefix = models.ForeignKey(MountainPrefix, on_delete=models.CASCADE)
  name = models.CharField(max_length=255)
  ascended = models.BooleanField(default=False)

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

  # Country and region according to the coordinates (cerros/location.py,
  # `manage.py asignar_ubicacion`). Filled automatically, shown in the admin.
  LOCATION_UNCHECKED = 0
  LOCATION_NO_COORDINATES = 1
  LOCATION_AUTO = 2
  LOCATION_TO_REVIEW = 3
  LOCATION_MISMATCH = 4
  LOCATION_MATCH = 5
  LOCATION_REVIEWED = 6
  LOCATION_OUTSIDE = 7
  LOCATION_STATUS_CHOICES = (
    (LOCATION_TO_REVIEW, 'Por completar: cerca de un límite'),
    (LOCATION_MISMATCH, 'No calza con las coordenadas'),
    (LOCATION_AUTO, 'Asignada por coordenadas'),
    (LOCATION_MATCH, 'Coincide con las coordenadas'),
    (LOCATION_REVIEWED, 'Revisada a mano'),
    (LOCATION_NO_COORDINATES, 'Sin coordenadas'),
    (LOCATION_OUTSIDE, 'Fuera de los mapas'),
    (LOCATION_UNCHECKED, 'Sin calcular'),
  )
  location_status = models.IntegerField(
    "Estado de la ubicación", choices=LOCATION_STATUS_CHOICES, default=LOCATION_UNCHECKED,
    help_text="Elige «Revisada a mano» cuando hayas confirmado el país y la región.",
  )
  suggested_country = models.ForeignKey(
    Country, on_delete=models.SET_NULL, null=True, blank=True, related_name='+', editable=False,
  )
  suggested_region = models.ForeignKey(
    Region, on_delete=models.SET_NULL, null=True, blank=True, related_name='+', editable=False,
  )
  location_note = models.CharField(max_length=500, blank=True, default='', editable=False)
  border_distance = models.IntegerField(null=True, blank=True, editable=False)  # metres

  # Internal history of every change (who, when, why), shown in the admin.
  history = HistoricalRecords(
    m2m_fields=["countries", "regions", "mountain_group"],
    excluded_fields=["ascended", "first_absolute", "location_status", "suggested_country",
                     "suggested_region", "location_note", "border_distance"],
  )

  def __str__(self):
      return self.prefix.prefix + " " + self.name

  def save(self, *args, **kwargs):
    from cerros.derived import compute_mountain_ascended
    self.first_absolute = self.get_first_ascent()
    # when changing main_altitude_source, update altitude field
    # (only if that source has a value, so a missing source never wipes it)
    source_altitude = {
      self.IGM: self.altitude_igm,
      self.ARG: self.altitude_arg,
      self.GPS: self.altitude_gps,
    }.get(self.main_altitude_source)
    if source_altitude is not None:
      self.altitude = source_altitude
    self.ascended = compute_mountain_ascended(self)
    super(Mountain, self).save(*args, **kwargs)
    # image_set is many-to-many: it needs a saved mountain (pk) first
    if self.main_image_id and not self.image_set.filter(pk=self.main_image_id).exists():
      self.image_set.add(self.main_image_id)

  def get_first_ascent(self):
    from cerros.derived import compute_mountain_first_ascent
    return compute_mountain_first_ascent(self)

  class Meta:
    verbose_name = "Montaña"
    verbose_name_plural = "Montañas"
    ## REVISAR ESTO, SERÁ EL ORDEN IDEAL?
    ordering = ['id']
    