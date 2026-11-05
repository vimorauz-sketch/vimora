"""Service areas and LOCAL (physical) orders: area rules and pickup / meetup handover.

Rules enforced here (server side, whatever the UI shows):
  * A LOCAL service can only be ordered by a customer whose chosen area is the service's own area,
    and only while that area is active with local services enabled. Today that is Qarapchi only.
  * Handover state is tracked separately from the order status and the payment status, so it can
    never mark anything as paid. Handing over requires the order to be READY_FOR_DELIVERY, which in
    turn requires the full amount to be paid (online, or cash recorded as a manual payment).
  * The pickup address is private. It is returned only to staff, and to the customer of a LOCAL
    PICKUP order once the work is physically ready.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session as DB

from app.core.db import utcnow
from app.core.errors import AppError, Conflict
from app.models import Deliverable, Order, Service, ServiceArea, User
from app.models.enums import ActorType as A
from app.models.enums import HandoverMethod as HM
from app.models.enums import HandoverStatus as HS
from app.models.enums import OrderStatus as S
from app.models.enums import ServiceMode
from app.services import order_state
from app.services.notifications import notify_admins, notify_customer

# order statuses in which a LOCAL order's work is physically finished (pickup address may be shown)
PHYSICALLY_READY = {S.COMPLETED_PENDING_FINAL_PAYMENT, S.FINAL_PAYMENT_PENDING, S.READY_FOR_DELIVERY}
HANDOVER_OPEN = {HS.WAITING, HS.PROPOSED_BY_CUSTOMER, HS.PROPOSED_BY_ADMIN, HS.CONFIRMED, HS.READY_FOR_PICKUP}
MAX_PLACE = 300


def ensure_default_areas(db: DB) -> int:
    """Create the default areas that are missing. Existing areas (and admin edits) are never changed."""
    from app.catalog_data import DEFAULT_AREAS

    have = set(db.scalars(select(ServiceArea.slug)))
    n = 0
    for slug, kind, name, region, district, locality, local_on, sort in DEFAULT_AREAS:
        if slug not in have:
            db.add(ServiceArea(slug=slug, kind=kind, name=name, region=region, district=district, locality=locality, is_active=True,
                               local_services_enabled=local_on, rules={}, pickup_address="", sort_order=sort))
            n += 1
    db.flush()
    return n


def effective_mode(service: Service | None) -> str:
    """Legacy rows without a mode behave as ONLINE."""
    return (service.service_mode if service and service.service_mode else ServiceMode.ONLINE)


def availability_status(service: Service) -> str:
    if service.archived_at is not None or service.service_mode == ServiceMode.DISABLED:
        return "ARCHIVED"
    if service.service_mode == ServiceMode.FUTURE:
        return "FUTURE"
    return "ACTIVE" if service.is_active else "PAUSED"


def get_area(db: DB, slug: str | None) -> ServiceArea | None:
    if not slug:
        return None
    area = db.scalar(select(ServiceArea).where(ServiceArea.slug == slug))
    if area is None or not area.is_active:
        raise AppError("Unknown or inactive area", code="INVALID_AREA", details={"field": "area"})
    return area


def local_available_in(service: Service, area: ServiceArea | None) -> bool:
    sa = service.service_area
    return bool(area and sa and area.id == sa.id and sa.is_active and sa.local_services_enabled)


def check_service_area(service: Service, area: ServiceArea | None) -> None:
    if effective_mode(service) != ServiceMode.LOCAL:
        return
    if service.service_area is None or not service.service_area.local_services_enabled or not service.service_area.is_active:
        raise AppError("This local service is not available right now", code="SERVICE_UNAVAILABLE")
    if area is None:
        raise AppError("Choose your area to order a local service", code="AREA_REQUIRED", details={"field": "area"})
    if not local_available_in(service, area):
        raise AppError("This service is only available in its own area", code="SERVICE_NOT_IN_AREA",
                       details={"field": "area", "service_area": service.service_area.slug})


def _parse_time(value: str | datetime | None) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        raise AppError("Invalid meeting time", code="INVALID_MEETUP", details={"field": "meetup_time"}) from None


def _proposal(place: str | None, when: str | datetime | None, note: str | None, by: str) -> dict:
    place = (place or "").strip()
    if not place:
        raise AppError("Write where you would like to meet", code="INVALID_MEETUP", details={"field": "meetup_place"})
    t = _parse_time(when)
    if t is None:
        raise AppError("Choose a convenient time", code="INVALID_MEETUP", details={"field": "meetup_time"})
    if t.tzinfo is None:
        raise AppError("Meeting time must include a timezone", code="INVALID_MEETUP", details={"field": "meetup_time"})
    if t < utcnow() - timedelta(minutes=5):
        raise AppError("Meeting time must be in the future", code="INVALID_MEETUP", details={"field": "meetup_time"})
    return {"place": place[:MAX_PLACE], "time": t.isoformat(), "note": (note or "").strip()[:1000], "by": by, "at": utcnow().isoformat()}


def init_local_order(order: Order, service: Service, area: ServiceArea | None, *, method: str | None, meetup: dict | None) -> None:
    """Called while creating an order. Validates area + handover choice for LOCAL services."""
    if area is not None:
        order.service_area_id = area.id
    if effective_mode(service) != ServiceMode.LOCAL:
        if method:
            raise AppError("Pickup / meetup is only for local services", code="HANDOVER_NOT_APPLICABLE")
        return
    check_service_area(service, area)
    if method not in (HM.PICKUP, HM.MEETUP):
        raise AppError("Choose pickup or meetup", code="HANDOVER_REQUIRED", details={"field": "handover_method"})
    order.is_local = True
    order.handover_method = method
    if method == HM.MEETUP:
        meetup = meetup or {}
        p = _proposal(meetup.get("place"), meetup.get("time"), meetup.get("note"), "customer")
        order.handover = {"proposal": p, "history": [p]}
        order.handover_status = HS.PROPOSED_BY_CUSTOMER
    else:
        order.handover = {"history": []}
        order.handover_status = HS.WAITING


def _require_local(order: Order) -> None:
    if not order.is_local:
        raise Conflict("This order has no physical handover", code="NOT_LOCAL")
    if order.handover_status == HS.HANDED_OVER or order.status in (S.CANCELLED, S.REFUNDED, S.REFUND_PENDING, S.CLOSED):
        raise Conflict("The handover is already finished", code="INVALID_STATE")


def _save(order: Order, proposal: dict | None, status: str, *, agreed: dict | None = None) -> None:
    h = dict(order.handover or {})
    hist = list(h.get("history") or [])
    if proposal:
        hist.append(proposal)
        h["proposal"] = proposal
    if agreed is not None:
        h["agreed"] = agreed
    h["history"] = hist[-20:]
    order.handover = h
    order.handover_status = status
    order.version += 1


def customer_propose(db: DB, order: Order, customer: User, *, place: str, time: str, note: str = "") -> None:
    _require_local(order)
    if order.handover_method != HM.MEETUP:
        raise Conflict("Only meetup orders have a meeting place", code="NOT_MEETUP")
    p = _proposal(place, time, note, "customer")
    _save(order, p, HS.PROPOSED_BY_CUSTOMER)
    order_state.add_event(db, order, "HANDOVER_PROPOSED", actor_type=A.CUSTOMER, actor_id=customer.id, data={"place": p["place"], "time": p["time"]})
    notify_admins(db, "handover.proposed", key_suffix=f"{order.id}:{len(order.handover['history'])}", title="MEETUP PROPOSAL",
                  lines=[("Order", f"#{order.order_number}"), ("Place", p["place"]), ("Time", p["time"])], order=order)


def customer_accept(db: DB, order: Order, customer: User) -> None:
    _require_local(order)
    if order.handover_status != HS.PROPOSED_BY_ADMIN:
        raise Conflict("There is no proposal from VIMORA to accept", code="INVALID_STATE")
    agreed = order.handover["proposal"]
    _save(order, None, HS.CONFIRMED, agreed=agreed)
    order_state.add_event(db, order, "HANDOVER_CONFIRMED", actor_type=A.CUSTOMER, actor_id=customer.id, data={"place": agreed["place"], "time": agreed["time"]})
    notify_admins(db, "handover.proposed", key_suffix=f"{order.id}:accepted:{len(order.handover['history'])}", title="MEETUP CONFIRMED BY CUSTOMER",
                  lines=[("Order", f"#{order.order_number}"), ("Place", agreed["place"]), ("Time", agreed["time"])], order=order)


def admin_confirm(db: DB, order: Order, admin: User) -> None:
    _require_local(order)
    if order.handover_status != HS.PROPOSED_BY_CUSTOMER:
        raise Conflict("There is no customer proposal to confirm", code="INVALID_STATE")
    agreed = order.handover["proposal"]
    _save(order, None, HS.CONFIRMED, agreed=agreed)
    order_state.add_event(db, order, "HANDOVER_CONFIRMED", actor_type=A.ADMIN, actor_id=admin.id, data={"place": agreed["place"], "time": agreed["time"]})
    _notify_confirmed(db, order, agreed)


def admin_propose(db: DB, order: Order, admin: User, *, place: str, time: str, note: str = "") -> None:
    _require_local(order)
    if order.handover_method != HM.MEETUP:
        raise Conflict("Only meetup orders have a meeting place", code="NOT_MEETUP")
    p = _proposal(place, time, note, "admin")
    _save(order, p, HS.PROPOSED_BY_ADMIN)
    order_state.add_event(db, order, "HANDOVER_PROPOSED", actor_type=A.ADMIN, actor_id=admin.id, data={"place": p["place"], "time": p["time"]})
    customer = db.get(User, order.customer_id)
    notify_customer(db, customer, "handover.proposed", key_suffix=f"{order.id}:{len(order.handover['history'])}", title_key="n.handover.proposed.title",
                    body_key="n.handover.proposed.body", params={"order": order.order_number, "place": p["place"]}, order=order,
                    link=f"/dashboard/orders/{order.id}")


def _notify_confirmed(db: DB, order: Order, agreed: dict) -> None:
    customer = db.get(User, order.customer_id)
    notify_customer(db, customer, "handover.confirmed", key_suffix=f"{order.id}:{len(order.handover['history'])}", title_key="n.handover.confirmed.title",
                    body_key="n.handover.confirmed.body", params={"order": order.order_number, "place": agreed["place"]}, order=order,
                    link=f"/dashboard/orders/{order.id}")


def on_work_completed(db: DB, order: Order) -> None:
    """Work on a LOCAL order is physically finished: open the pickup and tell the customer."""
    if not order.is_local:
        return
    if order.handover_method == HM.PICKUP and order.handover_status == HS.WAITING:
        order.handover_status = HS.READY_FOR_PICKUP
    customer = db.get(User, order.customer_id)
    notify_customer(db, customer, "local.ready", key_suffix=f"{order.id}:{order.revision_count}", title_key="n.local.ready.title",
                    body_key="n.local.ready.pickup" if order.handover_method == HM.PICKUP else "n.local.ready.meetup",
                    params={"order": order.order_number}, order=order, link=f"/dashboard/orders/{order.id}")


def admin_handover(db: DB, order: Order, admin: User, *, ip: str | None) -> None:
    """The customer received the physical result. Requires READY_FOR_DELIVERY (fully paid)."""
    _require_local(order)
    if order.status != S.READY_FOR_DELIVERY:
        if order.status in PHYSICALLY_READY and order.remaining_minor > 0:
            raise Conflict("Record the remaining payment (e.g. cash) before handing over", code="BALANCE_OUTSTANDING")
        raise Conflict("The order is not ready to hand over", code="INVALID_STATE")
    if order.handover_method == HM.MEETUP and order.handover_status != HS.CONFIRMED:
        raise Conflict("Confirm the meeting place and time first", code="MEETUP_NOT_CONFIRMED")
    now = utcnow()
    # any approved digital copies (e.g. scans) are released together with the paper result
    db.execute(update(Deliverable).where(Deliverable.order_id == order.id, Deliverable.approved_at.is_not(None), Deliverable.released_at.is_(None)).values(released_at=now))
    h = dict(order.handover or {})
    h["handed_over_at"] = now.isoformat()
    order.handover = h
    order.handover_status = HS.HANDED_OVER
    order_state.transition(db, order, S.DELIVERED, actor_type=A.ADMIN, actor_id=admin.id, ip=ip, data={"handover": order.handover_method})
    customer = db.get(User, order.customer_id)
    notify_customer(db, customer, "delivered", key_suffix=f"{order.id}:{order.revision_count}:handover", title_key="n.local.handed.title",
                    body_key="n.local.handed.body", params={"order": order.order_number}, order=order, link=f"/dashboard/orders/{order.id}")


def handover_view(db: DB, order: Order, *, staff: bool) -> dict | None:
    """What the order page shows about the handover. The pickup address is private (see module doc)."""
    if not order.is_local:
        return None
    area = db.get(ServiceArea, order.service_area_id) if order.service_area_id else None
    h = order.handover or {}
    out: dict = {"method": order.handover_method, "status": order.handover_status, "proposal": h.get("proposal"), "agreed": h.get("agreed"),
                 "handed_over_at": h.get("handed_over_at"), "pickup_address": None}
    show_address = staff or (order.handover_method == HM.PICKUP and order.status in PHYSICALLY_READY and order.handover_status in HANDOVER_OPEN)
    if show_address and area is not None and area.pickup_address:
        out["pickup_address"] = area.pickup_address
    if staff:
        out["history"] = h.get("history", [])
    return out
