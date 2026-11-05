# VIMORA

**Every task. One intelligent platform.**

VIMORA is a digital services marketplace: customers order a predefined service or describe a custom task, receive a quotation, pay a deposit, follow progress, chat with the operator and download reviewed results. Eligible tasks are produced by an AI pipeline; **every AI result is reviewed and approved by a person** before a customer can see it, and anything AI cannot do well goes to manual processing.

| Layer | Technology |
|---|---|
| Frontend | Next.js 15 (App Router), React 19, TypeScript strict, Tailwind CSS 4, Radix UI (shadcn-style components), TanStack Query, React Hook Form + Zod, Recharts |
| Backend | Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, Celery (worker + beat) |
| Data | PostgreSQL 16, Redis 7, local disk or S3-compatible storage |
| Edge | Caddy 2 (automatic HTTPS), Docker Compose on one Linux VPS |
| Languages | Uzbek (default), English, Russian |

## Repository layout

```
backend/            FastAPI app (app/), Alembic migrations, pytest suite
  app/api/v1/       HTTP routes (public, auth, account, orders, files, messages, webhooks, admin/*)
  app/services/     business rules: order state machine, pricing, orders, notifications, files, email
  app/payments/     Click, Payme, Stripe, manual — verification + idempotent confirmation
  app/ai/           provider adapters, manager (budgets), router/planner/executor/validator pipeline, sandbox
  app/telegram/     Bot API client and command handling
  app/tasks/        Celery app and scheduled jobs
frontend/           Next.js app: public site, customer dashboard (/dashboard), admin panel (/admin)
infrastructure/     Caddyfile and ops scripts (deploy, backup, restore, healthcheck, bootstrap-admin)
docs/               Architecture, API, database, security, deployment, backup, operations
```

## Local development

Requirements: Python 3.12+, Node 22, PostgreSQL 16, Redis 7 (or Docker).

```bash
# with Docker
cp .env.example .env            # for local dev you can leave most values empty
docker compose up -d --build
docker compose exec backend-api alembic upgrade head
docker compose exec backend-api python -m app.cli seed-categories
docker compose exec backend-api python -m app.cli seed-service-drafts   # inactive drafts, no prices
docker compose exec backend-api python -m app.cli seed-content
docker compose exec -it backend-api python -m app.cli create-admin --email you@example.com
# open http://localhost:3000 — dev emails are written to /data/storage/dev-mailbox.log in the backend container
```

Without Docker:

```bash
cd backend && python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
export APP_ENV=development EMAIL_BACKEND=console DATABASE_URL=postgresql+psycopg://vimora:vimora_dev@127.0.0.1:5432/vimora
alembic upgrade head && uvicorn app.main:app --reload --port 8000
celery -A app.tasks.celery_app worker -Q default,ai -c 2      # second terminal
celery -A app.tasks.celery_app beat                            # third terminal
cd ../frontend && npm ci && npm run dev                        # http://localhost:3000 (proxies /api to :8000)
```

## Tests

```bash
cd backend && pytest -q          # needs a database named vimora_test (refuses any other DB)
cd frontend && npm test && npm run typecheck && npm run build
```

## Production

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). In short:

```bash
cp .env.example .env && ./infrastructure/scripts/gen-secrets.sh   # paste secrets into .env
./infrastructure/scripts/deploy.sh
./infrastructure/scripts/bootstrap-admin.sh owner@yourdomain.com
```

Integrations that need your credentials (SMTP, Telegram, Click, Payme, Stripe, AI provider, S3) are built and tested against their documented protocols, but show **CONFIGURATION REQUIRED** until you supply credentials. Nothing pretends to work without them.
