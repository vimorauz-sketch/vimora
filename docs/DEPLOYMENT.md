# Deployment (Ubuntu VPS)

Target: Ubuntu 22.04/24.04, 2 vCPU / 4 GB RAM / 40 GB disk minimum, a domain you control.

## 1. Prepare the server

```bash
sudo apt update && sudo apt -y upgrade
sudo apt -y install ca-certificates curl git ufw gnupg
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER && newgrp docker
sudo ufw default deny incoming && sudo ufw allow OpenSSH && sudo ufw allow 80,443/tcp && sudo ufw allow 443/udp && sudo ufw enable
```

Harden SSH (key-only login, `PasswordAuthentication no`) and enable unattended security upgrades.

## 2. DNS and HTTPS

Create `A` (and `AAAA` if you have IPv6) records for `yourdomain` and `www.yourdomain` pointing to the VPS. Caddy obtains and renews Let's Encrypt certificates automatically on first start — ports 80 and 443 must be reachable. HSTS is enabled; make sure HTTPS works before pointing real users at the domain.

## 3. Configure

```bash
git clone <your repository> vimora && cd vimora
cp .env.example .env && chmod 600 .env
./infrastructure/scripts/gen-secrets.sh        # paste the output into .env
nano .env                                      # set VIMORA_DOMAIN, ACME_EMAIL, APP_URL, FRONTEND_URL, API_URL, SMTP ...
```

The API refuses to start in production if `SECRET_KEY`, `SETTINGS_ENCRYPTION_KEY`, HTTPS `APP_URL` or SMTP settings are missing — see `python -m app.cli check-config` output.

## 4. Deploy

```bash
./infrastructure/scripts/deploy.sh             # validate → build → backup → migrate → start → health check
./infrastructure/scripts/bootstrap-admin.sh owner@yourdomain.com   # prompts for a ≥14-char password
```

Then sign in at `https://yourdomain/login`, open **Security** and enable two-factor authentication (required before the admin panel opens in production). Store the recovery codes offline.

## 5. First-run configuration (admin panel)

1. **Services** — review the seeded inactive drafts (`python -m app.cli seed-categories && seed-service-drafts && seed-content` via `docker compose -f docker-compose.prod.yml run --rm backend-api ...`), set your real prices and activate them.
2. **Content** — write and publish Terms, Privacy, Refund, Service policy, About and the AI processing notice. They remain unpublished until you do.
3. **Settings** — contact details, release policy, manual payment instructions (if used), Telegram admin events. Use *Send test email* / *Send test message*.
4. **AI control** — add a provider + API key, add model(s) with current per-token prices, set budgets, then enable AI processing. Use *Test connection*.
5. **Telegram** — set `TELEGRAM_*` in `.env`, redeploy, then *Register webhook* in Settings.

## 6. Payment providers

| Provider | Configure in merchant cabinet | `.env` |
|---|---|---|
| Click | Prepare URL `https://DOMAIN/api/v1/webhooks/click/prepare`, Complete URL `https://DOMAIN/api/v1/webhooks/click/complete` | `CLICK_MERCHANT_ID`, `CLICK_SERVICE_ID`, `CLICK_SECRET_KEY` |
| Payme | Endpoint `https://DOMAIN/api/v1/webhooks/payme`; account field **`payment_ref`** | `PAYME_MERCHANT_ID`, `PAYME_SECRET_KEY` (use `PAYME_CHECKOUT_URL=https://test.paycom.uz` + test key in the sandbox first) |
| Stripe (USD) | Webhook `https://DOMAIN/api/v1/webhooks/stripe`, events `checkout.session.completed`, `checkout.session.async_payment_succeeded`, `checkout.session.async_payment_failed`, `checkout.session.expired` | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` |

Run each provider's sandbox/test flow end-to-end before going live (Payme provides a merchant API test suite in its sandbox). Unconfigured providers are shown as unavailable to customers.

## 7. Updating

```bash
git pull && ./infrastructure/scripts/deploy.sh   # takes a backup before migrating
```

## Commands

| Task | Command |
|---|---|
| Migrations | `./infrastructure/scripts/migrate.sh` |
| Logs | `docker compose -f docker-compose.prod.yml logs -f backend-api background-worker` |
| Health | `./infrastructure/scripts/healthcheck.sh` |
| Shell / CLI | `docker compose -f docker-compose.prod.yml run --rm backend-api python -m app.cli --help` |
| Backup / restore | see [BACKUP.md](BACKUP.md) |
