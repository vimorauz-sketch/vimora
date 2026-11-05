"""Stripe webhook verification and handling (no SDK; follows Stripe's documented scheme).

Signature header: Stripe-Signature: t=<ts>,v1=<hex hmac_sha256(secret, f"{t}.{payload}")>
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session as DB

from app.core.config import settings
from app.core.db import utcnow
from app.models import Payment, ProcessedWebhookEvent
from app.models.enums import PaymentProvider, PaymentStatus
from app.payments.service import PaymentVerificationError, cancel_payment, confirm_payment

TOLERANCE_SECONDS = 300


class SignatureError(Exception):
    pass


def verify_signature(payload: bytes, header: str | None, secret: str, *, now: int | None = None) -> None:
    if not header or not secret:
        raise SignatureError("missing signature")
    parts = dict(kv.split("=", 1) for kv in header.split(",") if "=" in kv)
    ts = parts.get("t")
    sigs = [v for k, v in (kv.split("=", 1) for kv in header.split(",") if "=" in kv) if k == "v1"]
    if not ts or not sigs or not ts.isdigit():
        raise SignatureError("malformed signature header")
    if abs((now or int(time.time())) - int(ts)) > TOLERANCE_SECONDS:
        raise SignatureError("timestamp outside tolerance")  # replay protection
    expected = hmac.new(secret.encode(), f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected, s) for s in sigs):
        raise SignatureError("signature mismatch")


def handle(db: DB, payload: bytes, header: str | None) -> dict:
    verify_signature(payload, header, settings.STRIPE_WEBHOOK_SECRET)
    event = json.loads(payload)
    event_id = str(event.get("id", ""))
    # replay / duplicate protection
    inserted = db.execute(
        insert(ProcessedWebhookEvent).values(provider=PaymentProvider.STRIPE, event_id=event_id, created_at=utcnow()).on_conflict_do_nothing().returning(ProcessedWebhookEvent.id)
    ).scalar()
    if inserted is None:
        return {"status": "duplicate"}
    etype = event.get("type", "")
    obj = (event.get("data") or {}).get("object") or {}
    ref = (obj.get("metadata") or {}).get("payment_ref") or obj.get("client_reference_id")
    p = db.scalar(select(Payment).where(Payment.reference == str(ref), Payment.provider == PaymentProvider.STRIPE)) if ref else None
    if p is None:
        db.commit()
        return {"status": "ignored"}

    if etype in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
        if obj.get("payment_status") != "paid":
            db.commit()
            return {"status": "awaiting_payment"}
        try:
            confirm_payment(db, p.id, amount_minor=int(obj.get("amount_total", -1)), currency=str(obj.get("currency", "")).upper(),
                            provider_transaction_id=str(obj.get("payment_intent") or obj.get("id")), provider_event_id=event_id)
        except PaymentVerificationError as e:
            db.commit()  # keep the processed-event + mismatch event record
            return {"status": "rejected", "reason": e.code}
    elif etype in ("checkout.session.async_payment_failed", "checkout.session.expired"):
        if p.status in (PaymentStatus.PENDING, PaymentStatus.PROCESSING):
            cancel_payment(db, p, etype, failed=etype.endswith("failed"))
    db.commit()
    return {"status": "ok"}
