"""
Reddit collector via Apify (automation-lab/reddit-scraper).

Reddit no longer serves posts to anonymous clients, so posts are fetched
through an Apify actor (APIFY_TOKEN in .env, pay-per-post). Two kinds of posts
are collected, twice a day by default:

  · new posts in hiring subreddits (r/forhire, r/slavelabour, …) whose title
    says [Hiring] / [Task] — the actor drops the rest before they are charged
  · posts anywhere on Reddit with client phrases such as "need a developer"

Sellers ("[For Hire]", "[Offer]"), unpaid co-founder searches and non-software
tasks are dropped here; the remaining posts go through the normal client-request
filter, the keyword gate and the AI buyer check like any web lead.
"""
import logging
import re
from datetime import datetime

import httpx
from django.conf import settings

from .base import BaseCollector

logger = logging.getLogger(__name__)

ACTOR = 'automation-lab~reddit-scraper'
API = f'https://api.apify.com/v2/acts/{ACTOR}/run-sync-get-dataset-items'

HIRING_SUBREDDITS = ['forhire', 'slavelabour', 'hiring', 'jobbit', 'freelance_forhire',
                     'DoneDirtCheap', 'ForHireFreelance']
CLIENT_PHRASES = [
    '"looking for a developer"', '"need a developer"', '"looking for a web developer"',
    '"looking for an app developer"', '"need someone to build"', '"need a website built"',
    '"need an app built"', '"hire a web developer"', '"looking for a freelancer"',
]

SELLER_RE = re.compile(r'\[\s*(?:for\s*hire|fh|offer|offering)\s*\]|\bfor\s+hire\b|^\s*offer\b', re.IGNORECASE)
SELLER_FLAIRS = {'for hire', 'offer', 'for hire - open', 'offering'}
# Partner/co-founder searches that pay with equity, not money.
EQUITY_RE = re.compile(
    r'\bco-?\s?founder\b|\bequity\b|\brev(?:enue)?\s*share\b|\bprofit\s*share\b|\bunpaid\b|\bvolunteer\b',
    re.IGNORECASE,
)
SOFTWARE_RE = re.compile(
    r'\b(?:website|web\s?site|web\s?app|landing\s+page|app|apps|application|software|developer|dev|'
    r'programmer|coder|engineer|wordpress|shopify|woocommerce|wix|webflow|squarespace|saas|mvp|platform|'
    r'dashboard|portal|api|backend|back-end|frontend|front-end|full[\s-]?stack|react|next\.?js|node|python|'
    r'django|laravel|php|flutter|android|ios|automation|automate|bot|scraper|scraping|chrome\s+extension|'
    r'chatbot|ai|llm|database|crm|erp|lms|e-?commerce|online\s+store|bug|script)\b',
    re.IGNORECASE,
)
NON_SOFTWARE_RE = re.compile(
    r'\b(?:video\s+edit\w*|editor|logo|translat\w*|writer|writing|copywrit\w*|voice|ugc|tiktok|instagram|'
    r'virtual\s+assistant|\bva\b|data\s+entry|annotat\w*|tutor\w*|essay|homework|artist|illustrat\w*|'
    r'sales\s+partner|commission|recruiter|cold\s+call\w*|appointment\s+setter)\b',
    re.IGNORECASE,
)


class ApifyNotConfigured(Exception):
    """APIFY_TOKEN is missing."""


def is_client_post(title, text, flair=''):
    """A paid software request from a client — not a seller, co-founder hunt or non-software task."""
    title = title or ''
    if (flair or '').strip().lower() in SELLER_FLAIRS or SELLER_RE.search(title):
        return False
    if EQUITY_RE.search(f'{title}\n{text}'):
        return False
    if SOFTWARE_RE.search(title):
        return True
    return bool(SOFTWARE_RE.search(text or '')) and not NON_SOFTWARE_RE.search(title)


def _published(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None


def to_row(item):
    title = (item.get('title') or '').strip()
    body = (item.get('selfText') or '').strip()
    sub = item.get('subreddit') or ''
    url = item.get('permalink') or item.get('url') or ''
    return {
        'external_id': str(item.get('id') or url),
        'original_url': url,
        'canonical_url': url,
        'title': title[:500],
        'text': f'{title}\n\n{body[:4000]}\n\nPosted in r/{sub} by u/{item.get("author") or "unknown"}'.strip(),
        'author': (item.get('author') or '')[:255],
        'source_published_at': _published(item.get('createdAt')),
        'raw_payload': {
            'platform': 'reddit',
            'subreddit': sub,
            'flair': item.get('linkFlairText') or '',
            'score': item.get('score'),
            'num_comments': item.get('numComments'),
        },
    }


class RedditApifyCollector(BaseCollector):
    """Fetches once per run (the keyword gate is applied to the posts afterwards)."""

    def __init__(self, source):
        super().__init__(source)
        self._done = False

    def _settings(self):
        return self.source.settings or {}

    def _lookback(self):
        from apps.observations.models import Observation
        # First run backfills a few days; later runs only need what is new since the last one.
        if not Observation.objects.filter(source=self.source).exists():
            return self._settings().get('first_lookback', '3 days')
        return self._settings().get('lookback', '14 hours')

    def _call(self, actor_input):
        token = settings.RADAR.get('APIFY_TOKEN', '')
        params = {
            'token': token,
            'timeout': 300,
            'maxTotalChargeUsd': self._settings().get('max_charge_usd_per_call', 0.3),
        }
        resp = httpx.post(API, params=params, json=actor_input, timeout=330)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else []

    def fetch_observations(self, term_query: str, market: str = 'PK') -> list[dict]:
        if self._done:
            return []
        self._done = True
        if not settings.RADAR.get('APIFY_TOKEN'):
            raise ApifyNotConfigured('APIFY_TOKEN is not set in .env — Reddit posts cannot be fetched.')

        cfg = self._settings()
        lookback = self._lookback()
        base = {'sort': 'new', 'includeComments': False, 'includeNsfw': False,
                'deduplicatePosts': True, 'postedAfter': lookback}
        items = []
        subs = cfg.get('subreddits') or HIRING_SUBREDDITS
        items += self._call({
            **base,
            'urls': [f'https://www.reddit.com/r/{s}/new/' for s in subs],
            'maxPostsPerSource': int(cfg.get('max_posts_per_subreddit', 60)),
            # Only [Hiring]/[Task] titles are kept (and charged) by the actor.
            'filterKeywords': ['hiring', 'task'],
            'filterKeywordMode': 'titleOnly',
        })
        phrases = cfg.get('search_phrases') or CLIENT_PHRASES
        items += self._call({
            **base,
            'searchQueries': phrases,
            'timeFilter': 'week',
            'maxPostsPerSource': int(cfg.get('max_posts_per_phrase', 15)),
        })

        rows, seen = [], set()
        for item in items:
            if item.get('type') not in (None, 'post'):
                continue
            row = to_row(item)
            if row['external_id'] in seen:
                continue
            seen.add(row['external_id'])
            body = (item.get('selfText') or '')
            if is_client_post(row['title'], body, item.get('linkFlairText') or ''):
                rows.append(row)
        logger.info('Reddit: %d posts fetched, %d look like client requests', len(items), len(rows))
        return rows
