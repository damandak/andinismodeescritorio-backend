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
    Image,
)

from django.db.models import Prefetch


# Register your models here.
class MountainAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "prefix",
        "name",
        "altitude_display",
        "ascended",
        "first_absolute_link",
        "main_image_link",
    )
    search_fields = ("id", "prefix__prefix", "name", "altitude")
    list_select_related = (
        "prefix",
    )  # Assuming 'prefix' is a ForeignKey. This optimizes query performance for list pages.

    @admin.display(description="Altitude")
    def altitude_display(self, obj):
        return f"{obj.altitude} m"  # Customize as needed

    @admin.display(description="First Absolute")
    def first_absolute_link(self, obj):
        if obj.first_absolute:
            return obj.first_absolute.name
        return "-"

    @admin.display(description="Main Image")
    def main_image_link(self, obj):
        if obj.main_image:
            return obj.main_image.tb_image_tag
        return "No Image"

    def get_queryset(self, request):
        # If 'main_image' or 'first_absolute' are used in list_display, consider prefetching to optimize queries
        queryset = super().get_queryset(request)
        queryset = queryset.prefetch_related("main_image", Prefetch("first_absolute"))
        return queryset


admin.site.register(Mountain, MountainAdmin)


class MountainInline(admin.TabularInline):
    model = Mountain.mountain_group.through
    extra = 0


admin.site.register(MountainPrefix)


class MountainGroupAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("id", "name")
    inlines = [MountainInline]


admin.site.register(MountainGroup, MountainGroupAdmin)

admin.site.register(Country)
admin.site.register(Region)
admin.site.register(NomenclaturaSummit)
admin.site.register(IGMMap)


class RouteAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "mountain", "first_ascent_year_display")
    list_select_related = ("mountain",)  # Reduce queries for mountain field
    search_fields = ("id", "name", "mountain__name")

    def get_queryset(self, request):
        # Prefetch first_ascent to reduce queries when accessing related ascent objects
        queryset = super().get_queryset(request)
        queryset = queryset.prefetch_related(
            Prefetch("first_ascent", queryset=Ascent.objects.select_related("route"))
        )
        return queryset

    def first_ascent_year_display(self, obj):
        # Access the cached first_ascent from the prefetch_related call
        return obj.first_ascent.date.year if obj.first_ascent else ""

    first_ascent_year_display.admin_order_field = (
        "first_ascent__date"  # Allows column sorting by first_ascent date
    )
    first_ascent_year_display.short_description = "First Ascent Year"


admin.site.register(Route, RouteAdmin)


class AndinistAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "surname")
    search_fields = ("id", "name", "surname", "clubs__name")


admin.site.register(Andinist, AndinistAdmin)


class ClubAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "shortname")
    search_fields = ("id", "name")


admin.site.register(Club, ClubAdmin)


class AscentAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "route_link", "mountain_link", "date")
    search_fields = (
        "id",
        "name",
        "route__name",
        "route__mountain__name",
    )  # Optimized for direct fields and one level of relationship
    list_select_related = (
        "route",
        "route__mountain",
    )  # Optimizes query for route and mountain

    @admin.display(description="Route")
    def route_link(self, obj):
        return obj.route.name

    @admin.display(description="Mountain")
    def mountain_link(self, obj):
        return obj.route.mountain.name

    def get_queryset(self, request):
        # Further optimize queryset if necessary, for example, prefetch_related for many-to-many relationships
        qs = super().get_queryset(request)
        return qs.prefetch_related("andinists", "support_andinists")


admin.site.register(Ascent, AscentAdmin)

admin.site.register(Reference)


class ImageAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "tb_image_tag",
        "image",
        "author",
        "date_captured",
        "location",
    )
    search_fields = ("name", "author", "date_captured", "location")
    list_filter = ("author",)


admin.site.register(Image, ImageAdmin)


class CustomUserAdmin(admin.ModelAdmin):
    exclude = ("password",)
    ordering = ("email",)
    list_display = ("email", "first_name", "last_name", "is_superuser")
    search_fields = ("email", "first_name", "last_name")
    list_filter = ("is_superuser",)


admin.site.register(CustomUser, CustomUserAdmin)
