from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.errors import _body
from app.core.logging import get_logger, request_id_ctx

log = get_logger("http")

API_CSP = "default-src 'none'; frame-ancestors 'none'"


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        rid = request.headers.get("x-request-id")
        rid = rid if rid and len(rid) <= 64 and rid.replace("-", "").isalnum() else uuid.uuid4().hex
        token = request_id_ctx.set(rid)
        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(token)
        response.headers["X-Request-ID"] = rid
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        h = response.headers
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("X-Frame-Options", "DENY")
        h.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        h.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        h.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        h.setdefault("Content-Security-Policy", API_CSP)
        if settings.is_production:
            h.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains")
        if request.url.path.startswith("/api/v1/") and "cache-control" not in h:
            h["Cache-Control"] = "no-store"
        return response


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Rejects oversize bodies early based on Content-Length (uploads allowed up to the upload limit)."""

    async def dispatch(self, request: Request, call_next) -> Response:
        cl = request.headers.get("content-length")
        limit = (settings.MAX_UPLOAD_MB + 1) * 1024 * 1024 if "multipart/form-data" in request.headers.get("content-type", "") else 1024 * 1024
        if cl and cl.isdigit() and int(cl) > limit:
            return JSONResponse(_body("PAYLOAD_TOO_LARGE", "Request body too large"), status_code=413)
        return await call_next(request)


MAINTENANCE_ALLOW = ("/api/v1/auth/", "/api/v1/admin", "/api/v1/webhooks/", "/api/v1/health", "/api/v1/site", "/health")


class MaintenanceMiddleware(BaseHTTPMiddleware):
    """When maintenance mode is on, customer write operations are paused. Payment webhooks,
    authentication and the admin panel keep working so no confirmed payment is lost."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method not in ("GET", "HEAD", "OPTIONS") and not request.url.path.startswith(MAINTENANCE_ALLOW):
            from app.core.db import SessionLocal
            from app.services.settings_service import maintenance_enabled

            try:
                with SessionLocal() as db:
                    on = maintenance_enabled(db)
            except Exception:
                on = False
            if on:
                return JSONResponse(_body("MAINTENANCE", "VIMORA is under maintenance. Please try again shortly."), status_code=503)
        return await call_next(request)
