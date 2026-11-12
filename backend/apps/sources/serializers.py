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
        extra_kwargs = {
            'group_name': {'required': False},
            'source': {'required': False},
        }

    def validate_query(self, value):
        value = ' '.join((value or '').split())
        if not value:
            raise serializers.ValidationError('Keyword cannot be empty.')
        if len(value) > 200:
            raise serializers.ValidationError('Keyword must be 200 characters or fewer.')
        return value

    def validate(self, attrs):
        if self.instance is None and 'source' not in attrs:
            # New keywords go to the web-search collector by default.
            attrs['source'] = (
                Source.objects.filter(connector_type='web_search', enabled=True).first()
                or Source.objects.filter(connector_type='web_search').first()
            )
        query = attrs.get('query', getattr(self.instance, 'query', ''))
        source = attrs.get('source', getattr(self.instance, 'source', None))
        clash = SearchTerm.objects.filter(source=source, query__iexact=query)
        if self.instance is not None:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError({'query': 'This keyword already exists.'})
        return attrs


class RunSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source='source.name', read_only=True, default='')

    class Meta:
        model = Run
        fields = (
            'id', 'source', 'source_name', 'state', 'trigger', 'started_at',
            'finished_at', 'counters', 'estimated_spend', 'error', 'created_at',
        )
        read_only_fields = fields
