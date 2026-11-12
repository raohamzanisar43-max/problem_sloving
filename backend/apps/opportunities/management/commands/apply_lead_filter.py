"""
Re-apply the strict "client wants software built" filter to existing leads.

new/review leads that fail the filter (ignore words, agency sites, job boards,
no client request) are moved to `rejected`; leads hidden by an earlier
re-check that now pass (e.g. an ignore word was removed) go back to `review`.
The Settings screen runs the same check when ignore words are saved.

Usage:
    python manage.py apply_lead_filter --dry-run   # only show what would change
    python manage.py apply_lead_filter
"""
from django.core.management.base import BaseCommand

from apps.sources.content_filters import refilter_existing_leads


class Command(BaseCommand):
    help = 'Re-check existing leads against the client-request filter and ignore words.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show the result without saving.')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        counts = refilter_existing_leads(dry_run=dry_run, log=self.stdout.write)
        prefix = 'Would reject' if dry_run else 'Rejected'
        self.stdout.write(self.style.SUCCESS(
            f"{prefix} {counts['rejected']}, restored {counts['restored']}, kept {counts['kept']}."
        ))
