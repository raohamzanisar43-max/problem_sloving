from django.contrib import admin
from .models import Source, SearchTerm, Run


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'connector_type', 'enabled', 'access_state', 'last_success_at')
    list_filter = ('connector_type', 'enabled', 'access_state')


@admin.register(SearchTerm)
class SearchTermAdmin(admin.ModelAdmin):
    list_display = ('group_name', 'query', 'market', 'language', 'enabled')
    list_filter = ('group_name', 'market', 'enabled')


@admin.register(Run)
class RunAdmin(admin.ModelAdmin):
    list_display = ('id', 'source', 'state', 'trigger', 'started_at', 'finished_at', 'estimated_spend')
    list_filter = ('state', 'trigger')
