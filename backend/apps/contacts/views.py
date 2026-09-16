from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.permissions import IsSalesManagerOrAdmin, IsSalesStaff
from .models import Contact
from .serializers import ContactSerializer


class ContactViewSet(viewsets.ModelViewSet):
    """
    Published business contacts with provenance (handover §8).

    Every record keeps the URL the address was published at. A contact is never
    invented: rows are only created from evidence, and suppressing one is a
    manager action so an opt-out cannot be silently undone by the queue.
    """
    serializer_class = ContactSerializer
    filterset_fields = ['opportunity', 'verification', 'is_primary', 'suppressed']
    search_fields = ['company_name', 'name', 'email']
    ordering = ['-is_primary', 'name']
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_permissions(self):
        if self.action in ('suppress', 'destroy'):
            return [IsSalesManagerOrAdmin()]
        return [IsSalesStaff()]

    def get_queryset(self):
        qs = Contact.objects.select_related('opportunity').all()
        user = self.request.user
        if user.role == 'sales_executive' and not user.is_superuser:
            # Mirror the opportunity queue visibility rules.
            qs = qs.filter(
                Q(opportunity__owner=user)
                | Q(opportunity__owner__isnull=True)
                | Q(opportunity__status__in=['new', 'review'])
            )
        return qs.exclude(suppressed=True)

    @action(detail=True, methods=['post'], url_path='suppress')
    def suppress(self, request, pk=None):
        """Honour a do-not-contact request without deleting the evidence trail."""
        contact = self.get_object()
        contact.suppressed = True
        contact.save(update_fields=['suppressed'])
        return Response({'id': str(contact.id), 'suppressed': True}, status=status.HTTP_200_OK)
