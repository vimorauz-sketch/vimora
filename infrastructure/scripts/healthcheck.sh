#!/usr/bin/env bash
# Verifies the public site, API readiness, worker heartbeat and disk space.
set -uo pipefail
cd "$(dirname "$0")/../.."
set -a; . ./.env; set +a
fail=0
check() { if eval "$2" >/dev/null 2>&1; then echo "OK    $1"; else echo "FAIL  $1"; fail=1; fi; }
check "website ${APP_URL}"            "curl -fsS --max-time 10 ${APP_URL}/robots.txt"
check "api readiness"                 "curl -fsS --max-time 10 ${APP_URL}/api/v1/health/ready"
check "containers running"            "! docker compose -f docker-compose.prod.yml ps --status exited --services | grep -v -E '^(migrate)$' | grep -q ."
if [ -n "${HEALTH_DETAILS_TOKEN:-}" ]; then
  DETAILS=$(docker compose -f docker-compose.prod.yml exec -T backend-api curl -fsS -H "X-Health-Token: $HEALTH_DETAILS_TOKEN" http://127.0.0.1:8000/api/v1/health/details || true)
  echo "$DETAILS" | grep -q '"worker": {"ok": true' && echo "OK    worker heartbeat" || { echo "FAIL  worker heartbeat"; fail=1; }
fi
USE=$(df -P / | awk 'NR==2 {print $5}' | tr -d %)
[ "$USE" -lt 85 ] && echo "OK    disk usage ${USE}%" || { echo "WARN  disk usage ${USE}% (clean old backups/images)"; }
exit $fail
