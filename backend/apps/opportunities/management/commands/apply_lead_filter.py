"""
Re-apply the strict "client wants software built" filter to existing leads.

Opportunities in the `new` / `review` queues that fail the filter (ignore
words, agency sites, job boards, no client request) are moved to `rejected`,
with the reason recorded in review_reasons. Run it again after editing the
Ignore words on the Settings screen.

Usage:
    python manage.py apply_lead_filter --dry-run   # only show what would change
    python manage.py apply_lead_filter
"""
from django.core.management.base import BaseCommand

from apps.opportunities.models import Opportunity
from apps.sources.content_filters import lead_rejection_reason


class Command(BaseCommand):
    help = 'Reject existing new/review opportunities that are not client software requests.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show the result without saving.')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        rejected = kept = 0

        for opp in Opportunity.objects.filter(status__in=['new', 'review']):
            link = opp.linked_observations.select_related('observation').first()
            obs = link.observation if link else None
            reason = lead_rejection_reason(
                title=obs.title if obs else opp.requirement,
                text=obs.text if obs else opp.text,
                url=opp.source_url,
            )
            if not reason:
                kept += 1
                continue

            rejected += 1
            self.stdout.write(f'  reject: {opp.requirement[:70]!r} -> {reason}')
            if not dry_run:
                opp.status = 'rejected'
                opp.review_reasons = [f'Filtered out: {reason}'] + list(opp.review_reasons or [])
                opp.revision += 1
                opp.save(update_fields=['status', 'review_reasons', 'revision'])

        verb = 'Would reject' if dry_run else 'Rejected'
        self.stdout.write(self.style.SUCCESS(f'{verb} {rejected}, kept {kept}.'))
