"""Order lifecycle state machine.

Every transition is declared here together with the actor types allowed to perform it.
Nothing else in the codebase may assign `Order.status` directly — use `transition()`,
which records an OrderEvent and an AuditLog entry in the same DB transaction.

Payment-driven transitions (deposit received, final payment received) are restricted to
ActorType.PAYMENT, which only the verified payment confirmation path uses. This is how the
rule "never mark an order as paid based on a frontend callback" is enforced structurally.
"""

from __future__ import annotations

from sqlalchemy.orm import Session as DB

from app.core.db import utcnow
from app.core.errors import InvalidTransition
from app.models import Order, OrderEvent
from app.models.enums import ActorType as A
from app.models.enums import OrderStatus as S
from app.services.audit import audit

C, AD, SYS, PAY, AI = A.CUSTOMER, A.ADMIN, A.SYSTEM, A.PAYMENT, A.AI

TRANSITIONS: dict[tuple[S, S], set[A]] = {
    (S.DRAFT, S.SUBMITTED): {C},
    (S.DRAFT, S.CANCELLED): {C, AD},
    (S.SUBMITTED, S.UNDER_REVIEW): {AD, SYS},
    (S.SUBMITTED, S.CANCELLED): {C, AD},
    (S.UNDER_REVIEW, S.QUOTATION_PENDING): {AD, SYS},
    (S.UNDER_REVIEW, S.CANCELLED): {C, AD},
    (S.UNDER_REVIEW, S.FAILED): {AD},
    (S.QUOTATION_PENDING, S.QUOTATION_ACCEPTED): {C},
    (S.QUOTATION_PENDING, S.UNDER_REVIEW): {C, AD},  # quotation rejected / withdrawn -> re-quote
    (S.QUOTATION_PENDING, S.CANCELLED): {C, AD},
    (S.QUOTATION_ACCEPTED, S.DEPOSIT_PENDING): {SYS},
    (S.QUOTATION_ACCEPTED, S.QUEUED): {SYS},  # zero-deposit quotation
    (S.QUOTATION_ACCEPTED, S.CANCELLED): {AD},
    (S.DEPOSIT_PENDING, S.PARTIALLY_PAID): {PAY},
    (S.DEPOSIT_PENDING, S.PAID): {PAY},
    (S.DEPOSIT_PENDING, S.CANCELLED): {C, AD},
    (S.PARTIALLY_PAID, S.QUEUED): {SYS},
    (S.PARTIALLY_PAID, S.PAID): {PAY},
    (S.PARTIALLY_PAID, S.CANCELLED): {AD},
    (S.PAID, S.QUEUED): {SYS},
    (S.PAID, S.CANCELLED): {AD},
    (S.QUEUED, S.AI_PROCESSING): {AD, SYS},
    (S.QUEUED, S.MANUAL_PROCESSING): {AD},
    (S.QUEUED, S.CANCELLED): {AD},
    (S.AI_PROCESSING, S.AI_REVIEW_REQUIRED): {AI, SYS},
    (S.AI_PROCESSING, S.MANUAL_PROCESSING): {AD, AI, SYS},  # fallback
    (S.AI_PROCESSING, S.CANCELLED): {AD},
    (S.AI_REVIEW_REQUIRED, S.AI_PROCESSING): {AD},  # retry / revision
    (S.AI_REVIEW_REQUIRED, S.MANUAL_PROCESSING): {AD},
    (S.AI_REVIEW_REQUIRED, S.COMPLETED_PENDING_FINAL_PAYMENT): {AD},
    (S.AI_REVIEW_REQUIRED, S.READY_FOR_DELIVERY): {AD},
    (S.AI_REVIEW_REQUIRED, S.CANCELLED): {AD},
    (S.MANUAL_PROCESSING, S.AI_PROCESSING): {AD},
    (S.MANUAL_PROCESSING, S.COMPLETED_PENDING_FINAL_PAYMENT): {AD},
    (S.MANUAL_PROCESSING, S.READY_FOR_DELIVERY): {AD},
    (S.MANUAL_PROCESSING, S.FAILED): {AD},
    (S.MANUAL_PROCESSING, S.CANCELLED): {AD},
    (S.COMPLETED_PENDING_FINAL_PAYMENT, S.FINAL_PAYMENT_PENDING): {SYS},
    (S.FINAL_PAYMENT_PENDING, S.READY_FOR_DELIVERY): {PAY},
    (S.FINAL_PAYMENT_PENDING, S.CANCELLED): {AD},
    (S.READY_FOR_DELIVERY, S.DELIVERED): {AD},
    (S.DELIVERED, S.REVISION_REQUESTED): {C},
    (S.DELIVERED, S.CLOSED): {C, AD, SYS},
    (S.REVISION_REQUESTED, S.MANUAL_PROCESSING): {AD},
    (S.REVISION_REQUESTED, S.AI_PROCESSING): {AD},
    (S.REVISION_REQUESTED, S.CLOSED): {AD},
    (S.CANCELLED, S.REFUND_PENDING): {AD, SYS},
    (S.DELIVERED, S.REFUND_PENDING): {AD},
    (S.CLOSED, S.REFUND_PENDING): {AD},
    (S.REFUND_PENDING, S.REFUNDED): {AD, PAY},
    (S.FAILED, S.MANUAL_PROCESSING): {AD},
    (S.FAILED, S.CANCELLED): {AD},
}

TERMINAL = {S.CLOSED, S.REFUNDED}
# States in which work may be executed (rule 14: cancelled orders cannot continue)
WORKING_STATES = {S.QUEUED, S.AI_PROCESSING, S.AI_REVIEW_REQUIRED, S.MANUAL_PROCESSING, S.REVISION_REQUESTED}
# States in which released deliverables are downloadable by the customer
DELIVERY_VISIBLE_STATES = {S.DELIVERED, S.CLOSED, S.REVISION_REQUESTED}


def allowed_targets(current: str, actor: A) -> list[str]:
    return [to.value for (frm, to), actors in TRANSITIONS.items() if frm == current and actor in actors]


def can_transition(current: str, target: str, actor: A) -> bool:
    try:
        key = (S(current), S(target))
    except ValueError:
        return False
    return actor in TRANSITIONS.get(key, set())


def transition(
    db: DB,
    order: Order,
    target: S | str,
    *,
    actor_type: A,
    actor_id: int | None = None,
    message: str = "",
    customer_visible: bool = True,
    data: dict | None = None,
    ip: str | None = None,
) -> OrderEvent:
    target = S(target)
    current = order.status
    if not can_transition(current, target, actor_type):
        raise InvalidTransition(
            f"Cannot move order from {current} to {target}",
            details={"from": current, "to": target.value, "allowed": allowed_targets(current, actor_type)},
        )
    now = utcnow()
    order.status = target.value
    order.version += 1
    if target == S.SUBMITTED:
        order.submitted_at = now
    elif target in (S.COMPLETED_PENDING_FINAL_PAYMENT, S.READY_FOR_DELIVERY) and order.completed_at is None:
        order.completed_at = now
    elif target == S.DELIVERED:
        order.delivered_at = now
    elif target == S.CLOSED:
        order.closed_at = now
    elif target == S.CANCELLED:
        order.cancelled_at = now

    event = OrderEvent(
        order_id=order.id,
        event_type="STATUS_CHANGED",
        from_status=current,
        to_status=target.value,
        actor_type=str(actor_type),
        actor_id=actor_id,
        customer_visible=customer_visible,
        message=message,
        data=data or {},
        created_at=now,
    )
    db.add(event)
    audit(
        db,
        "order.status_changed",
        actor_id=actor_id,
        actor_type=actor_type,
        entity_type="order",
        entity_id=order.id,
        ip=ip,
        data={"from": current, "to": target.value, "order_number": order.order_number},
    )
    return event


def add_event(db: DB, order: Order, event_type: str, *, actor_type: A, actor_id: int | None = None, message: str = "", customer_visible: bool = True, data: dict | None = None) -> OrderEvent:
    ev = OrderEvent(
        order_id=order.id,
        event_type=event_type,
        actor_type=str(actor_type),
        actor_id=actor_id,
        customer_visible=customer_visible,
        message=message,
        data=data or {},
        created_at=utcnow(),
    )
    db.add(ev)
    return ev
