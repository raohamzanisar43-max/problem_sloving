from django.contrib import admin
from .models import Contact


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('email', 'name', 'company_name', 'verification', 'is_primary', 'suppressed')
    list_filter = ('verification', 'is_primary', 'suppressed')
