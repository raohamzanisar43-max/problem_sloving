from django.conf import settings
from django.utils import timezone
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.permissions import IsSalesStaff
from . import inbox, mailer
from .models import InboxCheck, Notification


class NotificationSerializer(serializers.ModelSerializer):
    opportunity_title = serializers.CharField(source='opportunity.requirement', default='', read_only=True)
    read = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ('id', 'kind', 'title', 'body', 'sender', 'opportunity', 'opportunity_title',
                  'read', 'read_at', 'created_at')

    def get_read(self, obj):
        return obj.read_at is not None


def _inbox_status():
    last = InboxCheck.objects.first()
    return {
        'configured': inbox.is_configured(),
        'mailbox': inbox.inbox_settings().get('USER', '') if inbox.is_configured() else '',
        'last_check': last.created_at if last else None,
        'last_ok': last.ok if last else None,
        'last_error': last.error if last else '',
        'email_alerts': mailer.is_configured(),
        'alert_recipients': settings.TEAM_ALERT_EMAILS,
    }


class NotificationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """The signed-in user's notifications (client replies to proposals)."""
    serializer_class = NotificationSerializer
    permission_classes = [IsSalesStaff]
    pagination_class = None

    def get_queryset(self):
        qs = Notification.objects.filter(recipient=self.request.user).select_related('opportunity')
        if self.request.query_params.get('unread') in ('1', 'true'):
            qs = qs.filter(read_at__isnull=True)
        return qs[:100]

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        count = Notification.objects.filter(recipient=request.user, read_at__isnull=True).count()
        latest = Notification.objects.filter(recipient=request.user, read_at__isnull=True).first()
        return Response({
            'count': count,
            'latest': NotificationSerializer(latest).data if latest else None,
        })

    @action(detail=True, methods=['post'], url_path='read')
    def mark_read(self, request, pk=None):
        updated = Notification.objects.filter(recipient=request.user, pk=pk, read_at__isnull=True)\
            .update(read_at=timezone.now())
        return Response({'updated': updated})

    @action(detail=False, methods=['post'], url_path='read-all')
    def mark_all_read(self, request):
        updated = Notification.objects.filter(recipient=request.user, read_at__isnull=True)\
            .update(read_at=timezone.now())
        return Response({'updated': updated})

    @action(detail=False, methods=['get'], url_path='inbox-status')
    def inbox_status(self, request):
        return Response(_inbox_status())

    @action(detail=False, methods=['post'], url_path='check-inbox')
    def check_inbox(self, request):
        if not inbox.is_configured():
            return Response({**_inbox_status(), 'detail': 'The reply inbox is not configured.'},
                            status=status.HTTP_400_BAD_REQUEST)
        result = inbox.check_inbox()
        return Response({**_inbox_status(), 'result': result})
