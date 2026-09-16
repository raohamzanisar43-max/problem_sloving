"""
X (Twitter) collector — recent search v2 API.
"""
import logging
import httpx
from datetime import datetime, timezone as dt_tz
from django.conf import settings
from .base import BaseCollector

logger = logging.getLogger(__name__)

X_RECENT_SEARCH_URL = 'https://api.twitter.com/2/tweets/search/recent'


class XCollector(BaseCollector):
    def fetch_observations(self, term_query: str, market: str = 'PK') -> list[dict]:
        token = settings.RADAR.get('X_BEARER_TOKEN', '')
        if not token:
            logger.warning('X_BEARER_TOKEN not set — skipping X collection')
            return []

        query = f'{term_query} lang:en -is:retweet'
        params = {
            'query': query,
            'max_results': 100,
            'tweet.fields': 'created_at,author_id,text',
            'expansions': 'author_id',
            'user.fields': 'name,username',
        }
        headers = {'Authorization': f'Bearer {token}'}

        with httpx.Client(timeout=20) as client:
            resp = client.get(X_RECENT_SEARCH_URL, params=params, headers=headers)
            resp.raise_for_status()

        body = resp.json()
        tweets = body.get('data', [])
        users = {u['id']: u for u in body.get('includes', {}).get('users', [])}

        observations = []
        for t in tweets:
            uid = t.get('author_id', '')
            user = users.get(uid, {})
            uname = user.get('username', '')
            tweet_url = f'https://x.com/{uname}/status/{t["id"]}' if uname else ''
            observations.append({
                'external_id': t['id'],
                'original_url': tweet_url,
                'canonical_url': tweet_url,
                'title': '',
                'text': t.get('text', ''),
                'author': uname,
                'source_published_at': _parse_dt(t.get('created_at')),
                'raw_payload': t,
            })
        return observations


def _parse_dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace('Z', '+00:00'))
    except Exception:
        return None

