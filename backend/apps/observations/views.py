import hashlib
import logging

from rest_framework import status, viewsets
from rest_framework.response import Response

from apps.core.permissions import IsSalesStaff
from apps.sources.models import Source
from .models import Observation
from .serializers import ManualObservationSerializer, ObservationSerializer

logger = logging.getLogger(__name__)


class ObservationViewSet(viewsets.ModelViewSet):
    queryset = Observation.objects.select_related('source').all()
    serializer_class = ObservationSerializer
    permission_classes = [IsSalesStaff]
    filterset_fields = ['source', 'is_manual']
    ordering = ['-fetched_at']
    http_method_names = ['get', 'post', 'head', 'options']

    def create(self, request, *args, **kwargs):
        """
        Accept a supported manual or connector observation with provenance and
        immediately qualify it, so a pasted requirement reaches the queue the
        same way a collected one does.
        """
        manual = ManualObservationSerializer(data=request.data)
        if not manual.is_valid():
            # Fall back to the raw connector payload shape.
            return super().create(request, *args, **kwargs)

        data = manual.validated_data
        source, _ = Source.objects.get_or_create(
            connector_type='manual',
            defaults={
                'name': 'Manual references',
                'enabled': True,
                'access_state': 'planned_mvp',
                'planned_route': 'Paste URL and permitted excerpt',
            },
        )
        text = data['text']
        content_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
        observation = Observation.objects.create(
            source=source,
            original_url=data.get('url') or '',
            canonical_url=data.get('url') or '',
            title=data.get('title') or text[:120],
            text=text,
            is_manual=True,
            content_hash=content_hash,
            raw_payload={'company': data.get('company', '')},
        )

        payload = ObservationSerializer(observation).data
        payload['opportunity'] = None

        if data.get('qualify', True):
            from apps.scoring.llm import LLMClient
            from apps.sources.tasks import _extract_and_score
            try:
                opportunity = _extract_and_score(observation, source, LLMClient())
                if opportunity is not None:
                    company = (data.get('company') or '').strip()
                    if company and not opportunity.company_name:
                        opportunity.company_name = company
                        opportunity.save(update_fields=['company_name'])
                    payload['opportunity'] = {
                        'id': str(opportunity.id),
                        'public_id': opportunity.public_id,
                        'requirement': opportunity.requirement,
                        'score': opportunity.score,
                        'band': opportunity.band,
                        'status': opportunity.status,
                        'review_reasons': opportunity.review_reasons,
                    }
            except Exception as exc:
                # The evidence is already stored; qualification can be retried.
                logger.exception('Manual qualification failed for %s: %s', observation.id, exc)
                payload['qualification_error'] = str(exc)[:200]

        return Response(payload, status=status.HTTP_201_CREATED)
