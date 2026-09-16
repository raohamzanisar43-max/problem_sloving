"""
Base collector — all concrete collectors extend this.
"""
import hashlib
import logging
from abc import ABC, abstractmethod

from django.utils import timezone

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """Abstract base for all source collectors."""

    source = None  # set by factory

    def __init__(self, source):
        self.source = source

    @abstractmethod
    def fetch_observations(self, term_query: str, market: str = 'PK') -> list[dict]:
        """
        Fetch raw results for a single search query.
        Returns list of dicts with keys:
          external_id, original_url, canonical_url, title, text, author,
          source_published_at, raw_payload
        """

    def content_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode('utf-8', errors='replace')).hexdigest()[:64]

    def _persist(self, row):
        """
        Store one fetched row idempotently. Returns True when a new Observation
        was created.

        Rows carrying an external_id use the unique (source, external_id)
        constraint. Rows without one — some feeds omit a stable id — fall back
        to the canonical URL and content hash, because a blank external_id is
        excluded from that constraint and would otherwise collapse every such
        row onto a single record.
        """
        from apps.observations.models import Observation

        external_id = (row.get('external_id') or '')[:255]
        text = row.get('text', '') or ''
        canonical = row.get('canonical_url', '') or row.get('original_url', '') or ''
        digest = self.content_hash(text)

        defaults = {
            'original_url': row.get('original_url', '') or '',
            'canonical_url': canonical,
            'title': (row.get('title', '') or '')[:500],
            'text': text,
            'author': (row.get('author', '') or '')[:255],
            'source_published_at': row.get('source_published_at'),
            'content_hash': digest,
            'raw_payload': row.get('raw_payload', {}) or {},
        }

        if external_id:
            _, created = Observation.objects.get_or_create(
                source=self.source,
                external_id=external_id,
                defaults=defaults,
            )
            return created

        exists = Observation.objects.filter(source=self.source, external_id='').filter(
            content_hash=digest
        )
        if canonical:
            exists = Observation.objects.filter(source=self.source, external_id='').filter(
                canonical_url=canonical
            )
        if exists.exists():
            return False
        Observation.objects.create(source=self.source, external_id='', **defaults)
        return True

    def run(self, run_obj, terms):
        """
        Main entry point called by the Celery task.

        Iterates enabled search terms, fetches, deduplicates and persists. The
        caller owns the Run lifecycle; this returns
        ``(fetched, created, duplicates, errors)``.
        """
        run_obj.mark_running()
        fetched_total = 0
        created_total = 0
        duplicate_total = 0
        errors = []

        for term in terms:
            try:
                rows = self.fetch_observations(term.query, term.market)
            except Exception as exc:
                # One failing query must not abandon the remaining terms.
                logger.exception('Collector error for term %s: %s', term.query, exc)
                errors.append(str(exc)[:200])
                continue

            for row in rows:
                fetched_total += 1
                try:
                    if self._persist(row):
                        created_total += 1
                    else:
                        duplicate_total += 1
                except Exception as exc:
                    logger.exception('Could not store row from %s: %s', term.query, exc)
                    errors.append(str(exc)[:200])

        # Only a run that actually reached the source counts as a success.
        if not errors:
            self.source.last_success_at = timezone.now()
        self.source.last_error = '; '.join(errors) if errors else ''
        self.source.save(update_fields=['last_success_at', 'last_error'])

        return fetched_total, created_total, duplicate_total, errors
