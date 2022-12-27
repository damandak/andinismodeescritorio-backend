from django.contrib import admin
from .models import Mountain, MountainPrefix, MountainGroup, Country, Region, NomenclaturaSummit, IGMMap, CustomUser, Route, Andinist, Club, Ascent, Reference

# Register your models here.
admin.site.register(Mountain)
admin.site.register(MountainPrefix)
admin.site.register(MountainGroup)
admin.site.register(Country)
admin.site.register(Region)
admin.site.register(NomenclaturaSummit)
admin.site.register(IGMMap)
admin.site.register(Route)
admin.site.register(Andinist)
admin.site.register(Club)
admin.site.register(Ascent)
admin.site.register(Reference)

class CustomUserAdmin(admin.ModelAdmin):
  exclude = ('password',)
  ordering = ('email',)
  list_display = ('email', 'first_name', 'last_name', 'is_superuser')
  search_fields = ('email', 'first_name', 'last_name')
  list_filter = ('is_superuser',)
  readonly_fields = ('email',)
    
admin.site.register(CustomUser, CustomUserAdmin)
