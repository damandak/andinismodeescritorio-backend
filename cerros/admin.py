from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import (
    AndinistClaim,
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
from django.utils.html import format_html

from cerros import location


# --- Review filters: what's missing --------------------------------------------

class MissingFilter(admin.SimpleListFilter):
    """Filter "sin X / con X" for an empty field or relation."""

    lookup = None  # e.g. "altitude__isnull" or "countries__isnull"

    def lookups(self, request, model_admin):
        return (("sin", f"Sin {self.title.lower()}"), ("con", f"Con {self.title.lower()}"))

    def queryset(self, request, queryset):
        if self.value() == "sin":
            return queryset.filter(**{self.lookup: True}).distinct()
        if self.value() == "con":
            return queryset.filter(**{self.lookup: False}).distinct()
        return queryset


class MissingAltitudeFilter(MissingFilter):
    title, parameter_name, lookup = "Altitud", "altitud", "altitude__isnull"


class MissingCoordinatesFilter(MissingFilter):
    title, parameter_name, lookup = "Coordenadas", "coordenadas", "latitude__isnull"

    def queryset(self, request, queryset):
        if self.value() == "sin":
            return queryset.filter(latitude__isnull=True) | queryset.filter(longitude__isnull=True)
        if self.value() == "con":
            return queryset.filter(latitude__isnull=False, longitude__isnull=False)
        return queryset


class MissingCountryFilter(MissingFilter):
    title, parameter_name, lookup = "País", "pais", "countries__isnull"


class MissingRegionFilter(MissingFilter):
    title, parameter_name, lookup = "Región", "region", "regions__isnull"


class MissingDateFilter(MissingFilter):
    title, parameter_name, lookup = "Fecha", "fecha", "date__isnull"


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
        "location_status",
    )
    search_fields = ("id", "prefix__prefix", "name", "altitude")
    list_filter = (
        "location_status",
        MissingCountryFilter,
        MissingRegionFilter,
        MissingAltitudeFilter,
        MissingCoordinatesFilter,
    )
    readonly_fields = ("location_panel",)
    actions = ("use_suggested_location", "mark_location_reviewed", "recalculate_location")

    def get_fields(self, request, obj=None):
        # The location panel and its status right after countries/regions.
        fields = [f for f in super().get_fields(request, obj) if f not in ("location_panel", "location_status")]
        at = fields.index("regions") + 1 if "regions" in fields else len(fields)
        return fields[:at] + ["location_panel", "location_status"] + fields[at:]

    @admin.display(description="Ubicación según coordenadas")
    def location_panel(self, obj):
        if obj is None or obj.pk is None:
            return "Se calcula al guardar."
        colours = {
            Mountain.LOCATION_TO_REVIEW: "#b26b00",
            Mountain.LOCATION_MISMATCH: "#c0392b",
        }
        suggestion = ""
        if obj.suggested_country or obj.suggested_region:
            parts = [x.name for x in (obj.suggested_country, obj.suggested_region) if x]
            suggestion = format_html("<br><strong>Sugerencia:</strong> {}", " · ".join(parts))
        return format_html(
            '<div style="padding:8px 12px;border-left:4px solid {};background:#f8f9fa">'
            "<strong>{}</strong><br>{}{}</div>",
            colours.get(obj.location_status, "#6c757d"),
            obj.get_location_status_display(),
            obj.location_note or "—",
            suggestion,
        )

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        mountain = form.instance
        changed = set(form.changed_data)
        if "location_status" in changed:
            return  # the editor chose the status by hand
        if changed & {"countries", "regions"}:
            # The editor set them: keep the suggestion up to date, mark as reviewed.
            location.check_one(mountain)
            Mountain.objects.filter(pk=mountain.pk).update(location_status=Mountain.LOCATION_REVIEWED)
        elif not change or changed & {"latitude", "longitude"}:
            location.check_one(mountain)

    @admin.action(description="Usar país y región sugeridos (reemplaza los cargados)")
    def use_suggested_location(self, request, queryset):
        done = 0
        for mountain in queryset:
            if mountain.suggested_country or mountain.suggested_region:
                if mountain.suggested_country:
                    mountain.countries.set([mountain.suggested_country])
                if mountain.suggested_region:
                    mountain.regions.set([mountain.suggested_region])
                Mountain.objects.filter(pk=mountain.pk).update(location_status=Mountain.LOCATION_REVIEWED)
                done += 1
        self.message_user(request, f"{done} cerros actualizados con la ubicación sugerida.")

    @admin.action(description="Marcar ubicación como revisada a mano")
    def mark_location_reviewed(self, request, queryset):
        count = queryset.update(location_status=Mountain.LOCATION_REVIEWED)
        self.message_user(request, f"{count} cerros marcados como revisados.")

    @admin.action(description="Recalcular ubicación según coordenadas")
    def recalculate_location(self, request, queryset):
        from cerros import geo

        lookups = location.Lookups()
        try:
            for mountain in queryset:
                location.apply(mountain, location.evaluate(mountain, lookups=lookups))
        finally:
            geo.release_maps()
        self.message_user(request, f"{queryset.count()} cerros recalculados.")
    list_select_related = (
        "prefix",
    )  # Assuming 'prefix' is a ForeignKey. This optimizes query performance for list pages.

    @admin.display(description="Altitude", ordering="altitude")
    def altitude_display(self, obj):
        return f"{obj.altitude} m" if obj.altitude is not None else "—"

    @admin.display(description="First Absolute")
    def first_absolute_link(self, obj):
        if obj.first_absolute:
            return obj.first_absolute.name
        return "-"

    @admin.display(description="Main Image")
    def main_image_link(self, obj):
        if obj.main_image:
            return obj.main_image.tb_image_tag()
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
        if obj.first_ascent and obj.first_ascent.date:
            return obj.first_ascent.date.year
        return ""

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
    list_filter = (MissingDateFilter,)
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
    search_fields = ("name", "author__name", "author__surname", "date_captured", "location")
    list_filter = ("author",)


admin.site.register(Image, ImageAdmin)


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ("email",)


class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = CustomUser
        fields = "__all__"


class CustomUserAdmin(UserAdmin):
    """Users log in with their email. To make someone an editor: tick
    "Es staff" and add them to the "Editores" group."""

    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    ordering = ("email",)
    list_display = ("email", "public_name", "andinist", "is_staff", "is_superuser", "date_joined", "last_login")
    search_fields = ("email", "public_name", "first_name", "last_name")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    autocomplete_fields = ("andinist",)
    readonly_fields = ("last_login", "date_joined", "privacy_accepted_at")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Perfil", {"fields": ("public_name", "andinist", "first_name", "last_name", "privacy_accepted_at")}),
        ("Permisos", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Fechas", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "public_name", "password1", "password2")}),
    )


admin.site.register(CustomUser, CustomUserAdmin)


class AndinistClaimAdmin(admin.ModelAdmin):
    """Requests "this andinist is me". Approving links the account to the profile."""

    list_display = ("user", "andinist", "status", "created_at", "reviewed_by")
    list_filter = ("status",)
    search_fields = ("user__email", "user__public_name", "andinist__name", "andinist__surname")
    list_select_related = ("user", "andinist", "reviewed_by")
    readonly_fields = ("user", "andinist", "message", "created_at", "reviewed_by", "reviewed_at")
    fields = ("user", "andinist", "message", "status", "created_at", "reviewed_by", "reviewed_at")
    actions = ("approve", "reject")

    def has_add_permission(self, request):
        return False

    @admin.action(description="Aprobar (vincula la cuenta con el andinista)")
    def approve(self, request, queryset):
        from django.contrib import messages
        from django.utils import timezone

        done = 0
        for claim in queryset.filter(status=AndinistClaim.PENDING).select_related("user", "andinist"):
            other = CustomUser.objects.filter(andinist=claim.andinist).exclude(pk=claim.user_id).first()
            if other:
                self.message_user(request, f"{claim.andinist} ya está vinculado a {other}.", messages.ERROR)
                continue
            claim.user.andinist = claim.andinist
            claim.user.save(update_fields=["andinist"])
            claim.status, claim.reviewed_by, claim.reviewed_at = AndinistClaim.APPROVED, request.user, timezone.now()
            claim.save()
            done += 1
        self.message_user(request, f"{done} reclamos aprobados.")

    @admin.action(description="Rechazar")
    def reject(self, request, queryset):
        from django.utils import timezone

        count = queryset.filter(status=AndinistClaim.PENDING).update(
            status=AndinistClaim.REJECTED, reviewed_by=request.user, reviewed_at=timezone.now()
        )
        self.message_user(request, f"{count} reclamos rechazados.")


admin.site.register(AndinistClaim, AndinistClaimAdmin)
