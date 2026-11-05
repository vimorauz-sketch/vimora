# Architecture

## Services

```
                 Internet
                    │ 80/443
             ┌──────▼──────┐
             │ reverse-proxy│  Caddy: TLS, HSTS, /api → backend-api, everything else → frontend
             └──┬───────┬──┘
   edge network │       │
        ┌───────▼─┐   ┌─▼──────────┐
        │frontend │   │backend-api │  FastAPI (uvicorn, 3 workers)
        │Next.js  │──▶│            │  SSR fetches public data over the internal network
        └─────────┘   └─────┬──────┘
          internal network  │ (no internet route)
        ┌──────────┬────────┼─────────────┬───────────┐
        │postgres  │ redis  │ background- │ scheduler │  backup
        │          │        │ worker      │ (beat)    │  (daily pg_dump)
        └──────────┴────────┴─────────────┴───────────┘
   egress network: backend-api + worker only (payments, Telegram, SMTP, AI providers)
```

One codebase, one database, modular packages — no microservices. The worker consumes two queues: `default` (notifications, housekeeping) and `ai` (AI executions).

## Key design decisions

**Server-side sessions, not JWTs.** A random 256-bit token in an HttpOnly/Secure/SameSite=Lax cookie; only its SHA-256 is stored. Sessions can be revoked instantly (logout, password change, role change, account disable). A per-session CSRF token is double-submitted via header. Nothing auth-related is stored in localStorage.

**Order state machine** (`app/services/order_state.py`). Every transition is declared with the actor types allowed to perform it (CUSTOMER, ADMIN, SYSTEM, PAYMENT, AI). Payment-driven transitions are reserved for the PAYMENT actor, which only the verified payment path uses — so "mark as paid" is structurally impossible from the frontend or even from the generic admin status endpoint. Every transition writes an `OrderEvent` and an `AuditLog` row in the same transaction.

Main path: `SUBMITTED → UNDER_REVIEW → QUOTATION_PENDING → QUOTATION_ACCEPTED → DEPOSIT_PENDING → PARTIALLY_PAID|PAID → QUEUED → AI_PROCESSING|MANUAL_PROCESSING → AI_REVIEW_REQUIRED → COMPLETED_PENDING_FINAL_PAYMENT → FINAL_PAYMENT_PENDING → READY_FOR_DELIVERY → DELIVERED → CLOSED`, with `REVISION_REQUESTED`, `CANCELLED`, `REFUND_PENDING`, `REFUNDED`, `FAILED` branches.

**Money.** Integer minor units everywhere (tiyin, cents); no floats. Prices are computed only on the server (`app/services/pricing.py`). Accepting a quotation snapshots total/deposit/currency onto the order — later price or currency changes never alter an accepted quotation.

**Payments** (`app/payments/`). Provider adapters create checkouts; webhook handlers verify signatures/auth, the amount, currency and our payment reference, then call `confirm_payment()` — the single, idempotent function that records money. Duplicate notifications are no-ops; webhook event ids are stored for replay protection. Confirmed payment rows are protected by a DB trigger; `payment_events` is append-only.

**AI pipeline** (`app/ai/`). Router → Planner → Executor → Validator, each persisted as an `AIExecutionStep`. The executor can only return files of extensions allowed by an allowlisted *capability*; it has no shell, network or tools. Customer content is wrapped as untrusted data in prompts. The pipeline always stops at `REVIEW_REQUIRED`; only an admin action promotes files to deliverables. Any error, budget stop, policy flag or unparseable output falls back to `MANUAL_PROCESSING` with the reason recorded and the admin notified. Usage/cost is recorded in an independent transaction so spend can never be lost on rollback; budgets (daily, per execution, executions per day, attempts per order) are checked before every call. Optional code checks run in a disposable, network-less, non-root, resource-limited container on a *separate* Docker host.

**Notifications** are rows created inside business transactions (deduplicated by a unique key) and delivered by the worker after commit, with retries and a sweeper. Statuses are honest: `SENT`, `FAILED`, `SKIPPED` (not configured / opted out), `LOGGED_DEV` (dev console backend — not delivered).

**Files** are validated (size, extension allowlist, content sniffing, Office macro/zip-bomb checks, optional ClamAV), stored under random keys in private storage, and downloaded only through short-lived HMAC-signed links (or S3 presigned URLs) that re-check authorization, always as attachments with `nosniff` and a sandbox CSP.

## Frontend

- Public pages are server-rendered (SEO, metadata, sitemap); authenticated areas are client components backed by TanStack Query.
- `/dashboard` (customers) and `/admin` (staff) share an `AppShell`; the admin navigation is filtered by the permissions returned from `/auth/me`, but the API enforces every permission independently.
- i18n: dictionaries in `lib/i18n/{uz,en,ru}.ts`; `en` defines the type, so a missing translation fails the build. Locale comes from a cookie (default Uzbek).
- Design tokens live in `styles/globals.css` (Obsidian/Ivory/Electric Lime, Geist + Unbounded). Lime is reserved for primary actions, active state and "needs action" signals; the six-stage progress rail is the brand's recurring element.
