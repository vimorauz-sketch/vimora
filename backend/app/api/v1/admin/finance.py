from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DB

from app.api.deps import Auth, get_db, require
from app.core.db import utcnow
from app.models import AIUsageRecord, Order, Payment, PaymentEvent, Refund, Service, User
from app.models.enums import PaymentStatus, RefundStatus
from app.models.enums import OrderStatus as S
from app.schemas.serializers import iso, payment_out

router = APIRouter(prefix="/admin/finance", tags=["admin:finance"])


def _range(date_from: datetime | None, date_to: datetime | None) -> tuple[datetime, datetime]:
    end = date_to or utcnow()
    start = date_from or (end - timedelta(days=30))
    return start, end


@router.get("/summary")
def summary(date_from: datetime | None = None, date_to: datetime | None = None, db: DB = Depends(get_db), auth: Auth = Depends(require("finance.view"))):
    start, end = _range(date_from, date_to)
    gross = db.execute(select(Payment.currency, Payment.kind, func.sum(Payment.amount_minor), func.count()).where(
        Payment.status.in_([PaymentStatus.SUCCEEDED, PaymentStatus.REFUNDED]), Payment.confirmed_at.between(start, end)).group_by(Payment.currency, Payment.kind)).all()
    refunds = db.execute(select(Refund.currency, func.sum(Refund.amount_minor)).where(Refund.status == RefundStatus.COMPLETED, Refund.processed_at.between(start, end)).group_by(Refund.currency)).all()
    reversed_ = db.execute(select(Payment.currency, func.sum(Payment.amount_minor)).where(Payment.status == PaymentStatus.REFUNDED, Payment.cancelled_at.between(start, end)).group_by(Payment.currency)).all()
    outstanding = db.execute(select(Order.currency, func.sum(Order.total_minor - Order.paid_minor)).where(
        Order.status.in_([S.DEPOSIT_PENDING, S.PARTIALLY_PAID, S.QUEUED, S.AI_PROCESSING, S.AI_REVIEW_REQUIRED, S.MANUAL_PROCESSING, S.COMPLETED_PENDING_FINAL_PAYMENT, S.FINAL_PAYMENT_PENDING, S.REVISION_REQUESTED]),
        Order.total_minor > Order.paid_minor).group_by(Order.currency)).all()
    ai_cost = Decimal(str(db.scalar(select(func.coalesce(func.sum(AIUsageRecord.cost_usd), 0)).where(AIUsageRecord.created_at.between(start, end))) or 0))
    by_ccy: dict[str, dict] = {}
    kind_field = {"DEPOSIT": "deposits_minor", "FINAL": "final_minor", "FULL": "full_minor"}

    def bucket(ccy: str) -> dict:
        return by_ccy.setdefault(ccy, {"gross_minor": 0, "deposits_minor": 0, "final_minor": 0, "full_minor": 0, "payments": 0, "refunded_minor": 0, "outstanding_minor": 0})

    for ccy, kind, amt, n in gross:
        d = bucket(ccy)
        d["gross_minor"] += int(amt or 0)
        d[kind_field[kind]] += int(amt or 0)
        d["payments"] += n
    for ccy, amt in list(refunds) + list(reversed_):
        bucket(ccy)["refunded_minor"] += int(amt or 0)
    for ccy, amt in outstanding:
        bucket(ccy)["outstanding_minor"] += int(amt or 0)
    for d in by_ccy.values():
        d["net_minor"] = d["gross_minor"] - d["refunded_minor"]
    by_service = db.execute(select(Service.slug, Payment.currency, func.sum(Payment.amount_minor)).join(Order, Order.id == Payment.order_id).outerjoin(Service, Service.id == Order.service_id).where(
        Payment.status == PaymentStatus.SUCCEEDED, Payment.confirmed_at.between(start, end)).group_by(Service.slug, Payment.currency)).all()
    return {
        "from": iso(start), "to": iso(end), "currencies": by_ccy,
        "ai_expenses_usd": f"{ai_cost:.4f}",
        "net_estimate_note": "Net = gross received − refunds. AI expenses are reported in USD separately; convert at your own rate for profit estimates.",
        "by_service": [{"service": s or "custom", "currency": c, "amount_minor": int(a or 0)} for s, c, a in by_service],
    }


@router.get("/payments")
def payments(status: str | None = Query(None, max_length=20), provider: str | None = Query(None, max_length=20), page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
             db: DB = Depends(get_db), auth: Auth = Depends(require("finance.view"))):
    q = select(Payment, Order.order_number, User.email).join(Order, Order.id == Payment.order_id).join(User, User.id == Payment.customer_id)
    if status:
        q = q.where(Payment.status == status)
    if provider:
        q = q.where(Payment.provider == provider)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.execute(q.order_by(Payment.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": [{**payment_out(p, staff=True), "order_number": num, "customer_email": email} for p, num, email in rows], "total": total, "page": page}


@router.get("/payments/{pid}/events")
def payment_events(pid: int, db: DB = Depends(get_db), auth: Auth = Depends(require("finance.view"))):
    rows = db.scalars(select(PaymentEvent).where(PaymentEvent.payment_id == pid).order_by(PaymentEvent.id))
    return {"items": [{"id": e.id, "type": e.event_type, "from": e.from_status, "to": e.to_status, "provider_event_id": e.provider_event_id, "data": e.data, "created_at": iso(e.created_at)} for e in rows]}


@router.get("/refunds")
def refunds(db: DB = Depends(get_db), auth: Auth = Depends(require("finance.view"))):
    rows = db.execute(select(Refund, Order.order_number).join(Order, Order.id == Refund.order_id).order_by(Refund.id.desc()).limit(200)).all()
    return {"items": [{"id": r.id, "order_id": r.order_id, "order_number": n, "payment_id": r.payment_id, "amount_minor": r.amount_minor, "currency": r.currency, "status": r.status,
                       "reason": r.reason, "provider_refund_id": r.provider_refund_id, "created_at": iso(r.created_at), "processed_at": iso(r.processed_at)} for r, n in rows]}


@router.get("/reconciliation")
def reconciliation(db: DB = Depends(get_db), auth: Auth = Depends(require("finance.view"))):
    """Flags inconsistencies for manual reconciliation against provider dashboards."""
    stale = db.scalars(select(Payment).where(Payment.status == PaymentStatus.PROCESSING, Payment.updated_at < utcnow() - timedelta(hours=1)).limit(100)).all()
    mismatch = db.execute(select(PaymentEvent, Payment).join(Payment, Payment.id == PaymentEvent.payment_id).where(PaymentEvent.event_type == "AMOUNT_MISMATCH").order_by(PaymentEvent.id.desc()).limit(100)).all()
    paid_sum = dict(db.execute(select(Payment.order_id, func.sum(Payment.amount_minor)).where(Payment.status.in_([PaymentStatus.SUCCEEDED, PaymentStatus.REFUNDED])).group_by(Payment.order_id)).all())
    drift = [{"order_id": o.id, "order_number": o.order_number, "order_paid_minor": o.paid_minor, "payments_sum_minor": int(paid_sum.get(o.id, 0))}
             for o in db.scalars(select(Order).where(Order.paid_minor > 0)) if int(paid_sum.get(o.id, 0)) != o.paid_minor]
    return {"stale_processing": [payment_out(p, staff=True) for p in stale],
            "amount_mismatches": [{"payment": payment_out(p, staff=True), "event": e.data, "at": iso(e.created_at)} for e, p in mismatch], "ledger_drift": drift}


@router.get("/export.csv")
def export(date_from: datetime | None = None, date_to: datetime | None = None, db: DB = Depends(get_db), auth: Auth = Depends(require("finance.view"))):
    start, end = _range(date_from, date_to)
    rows = db.execute(select(Payment, Order.order_number, User.email).join(Order, Order.id == Payment.order_id).join(User, User.id == Payment.customer_id)
                      .where(Payment.created_at.between(start, end)).order_by(Payment.id)).all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["payment_ref", "order_number", "customer_email", "kind", "provider", "status", "amount", "currency", "provider_txn", "created_at", "confirmed_at"])
    for p, num, email in rows:
        # prefix cells that spreadsheet apps could interpret as formulas
        safe = lambda v: f"'{v}" if isinstance(v, str) and v[:1] in "=+-@" else v  # noqa: E731
        w.writerow([p.reference, num, safe(email), p.kind, p.provider, p.status, f"{p.amount_minor / 100:.2f}", p.currency, safe(p.provider_transaction_id or ""), iso(p.created_at), iso(p.confirmed_at)])
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="vimora-payments-{start:%Y%m%d}-{end:%Y%m%d}.csv"'})
