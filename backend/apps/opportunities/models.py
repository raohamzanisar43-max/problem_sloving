import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


SERVICE_CATEGORIES = [
    ('CUSTOM_DEV', 'Custom development'),
    ('MOBILE_APP', 'Mobile app'),
    ('WEBSITE', 'Website'),
    ('ERP', 'ERP'),
    ('CRM', 'CRM'),
    ('LMS', 'LMS'),
    ('AI_AUTOMATION', 'AI / Automation'),
    ('STAFF_AUGMENTATION', 'Staff augmentation'),
    ('MANAGED_IT', 'Managed IT'),
    ('CLOUD_DEVOPS', 'Cloud / DevOps'),
    ('CYBERSECURITY', 'Cybersecurity'),
    ('COMPLIANCE_AML', 'AML & compliance'),
    ('ACCOUNTING_TAX', 'Accounting & tax'),
    ('GOVERNANCE_AUDIT', 'Governance & audit'),
]

INTENT_CHOICES = [
    ('buyer', 'Buyer'),
    ('nonbuyer', 'Non-buyer'),
    ('uncertain', 'Uncertain'),
]

KIND_CHOICES = [
    ('direct_purchase', 'Direct purchase request'),
    ('rfp', 'RFP / tender'),
    ('agency_staffing', 'Agency / staffing request'),
    ('hiring_signal', 'Hiring signal'),
    ('indirect_pain', 'Indirect pain'),
    ('seller_promotion', 'Seller promotion'),
    ('other', 'Other'),
]

STATUS_CHOICES = [
    ('new', 'New'),
    ('review', 'Review'),
    ('reviewed', 'Reviewed'),
    ('contacted', 'Contacted'),
    ('meeting', 'Meeting'),
    ('proposal', 'Proposal'),
    ('won', 'Won'),
    ('rejected', 'Rejected'),
    ('closed', 'Closed'),
]

BAND_CHOICES = [
    ('Hot', 'Hot'),
    ('High potential', 'High potential'),
    ('Review', 'Review'),
    ('Archive', 'Archive'),
]


class Opportunity(models.Model):
    """
    Qualified opportunity with evidence, score and sales state (handover §3–§9).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Human-friendly demo id kept for prototype compatibility
    public_id = models.CharField(max_length=32, unique=True, blank=True)

    requirement = models.CharField(max_length=500)
    text = models.TextField(blank=True)  # original evidence excerpt
    intent = models.CharField(max_length=16, choices=INTENT_CHOICES, default='uncertain')
    kind = models.CharField(max_length=32, choices=KIND_CHOICES, default='other')
    confidence = models.FloatField(default=0.0)

    primary_category = models.CharField(max_length=32, choices=SERVICE_CATEGORIES, blank=True)
    categories = models.JSONField(default=list, blank=True)  # list of SERVICE_CATEGORIES
    technology = models.JSONField(default=list, blank=True)

    company_name = models.CharField(max_length=255, blank=True)
    company_domain = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=64, blank=True)
    industry = models.CharField(max_length=120, blank=True)
    budget_text = models.CharField(max_length=120, blank=True)
    deadline = models.DateField(null=True, blank=True)

    score = models.PositiveSmallIntegerField(default=0)
    band = models.CharField(max_length=32, choices=BAND_CHOICES, default='Review')
    score_factors = models.JSONField(default=list, blank=True)  # [intent, service, recency, evidence, contact, deadline]
    review_reasons = models.JSONField(default=list, blank=True)

    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='new')
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='owned_opportunities',
    )
    notes = models.TextField(blank=True)

    source_url = models.URLField(max_length=2000, blank=True)
    source_name = models.CharField(max_length=80, default='example_web')
    source_published_at = models.DateTimeField(null=True, blank=True)
    detected_at = models.DateTimeField(default=timezone.now, db_index=True)

    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    contact_name = models.CharField(max_length=120, blank=True)
    contact_designation = models.CharField(max_length=120, blank=True)
    contact_evidence_url = models.URLField(max_length=2000, blank=True)
    contact_verification = models.CharField(max_length=32, blank=True)  # published | verified | invalid | …

    extraction_version = models.CharField(max_length=32, default='v1')
    revision = models.PositiveIntegerField(default=1)  # optimistic concurrency

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-score', '-detected_at']
        verbose_name_plural = 'opportunities'
        indexes = [
            models.Index(fields=['status', 'score']),
            models.Index(fields=['primary_category', 'status']),
        ]

    def __str__(self):
        return self.requirement[:80]

    def save(self, *args, **kwargs):
        if not self.public_id:
            self.public_id = f'demo-{str(self.id)[:8]}'
        super().save(*args, **kwargs)


class OpportunityObservation(models.Model):
    """Many observations can link to one canonical opportunity."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name='linked_observations')
    observation = models.ForeignKey(
        'observations.Observation', on_delete=models.CASCADE, related_name='linked_opportunities'
    )
    is_canonical = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('opportunity', 'observation')


class Activity(models.Model):
    """Status history, notes, follow-ups."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name='activities')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=64)  # status_change, note, assignment, …
    from_value = models.CharField(max_length=255, blank=True)
    to_value = models.CharField(max_length=255, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'activities'


class Draft(models.Model):
    """Sales outreach draft – never auto-sent in MVP."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name='drafts')
    content = models.TextField()
    model_version = models.CharField(max_length=64, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class DuplicateCandidate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    opportunity_a = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name='dup_as_a')
    opportunity_b = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name='dup_as_b')
    similarity = models.FloatField(default=0.0)
    decision = models.CharField(
        max_length=16,
        choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('rejected', 'Rejected')],
        default='pending',
    )
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
