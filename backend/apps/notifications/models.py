"""
In-app notifications, fed by the reply inbox: when a client answers a proposal
(by email, or through a marketplace's email alert) the sales team sees it here.
"""
import uuid

from django.conf import settings
from django.db import models


class Notification(models.Model):
    KIND_CHOICES = [
        ('client_reply', 'Client replied'),
        ('marketplace_message', 'Marketplace message'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                  related_name='notifications')
    opportunity = models.ForeignKey('opportunities.Opportunity', on_delete=models.CASCADE,
                                    null=True, blank=True, related_name='notifications')
    kind = models.CharField(max_length=32, choices=KIND_CHOICES, default='client_reply')
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    sender = models.CharField(max_length=255, blank=True)
    message_id = models.CharField(max_length=255, blank=True, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['recipient', 'read_at'])]

    def __str__(self):
        return self.title


class InboxMessage(models.Model):
    """Every email already looked at, so each one is processed only once."""
    message_id = models.CharField(max_length=255, unique=True)
    subject = models.CharField(max_length=255, blank=True)
    sender = models.CharField(max_length=255, blank=True)
    opportunity = models.ForeignKey('opportunities.Opportunity', on_delete=models.SET_NULL,
                                    null=True, blank=True)
    notified = models.BooleanField(default=False)
    received_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class InboxCheck(models.Model):
    """Outcome of one inbox check, shown on the Notifications page."""
    ok = models.BooleanField(default=True)
    error = models.CharField(max_length=500, blank=True)
    scanned = models.IntegerField(default=0)
    notified = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
