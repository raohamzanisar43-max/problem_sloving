from django.contrib import admin
from .models import Opportunity, OpportunityObservation, Activity, Draft, DuplicateCandidate


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = (
        'public_id', 'requirement', 'primary_category', 'score', 'band',
        'status', 'owner', 'detected_at',
    )
    list_filter = ('status', 'band', 'primary_category', 'intent')
    search_fields = ('requirement', 'text', 'company_name', 'email', 'public_id')
    readonly_fields = ('id', 'revision', 'created_at', 'updated_at')


admin.site.register(OpportunityObservation)
admin.site.register(Activity)
admin.site.register(Draft)
admin.site.register(DuplicateCandidate)
