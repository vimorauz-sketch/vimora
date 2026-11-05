"""Order business operations. Routes are thin; all rules live here."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session as DB

from app.core.db import utcnow
from app.core.errors import AppError, Conflict, Forbidden, NotFound
from app.core.i18n import pick, t
from app.models import (
    Attachment,
    Conversation,
    Deliverable,
    Order,
    OrderCounter,
    OrderItem,
    PromoCodeUsage,
    Quotation,
    Service,
    ServiceCategory,
    User,
)
from app.models.enums import ActorType as A
from app.models.enums import AttachmentPurpose, ExecutionMethod, QuotationStatus
from app.models.enums import OrderStatus as S
from app.services import order_state
from app.services.notifications import notify_admins, notify_customer
from app.services.pricing import PriceResult, format_money, price_service
from app.services.settings_service import get_setting

CANCELLABLE_BY_CUSTOMER = {S.DRAFT, S.SUBMITTED, S.UNDER_REVIEW, S.QUOTATION_PENDING, S.DEPOSIT_PENDING}


def next_order_number(db: DB) -> str:
    year = datetime.now(UTC).year
    stmt = (
        insert(OrderCounter)
        .values(year=year, value=1)
        .on_conflict_do_update(index_elements=["year"], set_={"value": OrderCounter.value + 1})
        .returning(OrderCounter.value)
    )
    n = db.execute(stmt).scalar_one()
    return f"VM-{year}-{n:05d}"


def get_order_for_customer(db: DB, order_id: int, user_id: int, *, lock: bool = False) -> Order:
    """IDOR-safe lookup: ownership is part of the query; a foreign order is indistinguishable from a missing one."""
    stmt = select(Order).where(Order.id == order_id, Order.customer_id == user_id)
    if lock:
        stmt = stmt.with_for_update()
    order = db.scalar(stmt)
    if order is None:
        raise NotFound("Order not found")
    return order


def get_order(db: DB, order_id: int, *, lock: bool = False) -> Order:
    stmt = select(Order).where(Order.id == order_id)
    if lock:
        stmt = stmt.with_for_update()
    order = db.scalar(stmt)
    if order is None:
        raise NotFound("Order not found")
    return order


def _attach_inputs(db: DB, order: Order, attachment_ids: list[int], user_id: int) -> None:
    if not attachment_ids:
        return
    atts = list(db.scalars(select(Attachment).where(Attachment.id.in_(attachment_ids))))
    if len(atts) != len(set(attachment_ids)):
        raise AppError("One or more attachments were not found", code="ATTACHMENT_NOT_FOUND")
    for a in atts:
        # only the uploader's own, still-unassigned input files can be attached
        if a.owner_id != user_id or a.order_id is not None or a.purpose != AttachmentPurpose.ORDER_INPUT or a.deleted_at:
            raise Forbidden("Attachment cannot be used for this order")
        a.order_id = order.id


def _validate_requirements(service: Service, answers: dict) -> dict:
    clean: dict = {}
    for f in service.required_fields or []:
        key = f["key"]
        val = answers.get(key)
        if f.get("required") and (val is None or str(val).strip() == ""):
            raise AppError(f"Missing required field: {pick(f.get('label'), 'en') or key}", code="MISSING_REQUIREMENT", details={"field": key})
        if val is None or str(val).strip() == "":  # optional field left empty
            continue
        val = str(val)[:5000]
        if f.get("type") == "select" and f.get("options") and val not in [o if isinstance(o, str) else o.get("value") for o in f["options"]]:
            raise AppError(f"Invalid option for {key}", code="INVALID_REQUIREMENT", details={"field": key})
        if f.get("type") == "number":
            try:
                float(val)
            except ValueError:
                raise AppError(f"{key} must be a number", code="INVALID_REQUIREMENT", details={"field": key}) from None
        clean[key] = val
    return clean


def _create_quotation(db: DB, order: Order, pr: PriceResult, *, source: str, created_by_id: int | None, note: str = "", delivery_days: int | None = None, valid_days: int = 14) -> Quotation:
    # supersede any outstanding quotation
    db.execute(update(Quotation).where(Quotation.order_id == order.id, Quotation.status == QuotationStatus.PENDING).values(status=QuotationStatus.SUPERSEDED))
    q = Quotation(
        order_id=order.id, status=QuotationStatus.PENDING, currency=pr.currency, line_items=[li.as_dict() for li in pr.line_items],
        subtotal_minor=pr.subtotal_minor, discount_minor=pr.discount_minor, extra_charges_minor=pr.extra_charges_minor,
        total_minor=pr.total_minor, deposit_minor=pr.deposit_minor, promo_code_id=pr.promo_code_id, note=note,
        estimated_delivery_days=delivery_days, created_by_id=created_by_id, source=source, valid_until=utcnow() + timedelta(days=valid_days),
    )
    db.add(q)
    db.flush()
    return q


def create_order(
    db: DB,
    customer: User,
    *,
    service_slug: str | None,
    title: str,
    description: str,
    quantity: int = 1,
    addon_keys: list[str] | None = None,
    requirements: dict | None = None,
    promo_code: str | None = None,
    attachment_ids: list[int] | None = None,
    category_slug: str | None = None,
    deadline: datetime | None = None,
    budget_minor: int | None = None,
    preferred_language: str = "uz",
    contact_info: dict | None = None,
    area_slug: str | None = None,
    handover_method: str | None = None,
    meetup: dict | None = None,
    ip: str | None = None,
) -> Order:
    from app.services import local

    service: Service | None = None
    category: ServiceCategory | None = None
    if service_slug:
        service = db.scalar(select(Service).where(Service.slug == service_slug))
        if service is None or service.archived_at is not None:
            raise NotFound("Service not found")
        if not service.is_active or not service.category.is_active:
            raise AppError("This service is not currently accepting orders", code="SERVICE_UNAVAILABLE")  # rule 13
        category = service.category
    elif category_slug:
        category = db.scalar(select(ServiceCategory).where(ServiceCategory.slug == category_slug))
    if deadline and deadline < utcnow():
        raise AppError("Deadline must be in the future", code="INVALID_DEADLINE")

    lang = preferred_language if preferred_language in ("uz", "en", "ru") else "uz"
    pr: PriceResult | None = None
    if service:
        clean_req = _validate_requirements(service, requirements or {})
        pr = price_service(db, service, quantity=quantity, addon_keys=addon_keys, promo_code=promo_code, user_id=customer.id, lang=lang)
        if not service.allows_attachments and attachment_ids:
            raise AppError("This service does not accept attachments", code="ATTACHMENTS_NOT_ALLOWED")
        if service.requires_file and not attachment_ids:
            raise AppError("Attach the file for this order", code="FILE_REQUIRED", details={"field": "attachments"})
        if local.effective_mode(service) not in ("ONLINE", "REMOTE", "LOCAL"):
            raise AppError("This service is not currently accepting orders", code="SERVICE_UNAVAILABLE")
    else:
        clean_req = {}
    area = local.get_area(db, area_slug)
    if service:
        local.check_service_area(service, area)  # before anything is written
    elif handover_method:
        raise AppError("Pickup / meetup is only for local services", code="HANDOVER_NOT_APPLICABLE")

    currency = pr.currency if pr else get_setting(db, "platform.default_currency")
    order = Order(
        order_number=next_order_number(db), customer_id=customer.id, service_id=service.id if service else None,
        category_id=category.id if category else None, is_custom=service is None, title=title.strip()[:200],
        description=description.strip(), requirements=clean_req, preferred_language=lang, contact_info=contact_info or {},
        budget_minor=budget_minor, status=S.DRAFT, currency=currency, deadline=deadline,
        execution_method=ExecutionMethod.UNASSIGNED,
    )
    if service:
        local.init_local_order(order, service, area, method=handover_method, meetup=meetup)
    elif area is not None:
        order.service_area_id = area.id
    db.add(order)
    db.flush()
    if service and pr:
        db.add(OrderItem(order_id=order.id, service_id=service.id, description=pr.line_items[0].description if pr.line_items else pick(service.name, lang),
                         quantity=quantity, unit_price_minor=pr.line_items[0].unit_price_minor if pr.line_items else 0,
                         total_minor=pr.total_minor, addons=addon_keys or []))
    _attach_inputs(db, order, attachment_ids or [], customer.id)
    db.add(Conversation(order_id=order.id, customer_id=customer.id))
    order_state.transition(db, order, S.SUBMITTED, actor_type=A.CUSTOMER, actor_id=customer.id, ip=ip, message="Order submitted")

    # Fixed / per-unit / tiered pricing: the pricing engine issues the quotation (approved pricing logic).
    if pr and not pr.requires_quote:
        order_state.transition(db, order, S.UNDER_REVIEW, actor_type=A.SYSTEM, message="Automatically priced")
        q = _create_quotation(db, order, pr, source="PRICING_ENGINE", created_by_id=None)
        order_state.transition(db, order, S.QUOTATION_PENDING, actor_type=A.SYSTEM, data={"quotation_id": q.id})
        _notify_quotation(db, order, q, customer)

    svc_name = pick(service.name, "en") if service else "Custom request"
    lines = [("Order", f"#{order.order_number}"), ("Service", svc_name), ("Customer", customer.profile.full_name or "—" if customer.profile else "—")]
    if pr and pr.total_minor:
        lines += [("Amount", format_money(pr.total_minor, pr.currency)), ("Deposit", format_money(pr.deposit_minor, pr.currency))]
    if order.is_local:
        lines.append(("Handover", f"{order.handover_method} · {area.slug if area else ''}"))
    lines.append(("Status", order.status.replace("_", " ")))
    notify_admins(db, "custom_request.created" if order.is_custom else "order.created", key_suffix=str(order.id),
                  title="NEW VIMORA CUSTOM REQUEST" if order.is_custom else "NEW VIMORA ORDER", lines=lines, order=order)
    notify_customer(db, customer, "order.created", key_suffix=str(order.id), title_key="n.order.created.title", body_key="n.order.created.body",
                    params={"order": order.order_number}, order=order, link=f"/dashboard/orders/{order.id}")
    return order


def _notify_quotation(db: DB, order: Order, q: Quotation, customer: User) -> None:
    notify_customer(db, customer, "quotation.available", key_suffix=str(q.id), title_key="n.quotation.available.title", body_key="n.quotation.available.body",
                    params={"order": order.order_number, "total": format_money(q.total_minor, q.currency), "deposit": format_money(q.deposit_minor, q.currency)},
                    order=order, link=f"/dashboard/orders/{order.id}")


def admin_issue_quotation(db: DB, order: Order, pr: PriceResult, *, admin: User, note: str, delivery_days: int | None, ip: str | None) -> Quotation:
    if order.status == S.SUBMITTED:
        order_state.transition(db, order, S.UNDER_REVIEW, actor_type=A.ADMIN, actor_id=admin.id, ip=ip)
    if order.status not in (S.UNDER_REVIEW, S.QUOTATION_PENDING):
        raise Conflict("A quotation can only be issued while the order is under review", code="INVALID_STATE")
    q = _create_quotation(db, order, pr, source="ADMIN", created_by_id=admin.id, note=note, delivery_days=delivery_days)
    if order.status == S.UNDER_REVIEW:
        order_state.transition(db, order, S.QUOTATION_PENDING, actor_type=A.ADMIN, actor_id=admin.id, ip=ip, data={"quotation_id": q.id})
    else:
        order_state.add_event(db, order, "QUOTATION_REVISED", actor_type=A.ADMIN, actor_id=admin.id, data={"quotation_id": q.id})
    from app.services.audit import audit

    audit(db, "quotation.created", actor_id=admin.id, actor_type=A.ADMIN, entity_type="quotation", entity_id=q.id, ip=ip,
          data={"order_id": order.id, "total_minor": q.total_minor, "deposit_minor": q.deposit_minor, "currency": q.currency})
    customer = db.get(User, order.customer_id)
    _notify_quotation(db, order, q, customer)
    return q


def accept_quotation(db: DB, order: Order, quotation_id: int, customer: User, *, ip: str | None) -> Quotation:
    q = db.scalar(select(Quotation).where(Quotation.id == quotation_id, Quotation.order_id == order.id).with_for_update())
    if q is None:
        raise NotFound("Quotation not found")
    if q.status != QuotationStatus.PENDING:
        raise Conflict("This quotation is no longer open", code="QUOTATION_CLOSED")
    if q.valid_until and q.valid_until < utcnow():
        q.status = QuotationStatus.EXPIRED
        raise Conflict("This quotation has expired; please request a new one", code="QUOTATION_EXPIRED")
    order_state.transition(db, order, S.QUOTATION_ACCEPTED, actor_type=A.CUSTOMER, actor_id=customer.id, ip=ip, data={"quotation_id": q.id})
    q.status = QuotationStatus.ACCEPTED
    q.responded_at = utcnow()
    # Snapshot money onto the order. Later price/currency changes never alter an accepted quotation.
    order.accepted_quotation_id = q.id
    order.currency = q.currency
    order.total_minor = q.total_minor
    order.deposit_minor = q.deposit_minor
    if q.promo_code_id:
        db.add(PromoCodeUsage(promo_code_id=q.promo_code_id, user_id=customer.id, order_id=order.id, discount_minor=q.discount_minor, created_at=utcnow()))
    if q.total_minor == 0 or q.deposit_minor == 0:
        order_state.transition(db, order, S.QUEUED, actor_type=A.SYSTEM, message="No deposit required")
    else:
        order_state.transition(db, order, S.DEPOSIT_PENDING, actor_type=A.SYSTEM)
        notify_customer(db, customer, "payment.due", key_suffix=f"{order.id}:{q.id}", title_key="n.payment.due.title", body_key="n.payment.due.body",
                        params={"order": order.order_number, "amount": format_money(q.deposit_minor, q.currency)}, order=order,
                        link=f"/dashboard/orders/{order.id}")
    notify_admins(db, "quotation.accepted", key_suffix=str(q.id), title="QUOTATION ACCEPTED",
                  lines=[("Order", f"#{order.order_number}"), ("Total", format_money(q.total_minor, q.currency)), ("Deposit", format_money(q.deposit_minor, q.currency))], order=order)
    return q


def reject_quotation(db: DB, order: Order, quotation_id: int, customer: User, reason: str, *, ip: str | None) -> Quotation:
    q = db.scalar(select(Quotation).where(Quotation.id == quotation_id, Quotation.order_id == order.id).with_for_update())
    if q is None:
        raise NotFound("Quotation not found")
    if q.status != QuotationStatus.PENDING:
        raise Conflict("This quotation is no longer open", code="QUOTATION_CLOSED")
    order_state.transition(db, order, S.UNDER_REVIEW, actor_type=A.CUSTOMER, actor_id=customer.id, ip=ip, message="Quotation declined", data={"quotation_id": q.id, "reason": reason[:1000]})
    q.status = QuotationStatus.REJECTED
    q.responded_at = utcnow()
    q.rejection_reason = reason[:2000]
    return q


def cancel_by_customer(db: DB, order: Order, customer: User, reason: str, *, ip: str | None) -> None:
    if order.status not in CANCELLABLE_BY_CUSTOMER:
        raise Conflict("This order can no longer be cancelled online. Please contact support.", code="NOT_CANCELLABLE")
    if order.paid_minor > 0:
        raise Conflict("Paid orders are cancelled by support so the refund can be processed", code="NOT_CANCELLABLE")
    order_state.transition(db, order, S.CANCELLED, actor_type=A.CUSTOMER, actor_id=customer.id, ip=ip, message=reason[:500])
    notify_admins(db, "order.cancelled", key_suffix=str(order.id), title="ORDER CANCELLED", lines=[("Order", f"#{order.order_number}"), ("By", "customer")], order=order)


def request_revision(db: DB, order: Order, customer: User, note: str, *, ip: str | None) -> None:
    limit = 2
    if order.service_id:
        svc = db.get(Service, order.service_id)
        limit = svc.revision_limit if svc else 2
    if order.revision_count >= limit:
        raise Conflict(f"The revision limit for this service ({limit}) has been reached", code="REVISION_LIMIT")
    order_state.transition(db, order, S.REVISION_REQUESTED, actor_type=A.CUSTOMER, actor_id=customer.id, ip=ip, message=note[:4000])
    order.revision_count += 1
    notify_admins(db, "revision.requested", key_suffix=f"{order.id}:{order.revision_count}", title="REVISION REQUESTED",
                  lines=[("Order", f"#{order.order_number}"), ("Round", str(order.revision_count))], order=order)


def complete_work(db: DB, order: Order, admin: User, *, ip: str | None) -> None:
    """Admin marks work complete (after reviewing deliverables). Routes to final payment or delivery."""
    from app.services import local

    approved = db.scalar(select(Deliverable.id).where(Deliverable.order_id == order.id, Deliverable.approved_at.is_not(None), Deliverable.released_at.is_(None)).limit(1))
    if approved is None and not order.is_local:  # LOCAL orders produce a physical result (paper), files are optional
        raise Conflict("Approve at least one deliverable before completing the work", code="NO_APPROVED_DELIVERABLE")
    remaining = order.remaining_minor
    if remaining > 0:
        order_state.transition(db, order, S.COMPLETED_PENDING_FINAL_PAYMENT, actor_type=A.ADMIN, actor_id=admin.id, ip=ip)
        order_state.transition(db, order, S.FINAL_PAYMENT_PENDING, actor_type=A.SYSTEM)
        customer = db.get(User, order.customer_id)
        if not order.is_local:  # local orders get the "ready" notice from local.on_work_completed (cash on handover is fine)
            notify_customer(db, customer, "work.completed", key_suffix=f"{order.id}:{order.revision_count}", title_key="n.work.completed.title", body_key="n.work.completed.body",
                            params={"order": order.order_number, "amount": format_money(remaining, order.currency)}, order=order, link=f"/dashboard/orders/{order.id}")
    else:
        order_state.transition(db, order, S.READY_FOR_DELIVERY, actor_type=A.ADMIN, actor_id=admin.id, ip=ip)
    local.on_work_completed(db, order)


def release_delivery(db: DB, order: Order, admin: User, *, ip: str | None) -> int:
    """Release approved deliverables to the customer, respecting the payment release policy (rule 7)."""
    if order.status != S.READY_FOR_DELIVERY:
        raise Conflict("Order is not ready for delivery", code="INVALID_STATE")
    if order.is_local:
        raise Conflict("Local orders are completed with the handover action", code="USE_HANDOVER")
    policy = get_setting(db, "orders.release_policy")
    if policy == "AFTER_FULL_PAYMENT" and order.remaining_minor > 0:
        raise Conflict("The remaining balance must be paid before release", code="BALANCE_OUTSTANDING")
    now = utcnow()
    res = db.execute(update(Deliverable).where(Deliverable.order_id == order.id, Deliverable.approved_at.is_not(None), Deliverable.released_at.is_(None)).values(released_at=now))
    count = res.rowcount or 0
    if count == 0:
        raise Conflict("There are no approved deliverables to release", code="NO_APPROVED_DELIVERABLE")
    order_state.transition(db, order, S.DELIVERED, actor_type=A.ADMIN, actor_id=admin.id, ip=ip, data={"released": count})
    customer = db.get(User, order.customer_id)
    notify_customer(db, customer, "delivered", key_suffix=f"{order.id}:{order.revision_count}", title_key="n.delivered.title", body_key="n.delivered.body",
                    params={"order": order.order_number}, order=order, link=f"/dashboard/orders/{order.id}")
    return count


def notify_status(db: DB, order: Order) -> None:
    customer = db.get(User, order.customer_id)
    lang = customer.profile.language if customer.profile else "uz"
    notify_customer(db, customer, "order.status", key_suffix=f"{order.id}:{order.version}", title_key="n.order.status.title", body_key="n.order.status.body",
                    params={"order": order.order_number, "status": t(f"status.{order.status}", lang)}, order=order, link=f"/dashboard/orders/{order.id}")


def submit_review(db: DB, order: Order, customer: User, rating: int, text: str) -> None:
    if order.status not in (S.DELIVERED, S.CLOSED):
        raise Conflict("You can review an order after it has been delivered", code="INVALID_STATE")
    if order.reviewed_at is not None:
        raise Conflict("You have already reviewed this order", code="ALREADY_REVIEWED")
    if not 1 <= rating <= 5:
        raise AppError("Rating must be between 1 and 5", code="INVALID_RATING")
    order.review_rating = rating
    order.review_text = text.strip()[:3000]
    order.reviewed_at = utcnow()
    order.review_public = False  # an administrator approves reviews before they are displayed publicly
