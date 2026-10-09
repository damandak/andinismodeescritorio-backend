from rest_framework import pagination
from rest_framework.response import Response


class TablesPagination(pagination.PageNumberPagination):
  page_size = 10
  page_size_query_param = 'page_size'
  max_page_size = 100
  page_query_param = 'page'


class AllResultsPagination(pagination.BasePagination):
  """Return every item, in the same {count, next, previous, results} envelope
  as the paginated endpoints, so existing clients keep working.

  Used for short lists that must never be cut (a mountain's routes, ascents
  and references; filter options). Before, those views set `pagination = None`,
  which DRF ignores, so they silently returned only the first 10 items.
  """

  def paginate_queryset(self, queryset, request, view=None):
    self.items = list(queryset)
    return self.items

  def get_paginated_response(self, data):
    return Response({
      'count': len(self.items),
      'next': None,
      'previous': None,
      'results': data,
    })
