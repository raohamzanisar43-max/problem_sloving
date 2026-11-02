"""Container health check: healthy if the app answers with anything below 5xx (the API requires auth)."""
import sys
import urllib.error
import urllib.request

req = urllib.request.Request('http://127.0.0.1:8000/api/v1/', headers={'X-Forwarded-Proto': 'https'})
try:
    urllib.request.urlopen(req, timeout=3)
except urllib.error.HTTPError as exc:
    sys.exit(1 if exc.code >= 500 else 0)
