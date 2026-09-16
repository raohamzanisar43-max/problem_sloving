import uuid
from django.db import models


class SyncTarget(models.Model):
    """Configured cloud workbook / destination."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    target_type = models.CharField(max_length=32, default='excel_graph')  # excel_graph | sheets
    config = models.JSONField(default=dict, blank=True)  # non-secret
    enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class OutboxEvent(models.Model):
    """Idempotent export / alert event (handover §9, §12)."""
    STATE_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    destination = models.CharField(max_length=64)  # csv | sync_target_id | alert
    opportunity_id = models.UUIDField(null=True, blank=True)
    revision = models.PositiveIntegerField(default=1)
    event_key = models.CharField(max_length=255, unique=True)  # destination:opp:rev
    state = models.CharField(max_length=16, choices=STATE_CHOICES, default='pending')
    payload = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']


class SyncJob(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    target = models.ForeignKey(SyncTarget, on_delete=models.SET_NULL, null=True, blank=True)
    state = models.CharField(max_length=16, default='queued')
    counters = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
