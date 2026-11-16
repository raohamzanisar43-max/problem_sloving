"""
Brave Search collector — uses Brave Web Search API.
"""
import logging
import httpx
from datetime import datetime, timezone as dt_tz
from django.conf import settings
from .base import BaseCollector, CallBudgetExceeded

logger = logging.getLogger(__name__)

BRAVE_SEARCH_URL = 'https://api.search.brave.com/res/v1/web/search'


class BraveCollector(BaseCollector):
    def fetch_observations(self, term_query: str, market: str = 'PK') -> list[dict]:
        api_key = settings.RADAR.get('BRAVE_API_KEY', '')
        if not api_key:
            logger.warning('BRAVE_API_KEY not set — skipping brave collection')
            return []

        country = 'ALL' if market == 'PK' else 'us'
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
        reserve_daily_call()
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



USAGE_KEY = 'brave_daily_usage'


def reserve_daily_call():
    """
    Count one paid Brave call against today's limit (BRAVE_DAILY_CALL_LIMIT),
    or raise CallBudgetExceeded once the limit is reached. The counter lives in
    the database so every process on this server shares it.
    """
    from django.db import transaction
    from django.utils import timezone
    from apps.core.models import AppSetting

    limit = int(settings.RADAR.get('BRAVE_DAILY_CALL_LIMIT', 30) or 0)
    if limit <= 0:
        return
    today = timezone.localdate().isoformat()
    with transaction.atomic():
        row, _ = AppSetting.objects.select_for_update().get_or_create(
            pk=USAGE_KEY, defaults={'value': {'date': today, 'calls': 0}},
        )
        usage = row.value if isinstance(row.value, dict) else {}
        calls = usage.get('calls', 0) if usage.get('date') == today else 0
        if calls >= limit:
            raise CallBudgetExceeded(
                f'Daily Brave call limit reached ({limit}/day). Next calls tomorrow; '
                f'raise BRAVE_DAILY_CALL_LIMIT in .env to allow more.'
            )
        row.value = {'date': today, 'calls': calls + 1}
        row.save(update_fields=['value', 'updated_at'])
