#!/bin/sh
# Pull origin/main and rebuild the Novu Radar stack.
# Installed on the server as /usr/local/bin/novu-radar-deploy and used as the
# forced command of the CI deploy key (see deploy/README.md).
set -eu
exec 9>/var/lock/novu-radar-deploy.lock
flock -n 9 || { echo "another deploy is running"; exit 1; }

cd /opt/novu-radar
git fetch --quiet origin main
git reset --hard origin/main
docker compose up -d --build --remove-orphans
docker image prune -f >/dev/null

echo "waiting for backend health..."
for _ in $(seq 1 30); do
  status=$(docker inspect -f '{{.State.Health.Status}}' novu-radar-backend-1 2>/dev/null || echo none)
  if [ "$status" = healthy ]; then
    echo "deployed $(git rev-parse --short HEAD): healthy"
    exit 0
  fi
  sleep 5
done
echo "backend did not become healthy"
docker compose logs --tail 40 backend
exit 1
