from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters import rest_framework as filters

from apps.core.pagination import OpportunityCursorPagination
from apps.core.permissions import IsAdmin, IsSalesManagerOrAdmin, IsSalesStaff
from .models import Opportunity, Draft, Activity, DuplicateCandidate
from .serializers import (
    OpportunityListSerializer,
    OpportunityDetailSerializer,
    OpportunityUpdateSerializer,
    DraftSerializer,
    ActivitySerializer,
    DuplicateCandidateSerializer,
)


_SINCE_WINDOWS = {'24h': timedelta(hours=24), '7d': timedelta(days=7), '30d': timedelta(days=30)}


class OpportunityFilter(filters.FilterSet):
    service = filters.CharFilter(field_name='primary_category')
    status = filters.CharFilter(field_name='status')
    intent = filters.CharFilter(field_name='intent')
    kind = filters.CharFilter(field_name='kind')
    owner = filters.NumberFilter(field_name='owner_id')
    band = filters.CharFilter(field_name='band')
    search = filters.CharFilter(method='filter_search')
    # "Only the latest N" window, evaluated by the DB against the full table —
    # not a client-side filter over whatever page happened to load, which
    # silently hides recent leads that didn't also score high enough to be
    # on the first page. ?since=24h / 7d / 30d.
    since = filters.CharFilter(method='filter_since')

    class Meta:
        model = Opportunity
        fields = ['service', 'status', 'intent', 'kind', 'owner', 'band']

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(requirement__icontains=value) | Q(text__icontains=value) | Q(company_name__icontains=value)
        )

    def filter_since(self, queryset, name, value):
        window = _SINCE_WINDOWS.get(value)
        if not window:
            return queryset
        return queryset.filter(source_published_at__gte=timezone.now() - window)


class OpportunityViewSet(viewsets.ModelViewSet):
    """
    Role policy (handover §11):
      · sales executive — read the queue, work their own leads, write drafts
      · sales manager   — the above, plus create records and reassign
      · administrator   — the above, plus delete
    """
    permission_classes = [IsSalesStaff]
    pagination_class = OpportunityCursorPagination
    filterset_class = OpportunityFilter
    search_fields = ['requirement', 'text', 'company_name']
    ordering_fields = ['score', 'detected_at', 'source_published_at']
    ordering = ['-score', '-detected_at']

    def get_permissions(self):
        if self.action == 'destroy':
            return [IsAdmin()]
        if self.action == 'create':
            return [IsSalesManagerOrAdmin()]
        return [IsSalesStaff()]

    def get_queryset(self):
        qs = Opportunity.objects.select_related('owner').all()
        user = self.request.user
        # Executives see only assigned + unassigned (demo policy); managers see all
        if user.role == 'sales_executive' and not user.is_superuser:
            qs = qs.filter(Q(owner=user) | Q(owner__isnull=True) | Q(status='new') | Q(status='review'))
        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return OpportunityListSerializer
        if self.action in ('partial_update', 'update'):
            return OpportunityUpdateSerializer
        return OpportunityDetailSerializer

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        # Return full detail after update
        return Response(OpportunityDetailSerializer(instance, context={'request': request}).data)

    @action(detail=True, methods=['post'], url_path='drafts')
    def create_draft(self, request, pk=None):
        opportunity = self.get_object()
        if opportunity.status not in ('reviewed', 'contacted', 'meeting', 'proposal'):
            return Response(
                {'detail': 'Only reviewed leads can produce a sales draft.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Use provided content if given, else generate with LLM
        provided = request.data.get('content', '')
        if provided:
            content = provided
            model_version = 'manual'
        else:
            from apps.scoring.llm import LLMClient
            client = LLMClient()
            content, model_version = client.draft(opportunity)
        draft = Draft.objects.create(
            opportunity=opportunity,
            content=content,
            model_version=model_version,
            created_by=request.user,
        )
        Activity.objects.create(
            opportunity=opportunity,
            actor=request.user,
            action='draft_created',
            to_value=model_version,
        )
        return Response(DraftSerializer(draft).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='draft-list')
    def draft_list(self, request, pk=None):
        opportunity = self.get_object()
        return Response(DraftSerializer(opportunity.drafts.all()[:20], many=True).data)

    @action(detail=True, methods=['get'], url_path='activities')
    def activities(self, request, pk=None):
        opportunity = self.get_object()
        acts = opportunity.activities.select_related('actor').all()[:50]
        return Response(ActivitySerializer(acts, many=True).data)

    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        qs = self.get_queryset()
        return Response({
            'collected': qs.count(),
            'explicit_buyers': qs.filter(intent='buyer').exclude(status__in=['rejected', 'closed']).count(),
            'awaiting_review': qs.filter(status='review').count(),
            'published_email': qs.exclude(email='').count(),
        })

    @action(detail=False, methods=['get'], url_path='pipeline')
    def pipeline(self, request):
        stages = ['reviewed', 'contacted', 'meeting', 'proposal', 'won']
        qs = self.get_queryset()
        result = {}
        for stage in stages:
            items = qs.filter(status=stage).order_by('-score')[:20]
            result[stage] = OpportunityListSerializer(items, many=True).data
        return Response(result)


class DuplicateCandidateViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = DuplicateCandidateSerializer
    filterset_fields = ['decision']
    ordering = ['-created_at']

    def get_permissions(self):
        # Merging records is a sales-manager decision (handover §11).
        if self.action == 'resolve':
            return [IsSalesManagerOrAdmin()]
        return [IsSalesStaff()]

    def get_queryset(self):
        return DuplicateCandidate.objects.select_related(
            'opportunity_a', 'opportunity_b', 'reviewer'
        ).order_by('-created_at')

    @action(detail=True, methods=['post'], url_path='resolve')
    def resolve(self, request, pk=None):
        candidate = self.get_object()
        decision = request.data.get('decision')
        if decision not in ('accepted', 'rejected'):
            return Response({'detail': 'decision must be accepted or rejected'}, status=400)
        if candidate.decision != 'pending':
            return Response(
                {'detail': 'This pair was already resolved as ' + candidate.decision + '.'},
                status=status.HTTP_409_CONFLICT,
            )

        with transaction.atomic():
            candidate.decision = decision
            candidate.reviewer = request.user
            candidate.save(update_fields=['decision', 'reviewer'])
            if decision == 'accepted':
                # Soft-merge: close the lower-scored duplicate and record which
                # opportunity survived, so the merge can be audited later.
                a, b = candidate.opportunity_a, candidate.opportunity_b
                loser, winner = (a, b) if a.score <= b.score else (b, a)
                winner_ref = winner.public_id or str(winner.id)
                loser.status = 'closed'
                prefix = loser.notes + '\n' if loser.notes else ''
                loser.notes = prefix + '[Merged into ' + winner_ref + ' via duplicate review]'
                loser.revision += 1
                loser.save(update_fields=['status', 'notes', 'revision'])
                Activity.objects.create(
                    opportunity=loser,
                    actor=request.user,
                    action='duplicate_merged',
                    to_value=winner_ref,
                )
                from apps.exports.outbox import emit_for_opportunity
                emit_for_opportunity(loser, reason='duplicate_merged')

        return Response(DuplicateCandidateSerializer(candidate).data)