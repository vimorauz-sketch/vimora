#!/usr/bin/env bash
# Create (or reset) the SUPER_ADMIN account. The password is prompted interactively,
# validated (>= 14 chars, mixed classes) and never printed or logged.
set -euo pipefail
cd "$(dirname "$0")/../.."
EMAIL="${1:?usage: bootstrap-admin.sh owner@yourdomain.com}"
docker compose -f docker-compose.prod.yml run --rm -it --no-deps backend-api python -m app.cli create-admin --email "$EMAIL"
