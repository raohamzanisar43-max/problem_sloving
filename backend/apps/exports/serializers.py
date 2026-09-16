from rest_framework import serializers

from .models import OutboxEvent, SyncJob, SyncTarget


class SyncTargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncTarget
        fields = ('id', 'name', 'target_type', 'config', 'enabled', 'created_at')
        read_only_fields = ('id', 'created_at')


class SyncJobSerializer(serializers.ModelSerializer):
    target_name = serializers.CharField(source='target.name', read_only=True, default='')

    class Meta:
        model = SyncJob
        fields = (
            'id', 'target', 'target_name', 'state', 'counters', 'error',
            'created_at', 'finished_at',
        )
        read_only_fields = fields


class OutboxEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = OutboxEvent
        fields = (
            'id', 'destination', 'opportunity_id', 'revision', 'event_key',
            'state', 'error', 'created_at', 'processed_at',
        )
        read_only_fields = fields
