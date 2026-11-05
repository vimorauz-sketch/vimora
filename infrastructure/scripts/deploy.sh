#!/usr/bin/env bash
# Build images, run migrations, and (re)start the production stack. Safe to re-run.
set -euo pipefail
cd "$(dirname "$0")/../.."
COMPOSE="docker compose -f docker-compose.prod.yml"
[ -f .env ] || { echo "Missing .env (copy .env.example)"; exit 1; }

echo "==> Validating configuration"
$COMPOSE config -q
$COMPOSE run --rm --no-deps -e APP_ENV=production backend-api python -m app.cli check-config

echo "==> Building images"
export VIMORA_VERSION="${VIMORA_VERSION:-$(git rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M)}"
$COMPOSE build

echo "==> Starting data services"
$COMPOSE up -d postgres redis

echo "==> Backing up database before migrating"
./infrastructure/scripts/backup.sh || echo "WARN: pre-deploy backup failed (first deploy?)"

echo "==> Running migrations"
$COMPOSE --profile ops run --rm migrate

echo "==> Starting application"
$COMPOSE up -d --remove-orphans

echo "==> Health check"
sleep 10
./infrastructure/scripts/healthcheck.sh
echo "Deployed version $VIMORA_VERSION"
