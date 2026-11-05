# Operations — daily owner workflow

1. **Telegram notification** "NEW VIMORA ORDER" arrives (or check Admin → Overview → *Awaiting review*). `/pending` in the bot lists orders needing action.
2. **Open the order** (Admin → Orders → order). Read the request, requirements, attachments; message the customer if something is missing.
3. **Quotation.** Fixed / per-unit / tiered services are priced automatically. For custom or "starting from" requests use *Create quotation* (line items, discount, deposit %, delivery days). The customer accepts or declines in their dashboard.
4. **Wait for the deposit.** The order moves to *Queued* only after the payment provider confirms to the server (or after you record a verified bank transfer with *Record manual payment* — audited).
5. **Do the work.**
   - AI-eligible: *Start AI processing*. Follow the execution log in AI control. When it reaches *Quality review*, open the review page: read the plan, validation results (deterministic checks + the model's own assessment — verify it yourself), preview every file, then **Approve** selected files, **Request revision** with instructions, **Retry**, **Take over manually**, or **Reject**.
   - Manual: change status to *Manual processing*, upload deliverables with *Upload deliverable*.
   - Any AI failure moves the order to *Manual processing* automatically and notifies you.
6. **Complete work.** Requests the remaining balance (customer gets an email/Telegram/in-app notice; reminders are sent automatically every 2 days) — or, if fully paid, prepares delivery.
7. **Release to customer** once *Ready for delivery*. With the default policy, release is blocked until the balance is paid.
8. **Close.** The customer can accept or request a revision (within the service's revision limit). Delivered orders auto-close after `orders.auto_close_days`.
9. **Reviews** appear in Content → Reviews; publish genuine ones to show them on the home page.

## Refunds

Order → *Refund* → creates a refund request (order moves to *Refund pending*). Execute the refund in the provider: Stripe can be refunded automatically (enter `auto`); for Click/Payme refund in the merchant cabinet, then *Mark refund completed* with the provider's refund id. Payme reversals initiated by Payme are recorded automatically.

## Monitoring

| Signal | Where |
|---|---|
| Public health | `GET /api/v1/health/live`, `/health/ready` (up/down only) |
| Detailed health (DB latency, migration, Redis, worker heartbeat, storage, disk, AI providers) | Admin → Settings → integrations, or `/api/v1/health/details` with `X-Health-Token` from inside the server |
| Logs | JSON on stdout (`docker compose logs`), request ids in `X-Request-ID`; secrets redacted |
| Worker | heartbeat key refreshed every minute by the scheduler; `healthcheck.sh` alerts if stale |
| Payments | Admin → Finance → Reconciliation (stale processing payments, amount mismatches, ledger drift) |
| AI | Admin → AI control (spend vs budget, failures, fallback rate) |
| Disk | `healthcheck.sh` warns above 85 %; prune old images with `docker image prune -a` and old backups |

Error reporting: `SENTRY_DSN` is reserved as an integration point; wire your preferred service in `app/main.py` if needed. For uptime alerts, point an external monitor at `/api/v1/health/ready`.

## Maintenance mode

Settings → *Maintenance mode*. Customer write actions return 503; sign-in, the admin panel and **payment webhooks keep working** so in-flight payments are not lost.
