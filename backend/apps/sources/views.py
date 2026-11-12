import logging

from django.core.exceptions import ValidationError
from rest_framework import status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response

from apps.core.permissions import IsAdmin, IsManagerOrSuperuser, IsSalesManagerOrAdmin, IsSalesStaff
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


CUSTOM_KEYWORD_GROUP = 'Custom keywords'


class SearchTermViewSet(viewsets.ModelViewSet):
    """
    Search keywords the collectors query on every scheduled run.

    GET lists enabled keywords (``?all=1`` includes disabled ones, for the
    Settings screen). Managers, admins and superusers can add, switch on/off
    and delete keywords; the next collection run picks the change up.
    """
    serializer_class = SearchTermSerializer
    filterset_fields = ['group_name', 'market', 'language', 'source']
    ordering = ['group_name', 'query']
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        qs = SearchTerm.objects.select_related('source').all()
        # Only the plain list hides disabled keywords; a disabled keyword can
        # still be fetched, switched back on or deleted by id.
        if self.action == 'list' and self.request.query_params.get('all') not in ('1', 'true', 'yes'):
            qs = qs.filter(enabled=True)
        return qs

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsManagerOrSuperuser()]
        return [IsSalesStaff()]

    def perform_create(self, serializer):
        extra = {}
        if not serializer.validated_data.get('group_name'):
            extra['group_name'] = CUSTOM_KEYWORD_GROUP
        serializer.save(**extra)


class IgnoreKeywordsView(APIView):
    """
    GET  — the ignore words in force.
    PUT  — {"keywords": [...]} saves the list and re-checks existing leads:
           leads matching a new word are hidden, and leads hidden only because
           of a removed word come back to the review queue.
    """

    def get_permissions(self):
        if self.request.method == 'PUT':
            return [IsManagerOrSuperuser()]
        return [IsSalesStaff()]

    def get(self, request):
        from apps.sources.content_filters import get_ignore_keywords
        return Response({'keywords': get_ignore_keywords()})

    def put(self, request):
        from apps.core.models import AppSetting
        from apps.sources.content_filters import _parse_keywords, refilter_existing_leads

        raw = request.data.get('keywords') if isinstance(request.data, dict) else None
        if not isinstance(raw, list) or not all(isinstance(k, str) for k in raw):
            return Response({'detail': 'keywords must be a list of strings.'}, status=400)

        keywords = []
        for kw in _parse_keywords(raw):
            kw = ' '.join(kw.split())
            if len(kw) > 100:
                return Response({'detail': f'"{kw[:30]}..." is longer than 100 characters.'}, status=400)
            if kw not in keywords:
                keywords.append(kw)

        AppSetting.objects.update_or_create(
            pk='ignore_keywords',
            defaults={'value': ', '.join(keywords), 'updated_by': request.user},
        )
        counts = refilter_existing_leads()
        return Response({'keywords': keywords, **counts})


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
