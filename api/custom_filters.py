from django.db.models import F
from rest_framework.filters import OrderingFilter

# Names the frontend sorts by that are not model fields.
ORDERING_ALIASES = {
    "fullname": ["name", "surname"],
    "difficulty": ["alpine_grade"],
}


class CustomOrderingFilter(OrderingFilter):
    """OrderingFilter with aliases and empty values always last.

    Only the view's ordering_fields are accepted (anything else is ignored,
    instead of the 500 a raw order_by() produced). Rows with an empty value
    (no altitude, no date, ...) go to the end in both directions, so sorting
    by altitude descending starts with the highest mountain, not with the
    ones that have no altitude.
    """

    def filter_queryset(self, request, queryset, view):
        ordering = self.get_ordering(request, queryset, view)
        if not ordering:
            return queryset

        expressions = []
        for term in ordering:
            descending = term.startswith("-")
            name = term.lstrip("-")
            for field in ORDERING_ALIASES.get(name, [name]):
                expr = F(field)
                expressions.append(
                    expr.desc(nulls_last=True) if descending else expr.asc(nulls_last=True)
                )
        # Stable order between equal values, so pages don't repeat rows.
        expressions.append(F("pk").asc())
        return queryset.order_by(*expressions)
