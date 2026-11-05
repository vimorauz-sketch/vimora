#!/usr/bin/env bash
# Prints fresh random secrets to paste into .env. Nothing is written to disk.
set -euo pipefail
rand() { openssl rand -base64 48 | tr -d '/+=\n' | cut -c1-"$1"; }
echo "SECRET_KEY=$(rand 64)"
echo "SETTINGS_ENCRYPTION_KEY=$(openssl rand -base64 32 | tr '+/' '-_')"
echo "POSTGRES_PASSWORD=$(rand 40)"
echo "REDIS_PASSWORD=$(rand 40)"
echo "TELEGRAM_WEBHOOK_SECRET=$(rand 40)"
echo "HEALTH_DETAILS_TOKEN=$(rand 40)"
