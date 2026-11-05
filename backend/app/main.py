from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import account, auth, files, health, messages, orders, public, webhooks
from app.api.v1.admin import ai as admin_ai
from app.api.v1.admin import catalog as admin_catalog
from app.api.v1.admin import finance as admin_finance
from app.api.v1.admin import orders as admin_orders
from app.api.v1.admin import people as admin_people
from app.api.v1.admin import pricing as admin_pricing
from app.api.v1.admin import system as admin_system
from app.core.config import settings
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging, get_logger
from app.middleware.security import BodySizeLimitMiddleware, MaintenanceMiddleware, RequestContextMiddleware, SecurityHeadersMiddleware

configure_logging(settings.LOG_LEVEL)
log = get_logger("app")


def create_app() -> FastAPI:
    if settings.is_production:
        problems = settings.validate_for_production()
        if problems:
            # Fail fast and loudly instead of running insecurely.
            raise RuntimeError("Production configuration invalid:\n- " + "\n- ".join(problems))

    app = FastAPI(
        title="VIMORA API",
        version="1.0.0",
        docs_url=None if settings.is_production else "/api/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/api/openapi.json",
    )
    install_error_handlers(app)
    app.add_middleware(MaintenanceMiddleware)
    app.add_middleware(BodySizeLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-CSRF-Token", "Idempotency-Key", "X-Request-ID"],
        max_age=600,
    )
    app.add_middleware(RequestContextMiddleware)

    api = APIRouter(prefix="/api/v1")
    for r in (health.router, auth.router, account.router, public.router, orders.router, files.router, messages.router, webhooks.router,
              admin_orders.router, admin_catalog.router, admin_pricing.router, admin_people.router, admin_finance.router, admin_ai.router, admin_system.router):
        api.include_router(r)
    app.include_router(api)
    return app


app = create_app()
