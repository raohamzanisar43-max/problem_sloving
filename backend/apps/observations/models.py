import uuid
from django.db import models


class Observation(models.Model):
    """
    Normalized source observation. Uniqueness on (source, external_id)
    or canonical_url for idempotent replay (handover §4, §8, §9).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.ForeignKey(
        'sources.Source', on_delete=models.SET_NULL, null=True, blank=True, related_name='observations'
    )
    external_id = models.CharField(max_length=255, blank=True, db_index=True)
    original_url = models.URLField(max_length=2000, blank=True)
    canonical_url = models.URLField(max_length=2000, blank=True, db_index=True)
    title = models.CharField(max_length=500, blank=True)
    text = models.TextField()  # retained excerpt / full text when permitted
    author = models.CharField(max_length=255, blank=True)
    source_published_at = models.DateTimeField(null=True, blank=True)
    fetched_at = models.DateTimeField(auto_now_add=True)
    content_hash = models.CharField(max_length=64, blank=True, db_index=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    is_manual = models.BooleanField(default=False)

    class Meta:
        ordering = ['-fetched_at']
        constraints = [
            models.UniqueConstraint(
                fields=['source', 'external_id'],
                name='uniq_source_external_id',
                condition=~models.Q(external_id=''),
            ),
        ]

    def __str__(self):
        return self.title or self.original_url or str(self.id)
