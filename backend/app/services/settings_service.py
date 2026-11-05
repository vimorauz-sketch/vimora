"""Runtime system settings stored in DB with typed defaults. Secret values are Fernet-encrypted
and can never be read back through the API (only a masked indicator is returned)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session as DB

from app.core.config import settings as env
from app.core.errors import AppError
from app.models import SystemSetting
from app.security.crypto import decrypt_secret, encrypt_secret

DEFAULTS: dict[str, Any] = {
    "platform.name": "VIMORA",
    "platform.tagline": {"uz": "Har bir vazifa. Bitta aqlli platforma.", "en": "Every task. One intelligent platform.", "ru": "Любая задача. Одна умная платформа."},
    "platform.logo_attachment_id": None,
    "platform.brand_accent": "#D6F36A",
    "platform.default_language": env.DEFAULT_LANGUAGE,
    "platform.currencies": ["UZS", "USD"],
    "platform.default_currency": env.DEFAULT_CURRENCY,
    "platform.timezone": env.TIMEZONE,
    "platform.maintenance_mode": False,
    "platform.maintenance_message": {"uz": "", "en": "", "ru": ""},
    "platform.contact_email": "",
    "platform.contact_telegram": "",
    "auth.registration_enabled": env.REGISTRATION_ENABLED,
    "uploads.max_mb": env.MAX_UPLOAD_MB,
    "files.retention_days": 365,
    "notifications.email_enabled": True,
    "notifications.telegram_admin_events": [
        "order.created", "custom_request.created", "quotation.accepted", "payment.deposit_received", "payment.failed",
        "ai.started", "ai.completed", "ai.failed", "review.required", "message.received", "revision.requested",
        "payment.final_received", "order.cancelled",
    ],
    "ai.enabled": False,
    "ai.daily_budget_usd": env.AI_DAILY_BUDGET,
    "ai.per_execution_budget_usd": "1.00",
    "ai.max_retries": 2,
    "ai.max_executions_per_day": 50,
    "ai.assistant_enabled": True,
    "ai.assistant_daily_limit_per_ip": 20,
    "payments.manual_enabled": env.MANUAL_PAYMENTS_ENABLED,
    "payments.manual_instructions": {"uz": "", "en": "", "ru": ""},
    "payments.disabled_providers": [],
    "orders.release_policy": "AFTER_FULL_PAYMENT",  # AFTER_FULL_PAYMENT | ON_APPROVAL
    "orders.auto_close_days": 14,
}

SECRET_KEYS = {"telegram.bot_token_override"}  # extend as needed; AI keys live in AIProvider
PUBLIC_KEYS = {
    "platform.name", "platform.tagline", "platform.logo_attachment_id", "platform.brand_accent", "platform.default_language",
    "platform.currencies", "platform.default_currency", "platform.timezone", "platform.maintenance_mode",
    "platform.maintenance_message", "platform.contact_email", "platform.contact_telegram", "auth.registration_enabled",
    "uploads.max_mb", "ai.assistant_enabled", "payments.manual_enabled",
}


def get_setting(db: DB, key: str) -> Any:
    row = db.scalar(select(SystemSetting).where(SystemSetting.key == key))
    if row is None:
        return DEFAULTS.get(key)
    if row.is_secret:
        return decrypt_secret(row.encrypted_value)
    return row.value


def get_many(db: DB, keys: set[str] | None = None) -> dict[str, Any]:
    keys = keys or set(DEFAULTS)
    rows = {r.key: r for r in db.scalars(select(SystemSetting).where(SystemSetting.key.in_(keys)))}
    out: dict[str, Any] = {}
    for k in keys:
        r = rows.get(k)
        if r is None:
            out[k] = DEFAULTS.get(k)
        elif r.is_secret:
            out[k] = "********" if r.encrypted_value else None
        else:
            out[k] = r.value
    return out


def _validate(key: str, value: Any) -> Any:
    if key not in DEFAULTS and key not in SECRET_KEYS:
        raise AppError(f"Unknown setting: {key}", code="UNKNOWN_SETTING")
    default = DEFAULTS.get(key)
    if key == "uploads.max_mb":
        v = int(value)
        if not 1 <= v <= env.MAX_UPLOAD_MB:
            raise AppError(f"uploads.max_mb must be between 1 and {env.MAX_UPLOAD_MB} (server limit)", code="INVALID_SETTING")
        return v
    if key == "platform.default_language" and value not in ("uz", "en", "ru"):
        raise AppError("Unsupported language", code="INVALID_SETTING")
    if key == "platform.currencies" and (not isinstance(value, list) or not value or not set(value) <= {"UZS", "USD"}):
        raise AppError("Currencies must be a non-empty subset of UZS, USD", code="INVALID_SETTING")
    if key == "orders.release_policy" and value not in ("AFTER_FULL_PAYMENT", "ON_APPROVAL"):
        raise AppError("Invalid release policy", code="INVALID_SETTING")
    if key in ("ai.daily_budget_usd", "ai.per_execution_budget_usd"):
        from decimal import Decimal, InvalidOperation

        try:
            if Decimal(str(value)) < 0:
                raise InvalidOperation
        except InvalidOperation:
            raise AppError("Budget must be a non-negative number", code="INVALID_SETTING") from None
        return str(value)
    if default is not None and not isinstance(value, type(default)) and not (isinstance(default, (int, float)) and isinstance(value, (int, float)) and not isinstance(value, bool)):
        raise AppError(f"Invalid type for {key}", code="INVALID_SETTING")
    return value


def set_setting(db: DB, key: str, value: Any, *, actor_id: int | None) -> None:
    value = _validate(key, value)
    row = db.scalar(select(SystemSetting).where(SystemSetting.key == key))
    if row is None:
        row = SystemSetting(key=key)
        db.add(row)
    row.updated_by_id = actor_id
    if key in SECRET_KEYS:
        row.is_secret = True
        row.encrypted_value = encrypt_secret(str(value)) if value else None
        row.value = None
    else:
        row.value = value


def maintenance_enabled(db: DB) -> bool:
    return bool(get_setting(db, "platform.maintenance_mode"))
