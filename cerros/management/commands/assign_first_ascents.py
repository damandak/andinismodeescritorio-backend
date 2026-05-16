from django.core.management.base import BaseCommand

class Command(BaseCommand):
  help = 'Populate the database with the Cerros data'

  def handle(self, *args, **options):



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