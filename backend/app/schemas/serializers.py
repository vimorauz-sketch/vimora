"""Explicit output serializers. Each function decides exactly which fields leave the server,
with separate customer and staff views (e.g. admin_notes never reach customers)."""

from __future__ import annotations

from app.core.i18n import pick
from app.models import (
    AIExecution,
    Attachment,
    Deliverable,
    Message,
    Notification,
    Order,
    OrderEvent,
    Payment,
    Quotation,
    Service,
    ServiceArea,
    ServiceCategory,
    User,
)


def iso(dt) -> str | None:
    return dt.isoformat() if dt else None


def user_public(u: User) -> dict:
    p = u.profile
    return {
        "id": u.id,
        "email": u.email,
        "full_name": p.full_name if p else "",
        "phone": p.phone if p else None,
        "company": p.company if p else None,
        "language": p.language if p else "uz",
        "timezone": p.timezone if p else "Asia/Tashkent",
        "email_verified": u.email_verified_at is not None,
        "mfa_enabled": u.mfa_enabled,
        "roles": sorted(u.role_names),
        "is_staff": u.is_staff,
        "created_at": iso(u.created_at),
        "notification_prefs": (p.notification_prefs if p else {}) or {},
    }


def category_out(c: ServiceCategory, lang: str | None = None, *, full: bool = False) -> dict:
    out = {"id": c.id, "slug": c.slug, "icon": c.icon, "sort_order": c.sort_order, "is_active": c.is_active}
    if full or lang is None:
        out.update(name=c.name, description=c.description)
    else:
        out.update(name=pick(c.name, lang), description=pick(c.description, lang))
    return out


def pricing_out(s: Service, lang: str | None) -> dict | None:
    p = s.pricing
    if not p:
        return None
    return {
        "pricing_type": p.pricing_type, "currency": p.currency, "base_price_minor": p.base_price_minor,
        "unit_label": pick(p.unit_label, lang) if lang else p.unit_label, "min_quantity": p.min_quantity, "max_quantity": p.max_quantity,
        "tiers": p.tiers, "addons": [{**a, "label": pick(a.get("label"), lang) if lang else a.get("label")} for a in (p.addons or [])],
        "deposit_type": p.deposit_type, "deposit_value": p.deposit_value,
    }


def _availability(s: Service) -> str:
    from app.services.local import availability_status

    return availability_status(s)


def area_public(a: ServiceArea, lang: str | None = None) -> dict:
    """Public view of an area. Never includes the private pickup address."""
    return {"slug": a.slug, "kind": a.kind, "name": pick(a.name, lang) if lang else a.name, "region": a.region, "district": a.district,
            "locality": a.locality, "local_services_enabled": a.local_services_enabled, "rules": pick(a.rules, lang) if lang else a.rules}


def area_admin(a: ServiceArea) -> dict:
    return {**area_public(a), "id": a.id, "is_active": a.is_active, "provider_id": a.provider_id, "pickup_address": a.pickup_address,
            "sort_order": a.sort_order}


def service_out(s: Service, lang: str | None = None, *, full: bool = False, image_url: str | None = None) -> dict:
    tr = (lambda v: v) if (full or lang is None) else (lambda v: pick(v, lang))
    out = {
        "id": s.id, "slug": s.slug, "category": category_out(s.category, None if full else lang, full=full), "name": tr(s.name),
        "short_description": tr(s.short_description), "icon": s.icon, "image_url": image_url or s.cover_image_url,
        "image_credit": None if image_url else s.cover_image_credit, "estimated_delivery": tr(s.estimated_delivery),
        "estimated_hours": s.estimated_hours, "allows_attachments": s.allows_attachments, "is_active": s.is_active, "is_featured": s.is_featured,
        "ai_eligible": s.ai_eligible, "revision_limit": s.revision_limit, "pricing": pricing_out(s, None if full else lang),
        "mode": s.service_mode or "ONLINE", "requires_file": s.requires_file, "availability_status": _availability(s),
        "service_area": area_public(s.service_area, None if full else lang) if s.service_area else None,
    }
    if full or lang is not None:
        out["description"] = tr(s.description)
        out["required_fields"] = [{**f, "label": tr(f.get("label", {}))} for f in (s.required_fields or [])]
        out["examples"] = [{"title": tr(e.get("title", {})), "text": tr(e.get("text", {}))} for e in (s.examples or [])]
    if full:
        out.update(ai_capability=s.ai_capability, sort_order=s.sort_order, image_attachment_id=s.image_attachment_id,
                   cover_image_url=s.cover_image_url, cover_image_credit=s.cover_image_credit, service_mode=s.service_mode,
                   service_area_id=s.service_area_id, archived_at=iso(s.archived_at), category_id=s.category_id)
    return out


def quotation_out(q: Quotation) -> dict:
    return {
        "id": q.id, "status": q.status, "currency": q.currency, "line_items": q.line_items, "subtotal_minor": q.subtotal_minor,
        "discount_minor": q.discount_minor, "extra_charges_minor": q.extra_charges_minor, "total_minor": q.total_minor,
        "deposit_minor": q.deposit_minor, "remaining_minor": q.total_minor - q.deposit_minor, "estimated_delivery_days": q.estimated_delivery_days,
        "note": q.note, "source": q.source, "valid_until": iso(q.valid_until), "created_at": iso(q.created_at), "responded_at": iso(q.responded_at),
        "rejection_reason": q.rejection_reason,
    }


def attachment_out(a: Attachment) -> dict:
    return {"id": a.id, "name": a.original_name, "mime_type": a.mime_type, "size_bytes": a.size_bytes, "purpose": a.purpose, "scan_status": a.scan_status, "created_at": iso(a.created_at)}


def deliverable_out(d: Deliverable, att: Attachment | None, *, staff: bool) -> dict:
    out = {"id": d.id, "title": d.title, "note": d.note, "attachment": attachment_out(att) if att else None, "released_at": iso(d.released_at), "revision_round": d.revision_round, "created_at": iso(d.created_at)}
    if staff:
        out.update(source=d.source, approved_at=iso(d.approved_at), ai_execution_id=d.ai_execution_id)
    return out


def event_out(e: OrderEvent, *, staff: bool) -> dict:
    out = {"id": e.id, "type": e.event_type, "from_status": e.from_status, "to_status": e.to_status, "message": e.message, "created_at": iso(e.created_at), "actor_type": e.actor_type}
    if staff:
        out.update(actor_id=e.actor_id, customer_visible=e.customer_visible, data=e.data)
    return out


def payment_out(p: Payment, *, staff: bool = False) -> dict:
    out = {"id": p.id, "reference": p.reference, "kind": p.kind, "provider": p.provider, "status": p.status, "amount_minor": p.amount_minor,
           "currency": p.currency, "created_at": iso(p.created_at), "confirmed_at": iso(p.confirmed_at), "order_id": p.order_id}
    if staff:
        out.update(provider_transaction_id=p.provider_transaction_id, failure_reason=p.failure_reason, recorded_by_id=p.recorded_by_id, customer_id=p.customer_id)
    return out


def order_summary(o: Order, *, service_name: str | None = None, customer_email: str | None = None, staff: bool = False) -> dict:
    out = {
        "id": o.id, "order_number": o.order_number, "title": o.title, "status": o.status, "is_custom": o.is_custom, "service_name": service_name,
        "currency": o.currency, "total_minor": o.total_minor, "deposit_minor": o.deposit_minor, "paid_minor": o.paid_minor,
        "remaining_minor": o.remaining_minor, "payment_status": o.payment_status, "deadline": iso(o.deadline), "created_at": iso(o.created_at), "updated_at": iso(o.updated_at),
        "is_local": o.is_local, "handover_method": o.handover_method, "handover_status": o.handover_status,
    }
    if staff:
        out.update(customer_id=o.customer_id, customer_email=customer_email, execution_method=o.execution_method, ai_status=o.ai_status, refunded_minor=o.refunded_minor)
    return out


def order_detail(o: Order, *, staff: bool, service_name: str | None, extra: dict) -> dict:
    out = order_summary(o, service_name=service_name, staff=staff)
    out.update(
        description=o.description, requirements=o.requirements, preferred_language=o.preferred_language, contact_info=o.contact_info,
        budget_minor=o.budget_minor, customer_notes=o.customer_notes, revision_count=o.revision_count, submitted_at=iso(o.submitted_at),
        completed_at=iso(o.completed_at), delivered_at=iso(o.delivered_at), closed_at=iso(o.closed_at), cancelled_at=iso(o.cancelled_at),
        review_rating=o.review_rating, review_text=o.review_text, items=[{"description": i.description, "quantity": i.quantity, "unit_price_minor": i.unit_price_minor, "total_minor": i.total_minor, "addons": i.addons} for i in o.items],
        ai_assisted=o.execution_method == "AI",
    )
    if staff:
        out.update(admin_notes=o.admin_notes, ai_classification=o.ai_classification, review_public=o.review_public, version=o.version)
    out.update(extra)
    return out


def message_out(m: Message, attachments: list[Attachment], sender_name: str | None) -> dict:
    return {"id": m.id, "body": m.body, "sender_is_staff": m.sender_is_staff, "sender_name": sender_name, "created_at": iso(m.created_at),
            "read_by_customer_at": iso(m.read_by_customer_at), "read_by_staff_at": iso(m.read_by_staff_at), "attachments": [attachment_out(a) for a in attachments]}


def notification_out(n: Notification) -> dict:
    return {"id": n.id, "event_type": n.event_type, "title": n.title, "body": n.body, "link": (n.data or {}).get("link"), "read_at": iso(n.read_at), "created_at": iso(n.created_at)}


def execution_out(ex: AIExecution, *, detail: bool = False) -> dict:
    out = {"id": ex.id, "order_id": ex.order_id, "attempt": ex.attempt, "status": ex.status, "capability": ex.capability, "input_tokens": ex.input_tokens,
           "output_tokens": ex.output_tokens, "cost_usd": str(ex.cost_usd), "failure_reason": ex.failure_reason, "fallback_reason": ex.fallback_reason,
           "started_at": iso(ex.started_at), "finished_at": iso(ex.finished_at), "created_at": iso(ex.created_at), "cancel_requested": ex.cancel_requested}
    if detail:
        out.update(classification=ex.classification, plan=ex.plan, validation_report=ex.validation_report, revision_instructions=ex.revision_instructions)
    return out
