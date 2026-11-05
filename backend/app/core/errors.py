"""Consistent API error envelope: {"error": {"code": str, "message": str, "details": any}}."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger

log = get_logger("errors")


class AppError(Exception):
    status_code = 400
    code = "BAD_REQUEST"

    def __init__(self, message: str, *, code: str | None = None, status_code: int | None = None, details: Any = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code
        self.details = details


class NotFound(AppError):
    status_code = 404
    code = "NOT_FOUND"


class Forbidden(AppError):
    status_code = 403
    code = "FORBIDDEN"


class Unauthorized(AppError):
    status_code = 401
    code = "UNAUTHORIZED"


class Conflict(AppError):
    status_code = 409
    code = "CONFLICT"


class RateLimited(AppError):
    status_code = 429
    code = "RATE_LIMITED"


class ConfigurationRequired(AppError):
    status_code = 503
    code = "CONFIGURATION_REQUIRED"


class InvalidTransition(AppError):
    status_code = 409
    code = "INVALID_STATUS_TRANSITION"


# Stable, append-only error numbers shown to users ("E2105") so a problem can be reported precisely.
# 1xxx general / auth · 2xxx orders · 3xxx payments · 4xxx files · 5xxx AI · 6xxx catalog & admin · 7xxx local services
_CODES = {
    1000: "BAD_REQUEST", 1001: "VALIDATION_ERROR", 1002: "UNAUTHORIZED", 1003: "FORBIDDEN", 1004: "NOT_FOUND", 1005: "CONFLICT",
    1006: "RATE_LIMITED", 1007: "CSRF_FAILED", 1008: "MAINTENANCE", 1009: "PAYLOAD_TOO_LARGE", 1010: "METHOD_NOT_ALLOWED", 1011: "HTTP_ERROR",
    1012: "INTERNAL_ERROR", 1013: "CONFIGURATION_REQUIRED", 1014: "IDEMPOTENCY_CONFLICT", 1015: "DUPLICATE",
    1101: "INVALID_CREDENTIALS", 1102: "EMAIL_NOT_VERIFIED", 1103: "WEAK_PASSWORD", 1104: "TOKEN_INVALID", 1105: "LINK_EXPIRED",
    1106: "REGISTRATION_CLOSED", 1107: "MFA_REQUIRED", 1108: "MFA_PENDING", 1109: "MFA_INVALID", 1110: "MFA_NOT_SETUP", 1111: "MFA_NOT_ENABLED",
    1112: "MFA_ALREADY_ENABLED", 1113: "LAST_SUPER_ADMIN", 1114: "FORBIDDEN_TARGET", 1115: "FORBIDDEN_FOR_OWNER", 1116: "EMAIL_NOT_CONFIGURED",
    1117: "EMAIL_DELIVERY_FAILED",
    2001: "SERVICE_UNAVAILABLE", 2002: "MISSING_REQUIREMENT", 2003: "INVALID_REQUIREMENT", 2004: "INVALID_DEADLINE", 2005: "DESCRIPTION_TOO_SHORT",
    2006: "INVALID_QUANTITY", 2007: "INVALID_ADDON", 2008: "ATTACHMENTS_NOT_ALLOWED", 2009: "FILE_REQUIRED", 2010: "INVALID_STATE",
    2011: "INVALID_STATUS_TRANSITION", 2012: "NOT_CANCELLABLE", 2013: "QUOTATION_CLOSED", 2014: "QUOTATION_EXPIRED", 2015: "REVISION_LIMIT",
    2016: "ALREADY_REVIEWED", 2017: "INVALID_RATING", 2018: "NO_REVIEW", 2019: "EMPTY_MESSAGE", 2020: "NO_APPROVED_DELIVERABLE",
    2021: "ALREADY_RELEASED", 2022: "USE_DEDICATED_ACTION", 2023: "INVALID_LINE_ITEM",
    3001: "NO_PAYMENT_DUE", 3002: "ALREADY_PAID", 3003: "AMOUNT_MISMATCH", 3004: "DUPLICATE_PAYMENT", 3005: "INVALID_AMOUNT",
    3006: "INVALID_CURRENCY", 3007: "CURRENCY_NOT_SUPPORTED", 3008: "PROVIDER_UNAVAILABLE", 3009: "PROVIDER_ERROR", 3010: "UNKNOWN_PROVIDER",
    3011: "REFUND_TOO_LARGE", 3012: "BALANCE_OUTSTANDING", 3013: "INVALID_PROMO", 3014: "PROMO_INVALID", 3015: "PROMO_EXPIRED",
    3016: "PROMO_EXHAUSTED", 3017: "PROMO_MINIMUM", 3018: "PROMO_NOT_APPLICABLE", 3019: "PRICING_ERROR", 3020: "INVALID_PRICING",
    4001: "UPLOAD_EMPTY", 4002: "UPLOAD_TOO_LARGE", 4003: "UPLOAD_TYPE_NOT_ALLOWED", 4004: "UPLOAD_CONTENT_MISMATCH", 4005: "UPLOAD_CONTENT_REJECTED",
    4006: "UPLOAD_MALWARE", 4007: "STORAGE_QUOTA_EXCEEDED", 4008: "ATTACHMENT_NOT_FOUND", 4009: "NO_FILES_SELECTED",
    5001: "AI_NOT_ELIGIBLE", 5002: "AI_BUDGET_EXCEEDED", 5003: "AI_DAILY_LIMIT", 5004: "AI_ATTEMPTS_EXCEEDED", 5005: "UNKNOWN_CAPABILITY",
    5006: "CAPABILITY_REQUIRED",
    6001: "DUPLICATE_SLUG", 6002: "CATEGORY_IN_USE", 6003: "SERVICE_IN_USE", 6004: "UNKNOWN_SETTING", 6005: "INVALID_SETTING", 6006: "INVALID_PROVIDER",
    7001: "AREA_REQUIRED", 7002: "INVALID_AREA", 7003: "SERVICE_NOT_IN_AREA", 7004: "AREA_NOT_LOCAL", 7005: "HANDOVER_REQUIRED",
    7006: "HANDOVER_NOT_APPLICABLE", 7007: "INVALID_MEETUP", 7008: "MEETUP_NOT_CONFIRMED", 7009: "NOT_LOCAL", 7010: "NOT_MEETUP", 7011: "USE_HANDOVER",
}
ERROR_NUMBERS: dict[str, int] = {code: n for n, code in _CODES.items()}


def error_number(code: str) -> str:
    return f"E{ERROR_NUMBERS.get(code, 1000)}"


def _body(code: str, message: str, details: Any = None) -> dict:
    from app.core.logging import request_id_ctx

    out: dict[str, Any] = {"error": {"code": code, "number": error_number(code), "message": message, "request_id": request_id_ctx.get() or None}}
    if details is not None:
        out["error"]["details"] = details
    return out


def _clean_ctx(ctx: Any) -> dict:
    """Only simple limits (min/max length, bounds) go to the client; never echo submitted values."""
    if not isinstance(ctx, dict):
        return {}
    return {k: v for k, v in ctx.items() if k in ("min_length", "max_length", "ge", "gt", "le", "lt", "expected") and isinstance(v, (int, float, str)) and len(str(v)) < 80}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        headers = {"Retry-After": str(exc.details.get("retry_after"))} if isinstance(exc, RateLimited) and isinstance(exc.details, dict) and exc.details.get("retry_after") else None
        return JSONResponse(_body(exc.code, exc.message, exc.details), status_code=exc.status_code, headers=headers)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException):
        code = {401: "UNAUTHORIZED", 403: "FORBIDDEN", 404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED", 413: "PAYLOAD_TOO_LARGE"}.get(exc.status_code, "HTTP_ERROR")
        return JSONResponse(_body(code, str(exc.detail)), status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError):
        details = []
        for e in exc.errors():
            loc = [str(p) for p in e.get("loc", [])]
            path = [p for p in loc if p not in ("body", "query", "path", "header")]
            details.append({"loc": loc, "field": ".".join(path) or None, "msg": e.get("msg"), "type": e.get("type"), "ctx": _clean_ctx(e.get("ctx"))})
        return JSONResponse(_body("VALIDATION_ERROR", "Request validation failed", details), status_code=422)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):  # never leak stack traces to the client
        import secrets

        from app.core.logging import request_id_ctx

        rid = request_id_ctx.get() or request.headers.get("X-Request-ID") or secrets.token_hex(8)
        token = request_id_ctx.set(rid)
        try:
            # the full traceback goes to the server log together with the ID the user sees
            log.exception("Unhandled error id=%s %s %s: %s", rid, request.method, request.url.path, type(exc).__name__)
            body = _body("INTERNAL_ERROR", "An unexpected error occurred")
        finally:
            request_id_ctx.reset(token)
        return JSONResponse(body, status_code=500, headers={"X-Request-ID": rid})
