import logging

from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsSalesManagerOrAdmin, IsSalesStaff
from apps.opportunities.models import Opportunity
from .csv_utils import build_csv
from .graph_adapter import GraphAdapter
from .models import OutboxEvent, SyncJob, SyncTarget
from .serializers import OutboxEventSerializer, SyncJobSerializer, SyncTargetSerializer

logger = logging.getLogger(__name__)


def _visible_opportunities(request):
    """The opportunity queue as this user is allowed to see it."""
    qs = Opportunity.objects.select_related('owner').all()

    service = request.query_params.get('service')
    state = request.query_params.get('status')
    search = request.query_params.get('search')
    if service:
        qs = qs.filter(primary_category=service)
    if state:
        qs = qs.filter(status=state)
    if search:
        qs = qs.filter(Q(requirement__icontains=search) | Q(text__icontains=search))

    user = request.user
    if user.role == 'sales_executive' and not user.is_superuser:
        qs = qs.filter(Q(owner=user) | Q(owner__isnull=True) | Q(status__in=['new', 'review']))

    return qs.order_by('-score', '-detected_at')


class OpportunityCSVExportView(APIView):
    permission_classes = [IsSalesStaff]

    def get(self, request):
        csv_bytes = build_csv(_visible_opportunities(request))
        response = HttpResponse(csv_bytes, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="Novu_Radar_Leads.csv"'
        return response


class SyncTargetViewSet(viewsets.ModelViewSet):
    """Configured cloud workbook destinations. Non-secret config only."""
    queryset = SyncTarget.objects.all()
    serializer_class = SyncTargetSerializer
    ordering = ['name']
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_permissions(self):
        if self.request.method in ('POST', 'PATCH'):
            return [IsSalesManagerOrAdmin()]
        return [IsSalesStaff()]


class SyncJobViewSet(viewsets.ModelViewSet):
    """
    Cloud workbook sync.

    POST runs the Microsoft Graph adapter when it is configured; when it is
    not, the job is recorded as `skipped` with the reason, so the Exports
    screen can state plainly why nothing was written.
    """
    queryset = SyncJob.objects.select_related('target').all()
    serializer_class = SyncJobSerializer
    filterset_fields = ['state', 'target']
    ordering = ['-created_at']
    http_method_names = ['get', 'post', 'head', 'options']

    def get_permissions(self):
        if self.action == 'create':
            return [IsSalesManagerOrAdmin()]
        return [IsSalesStaff()]

    def create(self, request, *args, **kwargs):
        target_id = request.data.get('target_id')
        target = None
        if target_id:
            try:
                target = SyncTarget.objects.get(pk=target_id, enabled=True)
            except (SyncTarget.DoesNotExist, ValueError, TypeError):
                return Response({'detail': 'Sync target not found or disabled'}, status=400)

        job = SyncJob.objects.create(target=target, state='running')
        adapter = GraphAdapter()

        if not adapter.is_configured():
            job.state = 'skipped'
            job.counters = {'rows_written': 0}
            job.error = (
                'Microsoft Graph is not configured. Set MS_GRAPH_CLIENT_ID, '
                'MS_GRAPH_CLIENT_SECRET, MS_GRAPH_TENANT_ID and MS_GRAPH_WORKBOOK_ID, '
                'then retry.'
            )
            job.finished_at = timezone.now()
            job.save(update_fields=['state', 'counters', 'error', 'finished_at'])
            return Response(SyncJobSerializer(job).data, status=status.HTTP_202_ACCEPTED)

        try:
            rows = adapter.append_rows(list(_visible_opportunities(request)[:500]), sync_job=job)
            job.refresh_from_db()
            logger.info('Sync job %s wrote %d rows', job.id, rows)
        except Exception as exc:
            logger.exception('Sync job %s failed: %s', job.id, exc)
            job.state = 'failed'
            job.error = str(exc)[:500]
            job.finished_at = timezone.now()
            job.save(update_fields=['state', 'error', 'finished_at'])

        return Response(SyncJobSerializer(job).data, status=status.HTTP_202_ACCEPTED)


class OutboxEventViewSet(viewsets.ReadOnlyModelViewSet):
    """Delivery ledger — lets an operator see what is pending, done or failed."""
    queryset = OutboxEvent.objects.all()
    serializer_class = OutboxEventSerializer
    permission_classes = [IsSalesManagerOrAdmin]
    filterset_fields = ['state', 'destination']
    ordering = ['-created_at']
