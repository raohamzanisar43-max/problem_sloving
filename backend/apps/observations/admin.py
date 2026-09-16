from django.contrib import admin
from .models import Observation


@admin.register(Observation)
class ObservationAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'source', 'is_manual', 'source_published_at', 'fetched_at')
    list_filter = ('is_manual', 'source')
    search_fields = ('title', 'text', 'original_url', 'external_id')
