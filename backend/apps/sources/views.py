import logging

from django.core.exceptions import ValidationError
from rest_framework import status, viewsets
from rest_framework.response import Response

from apps.core.permissions import IsAdmin, IsSalesManagerOrAdmin, IsSalesStaff
from .models import Run, SearchTerm, Source
from .serializers import RunSerializer, SearchTermSerializer, SourceSerializer

logger = logging.getLogger(__name__)


class SourceViewSet(viewsets.ModelViewSet):
    queryset = Source.objects.all()
    serializer_class = SourceSerializer
    ordering = ['name']
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_permissions(self):
        if self.action in ('update', 'partial_update', 'destroy', 'create'):
            return [IsAdmin()]
        return [IsSalesStaff()]


class SearchTermViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SearchTerm.objects.filter(enabled=True)
    serializer_class = SearchTermSerializer
    permission_classes = [IsSalesStaff]
    filterset_fields = ['group_name', 'market', 'language']
    ordering = ['group_name', 'query']


class RunViewSet(viewsets.ModelViewSet):
    queryset = Run.objects.select_related('source').all()
    serializer_class = RunSerializer
    filterset_fields = ['source', 'state', 'trigger']
    ordering = ['-created_at']
    http_method_names = ['get', 'post', 'head', 'options']

    def get_permissions(self):
        # Triggering collection spends money against source quotas, so it is a
        # manager/admin action; anyone in sales can read the history.
        if self.action == 'create':
            return [IsSalesManagerOrAdmin()]
        return [IsSalesStaff()]

    def create(self, request, *args, **kwargs):
        """
        POST /v1/runs/ — queue a collection run (returns 202).

        The Run row created here is the one the worker fills in, so a manual
        trigger produces exactly one record whether or not Celery is reachable.
        """
        source_id = request.data.get('source_id')
        trigger = request.data.get('trigger', 'api')
        source = None
        if source_id:
            try:
                source = Source.objects.get(pk=source_id)
            except (Source.DoesNotExist, ValidationError, ValueError, TypeError):
                return Response({'detail': 'Source not found'}, status=status.HTTP_400_BAD_REQUEST)
            if not source.enabled:
                return Response(
                    {'detail': f'Source "{source.name}" is not enabled. Configure its access route first.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        run = Run.objects.create(
            source=source,
            state='queued',
            trigger=trigger,
            counters={'queued': True},
        )

        if source is not None:
            from apps.sources.tasks import collect_source
            try:
                collect_source.delay(str(source.id), run_id=str(run.id))
                run.counters = {'dispatched': True}
            except Exception as exc:
                # No broker reachable: the run stays queued and an operator can
                # pick it up with `python manage.py run_collection`.
                logger.warning('Could not dispatch collection task: %s', exc)
                run.counters = {'queued': True, 'dispatch_error': str(exc)[:200]}
            run.save(update_fields=['counters'])
            run.refresh_from_db()

        serializer = self.get_serializer(run)
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
