from rest_framework.response import Response
from rest_framework.decorators import api_view
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import F
from django.db.models.functions import ExtractYear


from rest_framework.generics import ListAPIView, RetrieveAPIView

from cerros.models import (
    Andinist,
    Ascent,
    IGMMap,
    MountainPrefix,
    Mountain,
    NomenclaturaSummit,
    Reference,
    Route,
    Image,
    Country,
    Region,
    MountainGroup,
)
from .serializers import (
    MountainSerializer,
    BasicMountainSerializer,
    MapMountainSerializer,
    NearbyMountainSerializer,
    RouteNameSerializer,
    AscentsSerializer,
    AndinistBasicSerializer,
    ReferencesSerializer,
    NomenclaturaSummitSerializer,
    RouteTableSerializer,
    AscentTableSerializer,
    AndinistTableSerializer,
    MountainTableSerializer,
    AscentSerializer,
    RouteSerializer,
    AndinistSerializer,
    ImageSerializer,
    CountrySerializer,
    RegionSerializer,
    MountainPrefixSerializer,
    MountainGroupSerializer,
)

from .pagination import TablesPagination
from .custom_filters import CustomOrderingFilter

from rest_framework import filters

from decimal import Decimal
from unidecode import unidecode
import time


@api_view(["GET"])
def getData(request):
    person = {"name": "John", "age": 30, "city": "New York"}
    return Response(person)


class MountainsView(ListAPIView):
    http_method_names = ["get"]

    def get_serializer_class(self):
        if "nearby" in self.request.query_params:
            return NearbyMountainSerializer
        elif "search" in self.request.query_params:
            return BasicMountainSerializer
        return MapMountainSerializer  # Default to MapMountainSerializer

    def get_queryset(self):
        if "nearby" in self.request.query_params:
            return self.get_nearby_mountains()
        # For map and basic views, optimize queryset with prefetch_related/select_related as needed
        queryset = Mountain.objects.all()
        if self.get_serializer_class() == MapMountainSerializer:
            queryset = queryset.prefetch_related(
                "prefix", "countries", "regions", "mountain_group"
            )
        return queryset

    def get_nearby_mountains(self):
        mountain_id = self.request.query_params.get("nearby")
        mountain = Mountain.objects.only("latitude", "longitude").get(pk=mountain_id)
        decimal_offset = Decimal("0.04")
        return Mountain.objects.exclude(pk=mountain_id).filter(
            latitude__range=(
                mountain.latitude - decimal_offset,
                mountain.latitude + decimal_offset,
            ),
            longitude__range=(
                mountain.longitude - decimal_offset,
                mountain.longitude + decimal_offset,
            ),
        )

    def paginate_queryset(self, queryset):
        if "no_pagination" in self.request.query_params:
            return None
        return super().paginate_queryset(queryset)

    def list(self, request, *args, **kwargs):
        start_time = time.time()
        queryset = self.filter_queryset(self.get_queryset())

        if "no_pagination" in self.request.query_params:
            serializer = self.get_serializer(queryset, many=True)
            end_time = time.time()
            print(
                f"API call duration without pagination: {end_time - start_time} seconds."
            )
            return Response(serializer.data)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            end_time = time.time()
            print(
                f"API call duration with pagination: {end_time - start_time} seconds."
            )
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        end_time = time.time()
        print(
            f"API call duration without pagination condition met: {end_time - start_time} seconds."
        )
        return Response(serializer.data)


class MountainView(RetrieveAPIView):
    queryset = Mountain.objects.all()
    serializer_class = MountainSerializer
    http_method_names = ["get"]

    def get_queryset(self):
        queryset = Mountain.objects.prefetch_related(
            "countries", "regions", "mountain_group"
        ).all()
        return queryset


class MountainRoutesView(ListAPIView):
    serializer_class = RouteNameSerializer
    http_method_names = ["get"]
    pagination = None

    def get_queryset(self):
        queryset = Route.objects.all()
        mountain_id = self.kwargs["pk"]
        if mountain_id is not None:
            queryset = queryset.prefetch_related("mountain").filter(
                mountain=mountain_id
            )
        return queryset


class MountainAscentsView(ListAPIView):
    serializer_class = AscentsSerializer
    http_method_names = ["get"]
    pagination = None

    def get_queryset(self):
        queryset = Ascent.objects.all()
        mountain_id = self.kwargs["pk"]
        if mountain_id is not None:
            queryset = (
                queryset.prefetch_related("route")
                .prefetch_related("route__mountain")
                .prefetch_related("andinists")
                .filter(route__mountain=mountain_id)
            )  # Filter the queryset by the mountain parameter
        return queryset


class AndinistBasicView(RetrieveAPIView):
    serializer_class = AndinistBasicSerializer
    http_method_names = ["get"]
    pagination = None

    def get_queryset(self):
        andinist_id = self.kwargs["pk"]
        queryset = Andinist.objects.filter(pk=andinist_id)
        return queryset


class RouteNameView(RetrieveAPIView):
    serializer_class = RouteNameSerializer
    http_method_names = ["get"]
    pagination = None

    def get_queryset(self):
        route_id = self.kwargs["pk"]
        queryset = Route.objects.filter(pk=route_id)
        return queryset


class MountainReferencesView(ListAPIView):
    serializer_class = ReferencesSerializer
    http_method_names = ["get"]
    pagination = None

    def get_queryset(self):
        mountain_id = self.kwargs["pk"]
        mountain = Mountain.objects.get(pk=mountain_id)
        queryset = mountain.references.all()
        return queryset


class MountainNomenclaturaView(RetrieveAPIView):
    serializer_class = NomenclaturaSummitSerializer
    http_method_names = ["get"]
    pagination = None

    def get_queryset(self):
        summit_id = self.kwargs["pk"]
        queryset = NomenclaturaSummit.objects.prefetch_related("igm_rectangle").filter(
            pk=summit_id
        )
        return queryset


class RouteTableView(ListAPIView):
    search_fields = [
        "parent_route__name",
        "name",
        "mountain__name",
        "mountain__prefix__prefix",
        "mountain__mountain_group__name",
        "mountain__regions__name",
        "mountain__countries__name",
    ]
    ordering_fields = [
        "name",
        "mountain_name",
        "first_ascent_year",
    ]
    filter_backends = (filters.SearchFilter, CustomOrderingFilter)
    queryset = (
        Route.objects.annotate(
            mountain_name=F("mountain__name"),
            first_ascent_year=ExtractYear("first_ascent__date"),
        )
        .prefetch_related("mountain")
        .all()
        .exclude(first_ascent=None)
        .order_by("-first_ascent")
    )
    serializer_class = RouteTableSerializer
    http_method_names = ["get"]
    pagination_class = TablesPagination


class AscentTableView(ListAPIView):
    search_fields = [
        "name",
        "date",
        "andinists__name",
        "andinists__surname",
        "route__name",
        "route__mountain__name",
        "route__mountain__prefix__prefix",
        "route__mountain__mountain_group__name",
        "route__mountain__regions__name",
        "route__mountain__countries__name",
    ]
    ordering_fields = ["name", "date", "mountain_name", "route_name"]
    filter_backends = (
        filters.SearchFilter,
        CustomOrderingFilter,
    )
    queryset = (
        Ascent.objects.annotate(route_name=F("route__name"))
        .annotate(mountain_name=F("route__mountain__name"))
        .prefetch_related("andinists", "route", "route__mountain")
        .all()
        .order_by("-date")
    )
    serializer_class = AscentTableSerializer
    http_method_names = ["get"]
    pagination_class = TablesPagination


class AndinistTableView(ListAPIView):
    search_fields = ["name", "surname", "clubs__name", "nationalities__name"]
    ordering_fields = [
        "fullname",
        "ascent_count",
        "new_routes_count",
        "first_ascent_count",
    ]
    filter_backends = (
        filters.SearchFilter,
        CustomOrderingFilter,
    )
    queryset = (
        Andinist.objects.prefetch_related("clubs", "nationalities")
        .all()
        .exclude(ascent_count=0)
        .order_by("name")
    )
    serializer_class = AndinistTableSerializer
    http_method_names = ["get"]
    pagination_class = TablesPagination


class AscentView(RetrieveAPIView):
    serializer_class = AscentSerializer
    http_method_names = ["get"]
    pagination = None

    def get_queryset(self):
        ascent_id = self.kwargs["pk"]
        queryset = Ascent.objects.filter(pk=ascent_id)
        return queryset


class AscentReferencesView(ListAPIView):
    serializer_class = ReferencesSerializer
    http_method_names = ["get"]
    pagination = None

    def get_queryset(self):
        ascent_id = self.kwargs["pk"]
        ascent = Ascent.objects.get(pk=ascent_id)
        queryset = ascent.references.all()
        return queryset


class RouteView(RetrieveAPIView):
    serializer_class = RouteSerializer
    http_method_names = ["get"]
    pagination = None

    def get_queryset(self):
        route_id = self.kwargs["pk"]
        queryset = Route.objects.filter(pk=route_id)
        return queryset


class RouteReferencesView(ListAPIView):
    serializer_class = ReferencesSerializer
    http_method_names = ["get"]
    pagination = None

    def get_queryset(self):
        route_id = self.kwargs["pk"]
        route = Route.objects.get(pk=route_id)
        queryset = route.references.all()
        return queryset


class RouteAscentsView(ListAPIView):
    serializer_class = AscentsSerializer
    http_method_names = ["get"]
    pagination = None

    def get_queryset(self):
        queryset = Ascent.objects.all()
        route_id = self.kwargs["pk"]
        if route_id is not None:
            queryset = queryset.filter(route=route_id)
        return queryset


class AndinistView(RetrieveAPIView):
    serializer_class = AndinistSerializer
    http_method_names = ["get"]
    pagination = None

    def get_queryset(self):
        andinist_id = self.kwargs["pk"]
        queryset = Andinist.objects.filter(pk=andinist_id)
        return queryset


class AndinistReferencesView(ListAPIView):
    serializer_class = ReferencesSerializer
    http_method_names = ["get"]
    pagination = None

    def get_queryset(self):
        andinist_id = self.kwargs["pk"]
        andinist = Andinist.objects.get(pk=andinist_id)
        queryset = andinist.references.all()
        return queryset


class AndinistAscentsView(ListAPIView):
    serializer_class = AscentSerializer
    http_method_names = ["get"]
    pagination = None

    def get_queryset(self):
        queryset = Ascent.objects.all()
        andinist_id = self.kwargs["pk"]
        if andinist_id is not None:
            queryset = queryset.filter(andinists=andinist_id)
        return queryset


class ImageView(RetrieveAPIView):
    serializer_class = ImageSerializer
    http_method_names = ["get"]
    pagination = None

    def get_queryset(self):
        image_id = self.kwargs["pk"]
        queryset = Image.objects.filter(pk=image_id)
        return queryset


class CountriesView(ListAPIView):
    serializer_class = CountrySerializer
    http_method_names = ["get"]
    pagination = None

    def get_queryset(self):
        queryset = Country.objects.all()
        return queryset


class RegionsView(ListAPIView):
    serializer_class = RegionSerializer
    http_method_names = ["get"]
    pagination = None

    def get_queryset(self):
        queryset = Region.objects.all()
        return queryset


class MountainGroupsView(ListAPIView):
    serializer_class = MountainGroupSerializer
    http_method_names = ["get"]
    pagination = None

    def get_queryset(self):
        queryset = MountainGroup.objects.all()
        return queryset


class MountainPrefixesView(ListAPIView):
    serializer_class = MountainPrefixSerializer
    http_method_names = ["get"]
    pagination = None

    def get_queryset(self):
        queryset = MountainPrefix.objects.all()
        return queryset
