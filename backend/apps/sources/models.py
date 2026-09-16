import uuid
from django.db import models
from django.utils import timezone


class Source(models.Model):
    """
    Connector definition. A source remains disabled until an administrator
    confirms its supported access route (handover §2).
    """
    CONNECTOR_TYPES = [
        ('web_search', 'Licensed web search'),
        ('rss', 'RSS / public website'),
        ('rfp_portal', 'RFP / tender portal'),
        ('x', 'X (Twitter) recent search'),
        ('reddit', 'Reddit Data API'),
        ('linkedin', 'LinkedIn (conditional)'),
        ('manual', 'Manual capture'),
    ]
    ACCESS_STATES = [
        ('disabled', 'Disabled'),
        ('credential_required', 'Credential required'),
        ('select_source_list', 'Select source list'),
        ('account_required', 'Account required'),
        ('commercial_agreement', 'Commercial agreement'),
        ('conditional', 'Conditional'),
        ('planned_mvp', 'Planned MVP'),
        ('ready', 'Ready'),
        ('error', 'Error'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    connector_type = models.CharField(max_length=32, choices=CONNECTOR_TYPES)
    enabled = models.BooleanField(default=False)
    access_state = models.CharField(max_length=32, choices=ACCESS_STATES, default='disabled')
    planned_route = models.CharField(max_length=255, blank=True)
    settings = models.JSONField(default=dict, blank=True)  # non-secret config only
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.connector_type})'


class SearchTerm(models.Model):
    """Connector-specific query expressions (handover §5)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name='search_terms', null=True, blank=True)
    group_name = models.CharField(max_length=80)  # e.g. Software partners
    query = models.TextField()
    market = models.CharField(max_length=32, default='PK')  # PK, GCC, WORLD
    language = models.CharField(max_length=16, default='en')
    enabled = models.BooleanField(default=True)
    schedule_minutes = models.PositiveIntegerField(default=15)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['group_name', 'query']

    def __str__(self):
        return f'{self.group_name}: {self.query[:60]}'


class Run(models.Model):
    """Collection run with counters, spend and error (handover §4, §9)."""
    STATE_CHOICES = [
        ('queued', 'Queued'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('partial', 'Partial'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.ForeignKey(Source, on_delete=models.SET_NULL, null=True, blank=True, related_name='runs')
    state = models.CharField(max_length=16, choices=STATE_CHOICES, default='queued')
    trigger = models.CharField(max_length=32, default='schedule')  # schedule | manual | api
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    counters = models.JSONField(default=dict, blank=True)  # fetched, new, duplicates, errors…
    estimated_spend = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def mark_running(self):
        self.state = 'running'
        self.started_at = timezone.now()
        self.save(update_fields=['state', 'started_at'])

    def mark_finished(self, state='completed', error=''):
        self.state = state
        self.finished_at = timezone.now()
        self.error = error
        self.save(update_fields=['state', 'finished_at', 'error'])
