# Backup and restore

**A backup is not reliable until a restore has been tested.** Test a restore on a separate machine at least once a month and after every major upgrade.

## What to back up

| Data | Location | How |
|---|---|---|
| Database (orders, payments, users, audit) | `pgdata` volume | Automatic daily `pg_dump` by the `backup` service → `BACKUP_DIR` (default `./backups`), retention `BACKUP_RETENTION_DAYS` (14) |
| Uploaded files and deliverables | `storage` volume (or your S3 bucket) | Volume snapshot / `restic`/`rclone` copy off-site; for S3 enable bucket versioning and lifecycle rules |
| Configuration | `.env` | Store encrypted in a password manager — it contains `SETTINGS_ENCRYPTION_KEY`, without which encrypted AI keys and MFA secrets cannot be read |
| TLS state | `caddy_data` volume | Optional (Caddy re-issues certificates) |

## Manual backup

```bash
./infrastructure/scripts/backup.sh          # also runs automatically before every deploy
```

Set `BACKUP_GPG_RECIPIENT` to encrypt dumps with your GPG public key (recommended). Copy backups **off the server** (another region/provider): a backup on the same disk does not survive disk loss or server compromise. Example:

```bash
rclone copy ./backups remote:vimora-backups --max-age 48h
docker run --rm -v vimora_storage:/data:ro -v $PWD/files-backup:/out alpine tar czf /out/storage-$(date +%F).tgz -C /data .
```

## Restore

```bash
./infrastructure/scripts/restore.sh backups/vimora-YYYYMMDDTHHMMSSZ.dump      # or .dump.gpg
```

The script asks for confirmation, stops application services, takes a safety backup of the current state, recreates the database, restores, applies any newer migrations, restarts and runs the health check. Restore the `storage` volume separately if files were lost.

## Restore drill (recommended monthly)

1. Provision a scratch VM, install Docker, copy the repo, `.env` (with a different domain) and the latest dump.
2. `docker compose -f docker-compose.prod.yml up -d postgres redis` then `./infrastructure/scripts/restore.sh <dump>`.
3. Sign in as admin, open a recent order, check payments and the audit log, download a deliverable (requires the storage backup).
4. Record the date and outcome.
