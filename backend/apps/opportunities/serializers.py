from django.db import transaction
from rest_framework import serializers

from .models import Opportunity, Activity, Draft, DuplicateCandidate


class OpportunityListSerializer(serializers.ModelSerializer):
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = Opportunity
        fields = (
            'id', 'public_id', 'requirement', 'primary_category', 'categories',
            'score', 'band', 'status', 'owner', 'owner_name', 'email',
            'source_published_at', 'detected_at', 'source_url', 'source_name',
'review_reasons', 'intent', 'kind', 'confidence',        )

    def get_owner_name(self, obj):
        if obj.owner:
            return obj.owner.display_name or obj.owner.username
        return ''


class OpportunityDetailSerializer(serializers.ModelSerializer):
    owner_name = serializers.SerializerMethodField()
    score_breakdown = serializers.SerializerMethodField()

    class Meta:
        model = Opportunity
        fields = (
            'id', 'public_id', 'requirement', 'text', 'intent', 'kind', 'confidence',
            'primary_category', 'categories', 'technology',
            'company_name', 'company_domain', 'country', 'industry',
            'budget_text', 'deadline',
            'score', 'band', 'score_factors', 'score_breakdown', 'review_reasons',
            'status', 'owner', 'owner_name', 'notes',
            'source_url', 'source_name', 'source_published_at', 'detected_at',
            'email', 'phone', 'contact_name', 'contact_designation',
            'contact_evidence_url', 'contact_verification',
            'extraction_version', 'revision', 'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'public_id', 'score', 'band', 'score_factors',
            'extraction_version', 'revision', 'created_at', 'updated_at',
        )

    def get_owner_name(self, obj):
        if obj.owner:
            return obj.owner.display_name or obj.owner.username
        return ''

    def get_score_breakdown(self, obj):
        labels = [
            'Buying intent', 'Service match', 'Recency',
            'Evidence quality', 'Contact path', 'Deadline urgency',
        ]
        max_pts = [30, 25, 15, 15, 10, 5]
        factors = obj.score_factors or [0] * 6
        return [
            {'label': labels[i], 'points': factors[i], 'max': max_pts[i]}
            for i in range(6)
        ]


# Extracted facts a sales user may correct by hand. Evidence, provenance and
# score stay read-only so the audit trail always reflects the source.
EDITABLE_DETAIL_FIELDS = (
    'requirement', 'primary_category', 'company_name', 'company_domain',
    'country', 'industry', 'budget_text', 'deadline',
    'email', 'phone', 'contact_name', 'contact_designation',
)


class OpportunityUpdateSerializer(serializers.ModelSerializer):
    expected_revision = serializers.IntegerField(required=False, write_only=True)

    class Meta:
        model = Opportunity
        fields = ('status', 'owner', 'notes', *EDITABLE_DETAIL_FIELDS, 'expected_revision')

    def validate(self, attrs):
        expected = attrs.pop('expected_revision', None)
        if expected is not None and self.instance and expected != self.instance.revision:
            raise serializers.ValidationError({
                'expected_revision': 'Revision conflict – record was modified by another user.',
            })
        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        from apps.exports.outbox import emit_for_opportunity

        actor = self.context['request'].user
        changed = []
        for field in ('status', 'owner', 'notes', *EDITABLE_DETAIL_FIELDS):
            if field in validated_data and getattr(instance, field) != validated_data[field]:
                changed.append(field)
                Activity.objects.create(
                    opportunity=instance,
                    actor=actor,
                    action=f'{field}_change',
                    from_value=str(getattr(instance, field) or '')[:255],
                    to_value=str(validated_data[field] or '')[:255],
                )
        # A hand-entered contact was not found in the source, so it must not
        # keep claiming to be a published one (handover §8).
        if {'email', 'phone'} & set(changed):
            validated_data['contact_verification'] = 'manual' if (
                validated_data.get('email', instance.email) or validated_data.get('phone', instance.phone)
            ) else ''
        instance = super().update(instance, validated_data)
        instance.revision += 1
        instance.save(update_fields=['revision', 'updated_at'])
        if changed:
            # Emitted in the same transaction as the change, keyed by the new
            # revision, so a replay cannot deliver the same edit twice.
            emit_for_opportunity(instance, reason=','.join(changed))
        return instance


class DraftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Draft
        fields = ('id', 'opportunity', 'content', 'model_version', 'created_by', 'created_at')
        read_only_fields = ('id', 'created_by', 'created_at')


class ActivitySerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = ('id', 'action', 'from_value', 'to_value', 'payload', 'actor', 'actor_name', 'created_at')

    def get_actor_name(self, obj):
        if obj.actor:
            return obj.actor.display_name or obj.actor.username
        return ''

class DuplicateCandidateSerializer(serializers.ModelSerializer):
    opportunity_a = OpportunityListSerializer(read_only=True)
    opportunity_b = OpportunityListSerializer(read_only=True)
    reviewer_name = serializers.CharField(source='reviewer.display_name', read_only=True, default='')

    class Meta:
        model = DuplicateCandidate
        fields = [
            'id', 'opportunity_a', 'opportunity_b',
            'similarity', 'decision', 'reviewer_name', 'created_at',
        ]
        read_only_fields = fields
