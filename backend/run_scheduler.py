import os
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.conf import settings
from apps.sources.tasks import collect_all_sources

# Free sources (Freelancer.com) cost nothing, and new projects get many bids
# within hours, so they are checked far more often.
FREE_TYPES = ('freelancer',)
FREE_INTERVAL_SECONDS = max(15, settings.RADAR.get('FREE_SOURCE_INTERVAL_MINUTES', 60)) * 60
# Reddit is fetched through Apify (pay-per-post): twice a day by default.
REDDIT_TYPES = ('reddit',)
REDDIT_INTERVAL_SECONDS = max(60, settings.RADAR.get('REDDIT_INTERVAL_MINUTES', 720)) * 60
# Paid web search (Brave) and anything else runs every COLLECTION_INTERVAL_MINUTES.
INTERVAL_SECONDS = settings.RADAR['COLLECTION_INTERVAL_MINUTES'] * 60
OWN_SCHEDULE = FREE_TYPES + REDDIT_TYPES

# Reply inbox (client answers to proposals) — cheap, so checked every few minutes.
INBOX_INTERVAL_SECONDS = max(1, settings.INBOX.get('CHECK_MINUTES', 5)) * 60


def seconds_until_due(interval_seconds, only_types=None, exclude_types=None):
    """
    Seconds until a sweep is next due, so that restarting the scheduler does
    not trigger an extra (paid) collection when its last scheduled run is recent.
    """
    from django.utils import timezone
    from apps.sources.models import Run

    runs = Run.objects.filter(trigger='schedule')
    if only_types:
        runs = runs.filter(source__connector_type__in=only_types)
    if exclude_types:
        runs = runs.exclude(source__connector_type__in=exclude_types)
    # Only a run that actually fetched something counts — a run that failed on
    # the network or on an exhausted key should be retried at the next start.
    recent = runs.order_by('-created_at')[:50]
    last = next((r for r in recent if (r.counters or {}).get('fetched')), None)
    if last is None:
        return 0
    elapsed = (timezone.now() - last.created_at).total_seconds()
    return max(0, int(interval_seconds - elapsed))


def run_inbox_check():
    from apps.notifications.inbox import check_inbox
    try:
        result = check_inbox()
        if result.get('notified') or not result.get('ok', True):
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Inbox: {result}")
    except Exception as exc:
        print(f"  Inbox error: {exc}")


def run_sweep(label, **kwargs):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Running {label} collection...")
    try:
        print(f"  Result: {collect_all_sources(**kwargs)}")
    except Exception as exc:
        print(f"  Error: {exc}")


SWEEPS = [
    # label, collect_all_sources kwargs, interval
    ('Freelancer.com', {'only_types': FREE_TYPES}, FREE_INTERVAL_SECONDS),
    ('Reddit', {'only_types': REDDIT_TYPES}, REDDIT_INTERVAL_SECONDS),
    ('paid-source', {'exclude_types': OWN_SCHEDULE}, INTERVAL_SECONDS),
]


if __name__ == '__main__':
    from apps.notifications.inbox import is_configured
    inbox_on = is_configured()
    print('Novu Opportunity Radar scheduler started. Press Ctrl+C to stop.')
    for label, _, interval in SWEEPS:
        print(f'  {label}: every {interval // 60} minute(s)')
    print(f"  Reply inbox: {'every ' + str(INBOX_INTERVAL_SECONDS // 60) + ' minute(s)' if inbox_on else 'not configured'}")

    now = time.time()
    next_due = {label: now + seconds_until_due(interval, **kwargs) for label, kwargs, interval in SWEEPS}
    for label, due in next_due.items():
        if due > now:
            print(f"  Last {label} run was recent - next one at {time.strftime('%Y-%m-%d %H:%M', time.localtime(due))}.")
    next_inbox = now

    while True:
        now = time.time()
        for label, kwargs, interval in SWEEPS:
            if now >= next_due[label]:
                run_sweep(label, **kwargs)
                next_due[label] = time.time() + interval
        if inbox_on and now >= next_inbox:
            run_inbox_check()
            next_inbox = time.time() + INBOX_INTERVAL_SECONDS
        wake = min(list(next_due.values()) + ([next_inbox] if inbox_on else []))
        time.sleep(max(1, wake - time.time()))
