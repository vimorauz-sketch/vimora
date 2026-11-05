from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session as DB

from app.api.deps import Auth, RequestCtx, get_ctx, get_db, require
from app.api.v1.orders import build_detail
from app.core.config import settings
from app.core.db import utcnow
from app.core.errors import AppError, Conflict, NotFound
from app.models import Attachment, Deliverable, Order, Payment, Refund, Service, User
from app.models.enums import ActorType as A
from app.models.enums import AttachmentPurpose, PaymentStatus, RefundStatus
from app.models.enums import HandoverStatus as HS
from app.models.enums import OrderStatus as S
from app.payments import service as payments
from app.schemas.inputs import AdminNotesIn, AIStartIn, HandoverProposalIn, DeliverableIn, ManualPaymentIn, MessageIn, QuotationCreateIn, RefundCompleteIn, RefundIn, ReviewModerationIn, StatusChangeIn
from app.schemas.serializers import attachment_out, deliverable_out, order_summary
from app.services import local, order_state
from app.services import orders as svc
from app.services.audit import audit
from app.services.files import store_upload
from app.services.messaging import list_messages, post_message
from app.services.notifications import notify_customer
from app.services.pricing import build_manual_quote, format_money

router = APIRouter(prefix="/admin/orders", tags=["admin:orders"])


LOCAL_STAGES: dict[str, list[str]] = {
    "new": [S.SUBMITTED],
    "awaiting_quote": [S.UNDER_REVIEW, S.QUOTATION_PENDING],
    "awaiting_payment": [S.QUOTATION_ACCEPTED, S.DEPOSIT_PENDING],
    "in_progress": [S.PAID, S.PARTIALLY_PAID, S.QUEUED, S.MANUAL_PROCESSING, S.AI_PROCESSING, S.AI_REVIEW_REQUIRED, S.REVISION_REQUESTED],
    "ready": [S.COMPLETED_PENDING_FINAL_PAYMENT, S.FINAL_PAYMENT_PENDING, S.READY_FOR_DELIVERY],
    "completed": [S.DELIVERED, S.CLOSED],
    "cancelled": [S.CANCELLED, S.REFUND_PENDING, S.REFUNDED, S.FAILED],
}


@router.get("/local-summary")
def local_summary(db: DB = Depends(get_db), auth: Auth = Depends(require("orders.view"))):
    """Counts for the 'Local orders' board."""
    out = {}
    for stage, statuses in LOCAL_STAGES.items():
        out[stage] = db.scalar(select(func.count()).select_from(Order).where(Order.is_local.is_(True), Order.status.in_(statuses))) or 0
    out["arranging"] = db.scalar(select(func.count()).select_from(Order).where(
        Order.is_local.is_(True), Order.handover_status.in_([HS.PROPOSED_BY_CUSTOMER, HS.PROPOSED_BY_ADMIN]),
        Order.status.not_in(LOCAL_STAGES["cancelled"] + LOCAL_STAGES["completed"]))) or 0
    return out


@router.post("/{order_id}/handover/confirm")
def handover_confirm(order_id: int, db: DB = Depends(get_db), auth: Auth = Depends(require("orders.manage"))):
    o = svc.get_order(db, order_id, lock=True)
    local.admin_confirm(db, o, auth.user)
    db.commit()
    return build_detail(db, o, staff=True, lang="uz")


@router.post("/{order_id}/handover/propose")
def handover_propose(order_id: int, body: HandoverProposalIn, db: DB = Depends(get_db), auth: Auth = Depends(require("orders.manage"))):
    o = svc.get_order(db, order_id, lock=True)
    local.admin_propose(db, o, auth.user, place=body.place, time=body.time, note=body.note)
    db.commit()
    return build_detail(db, o, staff=True, lang="uz")


@router.post("/{order_id}/handover/complete")
def handover_complete(order_id: int, db: DB = Depends(get_db), auth: Auth = Depends(require("orders.manage")), ctx: RequestCtx = Depends(get_ctx)):
    o = svc.get_order(db, order_id, lock=True)
    local.admin_handover(db, o, auth.user, ip=ctx.ip)
    db.commit()
    return build_detail(db, o, staff=True, lang="uz")


@router.get("")
def list_orders(
    q: str | None = Query(None, max_length=100),
    status: str | None = Query(None, max_length=40),
    customer_id: int | None = None,
    service_id: int | None = None,
    payment_status: str | None = Query(None, max_length=20),
    needs_action: bool = False,
    local: bool | None = None,
    handover_method: Literal["PICKUP", "MEETUP"] | None = None,
    local_stage: Literal["new", "awaiting_quote", "awaiting_payment", "in_progress", "ready", "arranging", "completed", "cancelled"] | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: DB = Depends(get_db),
    auth: Auth = Depends(require("orders.view")),
):
    stmt = select(Order, User.email).join(User, User.id == Order.customer_id)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Order.order_number.ilike(like), Order.title.ilike(like), User.email.ilike(like)))
    if status:
        stmt = stmt.where(Order.status.in_(status.split(",")))
    if needs_action:
        stmt = stmt.where(Order.status.in_([S.SUBMITTED, S.UNDER_REVIEW, S.QUEUED, S.AI_REVIEW_REQUIRED, S.MANUAL_PROCESSING, S.REVISION_REQUESTED, S.READY_FOR_DELIVERY, S.REFUND_PENDING]))
    if customer_id:
        stmt = stmt.where(Order.customer_id == customer_id)
    if service_id:
        stmt = stmt.where(Order.service_id == service_id)
    if payment_status:
        stmt = stmt.where(Order.payment_status == payment_status)
    if local is not None:
        stmt = stmt.where(Order.is_local.is_(local))
    if handover_method:
        stmt = stmt.where(Order.handover_method == handover_method)
    if local_stage:
        if local_stage == "arranging":
            stmt = stmt.where(Order.handover_status.in_([HS.PROPOSED_BY_CUSTOMER, HS.PROPOSED_BY_ADMIN]), Order.status.not_in(LOCAL_STAGES["cancelled"] + LOCAL_STAGES["completed"]))
        else:
            stmt = stmt.where(Order.status.in_(LOCAL_STAGES[local_stage]))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(stmt.order_by(Order.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    names = {s.id: s.name.get("en") for s in db.scalars(select(Service).where(Service.id.in_({o.service_id for o, _ in rows if o.service_id})))}
    return {"items": [order_summary(o, service_name=names.get(o.service_id), customer_email=email, staff=True) for o, email in rows], "total": total, "page": page, "page_size": page_size}


@router.get("/{order_id}")
def get_order(order_id: int, db: DB = Depends(get_db), auth: Auth = Depends(require("orders.view"))):
    o = svc.get_order(db, order_id)
    detail = build_detail(db, o, staff=True, lang="en")
    customer = db.get(User, o.customer_id)
    detail["customer"] = {"id": customer.id, "email": customer.email, "full_name": customer.profile.full_name if customer.profile else "", "is_active": customer.is_active}
    detail["allowed_transitions"] = order_state.allowed_targets(o.status, A.ADMIN)
    ai_outputs = db.scalars(select(Attachment).where(Attachment.order_id == o.id, Attachment.purpose == AttachmentPurpose.AI_OUTPUT, Attachment.deleted_at.is_(None)).order_by(Attachment.id.desc()).limit(50)).all()
    detail["ai_outputs"] = [attachment_out(a) for a in ai_outputs]
    from app.models import AIExecution
    from app.schemas.serializers import execution_out

    detail["ai_executions"] = [execution_out(e) for e in db.scalars(select(AIExecution).where(AIExecution.order_id == o.id).order_by(AIExecution.id.desc()))]
    return detail


@router.post("/{order_id}/status")
def change_status(order_id: int, body: StatusChangeIn, db: DB = Depends(get_db), auth: Auth = Depends(require("orders.manage")), ctx: RequestCtx = Depends(get_ctx)):
    o = svc.get_order(db, order_id, lock=True)
    # Special transitions with business side effects go through dedicated endpoints.
    if body.to_status in (S.COMPLETED_PENDING_FINAL_PAYMENT, S.READY_FOR_DELIVERY):
        raise Conflict("Use the 'complete work' action", code="USE_DEDICATED_ACTION")
    if body.to_status == S.DELIVERED:
        raise Conflict("Use the 'release delivery' action", code="USE_DEDICATED_ACTION")
    if body.to_status == S.AI_PROCESSING:
        raise Conflict("Use the 'start AI' action", code="USE_DEDICATED_ACTION")
    if body.to_status == S.REFUNDED:
        raise Conflict("Complete the refund in Finance", code="USE_DEDICATED_ACTION")
    if body.to_status == S.QUOTATION_PENDING:
        raise Conflict("Create a quotation instead", code="USE_DEDICATED_ACTION")
    started = o.status == S.QUEUED and body.to_status == S.MANUAL_PROCESSING
    order_state.transition(db, o, body.to_status, actor_type=A.ADMIN, actor_id=auth.user.id, ip=ctx.ip, message=body.message, customer_visible=body.customer_visible)
    if body.to_status == S.MANUAL_PROCESSING:
        o.execution_method = "MANUAL"
    if started:
        notify_customer(db, db.get(User, o.customer_id), "work.started", key_suffix=str(o.id), title_key="n.work.started.title", body_key="n.work.started.body",
                        params={"order": o.order_number}, order=o, link=f"/dashboard/orders/{o.id}")
    if body.to_status == S.CANCELLED and o.paid_minor - o.refunded_minor > 0:
        order_state.transition(db, o, S.REFUND_PENDING, actor_type=A.ADMIN, actor_id=auth.user.id, ip=ctx.ip, message="Cancelled with payments on record", customer_visible=True)
    if body.customer_visible:
        svc.notify_status(db, o)
    db.commit()
    return get_order(order_id, db, auth)


@router.patch("/{order_id}")
def update_notes(order_id: int, body: AdminNotesIn, db: DB = Depends(get_db), auth: Auth = Depends(require("orders.manage"))):
    o = svc.get_order(db, order_id, lock=True)
    changed = {}
    for f in ("admin_notes", "customer_notes", "deadline"):
        v = getattr(body, f)
        if v is not None:
            setattr(o, f, v)
            changed[f] = True
    audit(db, "order.updated", actor_id=auth.user.id, actor_type=A.ADMIN, entity_type="order", entity_id=o.id, data={"fields": list(changed)})
    db.commit()
    return {"status": "ok"}


@router.post("/{order_id}/quotations", status_code=201)
def create_quotation(order_id: int, body: QuotationCreateIn, db: DB = Depends(get_db), auth: Auth = Depends(require("quotations.manage")), ctx: RequestCtx = Depends(get_ctx)):
    o = svc.get_order(db, order_id, lock=True)
    pr = build_manual_quote([li.model_dump() for li in body.line_items], currency=body.currency, discount_minor=body.discount_minor,
                            extra_charges_minor=body.extra_charges_minor, deposit_minor=body.deposit_minor, deposit_percent=body.deposit_percent)
    svc.admin_issue_quotation(db, o, pr, admin=auth.user, note=body.note, delivery_days=body.estimated_delivery_days, ip=ctx.ip)
    db.commit()
    return get_order(order_id, db, auth)


@router.post("/{order_id}/ai/start")
def start_ai(order_id: int, body: AIStartIn, db: DB = Depends(get_db), auth: Auth = Depends(require("ai.operate")), ctx: RequestCtx = Depends(get_ctx)):
    from app.ai.pipeline import start_execution

    o = svc.get_order(db, order_id, lock=True)
    ex = start_execution(db, o, auth.user, capability=body.capability, instructions=body.instructions, ip=ctx.ip)
    db.commit()
    from app.tasks.jobs import run_ai_execution

    try:
        r = run_ai_execution.delay(ex.id)
        ex.celery_task_id = getattr(r, "id", None)
        db.commit()
    except Exception:
        pass  # recover_stuck_ai re-enqueues PENDING executions
    return {"execution_id": ex.id}


# ------------------------------------------------------------------- deliverables
@router.post("/{order_id}/files", status_code=201)
async def upload_deliverable_file(order_id: int, file: UploadFile = File(...), title: str = Form(...), note: str = Form(""), db: DB = Depends(get_db),
                                  auth: Auth = Depends(require("deliverables.manage"))):
    o = svc.get_order(db, order_id, lock=True)
    if o.status not in order_state.WORKING_STATES and o.status != S.READY_FOR_DELIVERY:
        raise Conflict("Deliverables can only be added while work is in progress", code="INVALID_STATE")
    data = await file.read(settings.MAX_UPLOAD_MB * 1024 * 1024 + 1)
    att = store_upload(db, owner_id=auth.user.id, filename=file.filename or "file", data=data, purpose=AttachmentPurpose.DELIVERABLE, order_id=o.id, enforce_quota=False)
    d = Deliverable(order_id=o.id, attachment_id=att.id, title=title[:200], note=note[:4000], source="MANUAL", approved_by_id=auth.user.id, approved_at=utcnow(), revision_round=o.revision_count)
    db.add(d)
    db.flush()
    audit(db, "deliverable.uploaded", actor_id=auth.user.id, actor_type=A.ADMIN, entity_type="deliverable", entity_id=d.id, data={"order_id": o.id})
    db.commit()
    return deliverable_out(d, att, staff=True)


@router.post("/{order_id}/deliverables/from-ai", status_code=201)
def promote_ai_output(order_id: int, body: DeliverableIn, db: DB = Depends(get_db), auth: Auth = Depends(require("deliverables.manage"))):
    """Admin explicitly approves an AI-generated file as a customer deliverable (human-in-the-loop)."""
    o = svc.get_order(db, order_id, lock=True)
    att = db.get(Attachment, body.attachment_id)
    if att is None or att.order_id != o.id or att.purpose != AttachmentPurpose.AI_OUTPUT:
        raise NotFound("AI output not found for this order")
    if db.scalar(select(Deliverable.id).where(Deliverable.attachment_id == att.id)):
        raise Conflict("This file is already a deliverable", code="DUPLICATE")
    att.purpose = AttachmentPurpose.DELIVERABLE
    d = Deliverable(order_id=o.id, attachment_id=att.id, title=body.title, note=body.note, source="AI", approved_by_id=auth.user.id, approved_at=utcnow(), revision_round=o.revision_count)
    db.add(d)
    db.flush()
    audit(db, "deliverable.approved_from_ai", actor_id=auth.user.id, actor_type=A.ADMIN, entity_type="deliverable", entity_id=d.id, data={"order_id": o.id, "attachment_id": att.id})
    db.commit()
    return deliverable_out(d, att, staff=True)


@router.delete("/{order_id}/deliverables/{deliverable_id}")
def delete_deliverable(order_id: int, deliverable_id: int, db: DB = Depends(get_db), auth: Auth = Depends(require("deliverables.manage"))):
    d = db.scalar(select(Deliverable).where(Deliverable.id == deliverable_id, Deliverable.order_id == order_id))
    if d is None:
        raise NotFound("Deliverable not found")
    if d.released_at:
        raise Conflict("Released deliverables cannot be removed", code="ALREADY_RELEASED")
    att = db.get(Attachment, d.attachment_id)
    db.delete(d)
    if att:
        att.deleted_at = utcnow()
    audit(db, "deliverable.removed", actor_id=auth.user.id, actor_type=A.ADMIN, entity_type="deliverable", entity_id=deliverable_id)
    db.commit()
    return {"status": "ok"}


@router.post("/{order_id}/complete")
def complete(order_id: int, db: DB = Depends(get_db), auth: Auth = Depends(require("deliverables.manage")), ctx: RequestCtx = Depends(get_ctx)):
    o = svc.get_order(db, order_id, lock=True)
    from app.models import AIExecution
    from app.models.enums import AIExecutionStatus as X

    # approving completion closes any execution awaiting review
    for ex in db.scalars(select(AIExecution).where(AIExecution.order_id == o.id, AIExecution.status == X.REVIEW_REQUIRED)):
        ex.status = X.APPROVED
    svc.complete_work(db, o, auth.user, ip=ctx.ip)
    db.commit()
    return get_order(order_id, db, auth)


@router.post("/{order_id}/release")
def release(order_id: int, db: DB = Depends(get_db), auth: Auth = Depends(require("deliverables.manage")), ctx: RequestCtx = Depends(get_ctx)):
    o = svc.get_order(db, order_id, lock=True)
    svc.release_delivery(db, o, auth.user, ip=ctx.ip)
    db.commit()
    return get_order(order_id, db, auth)


@router.post("/{order_id}/review-visibility")
def moderate_review(order_id: int, body: ReviewModerationIn, db: DB = Depends(get_db), auth: Auth = Depends(require("orders.manage"))):
    o = svc.get_order(db, order_id, lock=True)
    if o.reviewed_at is None:
        raise Conflict("This order has no review", code="NO_REVIEW")
    o.review_public = body.public
    audit(db, "review.moderated", actor_id=auth.user.id, actor_type=A.ADMIN, entity_type="order", entity_id=o.id, data={"public": body.public})
    db.commit()
    return {"status": "ok"}


# ------------------------------------------------------------------- messages
@router.get("/{order_id}/messages")
def messages(order_id: int, before_id: int | None = None, db: DB = Depends(get_db), auth: Auth = Depends(require("orders.view"))):
    o = svc.get_order(db, order_id)
    items = list_messages(db, o, viewer_is_staff=True, before_id=before_id)
    db.commit()
    return {"items": items}


@router.post("/{order_id}/messages", status_code=201)
def post(order_id: int, body: MessageIn, db: DB = Depends(get_db), auth: Auth = Depends(require("orders.message"))):
    o = svc.get_order(db, order_id)
    out = post_message(db, o, auth.user, as_staff=True, body=body.body, attachment_ids=body.attachment_ids)
    db.commit()
    return out


# ------------------------------------------------------------------- money
@router.post("/{order_id}/manual-payment", status_code=201)
def manual_payment(order_id: int, body: ManualPaymentIn, db: DB = Depends(get_db), auth: Auth = Depends(require("finance.manage")), ctx: RequestCtx = Depends(get_ctx)):
    o = svc.get_order(db, order_id, lock=True)
    payments.record_manual_payment(db, o, auth.user, amount_minor=body.amount_minor, reference=body.reference, note=body.note, ip=ctx.ip)
    db.commit()
    return get_order(order_id, db, auth)


@router.post("/{order_id}/refunds", status_code=201)
def request_refund(order_id: int, body: RefundIn, db: DB = Depends(get_db), auth: Auth = Depends(require("finance.manage")), ctx: RequestCtx = Depends(get_ctx)):
    o = svc.get_order(db, order_id, lock=True)
    p = db.scalar(select(Payment).where(Payment.id == body.payment_id, Payment.order_id == o.id))
    if p is None or p.status != PaymentStatus.SUCCEEDED:
        raise NotFound("Confirmed payment not found for this order")
    already = db.scalar(select(func.coalesce(func.sum(Refund.amount_minor), 0)).where(Refund.payment_id == p.id, Refund.status.in_([RefundStatus.REQUESTED, RefundStatus.APPROVED, RefundStatus.COMPLETED]))) or 0
    if body.amount_minor > p.amount_minor - already:
        raise AppError("Refund exceeds the refundable amount of this payment", code="REFUND_TOO_LARGE", details={"refundable": p.amount_minor - already})
    r = Refund(order_id=o.id, payment_id=p.id, amount_minor=body.amount_minor, currency=p.currency, status=RefundStatus.REQUESTED, reason=body.reason, requested_by_id=auth.user.id)
    db.add(r)
    db.flush()
    if o.status not in (S.REFUND_PENDING, S.REFUNDED) and order_state.can_transition(o.status, S.REFUND_PENDING, A.ADMIN):
        order_state.transition(db, o, S.REFUND_PENDING, actor_type=A.ADMIN, actor_id=auth.user.id, ip=ctx.ip, message="Refund requested")
    audit(db, "refund.requested", actor_id=auth.user.id, actor_type=A.ADMIN, entity_type="refund", entity_id=r.id, ip=ctx.ip, data={"amount_minor": body.amount_minor, "payment_id": p.id})
    db.commit()
    return {"refund_id": r.id, "status": r.status}


@router.post("/{order_id}/refunds/{refund_id}/complete")
def complete_refund(order_id: int, refund_id: int, body: RefundCompleteIn, db: DB = Depends(get_db), auth: Auth = Depends(require("finance.manage")), ctx: RequestCtx = Depends(get_ctx)):
    """Records a refund that was executed with the provider (Stripe API or Click/Payme merchant cabinet)."""
    o = svc.get_order(db, order_id, lock=True)
    r = db.scalar(select(Refund).where(Refund.id == refund_id, Refund.order_id == o.id).with_for_update())
    if r is None or r.status not in (RefundStatus.REQUESTED, RefundStatus.APPROVED):
        raise NotFound("Open refund not found")
    p = db.get(Payment, r.payment_id)
    if p.provider == "STRIPE" and body.provider_refund_id == "auto":
        import httpx

        resp = httpx.post("https://api.stripe.com/v1/refunds", data={"payment_intent": p.provider_transaction_id, "amount": str(r.amount_minor)},
                          auth=(settings.STRIPE_SECRET_KEY, ""), headers={"Idempotency-Key": f"refund-{r.id}"}, timeout=20)
        if resp.status_code >= 400:
            raise AppError("Stripe refused the refund", code="PROVIDER_ERROR", status_code=502)
        r.provider_refund_id = resp.json().get("id")
    else:
        r.provider_refund_id = body.provider_refund_id
    r.status = RefundStatus.COMPLETED
    r.processed_by_id = auth.user.id
    r.processed_at = utcnow()
    o.refunded_minor += r.amount_minor
    o.payment_status = "REFUNDED" if o.refunded_minor >= o.paid_minor else "PARTIALLY_REFUNDED"
    if o.status == S.REFUND_PENDING and o.refunded_minor >= o.paid_minor:
        order_state.transition(db, o, S.REFUNDED, actor_type=A.ADMIN, actor_id=auth.user.id, ip=ctx.ip)
    audit(db, "refund.completed", actor_id=auth.user.id, actor_type=A.ADMIN, entity_type="refund", entity_id=r.id, ip=ctx.ip, data={"amount_minor": r.amount_minor, "provider_refund_id": r.provider_refund_id})
    customer = db.get(User, o.customer_id)
    notify_customer(db, customer, "order.status", key_suffix=f"refund:{r.id}", title_key="n.order.status.title", body_key="n.order.status.body",
                    params={"order": o.order_number, "status": f"Refund {format_money(r.amount_minor, r.currency)}"}, order=o, link=f"/dashboard/orders/{o.id}")
    db.commit()
    return {"status": r.status}
