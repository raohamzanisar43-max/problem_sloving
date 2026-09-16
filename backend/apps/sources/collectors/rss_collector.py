"""
RSS / RFP portal collector — uses feedparser.
Feed URLs are stored in Source.settings['feed_urls'] as a list.
"""
import logging
import httpx
from datetime import datetime, timezone as dt_tz
from email.utils import parsedate_to_datetime
from .base import BaseCollector

logger = logging.getLogger(__name__)


class RSSCollector(BaseCollector):
    def fetch_observations(self, term_query: str, market: str = 'PK') -> list[dict]:
        import feedparser  # lazy import so a missing install cannot crash the server

        feed_urls = self.source.settings.get('feed_urls', [])
        if not feed_urls:
            logger.warning('RSS source %s has no feed_urls configured', self.source.name)
            return []

        observations = []
        for url in feed_urls:
            try:
                with httpx.Client(timeout=20) as client:
                    resp = client.get(url, follow_redirects=True)
                    resp.raise_for_status()
                feed = feedparser.parse(resp.text)
                for entry in feed.entries:
                    text = _entry_text(entry)
                    link = getattr(entry, 'link', '')
                    observations.append({
                        'external_id': getattr(entry, 'id', link)[:255],
                        'original_url': link,
                        'canonical_url': link,
                        'title': getattr(entry, 'title', '')[:500],
                        'text': text,
                        'author': getattr(entry, 'author', ''),
                        'source_published_at': _parse_published(entry),
                        'raw_payload': {'feed_url': url, 'entry_id': getattr(entry, 'id', '')},
                    })
            except Exception as exc:
                logger.warning('RSS fetch error %s: %s', url, exc)
        return observations


def _entry_text(entry):
    summary = getattr(entry, 'summary', '') or ''
    content_list = getattr(entry, 'content', [])
    if content_list:
        return content_list[0].get('value', summary)[:4000]
    return summary[:4000]


def _parse_published(entry):
    for field in ('published', 'updated'):
        val = getattr(entry, field + '_parsed', None)
        if val:
            try:
                return datetime(*val[:6], tzinfo=dt_tz.utc)
            except Exception:
                pass
    return None

