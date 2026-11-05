"""Admin -> Prices: every service's price on one page, quick edits and suggested starting prices."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DB

from app.api.deps import Auth, get_db, require
from app.catalog_prices import apply_suggestion, is_unpriced, suggestion
from app.core.errors import AppError, NotFound
from app.models import Service, ServicePricing
from app.models.enums import ActorType as A
from app.models.enums import PricingType
from app.schemas.inputs import PricingIn, Strict
from app.services.audit import audit

router = APIRouter(prefix="/admin/pricing", tags=["admin:pricing"])
LANGS = ("uz", "en", "ru")


def _tr(v: dict | None, lang: str) -> str:
    v = v or {}
    return v.get(lang) or v.get("uz") or v.get("en") or ""


def _pricing(p: ServicePricing | None) -> dict | None:
    if p is None:
        return None
    return {"pricing_type": p.pricing_type, "currency": p.currency, "base_price_minor": p.base_price_minor, "unit_label": p.unit_label or {},
            "min_quantity": p.min_quantity, "max_quantity": p.max_quantity, "tiers": p.tiers or [], "addons": p.addons or [],
            "deposit_type": p.deposit_type, "deposit_value": p.deposit_value}


def _row(s: Service, lang: str) -> dict:
    return {
        "id": s.id, "slug": s.slug, "name": _tr(s.name, lang), "is_active": s.is_active, "mode": s.service_mode or "ONLINE",
        "archived": s.archived_at is not None,
        "category": {"slug": s.category.slug, "name": _tr(s.category.name, lang), "icon": s.category.icon},
        "pricing": _pricing(s.pricing), "unpriced": is_unpriced(s.pricing), "suggested": suggestion(s.slug),
    }


def validate_pricing(pr: PricingIn) -> None:
    if pr.pricing_type in (PricingType.FIXED, PricingType.PER_UNIT, PricingType.STARTING_FROM, PricingType.QUANTITY_TIERED) and pr.base_price_minor <= 0:
        raise AppError("A positive base price is required for this pricing type", code="INVALID_PRICING")
    if pr.deposit_type == "PERCENT" and pr.deposit_value > 100:
        raise AppError("Deposit percent must be 0-100", code="INVALID_PRICING")
    if pr.min_quantity > pr.max_quantity:
        raise AppError("Minimum quantity exceeds maximum", code="INVALID_PRICING")


@router.get("")
def list_prices(lang: str = Query("uz", pattern="^(uz|en|ru)$"), db: DB = Depends(get_db), auth: Auth = Depends(require("orders.view"))):
    rows = db.scalars(select(Service).where(Service.archived_at.is_(None)).order_by(Service.category_id, Service.sort_order, Service.id)).all()
    items = [_row(s, lang) for s in rows]
    return {"items": items, "unpriced": sum(1 for i in items if i["unpriced"]),
            "suggestable": sum(1 for i in items if i["unpriced"] and i["suggested"])}


@router.put("/{sid}")
def set_price(sid: int, body: PricingIn, lang: str = Query("uz", pattern="^(uz|en|ru)$"), db: DB = Depends(get_db), auth: Auth = Depends(require("services.manage"))):
    s = db.get(Service, sid)
    if s is None or s.archived_at is not None:
        raise NotFound("Service not found")
    validate_pricing(body)
    before = _pricing(s.pricing)
    if s.pricing is None:
        s.pricing = ServicePricing(pricing_type=body.pricing_type)
    p = s.pricing
    p.pricing_type, p.currency, p.base_price_minor, p.unit_label = body.pricing_type, body.currency, body.base_price_minor, body.unit_label.model_dump()
    p.min_quantity, p.max_quantity = body.min_quantity, body.max_quantity
    p.tiers = sorted((t.model_dump() for t in body.tiers), key=lambda t: t["min_qty"])
    p.addons = [{"key": a.key, "label": a.label.model_dump(), "price_minor": a.price_minor} for a in body.addons]
    p.deposit_type, p.deposit_value = body.deposit_type, body.deposit_value
    audit(db, "service.price_changed", actor_id=auth.user.id, actor_type=A.ADMIN, entity_type="service", entity_id=s.id,
          data={"before": {k: before[k] for k in ("pricing_type", "base_price_minor")} if before else None,
                "after": {"pricing_type": p.pricing_type, "base_price_minor": p.base_price_minor}})
    db.commit()
    return _row(s, lang)


class SuggestIn(Strict):
    service_ids: list[int] = Field(default_factory=list, max_length=500)


@router.post("/apply-suggested")
def apply_suggested(body: SuggestIn, lang: str = Query("uz", pattern="^(uz|en|ru)$"), db: DB = Depends(get_db), auth: Auth = Depends(require("services.manage"))):
    """Without ids: fill every service that still has no price. With ids: use the suggestion for exactly those services."""
    q = select(Service).where(Service.archived_at.is_(None))
    if body.service_ids:
        q = q.where(Service.id.in_(body.service_ids))
    changed = []
    for s in db.scalars(q):
        if not body.service_ids and not is_unpriced(s.pricing):
            continue  # never overwrite a price the owner set
        if apply_suggestion(s):
            changed.append(s.id)
    if changed:
        audit(db, "service.prices_suggested", actor_id=auth.user.id, actor_type=A.ADMIN, entity_type="service", data={"service_ids": changed})
    db.commit()
    return {"changed": len(changed), "service_ids": changed}
