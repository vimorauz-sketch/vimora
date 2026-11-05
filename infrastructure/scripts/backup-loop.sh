#!/bin/sh
# Runs inside the `backup` container: daily pg_dump with retention.
set -eu
while true; do
  TS=$(date -u +%Y%m%dT%H%M%SZ)
  F="/backups/vimora-$TS.dump"
  if pg_dump -h postgres -U vimora -d vimora -Fc -Z 6 -f "$F.part"; then
    mv "$F.part" "$F"; chmod 600 "$F"
    echo "$(date -u) backup ok: $F"
  else
    echo "$(date -u) BACKUP FAILED" >&2; rm -f "$F.part"
  fi
  find /backups -name 'vimora-*.dump*' -mtime +"${BACKUP_RETENTION_DAYS:-14}" -delete
  sleep 86400
done
