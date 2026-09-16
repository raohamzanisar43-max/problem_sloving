"""
Brave Search collector — uses Brave Web Search API.
"""
import logging
import httpx
from datetime import datetime, timezone as dt_tz
from django.conf import settings
from .base import BaseCollector

logger = logging.getLogger(__name__)

BRAVE_SEARCH_URL = 'https://api.search.brave.com/res/v1/web/search'


class BraveCollector(BaseCollector):
    def fetch_observations(self, term_query: str, market: str = 'PK') -> list[dict]:
        api_key = settings.RADAR.get('BRAVE_API_KEY', '')
        if not api_key:
            logger.warning('BRAVE_API_KEY not set — skipping brave collection')
            return []

        country = 'pk' if market == 'PK' else 'us'
        params = {
            'q': term_query,
            'count': 20,
            'country': country,
            'search_lang': 'en',
            'result_filter': 'web',
        }
        headers = {
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip',
            'X-Subscription-Token': api_key,
        }
        with httpx.Client(timeout=20) as client:
            resp = client.get(BRAVE_SEARCH_URL, params=params, headers=headers)
            resp.raise_for_status()

        results = resp.json().get('web', {}).get('results', [])
        observations = []
        for r in results:
            observations.append({
                'external_id': r.get('url', '')[:255],
                'original_url': r.get('url', ''),
                'canonical_url': r.get('url', ''),
                'title': r.get('title', '')[:500],
                'text': r.get('description', ''),
                'author': '',
                'source_published_at': _parse_age(r.get('age')),
                'raw_payload': r,
            })
        return observations


def _parse_age(age_str):
    """Brave returns 'age' as ISO or human string; return datetime or None."""
    if not age_str:
        return None
    try:
        return datetime.fromisoformat(age_str.replace('Z', '+00:00'))
    except Exception:
        return None

