import uuid
from django.db import models


class Contact(models.Model):
    """
    Published business contact with provenance and verification state (handover §8).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    opportunity = models.ForeignKey(
        'opportunities.Opportunity', on_delete=models.CASCADE, related_name='contacts', null=True, blank=True
    )
    company_name = models.CharField(max_length=255, blank=True)
    company_domain = models.CharField(max_length=255, blank=True)
    name = models.CharField(max_length=120, blank=True)
    designation = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    evidence_url = models.URLField(max_length=2000, blank=True)
    verification = models.CharField(
        max_length=32, blank=True,
        help_text='published | verified | invalid | catch_all | unknown',
    )
    is_primary = models.BooleanField(default=False)
    suppressed = models.BooleanField(default=False)
    fetched_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_primary', 'name']

    def __str__(self):
        return self.email or self.name or str(self.id)
