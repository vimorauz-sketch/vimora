"""Payme Merchant API (JSON-RPC 2.0). Docs: https://developer.help.paycom.uz/

Authentication: HTTP Basic "Paycom:<SECRET_KEY>". Amounts are in tiyin (== our UZS minor unit).
Account field: `payment_ref` (our Payment.reference).
"""

from __future__ import annotations

import base64
import hmac
import time

from sqlalchemy import select
from sqlalchemy.orm import Session as DB

from app.core.config import settings
from app.core.logging import get_logger
from app.models import Payment
from app.models.enums import PaymentProvider, PaymentStatus
from app.payments.service import (
    PaymentVerificationError,
    cancel_payment,
    confirm_payment,
    mark_processing,
    reverse_succeeded_payment,
    verify_payable,
)

log = get_logger("payme")
TIMEOUT_MS = 12 * 60 * 60 * 1000

ERR_AUTH = -32504
ERR_METHOD = -32601
ERR_PARSE = -32700
ERR_RPC = -32600
ERR_AMOUNT = -31001
ERR_TXN_NOT_FOUND = -31003
ERR_CANNOT_CANCEL = -31007
ERR_CANNOT_PERFORM = -31008
ERR_ACCOUNT = -31050  # -31050..-31099: account (order) errors


def _msg(text: str) -> dict:
    return {"ru": text, "uz": text, "en": text}


def err(req_id, code: int, text: str, data: str | None = None) -> dict:
    e = {"code": code, "message": _msg(text)}
    if data:
        e["data"] = data
    return {"jsonrpc": "2.0", "id": req_id, "error": e}


def ok(req_id, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def check_auth(header: str | None) -> bool:
    if not header or not header.startswith("Basic ") or not settings.PAYME_SECRET_KEY:
        return False
    try:
        login, _, password = base64.b64decode(header[6:]).decode().partition(":")
    except (ValueError, UnicodeDecodeError):
        return False
    return hmac.compare_digest(login, "Paycom") & hmac.compare_digest(password, settings.PAYME_SECRET_KEY)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _by_ref(db: DB, account: dict | None) -> Payment | None:
    ref = (account or {}).get("payment_ref")
    if not ref:
        return None
    return db.scalar(select(Payment).where(Payment.reference == str(ref), Payment.provider == PaymentProvider.PAYME).with_for_update())


def _by_txn(db: DB, txn_id: str) -> Payment | None:
    return db.scalar(select(Payment).where(Payment.provider == PaymentProvider.PAYME, Payment.provider_transaction_id == str(txn_id)).with_for_update())


def _state(p: Payment) -> dict:
    s = p.provider_state or {}
    return {
        "create_time": s.get("create_time", 0), "perform_time": s.get("perform_time", 0), "cancel_time": s.get("cancel_time", 0),
        "transaction": str(p.id), "state": s.get("state", 1), "reason": s.get("reason"),
    }


def handle(db: DB, body: dict) -> dict:
    req_id = body.get("id")
    method = body.get("method")
    params = body.get("params") or {}
    if not isinstance(params, dict):
        return err(req_id, ERR_RPC, "Invalid params")

    if method == "CheckPerformTransaction":
        p = _by_ref(db, params.get("account"))
        if p is None:
            return err(req_id, ERR_ACCOUNT, "Payment not found", "payment_ref")
        try:
            verify_payable(db, p, int(params.get("amount", -1)), "UZS")
        except PaymentVerificationError as e:
            if e.code == "AMOUNT_MISMATCH":
                return err(req_id, ERR_AMOUNT, "Incorrect amount")
            return err(req_id, ERR_ACCOUNT - 1, "Payment cannot be performed", "payment_ref")
        if p.status == PaymentStatus.PROCESSING:
            return err(req_id, ERR_ACCOUNT - 2, "Another transaction is in progress", "payment_ref")
        return ok(req_id, {"allow": True})

    if method == "CreateTransaction":
        txn_id = str(params.get("id", ""))
        existing = _by_txn(db, txn_id) if txn_id else None
        if existing is not None:
            st = _state(existing)
            if st["state"] != 1:
                return err(req_id, ERR_CANNOT_PERFORM, "Transaction is not in a creatable state")
            if _now_ms() - st["create_time"] > TIMEOUT_MS:
                cancel_payment(db, existing, "Payme timeout", state={"state": -1, "reason": 4, "cancel_time": _now_ms()})
                db.commit()
                return err(req_id, ERR_CANNOT_PERFORM, "Transaction timed out")
            return ok(req_id, {"create_time": st["create_time"], "transaction": st["transaction"], "state": 1})
        p = _by_ref(db, params.get("account"))
        if p is None:
            return err(req_id, ERR_ACCOUNT, "Payment not found", "payment_ref")
        if p.status == PaymentStatus.PROCESSING and p.provider_transaction_id != txn_id:
            return err(req_id, ERR_ACCOUNT - 2, "Another transaction is in progress", "payment_ref")
        try:
            verify_payable(db, p, int(params.get("amount", -1)), "UZS")
        except PaymentVerificationError as e:
            if e.code == "AMOUNT_MISMATCH":
                return err(req_id, ERR_AMOUNT, "Incorrect amount")
            return err(req_id, ERR_ACCOUNT - 1, "Payment cannot be performed", "payment_ref")
        create_time = _now_ms()
        mark_processing(db, p, txn_id, state={"state": 1, "create_time": create_time, "payme_time": params.get("time")})
        db.commit()
        return ok(req_id, {"create_time": create_time, "transaction": str(p.id), "state": 1})

    if method == "PerformTransaction":
        p = _by_txn(db, str(params.get("id", "")))
        if p is None:
            return err(req_id, ERR_TXN_NOT_FOUND, "Transaction not found")
        st = _state(p)
        if st["state"] == 2:
            return ok(req_id, {"transaction": st["transaction"], "perform_time": st["perform_time"], "state": 2})
        if st["state"] != 1:
            return err(req_id, ERR_CANNOT_PERFORM, "Transaction cannot be performed")
        if _now_ms() - st["create_time"] > TIMEOUT_MS:
            cancel_payment(db, p, "Payme timeout", state={"state": -1, "reason": 4, "cancel_time": _now_ms()})
            db.commit()
            return err(req_id, ERR_CANNOT_PERFORM, "Transaction timed out")
        try:
            verify_payable(db, p, p.amount_minor, "UZS")
            confirm_payment(db, p.id, amount_minor=p.amount_minor, currency="UZS", provider_transaction_id=p.provider_transaction_id, provider_event_id=f"payme:{p.provider_transaction_id}:perform")
        except PaymentVerificationError:
            db.rollback()
            return err(req_id, ERR_CANNOT_PERFORM, "Transaction cannot be performed")
        perform_time = _now_ms()
        p = _by_txn(db, str(params.get("id")))
        p.provider_state = {**(p.provider_state or {}), "state": 2, "perform_time": perform_time}
        db.commit()
        return ok(req_id, {"transaction": str(p.id), "perform_time": perform_time, "state": 2})

    if method == "CancelTransaction":
        p = _by_txn(db, str(params.get("id", "")))
        if p is None:
            return err(req_id, ERR_TXN_NOT_FOUND, "Transaction not found")
        st = _state(p)
        reason = params.get("reason")
        if st["state"] in (-1, -2):
            return ok(req_id, {"transaction": st["transaction"], "cancel_time": st["cancel_time"], "state": st["state"]})
        cancel_time = _now_ms()
        if st["state"] == 1:
            cancel_payment(db, p, f"Cancelled by Payme (reason {reason})", state={"state": -1, "reason": reason, "cancel_time": cancel_time})
            new_state = -1
        else:
            # Performed transaction reversed by Payme. Record it; the order goes to refund handling.
            reverse_succeeded_payment(db, p, f"Cancelled by Payme after perform (reason {reason})", state={"state": -2, "reason": reason, "cancel_time": cancel_time})
            new_state = -2
        db.commit()
        return ok(req_id, {"transaction": str(p.id), "cancel_time": cancel_time, "state": new_state})

    if method == "CheckTransaction":
        p = db.scalar(select(Payment).where(Payment.provider == PaymentProvider.PAYME, Payment.provider_transaction_id == str(params.get("id", ""))))
        if p is None:
            return err(req_id, ERR_TXN_NOT_FOUND, "Transaction not found")
        return ok(req_id, _state(p))

    if method == "GetStatement":
        frm, to = int(params.get("from", 0)), int(params.get("to", 0))
        rows = db.scalars(select(Payment).where(Payment.provider == PaymentProvider.PAYME, Payment.provider_transaction_id.is_not(None)))
        txns = []
        for p in rows:
            st = _state(p)
            if frm <= st["create_time"] <= to:
                txns.append({"id": p.provider_transaction_id, "time": (p.provider_state or {}).get("payme_time"), "amount": p.amount_minor,
                             "account": {"payment_ref": p.reference}, **{k: st[k] for k in ("create_time", "perform_time", "cancel_time", "transaction", "state", "reason")}})
        return ok(req_id, {"transactions": txns})

    return err(req_id, ERR_METHOD, "Method not found")
