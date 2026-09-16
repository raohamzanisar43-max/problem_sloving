from rest_framework import serializers
from .models import Observation


class ObservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Observation
        fields = (
            'id', 'source', 'external_id', 'original_url', 'canonical_url',
            'title', 'text', 'author', 'source_published_at', 'fetched_at',
            'content_hash', 'is_manual',
        )
        read_only_fields = ('id', 'fetched_at', 'content_hash')


class ManualObservationSerializer(serializers.Serializer):
    """Manual capture payload (handover §4)."""
    url = serializers.URLField(required=False, allow_blank=True)
    text = serializers.CharField()
    title = serializers.CharField(required=False, allow_blank=True)
    company = serializers.CharField(required=False, allow_blank=True)
    source_name = serializers.CharField(required=False, default='manual')
    # Set false to store the evidence without running extraction and scoring.
    qualify = serializers.BooleanField(required=False, default=True)
