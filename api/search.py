"""
Accent- and case-insensitive search for the API.

"Volcán", "volcan" and "VOLCAN" all find "Volcán San José", and a search for
"Cerro El Plomo" matches a mountain whose prefix is "Cerro" and whose name is
"El Plomo": every word must appear in at least one search field.

It uses PostgreSQL's built-in translate() instead of the unaccent extension,
so it needs no extra database permissions.
"""
from django.db import models
from rest_framework.filters import SearchFilter
from unidecode import unidecode

_ACCENTED = "ÁÀÄÂÃÉÈËÊÍÌÏÎÓÒÖÔÕÚÙÜÛÑÇáàäâãéèëêíìïîóòöôõúùüûñç"
_PLAIN = "AAAAAEEEEIIIIOOOOOUUUUNCaaaaaeeeeiiiiooooouuuunc"
assert len(_ACCENTED) == len(_PLAIN)


class SinAcentos(models.Transform):
    """`field__sin_acentos` = the field as lowercase text without accents."""

    lookup_name = "sin_acentos"
    output_field = models.TextField()

    def as_sql(self, compiler, connection):
        lhs, params = compiler.compile(self.lhs)
        sql = f"LOWER(TRANSLATE(CAST({lhs} AS TEXT), %s, %s))"
        return sql, (*params, _ACCENTED, _PLAIN)


# Registered on Field so it also works on numbers and dates (e.g. altitude,
# ascent date), which the old icontains search matched as text.
models.Field.register_lookup(SinAcentos)


def normalize(text):
    return unidecode(text).lower()


class AccentInsensitiveSearchFilter(SearchFilter):
    def get_search_terms(self, request):
        return [normalize(term) for term in super().get_search_terms(request)]

    def construct_search(self, field_name, *args):
        # DRF 3.15+ passes the queryset as a second argument.
        return f"{field_name}__sin_acentos__contains"
