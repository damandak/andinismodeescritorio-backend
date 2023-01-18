from django.contrib import admin
from .models import (
  Mountain,
  MountainPrefix,
  MountainGroup,
  Country,
  Region,
  NomenclaturaSummit,
  IGMMap,
  CustomUser,
  Route,
  Andinist,
  Club,
  Ascent,
  Reference,
  Image
)

# Register your models here.
class MountainAdmin(admin.ModelAdmin):
  list_display = ('id', 'prefix', 'name', 'altitude', 'ascended', 'first_absolute', 'main_image')
  search_fields = ('id', 'prefix__prefix', 'name', 'altitude')

admin.site.register(Mountain, MountainAdmin)

admin.site.register(MountainPrefix)
admin.site.register(MountainGroup)
admin.site.register(Country)
admin.site.register(Region)
admin.site.register(NomenclaturaSummit)
admin.site.register(IGMMap)

class RouteAdmin(admin.ModelAdmin):
  list_display = ('id', 'name', 'mountain')
  search_fields = ('id', 'name', 'mountain__name', 'mountain__prefix__prefix')
admin.site.register(Route, RouteAdmin)

class AndinistAdmin(admin.ModelAdmin):
  list_display = ('id', 'name', 'surname')
  search_fields = ('id', 'name', 'surname', 'clubs__name')
admin.site.register(Andinist, AndinistAdmin)

class ClubAdmin(admin.ModelAdmin):
  list_display = ('id', 'name', 'shortname')
  search_fields = ('id', 'name')
admin.site.register(Club, ClubAdmin)

class AscentAdmin(admin.ModelAdmin):
  list_display = ('id', 'name', 'route', 'mountain', 'date')
  search_fields = ('id', 'name', 'route__name', 'route__mountain__name', 'route__mountain__prefix__prefix')
  @admin.display(description='Mountain')
  def mountain(self, obj):
    return obj.route.mountain
admin.site.register(Ascent, AscentAdmin)

admin.site.register(Reference)

class ImageAdmin(admin.ModelAdmin):
  list_display = ('name', 'tb_image_tag', 'image', 'author', 'date_captured', 'location')
  search_fields = ('name', 'author', 'date_captured', 'location')
  list_filter = ('author',)

admin.site.register(Image, ImageAdmin)

class CustomUserAdmin(admin.ModelAdmin):
  exclude = ('password',)
  ordering = ('email',)
  list_display = ('email', 'first_name', 'last_name', 'is_superuser')
  search_fields = ('email', 'first_name', 'last_name')
  list_filter = ('is_superuser',)
  readonly_fields = ('email',)
    
admin.site.register(CustomUser, CustomUserAdmin)
