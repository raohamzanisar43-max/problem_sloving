#!/bin/sh
set -e

# Only the web process migrates and collects static; other services skip it.
if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
  python manage.py migrate --noinput
  python manage.py collectstatic --noinput
fi

exec "$@"
