from rest_framework.filters import OrderingFilter


class CustomOrderingFilter(OrderingFilter):
    def filter_queryset(self, request, queryset, view):
        ordering = self.get_ordering(request, queryset, view)

        if ordering:
            custom_ordering = []
            for field in ordering:
                if field == "fullname":
                    custom_ordering.extend(["name", "surname"])
                elif field == "-fullname":
                    custom_ordering.extend(["-name", "-surname"])
                else:
                    custom_ordering.append(field)
            return queryset.order_by(*custom_ordering)

        return queryset
