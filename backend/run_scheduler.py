import os
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.conf import settings
from apps.sources.tasks import collect_all_sources

INTERVAL_SECONDS = settings.RADAR['COLLECTION_INTERVAL_MINUTES'] * 60

if __name__ == '__main__':
    print(
        f"Novu Opportunity Radar scheduler started. "
        f"Collecting every {settings.RADAR['COLLECTION_INTERVAL_MINUTES']} minute(s). Press Ctrl+C to stop."
    )
    while True:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Running collect_all_sources()...")
        try:
            result = collect_all_sources()
            print(f"  Result: {result}")
        except Exception as exc:
            print(f"  Error: {exc}")
        time.sleep(INTERVAL_SECONDS)