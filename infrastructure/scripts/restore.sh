#!/usr/bin/env bash
# Restore a backup into the production database. DESTRUCTIVE: replaces current data.
# Usage: ./infrastructure/scripts/restore.sh backups/vimora-20261101T020000Z.dump[.gpg]
set -euo pipefail
cd "$(dirname "$0")/../.."
FILE="${1:?usage: restore.sh <backup file>}"
set -a; . ./.env; set +a
COMPOSE="docker compose -f docker-compose.prod.yml"
read -r -p "This REPLACES the current database with $FILE. Type 'restore' to continue: " ok
[ "$ok" = "restore" ] || { echo "Aborted"; exit 1; }
if [[ "$FILE" == *.gpg ]]; then TMP=$(mktemp); gpg --batch --decrypt "$FILE" > "$TMP"; FILE="$TMP"; fi
echo "==> Stopping application services"
$COMPOSE stop backend-api background-worker scheduler frontend
echo "==> Taking a safety backup of the current state"
./infrastructure/scripts/backup.sh || true
echo "==> Restoring"
$COMPOSE exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" postgres psql -U vimora -d postgres -c "DROP DATABASE IF EXISTS vimora WITH (FORCE);" -c "CREATE DATABASE vimora OWNER vimora;"
$COMPOSE exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" postgres pg_restore -U vimora -d vimora --no-owner --exit-on-error < "$FILE"
[ -n "${TMP:-}" ] && shred -u "$TMP"
echo "==> Applying any newer migrations"
$COMPOSE --profile ops run --rm migrate
$COMPOSE up -d
./infrastructure/scripts/healthcheck.sh
