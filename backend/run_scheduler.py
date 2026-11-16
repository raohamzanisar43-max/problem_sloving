import os
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.conf import settings
from apps.sources.tasks import collect_all_sources

# Paid sources (Brave web search) run every COLLECTION_INTERVAL_MINUTES.
INTERVAL_SECONDS = settings.RADAR['COLLECTION_INTERVAL_MINUTES'] * 60
# Free sources (Freelancer.com) cost nothing, and new projects get many bids
# within hours, so they are checked far more often.
FREE_TYPES = ('freelancer',)
FREE_INTERVAL_SECONDS = max(15, settings.RADAR.get('FREE_SOURCE_INTERVAL_MINUTES', 60)) * 60


def seconds_until_due(interval_seconds, free):
    """
    Seconds until the next run of the paid (free=False) or free sweep, so that
    restarting the scheduler does not trigger an extra paid collection when the
    last scheduled run is recent.
    """
    from django.utils import timezone
    from apps.sources.models import Run

    runs = Run.objects.filter(trigger='schedule')
    if free:
        runs = runs.filter(source__connector_type__in=FREE_TYPES)
    else:
        runs = runs.exclude(source__connector_type__in=FREE_TYPES)
    # Only a run that actually fetched something counts — a run that failed on
    # the network or on an exhausted key should be retried at the next start.
    recent = runs.order_by('-created_at')[:50]
    last = next((r for r in recent if (r.counters or {}).get('fetched')), None)
    if last is None:
        return 0
    elapsed = (timezone.now() - last.created_at).total_seconds()
    return max(0, int(interval_seconds - elapsed))


def run_sweep(label, **kwargs):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Running {label} collection...")
    try:
        print(f"  Result: {collect_all_sources(**kwargs)}")
    except Exception as exc:
        print(f"  Error: {exc}")


if __name__ == '__main__':
    print(
        f"Novu Opportunity Radar scheduler started. "
        f"Paid sources every {INTERVAL_SECONDS // 60} minute(s), "
        f"Freelancer.com every {FREE_INTERVAL_SECONDS // 60} minute(s). Press Ctrl+C to stop."
    )
    now = time.time()
    next_paid = now + seconds_until_due(INTERVAL_SECONDS, free=False)
    next_free = now + seconds_until_due(FREE_INTERVAL_SECONDS, free=True)
    if next_paid > now:
        print(
            f"Last paid run was recent - next one at "
            f"{time.strftime('%Y-%m-%d %H:%M', time.localtime(next_paid))}."
        )
    while True:
        now = time.time()
        if now >= next_free:
            run_sweep('Freelancer.com', only_types=FREE_TYPES)
            next_free = time.time() + FREE_INTERVAL_SECONDS
        if now >= next_paid:
            run_sweep('paid-source', exclude_types=FREE_TYPES)
            next_paid = time.time() + INTERVAL_SECONDS
        time.sleep(max(1, min(next_free, next_paid) - time.time()))
