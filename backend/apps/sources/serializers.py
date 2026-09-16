from rest_framework import serializers
from .models import Source, SearchTerm, Run


class SourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Source
        fields = (
            'id', 'name', 'connector_type', 'enabled', 'access_state',
            'planned_route', 'last_success_at', 'last_error', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'last_success_at', 'last_error', 'created_at', 'updated_at')


class SearchTermSerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchTerm
        fields = (
            'id', 'source', 'group_name', 'query', 'market', 'language',
            'enabled', 'schedule_minutes', 'created_at',
        )
        read_only_fields = ('id', 'created_at')


class RunSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source='source.name', read_only=True, default='')

    class Meta:
        model = Run
        fields = (
            'id', 'source', 'source_name', 'state', 'trigger', 'started_at',
            'finished_at', 'counters', 'estimated_spend', 'error', 'created_at',
        )
        read_only_fields = fields
