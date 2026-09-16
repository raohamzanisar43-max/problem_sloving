"""
Reddit collector — PRAW subreddit search.
"""
import logging
from datetime import datetime, timezone as dt_tz
from django.conf import settings
from .base import BaseCollector

logger = logging.getLogger(__name__)

TARGET_SUBREDDITS = [
    'forhire', 'slavelabour', 'entrepreneur', 'smallbusiness',
    'outsourcing', 'digitalnomad', 'webdev', 'sysadmin',
]


class RedditCollector(BaseCollector):
    def fetch_observations(self, term_query: str, market: str = 'PK') -> list[dict]:
        import praw  # lazy import so missing install doesn't crash server

        r = settings.RADAR
        client_id = r.get('REDDIT_CLIENT_ID', '')
        client_secret = r.get('REDDIT_CLIENT_SECRET', '')
        user_agent = r.get('REDDIT_USER_AGENT', 'novu-radar/1.0')

        if not client_id or not client_secret:
            logger.warning('REDDIT_CLIENT_ID / SECRET not set — skipping Reddit')
            return []

        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
        )

        subs = '+'.join(TARGET_SUBREDDITS)
        observations = []
        for submission in reddit.subreddit(subs).search(term_query, limit=50, sort='new'):
            post_url = f'https://www.reddit.com{submission.permalink}'
            body = (submission.selftext or '')[:4000]
            observations.append({
                'external_id': submission.id,
                'original_url': post_url,
                'canonical_url': post_url,
                'title': (submission.title or '')[:500],
                'text': f"{submission.title}\n\n{body}",
                'author': str(submission.author or ''),
                'source_published_at': datetime.fromtimestamp(
                    submission.created_utc, tz=dt_tz.utc
                ),
                'raw_payload': {
                    'id': submission.id,
                    'score': submission.score,
                    'upvote_ratio': submission.upvote_ratio,
                    'subreddit': str(submission.subreddit),
                },
            })
        return observations

