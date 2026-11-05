"""Customer order endpoints. Every query is scoped to the authenticated customer (IDOR-safe)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DB

from app.api.deps import Auth, RequestCtx, get_auth, get_ctx, get_db, get_verified_auth
from app.core.config import settings
from app.core.errors import AppError, Conflict
from app.core.i18n import pick
from app.models import Attachment, Deliverable, Invoice, Order, OrderEvent, Payment, Quotation, Service, ServiceArea
from app.models.enums import AttachmentPurpose, PaymentStatus
from app.models.enums import OrderStatus as S
from app.payments import service as payments
from app.payments.providers import get_adapter
from app.schemas.inputs import AttachFilesIn, CancelIn, HandoverProposalIn, OrderCreateIn, PaymentCreateIn, QuotationDecisionIn, ReviewIn, RevisionIn
from app.schemas.serializers import attachment_out, deliverable_out, event_out, iso, order_detail, order_summary, payment_out, quotation_out
from app.security.rate_limit import enforce
from app.services import local
from app.services import orders as svc
from app.services.order_state import DELIVERY_VISIBLE_STATES
from app.services.settings_service import get_setting

router = APIRouter(prefix="/orders", tags=["orders"])


def _service_name(db: DB, o: Order, lang: str) -> str | None:
    if not o.service_id:
        return None
    s = db.get(Service, o.service_id)
    return pick(s.name, lang) if s else None


def _area_out(db: DB, area_id: int | None, lang: str) -> dict | None:
    a = db.get(ServiceArea, area_id) if area_id else None
    return {"slug": a.slug, "name": pick(a.name, lang)} if a else None


def build_detail(db: DB, o: Order, *, staff: bool, lang: str) -> dict:
    quotes = db.scalars(select(Quotation).where(Quotation.order_id == o.id).order_by(Quotation.id.desc())).all()
    ev_q = select(OrderEvent).where(OrderEvent.order_id == o.id)
    if not staff:
        ev_q = ev_q.where(OrderEvent.customer_visible.is_(True))
    events = db.scalars(ev_q.order_by(OrderEvent.id)).all()
    att_q = select(Attachment).where(Attachment.order_id == o.id, Attachment.deleted_at.is_(None), Attachment.purpose.in_([AttachmentPurpose.ORDER_INPUT, AttachmentPurpose.MESSAGE]))
    inputs = db.scalars(att_q.order_by(Attachment.id)).all()
    d_q = select(Deliverable).where(Deliverable.order_id == o.id)
    if not staff:
        d_q = d_q.where(Deliverable.released_at.is_not(None))
    dels = db.scalars(d_q.order_by(Deliverable.id)).all() if staff or o.status in DELIVERY_VISIBLE_STATES else []
    pays = db.scalars(select(Payment).where(Payment.order_id == o.id).order_by(Payment.id.desc())).all()
    invoices = db.scalars(select(Invoice).where(Invoice.order_id == o.id).order_by(Invoice.id)).all()
    payment_due = None
    if o.status in payments.PAYABLE_STATES:
        kind, amount = payments.amount_due(o)
        payment_due = {"kind": kind, "amount_minor": amount, "currency": o.currency, "full_amount_minor": o.total_minor - o.paid_minor}
    extra = {
        "quotations": [quotation_out(q) for q in quotes],
        "events": [event_out(e, staff=staff) for e in events],
        "attachments": [attachment_out(a) for a in inputs],
        "deliverables": [deliverable_out(d, db.get(Attachment, d.attachment_id), staff=staff) for d in dels],
        "payments": [payment_out(p, staff=staff) for p in pays],
        "invoices": [{"invoice_number": i.invoice_number, "kind": i.kind, "amount_minor": i.amount_minor, "currency": i.currency, "status": i.status, "paid_at": iso(i.paid_at)} for i in invoices],
        "payment_due": payment_due,
        "can_cancel": o.status in svc.CANCELLABLE_BY_CUSTOMER and o.paid_minor == 0,
        "can_request_revision": o.status == S.DELIVERED,
        "can_review": o.status in (S.DELIVERED, S.CLOSED) and o.reviewed_at is None,
        "handover": local.handover_view(db, o, staff=staff),
        "area": _area_out(db, o.service_area_id, lang),
    }
    return order_detail(o, staff=staff, service_name=_service_name(db, o, lang), extra=extra)


@router.post("", status_code=201)
def create_order(body: OrderCreateIn, db: DB = Depends(get_db), auth: Auth = Depends(get_verified_auth), ctx: RequestCtx = Depends(get_ctx)):
    enforce(f"order-create:{auth.user.id}", 10, 3600, message="Too many orders submitted. Please wait a while.")
    if not body.service_slug and not body.category_slug and len(body.description) < 30:
        raise AppError("Please describe your custom task in more detail (at least 30 characters)", code="DESCRIPTION_TOO_SHORT")
    contact = {k: v for k, v in {"phone": body.contact_phone, "telegram": body.contact_telegram, "email": auth.user.email}.items() if v}
    o = svc.create_order(
        db, auth.user, service_slug=body.service_slug, title=body.title, description=body.description, quantity=body.quantity, addon_keys=body.addons,
        requirements=body.requirements, promo_code=body.promo_code, attachment_ids=body.attachment_ids, category_slug=body.category_slug, deadline=body.deadline,
        budget_minor=body.budget_minor, preferred_language=body.preferred_language, contact_info=contact, area_slug=body.area,
        handover_method=body.handover_method, meetup={"place": body.meetup_place, "time": body.meetup_time, "note": body.meetup_note}, ip=ctx.ip,
    )
    db.commit()
    return build_detail(db, o, staff=False, lang=body.preferred_language)


@router.get("")
def list_orders(
    status: str | None = Query(None, max_length=40),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    lang: str = "uz",
    db: DB = Depends(get_db),
    auth: Auth = Depends(get_auth),
):
    q = select(Order).where(Order.customer_id == auth.user.id)
    if status == "active":
        q = q.where(Order.status.not_in([S.CLOSED, S.CANCELLED, S.REFUNDED]))
    elif status:
        q = q.where(Order.status == status)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.scalars(q.order_by(Order.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": [order_summary(o, service_name=_service_name(db, o, lang)) for o in rows], "total": total, "page": page, "page_size": page_size}


@router.get("/overview")
def overview(db: DB = Depends(get_db), auth: Auth = Depends(get_auth)):
    uid = auth.user.id
    by_status = dict(db.execute(select(Order.status, func.count()).where(Order.customer_id == uid).group_by(Order.status)).all())
    outstanding = db.execute(select(Order.currency, func.sum(Order.total_minor - Order.paid_minor)).where(Order.customer_id == uid, Order.status.in_(list(payments.PAYABLE_STATES))).group_by(Order.currency)).all()
    action_needed = db.scalar(select(func.count()).select_from(Order).where(Order.customer_id == uid, Order.status.in_([S.QUOTATION_PENDING, S.DEPOSIT_PENDING, S.FINAL_PAYMENT_PENDING, S.DELIVERED]))) or 0
    return {"by_status": by_status, "outstanding": [{"currency": c, "amount_minor": int(v or 0)} for c, v in outstanding], "action_needed": action_needed,
            "total": sum(by_status.values()), "active": sum(v for k, v in by_status.items() if k not in (S.CLOSED, S.CANCELLED, S.REFUNDED))}


@router.get("/{order_id}")
def get_order(order_id: int, lang: str = "uz", db: DB = Depends(get_db), auth: Auth = Depends(get_auth)):
    o = svc.get_order_for_customer(db, order_id, auth.user.id)
    return build_detail(db, o, staff=False, lang=lang)


@router.post("/{order_id}/quotation/accept")
def accept_quotation(order_id: int, body: QuotationDecisionIn, db: DB = Depends(get_db), auth: Auth = Depends(get_verified_auth), ctx: RequestCtx = Depends(get_ctx)):
    o = svc.get_order_for_customer(db, order_id, auth.user.id, lock=True)
    svc.accept_quotation(db, o, body.quotation_id, auth.user, ip=ctx.ip)
    db.commit()
    return build_detail(db, o, staff=False, lang=o.preferred_language)


@router.post("/{order_id}/quotation/reject")
def reject_quotation(order_id: int, body: QuotationDecisionIn, db: DB = Depends(get_db), auth: Auth = Depends(get_verified_auth), ctx: RequestCtx = Depends(get_ctx)):
    o = svc.get_order_for_customer(db, order_id, auth.user.id, lock=True)
    svc.reject_quotation(db, o, body.quotation_id, auth.user, body.reason, ip=ctx.ip)
    db.commit()
    return build_detail(db, o, staff=False, lang=o.preferred_language)


@router.post("/{order_id}/cancel")
def cancel(order_id: int, body: CancelIn, db: DB = Depends(get_db), auth: Auth = Depends(get_auth), ctx: RequestCtx = Depends(get_ctx)):
    o = svc.get_order_for_customer(db, order_id, auth.user.id, lock=True)
    svc.cancel_by_customer(db, o, auth.user, body.reason, ip=ctx.ip)
    db.commit()
    return build_detail(db, o, staff=False, lang=o.preferred_language)


@router.post("/{order_id}/revision")
def revision(order_id: int, body: RevisionIn, db: DB = Depends(get_db), auth: Auth = Depends(get_auth), ctx: RequestCtx = Depends(get_ctx)):
    o = svc.get_order_for_customer(db, order_id, auth.user.id, lock=True)
    svc.request_revision(db, o, auth.user, body.note, ip=ctx.ip)
    db.commit()
    return build_detail(db, o, staff=False, lang=o.preferred_language)


@router.post("/{order_id}/close")
def close(order_id: int, db: DB = Depends(get_db), auth: Auth = Depends(get_auth), ctx: RequestCtx = Depends(get_ctx)):
    from app.models.enums import ActorType as A
    from app.services.order_state import transition

    o = svc.get_order_for_customer(db, order_id, auth.user.id, lock=True)
    transition(db, o, S.CLOSED, actor_type=A.CUSTOMER, actor_id=auth.user.id, ip=ctx.ip, message="Accepted by customer")
    db.commit()
    return build_detail(db, o, staff=False, lang=o.preferred_language)


@router.post("/{order_id}/handover/propose")
def handover_propose(order_id: int, body: HandoverProposalIn, db: DB = Depends(get_db), auth: Auth = Depends(get_auth)):
    o = svc.get_order_for_customer(db, order_id, auth.user.id, lock=True)
    local.customer_propose(db, o, auth.user, place=body.place, time=body.time, note=body.note)
    db.commit()
    return build_detail(db, o, staff=False, lang=auth.user.profile.language if auth.user.profile else "uz")


@router.post("/{order_id}/handover/accept")
def handover_accept(order_id: int, db: DB = Depends(get_db), auth: Auth = Depends(get_auth)):
    o = svc.get_order_for_customer(db, order_id, auth.user.id, lock=True)
    local.customer_accept(db, o, auth.user)
    db.commit()
    return build_detail(db, o, staff=False, lang=auth.user.profile.language if auth.user.profile else "uz")


@router.post("/{order_id}/review")
def review(order_id: int, body: ReviewIn, db: DB = Depends(get_db), auth: Auth = Depends(get_auth)):
    o = svc.get_order_for_customer(db, order_id, auth.user.id, lock=True)
    svc.submit_review(db, o, auth.user, body.rating, body.text)
    db.commit()
    return {"status": "ok"}


@router.post("/{order_id}/attachments")
def add_attachments(order_id: int, body: AttachFilesIn, db: DB = Depends(get_db), auth: Auth = Depends(get_auth)):
    o = svc.get_order_for_customer(db, order_id, auth.user.id, lock=True)
    if o.status in (S.CLOSED, S.CANCELLED, S.REFUNDED, S.REFUND_PENDING):
        raise Conflict("Files cannot be added to this order anymore", code="INVALID_STATE")
    svc._attach_inputs(db, o, body.attachment_ids, auth.user.id)
    from app.models.enums import ActorType as A
    from app.services.order_state import add_event

    add_event(db, o, "FILES_ADDED", actor_type=A.CUSTOMER, actor_id=auth.user.id, data={"count": len(body.attachment_ids)})
    from app.services.notifications import notify_admins

    notify_admins(db, "file.received", key_suffix=f"{o.id}:{o.version}:{len(body.attachment_ids)}:{body.attachment_ids[0] if body.attachment_ids else 0}",
                  title="NEW FILE FROM CUSTOMER", lines=[("Order", f"#{o.order_number}"), ("Files", str(len(body.attachment_ids)))], order=o)
    db.commit()
    return {"status": "ok"}


@router.post("/{order_id}/payments", status_code=201)
def start_payment(order_id: int, body: PaymentCreateIn, idempotency_key: str | None = Header(None, max_length=80), db: DB = Depends(get_db),
                  auth: Auth = Depends(get_verified_auth)):
    enforce(f"pay:{auth.user.id}", 20, 3600)
    o = svc.get_order_for_customer(db, order_id, auth.user.id, lock=True)
    disabled = get_setting(db, "payments.disabled_providers") or []
    instructions = pick(get_setting(db, "payments.manual_instructions") or {}, o.preferred_language)
    adapter = get_adapter(body.provider, disabled=disabled, manual_enabled=bool(get_setting(db, "payments.manual_enabled")), manual_instructions=instructions, currency=o.currency)
    p = payments.create_payment(db, o, auth.user, body.provider, pay_full=body.pay_full, idempotency_key=idempotency_key)
    return_url = f"{settings.APP_URL.rstrip('/')}/dashboard/orders/{o.id}?payment={p.reference}"
    checkout = adapter.checkout(p, return_url)
    db.commit()
    return {"payment": payment_out(p), "redirect_url": checkout.redirect_url, "instructions": checkout.instructions,
            "note": "Payment status is updated only after the provider confirms the transaction to our server."}


@router.get("/{order_id}/payments/{reference}")
def payment_status(order_id: int, reference: str, db: DB = Depends(get_db), auth: Auth = Depends(get_auth)):
    """Polled by the return page. Reports server-side state only — never trusts the redirect."""
    o = svc.get_order_for_customer(db, order_id, auth.user.id)
    p = db.scalar(select(Payment).where(Payment.order_id == o.id, Payment.reference == reference))
    if p is None:
        from app.core.errors import NotFound

        raise NotFound("Payment not found")
    return {"payment": payment_out(p), "confirmed": p.status == PaymentStatus.SUCCEEDED, "order_status": o.status}
