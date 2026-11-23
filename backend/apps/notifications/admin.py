from django.contrib import admin

from .models import InboxCheck, InboxMessage, Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'kind', 'recipient', 'sender', 'read_at', 'created_at')
    list_filter = ('kind',)
    search_fields = ('title', 'body', 'sender')


@admin.register(InboxMessage)
class InboxMessageAdmin(admin.ModelAdmin):
    list_display = ('subject', 'sender', 'notified', 'opportunity', 'received_at')
    list_filter = ('notified',)
    search_fields = ('subject', 'sender')


@admin.register(InboxCheck)
class InboxCheckAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'ok', 'scanned', 'notified', 'error')
