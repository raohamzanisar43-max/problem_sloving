"""
Run the collection pipeline synchronously, without Celery or Redis.

    python manage.py run_collection                 # every enabled source
    python manage.py run_collection --source "X"    # one source by name or id
    python manage.py run_collection --duplicates    # only the duplicate scan
"""
from django.core.management.base import BaseCommand, CommandError

from apps.sources.models import Source
from apps.sources.tasks import collect_source, find_duplicates


class Command(BaseCommand):
    help = 'Run collection, extraction and scoring in-process (no broker required)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            help='Limit to a single source, by name or UUID.',
        )
        parser.add_argument(
            '--duplicates',
            action='store_true',
            help='Skip collection and only run the duplicate scan.',
        )

    def handle(self, *args, **options):
        if not options['duplicates']:
            sources = Source.objects.filter(enabled=True).exclude(connector_type='manual')
            if options['source']:
                needle = options['source']
                sources = Source.objects.filter(name__iexact=needle)
                if not sources.exists():
                    sources = Source.objects.filter(pk__in=[needle]) if _looks_like_uuid(needle) else sources
                if not sources.exists():
                    raise CommandError(f'No source matches "{needle}".')

            if not sources.exists():
                self.stdout.write(self.style.WARNING(
                    'No enabled sources. Enable one in Django admin and attach its credentials first.'
                ))
            for source in sources:
                self.stdout.write(f'Collecting from {source.name}…')
                try:
                    counters = collect_source(str(source.id))
                except Exception as exc:
                    # One connector failing must never stop the others.
                    self.stdout.write(self.style.ERROR(f'  {source.name} failed: {exc}'))
                    continue
                self.stdout.write(self.style.SUCCESS(f'  {source.name}: {counters}'))

        created = find_duplicates()
        self.stdout.write(self.style.SUCCESS(f'Duplicate scan: {created} new candidate pair(s).'))


def _looks_like_uuid(value):
    import uuid
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, AttributeError, TypeError):
        return False
