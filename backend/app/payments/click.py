"""Click SHOP API (merchant side): Prepare (action=0) and Complete (action=1).

Signature: md5(click_trans_id + service_id + SECRET_KEY + merchant_trans_id
               [+ merchant_prepare_id for complete] + amount + action + sign_time)
Docs: https://docs.click.uz/click-api-request/
"""

from __future__ import annotations

import hashlib
import hmac
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.orm import Session as DB

from app.core.config import settings
from app.core.logging import get_logger
from app.models import Payment
from app.models.enums import PaymentProvider, PaymentStatus
from app.payments.service import PaymentVerificationError, cancel_payment, confirm_payment, mark_processing, verify_payable

log = get_logger("click")

OK, SIGN_FAILED, BAD_AMOUNT, ACTION_NOT_FOUND, ALREADY_PAID, NOT_FOUND, TXN_NOT_FOUND, BAD_REQUEST, CANCELLED = 0, -1, -2, -3, -4, -5, -6, -8, -9


def compute_sign(p: dict, *, with_prepare_id: bool) -> str:
    parts = [str(p.get("click_trans_id", "")), str(p.get("service_id", "")), settings.CLICK_SECRET_KEY, str(p.get("merchant_trans_id", ""))]
    if with_prepare_id:
        parts.append(str(p.get("merchant_prepare_id", "")))
    parts += [str(p.get("amount", "")), str(p.get("action", "")), str(p.get("sign_time", ""))]
    return hashlib.md5("".join(parts).encode()).hexdigest()


def _amount_minor(raw: str) -> int | None:
    try:
        d = Decimal(str(raw))
    except InvalidOperation:
        return None
    if d < 0 or d != d.quantize(Decimal("0.01")):
        return None
    return int(d * 100)


def _resp(p: dict, error: int, note: str, **extra) -> dict:
    return {"click_trans_id": p.get("click_trans_id"), "merchant_trans_id": p.get("merchant_trans_id"), "error": error, "error_note": note, **extra}


def handle(db: DB, params: dict, *, action_expected: int) -> dict:
    required = ["click_trans_id", "service_id", "merchant_trans_id", "amount", "action", "sign_time", "sign_string"]
    if any(params.get(k) in (None, "") for k in required):
        return _resp(params, BAD_REQUEST, "Missing parameters")
    try:
        action = int(params["action"])
    except ValueError:
        return _resp(params, ACTION_NOT_FOUND, "Action not found")
    if action != action_expected:
        return _resp(params, ACTION_NOT_FOUND, "Action not found")
    expected = compute_sign(params, with_prepare_id=action == 1)
    if not settings.CLICK_SECRET_KEY or not hmac.compare_digest(expected, str(params["sign_string"]).lower()):
        log.warning("Click signature verification failed")
        return _resp(params, SIGN_FAILED, "SIGN CHECK FAILED!")
    if str(params["service_id"]) != str(settings.CLICK_SERVICE_ID):
        return _resp(params, BAD_REQUEST, "Unknown service")

    p = db.scalar(select(Payment).where(Payment.reference == str(params["merchant_trans_id"]), Payment.provider == PaymentProvider.CLICK).with_for_update())
    if p is None:
        return _resp(params, NOT_FOUND, "Order not found")
    amount = _amount_minor(params["amount"])
    if amount is None:
        return _resp(params, BAD_AMOUNT, "Incorrect parameter amount")
    click_txn = str(params["click_trans_id"])

    if action == 0:  # PREPARE
        if p.status == PaymentStatus.SUCCEEDED:
            return _resp(params, ALREADY_PAID, "Already paid")
        if p.status in (PaymentStatus.CANCELLED, PaymentStatus.FAILED):
            return _resp(params, CANCELLED, "Transaction cancelled")
        try:
            verify_payable(db, p, amount, "UZS")
        except PaymentVerificationError as e:
            code = BAD_AMOUNT if e.code == "AMOUNT_MISMATCH" else (ALREADY_PAID if e.code == "ALREADY_PROCESSED" else CANCELLED)
            return _resp(params, code, str(e))
        if p.provider_transaction_id and p.provider_transaction_id != click_txn:
            return _resp(params, BAD_REQUEST, "Transaction already in progress")
        mark_processing(db, p, click_txn, state={"click_paydoc_id": params.get("click_paydoc_id")})
        db.commit()
        return _resp(params, OK, "Success", merchant_prepare_id=p.id)

    # COMPLETE
    if str(params.get("merchant_prepare_id", "")) != str(p.id):
        return _resp(params, TXN_NOT_FOUND, "Transaction does not exist")
    if p.provider_transaction_id != click_txn:
        return _resp(params, TXN_NOT_FOUND, "Transaction does not exist")
    if p.status == PaymentStatus.SUCCEEDED:
        return _resp(params, ALREADY_PAID, "Already paid", merchant_confirm_id=p.id)
    if p.status in (PaymentStatus.CANCELLED, PaymentStatus.FAILED):
        return _resp(params, CANCELLED, "Transaction cancelled")
    try:
        click_error = int(params.get("error", 0))
    except ValueError:
        click_error = -1
    if click_error < 0:
        cancel_payment(db, p, f"Click reported error {click_error}: {params.get('error_note', '')}"[:200], failed=True)
        db.commit()
        return _resp(params, CANCELLED, "Transaction cancelled")
    try:
        verify_payable(db, p, amount, "UZS")
        confirm_payment(db, p.id, amount_minor=amount, currency="UZS", provider_transaction_id=click_txn, provider_event_id=f"click:{click_txn}:complete", data={"paydoc": params.get("click_paydoc_id")})
    except PaymentVerificationError as e:
        db.rollback()
        return _resp(params, BAD_AMOUNT if e.code == "AMOUNT_MISMATCH" else BAD_REQUEST, str(e))
    db.commit()
    return _resp(params, OK, "Success", merchant_confirm_id=p.id)
