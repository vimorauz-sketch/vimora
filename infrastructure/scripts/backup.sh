#!/usr/bin/env bash
# One-off database backup (custom format, compressed). Optionally GPG-encrypted.
set -euo pipefail
cd "$(dirname "$0")/../.."
set -a; . ./.env; set +a
DIR="${BACKUP_DIR:-./backups}"; mkdir -p "$DIR"; chmod 700 "$DIR"
FILE="$DIR/vimora-$(date -u +%Y%m%dT%H%M%SZ).dump"
docker compose -f docker-compose.prod.yml exec -T -e PGPASSWORD="$POSTGRES_PASSWORD" postgres pg_dump -U vimora -d vimora -Fc -Z 6 > "$FILE"
if [ -n "${BACKUP_GPG_RECIPIENT:-}" ]; then gpg --batch --yes --encrypt --recipient "$BACKUP_GPG_RECIPIENT" "$FILE" && shred -u "$FILE" && FILE="$FILE.gpg"; fi
chmod 600 "$FILE"
echo "Backup written: $FILE ($(du -h "$FILE" | cut -f1))"
echo "Remember: a backup is not reliable until a restore has been tested (see docs/BACKUP.md)."
