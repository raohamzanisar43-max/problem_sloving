"""
Brave Search collector — uses Brave Web Search API.
"""
import logging
import re
import time
import httpx
from datetime import datetime, timezone as dt_tz
from django.conf import settings
from .base import BaseCollector

logger = logging.getLogger(__name__)

BRAVE_SEARCH_URL = 'https://api.search.brave.com/res/v1/web/search'

# Brave only accepts ALL or a short list of country codes (PK is rejected with a 422),
# so local targeting is done in the query text (e.g. "Pakistan", Roman Urdu) instead.
MARKET_COUNTRY = {'US': 'us', 'UK': 'gb', 'AU': 'au', 'CA': 'ca'}
DEFAULT_COUNTRY = 'ALL'
# Only recent pages are worth a sales follow-up; Brave's lowest-cost freshness bucket
# that still catches ongoing RFPs and forum requests.
FRESHNESS = 'pm'
# Free/standard plans allow roughly one request per second.
REQUEST_GAP_SECONDS = 1.1


class BraveCollector(BaseCollector):
    def fetch_observations(self, term_query: str, market: str = 'PK') -> list[dict]:
        api_key = settings.RADAR.get('BRAVE_API_KEY', '')
        if not api_key:
            logger.warning('BRAVE_API_KEY not set — skipping brave collection')
            return []

        params = {
            'q': term_query,
            'count': 20,
            'country': MARKET_COUNTRY.get((market or '').upper(), DEFAULT_COUNTRY),
            'search_lang': 'en',
            'result_filter': 'web',
            'freshness': FRESHNESS,
        }
        headers = {
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip',
            'X-Subscription-Token': api_key,
        }
        with httpx.Client(timeout=20) as client:
            resp = client.get(BRAVE_SEARCH_URL, params=params, headers=headers)
            time.sleep(REQUEST_GAP_SECONDS)
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
                'source_published_at': _parse_age(r.get('page_age') or r.get('age')),
                'raw_payload': r,
            })
        return observations


_RELATIVE_AGE = re.compile(r'(\d+)\s+(minute|hour|day|week|month|year)s?\s+ago', re.I)
_UNIT_DAYS = {'minute': 0, 'hour': 0, 'day': 1, 'week': 7, 'month': 30, 'year': 365}


def _parse_age(age_str):
    """
    Brave returns `page_age` as ISO-8601 and `age` as ISO or a human string such as
    "2 weeks ago"; return an aware datetime or None.
    """
    if not age_str:
        return None
    text = str(age_str).strip()
    try:
        parsed = datetime.fromisoformat(text.replace('Z', '+00:00'))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt_tz.utc)
    except ValueError:
        pass
    match = _RELATIVE_AGE.search(text)
    if match:
        from datetime import timedelta
        days = int(match.group(1)) * _UNIT_DAYS[match.group(2).lower()]
        return datetime.now(dt_tz.utc) - timedelta(days=days)
    return None
