"""
Pagination classes.

`StandardPagination` is the project-wide default: it works against any model
because it does not assume a particular ordering field.

`OpportunityCursorPagination` implements the keyset pagination recommended in
the handover for the opportunity queue, and additionally reports the total
count so the queue header can show "N opportunities".
"""
from rest_framework.pagination import (
    CursorPagination as DRFCursorPagination,
    PageNumberPagination,
)
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    """Default paginator — safe for every model in the project."""
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


class OpportunityCursorPagination(DRFCursorPagination):
    """
    Cursor pagination for the opportunity queue.

    The ordering is taken from the view (``-score, -detected_at``) via the
    OrderingFilter; ``ordering`` below is only the fallback used when the view
    does not declare one.
    """
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100
    ordering = '-detected_at'
    cursor_query_param = 'cursor'

    def paginate_queryset(self, queryset, request, view=None):
        # Capture the unpaginated total so the UI can display a real count.
        try:
            self._total = queryset.count()
        except (TypeError, AttributeError):
            self._total = None
        return super().paginate_queryset(queryset, request, view)

    def get_paginated_response(self, data):
        return Response({
            'count': getattr(self, '_total', None),
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data,
        })


# Backwards-compatible alias for the original name.
CursorPagination = OpportunityCursorPagination
