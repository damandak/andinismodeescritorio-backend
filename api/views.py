from rest_framework.response import Response
from rest_framework.decorators import api_view

from rest_framework.generics import ListAPIView, RetrieveAPIView

from cerros.models import (
  Andinist,
  Ascent,
  IGMMap,
  MountainPrefix,
  Mountain,
  NomenclaturaSummit,
  Reference,
  Route
)
from .serializers import (
  MountainSerializer,
  BasicMountainSerializer,
  MapMountainSerializer,
  RouteNameSerializer,
  AscentsSerializer,
  AndinistBasicSerializer,
  ReferencesSerializer,
  NomenclaturaSummitSerializer,
  RouteTableSerializer,
  AscentTableSerializer,
  AndinistTableSerializer,
  AscentSerializer,
  RouteSerializer,
  AndinistSerializer
)

from .pagination import TablesPagination

from rest_framework import filters

from decimal import Decimal
from unidecode import unidecode

@api_view(['GET'])
def getData(request):
  person = {'name': 'John', 'age': 30, 'city': 'New York'}
  return Response(person)

class MapMountainsView(ListAPIView):
  queryset = Mountain.objects.all()
  serializer_class = MapMountainSerializer
  http_method_names = ['get']
  pagination_class = None

class BasicMountainsView(ListAPIView):
  queryset = Mountain.objects.prefetch_related('countries').prefetch_related('regions').prefetch_related('mountain_group').all()
  serializer_class = BasicMountainSerializer
  http_method_names = ['get']

class MountainView(RetrieveAPIView):
  queryset = Mountain.objects.all()
  serializer_class = MountainSerializer
  http_method_names = ['get']

class MountainRoutesView(ListAPIView):
  serializer_class = RouteNameSerializer
  http_method_names = ['get']
  pagination = None

  def get_queryset(self):
    queryset = Route.objects.all()
    mountain_id = self.kwargs['pk']
    if mountain_id is not None:
      queryset = queryset.filter(mountain=mountain_id) # Filter the queryset by the mountain parameter
      print(queryset)
    return queryset

class MountainNearbyView(ListAPIView):
  serializer_class = MapMountainSerializer
  http_method_names = ['get']
  pagination = None

  def get_queryset(self):
    queryset = Mountain.objects.all()
    mountain_id = self.kwargs['pk']
    mountain = Mountain.objects.get(pk=mountain_id)
    # check mountains with latitude or longitude near the mountain
    queryset = queryset.filter(latitude__range=(mountain.latitude-Decimal('0.04'), mountain.latitude+Decimal('0.04')))
    queryset = queryset.filter(longitude__range=(mountain.longitude-Decimal('0.04'), mountain.longitude+Decimal('0.04')))
    queryset = queryset.exclude(pk=mountain_id) # Exclude the mountain itself
    return queryset

class MountainAscentsView(ListAPIView):
  serializer_class = AscentsSerializer
  http_method_names = ['get']
  pagination = None

  def get_queryset(self):
    queryset = Ascent.objects.all()
    mountain_id = self.kwargs['pk']
    if mountain_id is not None:
      queryset = queryset.filter(route__mountain=mountain_id) # Filter the queryset by the mountain parameter
      print(queryset)
    return queryset

class AndinistBasicView(RetrieveAPIView):
  serializer_class = AndinistBasicSerializer
  http_method_names = ['get']
  pagination = None

  def get_queryset(self):
    andinist_id = self.kwargs['pk']
    queryset = Andinist.objects.filter(pk=andinist_id)
    return queryset

class RouteNameView(RetrieveAPIView):
  serializer_class = RouteNameSerializer
  http_method_names = ['get']
  pagination = None

  def get_queryset(self):
    route_id = self.kwargs['pk']
    queryset = Route.objects.filter(pk=route_id)
    return queryset

class MountainReferencesView(ListAPIView):
  serializer_class = ReferencesSerializer
  http_method_names = ['get']
  pagination = None

  def get_queryset(self):
    mountain_id = self.kwargs['pk']
    mountain = Mountain.objects.get(pk=mountain_id)
    queryset = mountain.references.all()
    return queryset

class MountainNomenclaturaView(RetrieveAPIView):
  serializer_class = NomenclaturaSummitSerializer
  http_method_names = ['get']
  pagination = None

  def get_queryset(self):
    summit_id = self.kwargs['pk']
    queryset = NomenclaturaSummit.objects.prefetch_related('igm_rectangle').filter(pk=summit_id)
    return queryset

class RouteTableView(ListAPIView):
  search_fields = ['parent_route__name', 'name', 'mountain__name', 'mountain__prefix__prefix', 'mountain__mountain_group__name', 'mountain__regions__name', 'mountain__countries__name']
  filter_backends = (filters.SearchFilter,)
  queryset = Route.objects.all().exclude(first_ascent=None).order_by('-first_ascent')
  serializer_class = RouteTableSerializer
  http_method_names = ['get']
  pagination_class = TablesPagination

class AscentTableView(ListAPIView):
  search_fields = ['name', 'andinists__name', 'andinists__surname', 'route__name', 'route__mountain__name', 'route__mountain__prefix__prefix', 'route__mountain__mountain_group__name', 'route__mountain__regions__name', 'route__mountain__countries__name']
  filter_backends = (filters.SearchFilter,)
  queryset = Ascent.objects.all().order_by('-date')
  serializer_class = AscentTableSerializer
  http_method_names = ['get']
  pagination_class = TablesPagination

class AndinistTableView(ListAPIView):
  search_fields = ['name', 'surname', 'clubs__name', 'nationalities__name']
  filter_backends = (filters.SearchFilter,)
  queryset = Andinist.objects.all().exclude(ascent_count=0).order_by('name')
  serializer_class = AndinistTableSerializer
  http_method_names = ['get']
  pagination_class = TablesPagination

class AscentView(RetrieveAPIView):
  serializer_class = AscentSerializer
  http_method_names = ['get']
  pagination = None

  def get_queryset(self):
    ascent_id = self.kwargs['pk']
    queryset = Ascent.objects.filter(pk=ascent_id)
    return queryset


class AscentReferencesView(ListAPIView):
  serializer_class = ReferencesSerializer
  http_method_names = ['get']
  pagination = None

  def get_queryset(self):
    ascent_id = self.kwargs['pk']
    ascent = Ascent.objects.get(pk=ascent_id)
    queryset = ascent.references.all()
    return queryset

class RouteView(RetrieveAPIView):
  serializer_class = RouteSerializer
  http_method_names = ['get']
  pagination = None

  def get_queryset(self):
    route_id = self.kwargs['pk']
    queryset = Route.objects.filter(pk=route_id)
    return queryset

class RouteReferencesView(ListAPIView):
  serializer_class = ReferencesSerializer
  http_method_names = ['get']
  pagination = None

  def get_queryset(self):
    route_id = self.kwargs['pk']
    route = Route.objects.get(pk=route_id)
    queryset = route.references.all()
    return queryset
  
class RouteAscentsView(ListAPIView):
  serializer_class = AscentsSerializer
  http_method_names = ['get']
  pagination = None

  def get_queryset(self):
    queryset = Ascent.objects.all()
    route_id = self.kwargs['pk']
    if route_id is not None:
      queryset = queryset.filter(route=route_id)
      print(queryset)
    return queryset

class AndinistView(RetrieveAPIView):
  serializer_class = AndinistSerializer
  http_method_names = ['get']
  pagination = None

  def get_queryset(self):
    andinist_id = self.kwargs['pk']
    queryset = Andinist.objects.filter(pk=andinist_id)
    return queryset

class AndinistReferencesView(ListAPIView):
  serializer_class = ReferencesSerializer
  http_method_names = ['get']
  pagination = None

  def get_queryset(self):
    andinist_id = self.kwargs['pk']
    andinist = Andinist.objects.get(pk=andinist_id)
    queryset = andinist.references.all()
    return queryset

class AndinistAscentsView(ListAPIView):
  serializer_class = AscentSerializer
  http_method_names = ['get']
  pagination = None

  def get_queryset(self):
    queryset = Ascent.objects.all()
    andinist_id = self.kwargs['pk']
    if andinist_id is not None:
      queryset = queryset.filter(andinists=andinist_id)
      print(queryset)
    return queryset
