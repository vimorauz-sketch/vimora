"""Payment lifecycle.

The ONLY function that marks money as received is `confirm_payment()`. It is called solely
from (a) provider webhook handlers after signature + amount + reference verification, or
(b) an authorised admin recording a manual payment (audited). It is idempotent: duplicate
provider notifications cannot double count.
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session as DB

from app.core.db import utcnow
from app.core.errors import AppError, Conflict
from app.core.logging import get_logger
from app.models import Invoice, Order, Payment, PaymentEvent, User
from app.models.enums import ActorType as A
from app.models.enums import OrderStatus as S
from app.models.enums import PaymentKind, PaymentProvider, PaymentStatus
from app.security.crypto import new_token
from app.services import order_state
from app.services.audit import audit
from app.services.notifications import notify_admins, notify_customer
from app.services.pricing import format_money

log = get_logger("payments")
PAYABLE_STATES = {S.DEPOSIT_PENDING, S.PARTIALLY_PAID, S.FINAL_PAYMENT_PENDING}
REUSE_WINDOW = timedelta(minutes=30)


class PaymentVerificationError(Exception):
    """Raised when a provider notification fails amount/reference/state verification."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _event(db: DB, p: Payment, event_type: str, *, frm: str | None, to: str | None, provider_event_id: str | None = None, data: dict | None = None) -> None:
    db.add(PaymentEvent(payment_id=p.id, event_type=event_type, from_status=frm, to_status=to, provider_event_id=provider_event_id, data=data or {}, created_at=utcnow()))


def amount_due(order: Order, *, pay_full: bool = False) -> tuple[str, int]:
    """Server-side computation of what the customer owes right now."""
    if order.status == S.DEPOSIT_PENDING:
        if pay_full:
            return PaymentKind.FULL, order.total_minor - order.paid_minor
        return PaymentKind.DEPOSIT, max(order.deposit_minor - order.paid_minor, 0)
    if order.status == S.PARTIALLY_PAID:
        # customer may optionally settle the balance early
        return PaymentKind.FINAL, order.total_minor - order.paid_minor
    if order.status == S.FINAL_PAYMENT_PENDING:
        return PaymentKind.FINAL, order.total_minor - order.paid_minor
    raise Conflict("No payment is due for this order", code="NO_PAYMENT_DUE")


def create_payment(db: DB, order: Order, customer: User, provider: str, *, pay_full: bool = False, idempotency_key: str | None = None) -> Payment:
    if order.status not in PAYABLE_STATES:
        raise Conflict("No payment is due for this order", code="NO_PAYMENT_DUE")
    kind, amount = amount_due(order, pay_full=pay_full)
    if amount <= 0:
        raise Conflict("No payment is due for this order", code="NO_PAYMENT_DUE")
    if idempotency_key:
        existing = db.scalar(select(Payment).where(Payment.idempotency_key == f"c:{customer.id}:{idempotency_key}"))
        if existing:
            if existing.order_id != order.id:
                raise Conflict("Idempotency key reuse", code="IDEMPOTENCY_CONFLICT")
            return existing
    # Reuse a recent identical pending payment instead of creating duplicates
    recent = db.scalar(
        select(Payment).where(
            Payment.order_id == order.id, Payment.provider == provider, Payment.kind == kind, Payment.amount_minor == amount,
            Payment.status == PaymentStatus.PENDING, Payment.created_at > utcnow() - REUSE_WINDOW,
        ).order_by(Payment.id.desc())
    )
    if recent:
        return recent
    p = Payment(
        reference=f"P{utcnow():%y%m%d}{new_token(6).upper().replace('-', 'X').replace('_', 'Y')}"[:24],
        order_id=order.id, customer_id=customer.id, kind=kind, provider=provider, status=PaymentStatus.PENDING,
        amount_minor=amount, currency=order.currency,
        idempotency_key=f"c:{customer.id}:{idempotency_key}" if idempotency_key else f"s:{new_token(16)}",
    )
    db.add(p)
    db.flush()
    _event(db, p, "CREATED", frm=None, to=PaymentStatus.PENDING, data={"amount_minor": amount, "kind": kind})
    audit(db, "payment.created", actor_id=customer.id, actor_type=A.CUSTOMER, entity_type="payment", entity_id=p.id, data={"order_id": order.id, "provider": provider, "amount_minor": amount})
    return p


def verify_payable(db: DB, payment: Payment, amount_minor: int, currency: str | None = None) -> Order:
    """Checks used by provider 'check/prepare' calls before funds move."""
    if payment.status not in (PaymentStatus.PENDING, PaymentStatus.PROCESSING):
        raise PaymentVerificationError("ALREADY_PROCESSED" if payment.status == PaymentStatus.SUCCEEDED else "NOT_PAYABLE", "Payment is not payable")
    if amount_minor != payment.amount_minor:
        raise PaymentVerificationError("AMOUNT_MISMATCH", "Amount does not match")
    if currency and currency.upper() != payment.currency:
        raise PaymentVerificationError("CURRENCY_MISMATCH", "Currency does not match")
    order = db.get(Order, payment.order_id)
    if order is None:
        raise PaymentVerificationError("ORDER_NOT_FOUND", "Order not found")
    if order.status not in PAYABLE_STATES:
        raise PaymentVerificationError("NOT_PAYABLE", "Order is not awaiting payment")
    if payment.amount_minor > order.total_minor - order.paid_minor:
        raise PaymentVerificationError("AMOUNT_MISMATCH", "Amount exceeds outstanding balance")
    return order


def confirm_payment(
    db: DB,
    payment_id: int,
    *,
    amount_minor: int,
    currency: str,
    provider_transaction_id: str,
    provider_event_id: str | None = None,
    recorded_by: User | None = None,
    data: dict | None = None,
) -> Payment:
    """Verified, idempotent confirmation. Caller commits."""
    p = db.scalar(select(Payment).where(Payment.id == payment_id).with_for_update())
    if p is None:
        raise PaymentVerificationError("NOT_FOUND", "Payment not found")
    if p.status == PaymentStatus.SUCCEEDED:
        if p.provider_transaction_id == provider_transaction_id:
            return p  # duplicate notification: no-op (rule 15)
        raise PaymentVerificationError("ALREADY_PROCESSED", "Payment already confirmed with a different transaction")
    if p.status not in (PaymentStatus.PENDING, PaymentStatus.PROCESSING):
        raise PaymentVerificationError("NOT_PAYABLE", f"Payment is {p.status}")
    if amount_minor != p.amount_minor or currency.upper() != p.currency:
        _event(db, p, "AMOUNT_MISMATCH", frm=p.status, to=p.status, provider_event_id=provider_event_id, data={"received": amount_minor, "currency": currency})
        raise PaymentVerificationError("AMOUNT_MISMATCH", "Amount or currency mismatch")

    order = db.scalar(select(Order).where(Order.id == p.order_id).with_for_update())
    prev = p.status
    p.status = PaymentStatus.SUCCEEDED
    p.provider_transaction_id = provider_transaction_id
    p.confirmed_at = utcnow()
    p.recorded_by_id = recorded_by.id if recorded_by else None
    _event(db, p, "SUCCEEDED", frm=prev, to=PaymentStatus.SUCCEEDED, provider_event_id=provider_event_id, data=data or {})

    order.paid_minor += amount_minor
    order.payment_status = "PAID" if order.paid_minor >= order.total_minor else "DEPOSIT_PAID"
    db.add(Invoice(invoice_number=f"INV-{order.order_number}-{p.id}", order_id=order.id, payment_id=p.id, kind=p.kind, amount_minor=amount_minor,
                   currency=p.currency, status="PAID", issued_at=utcnow(), paid_at=utcnow()))
    actor_type = A.ADMIN if recorded_by else A.PAYMENT
    audit(db, "payment.confirmed", actor_id=recorded_by.id if recorded_by else None, actor_type=actor_type, entity_type="payment", entity_id=p.id,
          data={"order_id": order.id, "amount_minor": amount_minor, "provider": p.provider, "provider_txn": provider_transaction_id})

    fully_paid = order.paid_minor >= order.total_minor
    if order.status == S.DEPOSIT_PENDING:
        order_state.transition(db, order, S.PAID if fully_paid else S.PARTIALLY_PAID, actor_type=A.PAYMENT, data={"payment_id": p.id})
        order_state.transition(db, order, S.QUEUED, actor_type=A.SYSTEM, message="Payment verified; queued for execution")
        notify_admins(db, "payment.deposit_received", key_suffix=str(p.id), title="DEPOSIT RECEIVED",
                      lines=[("Order", f"#{order.order_number}"), ("Amount", format_money(amount_minor, p.currency)), ("Provider", p.provider)], order=order)
    elif order.status == S.PARTIALLY_PAID and fully_paid:
        order_state.add_event(db, order, "BALANCE_PAID_EARLY", actor_type=A.PAYMENT, data={"payment_id": p.id})
    elif order.status == S.FINAL_PAYMENT_PENDING and fully_paid:
        order_state.transition(db, order, S.READY_FOR_DELIVERY, actor_type=A.PAYMENT, data={"payment_id": p.id})
        notify_admins(db, "payment.final_received", key_suffix=str(p.id), title="FINAL PAYMENT RECEIVED",
                      lines=[("Order", f"#{order.order_number}"), ("Amount", format_money(amount_minor, p.currency))], order=order)
    elif order.status in (S.CANCELLED,):
        # Money arrived for a cancelled order: keep the record and route to refund handling.
        order_state.transition(db, order, S.REFUND_PENDING, actor_type=A.SYSTEM, message="Payment received after cancellation", customer_visible=False)
    else:
        order_state.add_event(db, order, "PAYMENT_RECEIVED", actor_type=A.PAYMENT, data={"payment_id": p.id})

    customer = db.get(User, order.customer_id)
    notify_customer(db, customer, "payment.confirmed", key_suffix=str(p.id), title_key="n.payment.confirmed.title", body_key="n.payment.confirmed.body",
                    params={"order": order.order_number, "amount": format_money(amount_minor, p.currency)}, order=order, link=f"/dashboard/orders/{order.id}")
    return p


def mark_processing(db: DB, p: Payment, provider_transaction_id: str, *, state: dict | None = None) -> None:
    if p.status == PaymentStatus.PENDING:
        _event(db, p, "PROCESSING", frm=p.status, to=PaymentStatus.PROCESSING, provider_event_id=provider_transaction_id)
        p.status = PaymentStatus.PROCESSING
    p.provider_transaction_id = provider_transaction_id
    if state:
        p.provider_state = {**(p.provider_state or {}), **state}


def cancel_payment(db: DB, p: Payment, reason: str, *, failed: bool = False, state: dict | None = None) -> None:
    if p.status in (PaymentStatus.CANCELLED, PaymentStatus.FAILED):
        return
    if p.status == PaymentStatus.SUCCEEDED:
        raise Conflict("A confirmed payment must be refunded, not cancelled", code="ALREADY_PAID")
    to = PaymentStatus.FAILED if failed else PaymentStatus.CANCELLED
    _event(db, p, "FAILED" if failed else "CANCELLED", frm=p.status, to=to, data={"reason": reason})
    p.status = to
    p.cancelled_at = utcnow()
    p.failure_reason = reason[:1000]
    if state:
        p.provider_state = {**(p.provider_state or {}), **state}
    order = db.get(Order, p.order_id)
    if failed and order:
        notify_admins(db, "payment.failed", key_suffix=str(p.id), title="PAYMENT FAILED",
                      lines=[("Order", f"#{order.order_number}"), ("Provider", p.provider), ("Reason", reason[:120])], order=order)


def reverse_succeeded_payment(db: DB, p: Payment, reason: str, *, state: dict | None = None) -> None:
    """Provider-initiated reversal of a completed payment (e.g. Payme state -2)."""
    if p.status != PaymentStatus.SUCCEEDED:
        return
    order = db.scalar(select(Order).where(Order.id == p.order_id).with_for_update())
    _event(db, p, "REVERSED", frm=p.status, to=PaymentStatus.REFUNDED, data={"reason": reason})
    p.status = PaymentStatus.REFUNDED
    p.cancelled_at = utcnow()
    if state:
        p.provider_state = {**(p.provider_state or {}), **state}
    order.refunded_minor += p.amount_minor
    order.payment_status = "REFUNDED" if order.refunded_minor >= order.paid_minor else "PARTIALLY_REFUNDED"
    order_state.add_event(db, order, "PAYMENT_REVERSED", actor_type=A.PAYMENT, customer_visible=True, data={"payment_id": p.id})
    audit(db, "payment.reversed", actor_type=A.PAYMENT, entity_type="payment", entity_id=p.id, data={"reason": reason})


def record_manual_payment(db: DB, order: Order, admin: User, *, amount_minor: int, reference: str, note: str, ip: str | None) -> Payment:
    """Admin confirms a payment received outside integrated providers (bank transfer, cash).

    Requires finance.manage. The amount must equal what is currently due — no arbitrary amounts.
    """
    if order.status not in PAYABLE_STATES:
        raise Conflict("No payment is due for this order", code="NO_PAYMENT_DUE")
    kind, due = amount_due(order)
    full_due = order.total_minor - order.paid_minor
    if amount_minor not in (due, full_due):
        raise AppError("Amount must equal the deposit or the full outstanding balance", code="AMOUNT_MISMATCH", details={"due": due, "full": full_due})
    if amount_minor == full_due and kind == PaymentKind.DEPOSIT:
        kind = PaymentKind.FULL
    p = Payment(reference=f"M{utcnow():%y%m%d}{new_token(6).upper().replace('-', 'X').replace('_', 'Y')}"[:24], order_id=order.id, customer_id=order.customer_id,
                kind=kind, provider=PaymentProvider.MANUAL, status=PaymentStatus.PENDING, amount_minor=amount_minor, currency=order.currency,
                idempotency_key=f"m:{order.id}:{reference.strip()[:60]}")
    if db.scalar(select(Payment.id).where(Payment.idempotency_key == p.idempotency_key)):
        raise Conflict("A manual payment with this reference was already recorded", code="DUPLICATE_PAYMENT")
    db.add(p)
    db.flush()
    _event(db, p, "MANUAL_RECORDED", frm=None, to=PaymentStatus.PENDING, data={"reference": reference[:120], "note": note[:500], "admin_id": admin.id})
    audit(db, "payment.manual_recorded", actor_id=admin.id, actor_type=A.ADMIN, entity_type="payment", entity_id=p.id, ip=ip, data={"order_id": order.id, "amount_minor": amount_minor, "reference": reference[:120]})
    return confirm_payment(db, p.id, amount_minor=amount_minor, currency=order.currency, provider_transaction_id=f"manual:{reference.strip()[:100]}", recorded_by=admin)
