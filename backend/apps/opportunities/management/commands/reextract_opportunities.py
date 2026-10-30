"""
One-off data-repair command.

Re-runs AI extraction for opportunities that were created while the LLM was
misconfigured (offline stub fallback, or a wrong model name) — so Company,
Website, Country, Budget and Deadline get filled in retroactively using the
now-correctly-configured Gemini client.

Usage:
    python manage.py reextract_opportunities
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.opportunities.models import Opportunity
from apps.scoring.engine import compute_score
from apps.scoring.llm import LLMClient


class Command(BaseCommand):
    help = (
        'Re-runs AI extraction for opportunities with confidence=0.0 '
        '(created while the LLM was stubbed or misconfigured), so Company, '
        'Website, Country, Budget and Deadline get filled in retroactively.'
    )

    def handle(self, *args, **options):
        llm = LLMClient()
        candidates = Opportunity.objects.filter(confidence=0.0)

        total = candidates.count()
        self.stdout.write(f'Found {total} opportunities to re-extract.')

        fixed = 0
        skipped = 0
        for opportunity in candidates:
            link = opportunity.linked_observations.select_related('observation').first()
            if not link or not link.observation.text:
                skipped += 1
                continue

            text = link.observation.text
            fields = llm.extract(text) or {}

            score_result = compute_score(
                intent=fields.get('intent', 'uncertain'),
                kind=fields.get('kind', 'other'),
                categories=fields.get('categories', []),
                published_at=opportunity.source_published_at,
                has_quote=bool(text),
                has_full_text=len(text) > 100,
                email=fields.get('email', ''),
                phone=fields.get('phone', ''),
                source_url=opportunity.source_url,
                deadline=fields.get('deadline'),
            )

            with transaction.atomic():
                opportunity.intent = fields.get('intent', 'uncertain')
                opportunity.kind = fields.get('kind', 'other')
                opportunity.confidence = float(fields.get('confidence') or 0.0)
                opportunity.primary_category = fields.get('primary_category', '') or ''
                opportunity.categories = fields.get('categories', []) or []
                opportunity.technology = fields.get('technology', []) or []
                opportunity.company_name = fields.get('company_name', '') or ''
                opportunity.company_domain = fields.get('company_domain', '') or ''
                opportunity.country = fields.get('country', '') or ''
                opportunity.industry = fields.get('industry', '') or ''
                opportunity.budget_text = fields.get('budget_text', '') or ''
                opportunity.deadline = fields.get('deadline') or None
                opportunity.email = fields.get('email', '') or ''
                opportunity.phone = fields.get('phone', '') or ''
                opportunity.contact_name = fields.get('contact_name', '') or ''
                opportunity.score = score_result['score']
                opportunity.band = score_result['band']
                opportunity.score_factors = score_result['factors']
                opportunity.review_reasons = score_result['review_reasons']
                if score_result.get('status_override'):
                    opportunity.status = score_result['status_override']
                opportunity.revision += 1
                opportunity.save()

            fixed += 1
            label = opportunity.company_name or '(no company found in text)'
            self.stdout.write(f'  [{fixed}/{total}] {opportunity.public_id}: {label}')

        self.stdout.write(self.style.SUCCESS(
            f'Done. Re-extracted {fixed} opportunities, skipped {skipped} (no linked text).'
        ))