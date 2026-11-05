from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DB

from app.ai.capabilities import CAPABILITIES
from app.api.deps import Auth, get_db, require
from app.core.config import settings
from app.core.db import utcnow
from app.core.errors import AppError, Conflict, NotFound
from app.models import Order, PromoCode, PromoCodeUsage, Service, ServiceArea, ServiceCategory, ServicePricing, User
from app.models.enums import ActorType as A
from app.models.enums import AttachmentPurpose, PricingType
from app.schemas.inputs import CategoryIn, PromoIn, ServiceAreaIn, ServiceIn
from app.schemas.serializers import area_admin, category_out, iso, service_out
from app.services.audit import audit
from app.services.files import store_upload

router = APIRouter(prefix="/admin", tags=["admin:catalog"])


@router.get("/categories")
def categories(db: DB = Depends(get_db), auth: Auth = Depends(require("orders.view"))):
    return {"items": [category_out(c, full=True) for c in db.scalars(select(ServiceCategory).order_by(ServiceCategory.sort_order, ServiceCategory.id))]}


@router.post("/categories", status_code=201)
def create_category(body: CategoryIn, db: DB = Depends(get_db), auth: Auth = Depends(require("services.manage"))):
    if db.scalar(select(ServiceCategory.id).where(ServiceCategory.slug == body.slug)):
        raise Conflict("A category with this slug exists", code="DUPLICATE_SLUG")
    c = ServiceCategory(slug=body.slug, name=body.name.model_dump(), description=body.description.model_dump(), icon=body.icon, sort_order=body.sort_order, is_active=body.is_active)
    db.add(c)
    db.flush()
    audit(db, "category.created", actor_id=auth.user.id, actor_type=A.ADMIN, entity_type="category", entity_id=c.id)
    db.commit()
    return category_out(c, full=True)


@router.put("/categories/{cid}")
def update_category(cid: int, body: CategoryIn, db: DB = Depends(get_db), auth: Auth = Depends(require("services.manage"))):
    c = db.get(ServiceCategory, cid)
    if c is None:
        raise NotFound("Category not found")
    if body.slug != c.slug and db.scalar(select(ServiceCategory.id).where(ServiceCategory.slug == body.slug)):
        raise Conflict("A category with this slug exists", code="DUPLICATE_SLUG")
    c.slug, c.name, c.description, c.icon, c.sort_order, c.is_active = body.slug, body.name.model_dump(), body.description.model_dump(), body.icon, body.sort_order, body.is_active
    audit(db, "category.updated", actor_id=auth.user.id, actor_type=A.ADMIN, entity_type="category", entity_id=c.id)
    db.commit()
    return category_out(c, full=True)


@router.delete("/categories/{cid}")
def delete_category(cid: int, db: DB = Depends(get_db), auth: Auth = Depends(require("services.manage"))):
    c = db.get(ServiceCategory, cid)
    if c is None:
        raise NotFound("Category not found")
    if db.scalar(select(func.count()).select_from(Service).where(Service.category_id == cid)):
        raise Conflict("Move or archive the category's services first (or deactivate the category)", code="CATEGORY_IN_USE")
    db.delete(c)
    audit(db, "category.deleted", actor_id=auth.user.id, actor_type=A.ADMIN, entity_type="category", entity_id=cid)
    db.commit()
    return {"status": "ok"}


@router.get("/services")
def services(include_archived: bool = False, q: str | None = Query(None, max_length=100), db: DB = Depends(get_db), auth: Auth = Depends(require("orders.view"))):
    stmt = select(Service)
    if not include_archived:
        stmt = stmt.where(Service.archived_at.is_(None))
    if q:
        stmt = stmt.where(Service.slug.ilike(f"%{q}%"))
    rows = db.scalars(stmt.order_by(Service.category_id, Service.sort_order, Service.id)).unique().all()
    counts = dict(db.execute(select(Order.service_id, func.count()).group_by(Order.service_id)).all())
    return {"items": [{**service_out(s, full=True), "order_count": counts.get(s.id, 0)} for s in rows], "capabilities": {k: c.description for k, c in CAPABILITIES.items()}}


@router.get("/services/{sid}")
def get_service(sid: int, db: DB = Depends(get_db), auth: Auth = Depends(require("orders.view"))):
    s = db.get(Service, sid)
    if s is None:
        raise NotFound("Service not found")
    return service_out(s, full=True)


def _apply_mode(db: DB, s: Service, body: ServiceIn) -> None:
    mode = body.service_mode or s.service_mode or "ONLINE"
    area = db.get(ServiceArea, body.service_area_id) if body.service_area_id else None
    if body.service_area_id and area is None:
        raise AppError("Unknown area", code="INVALID_AREA")
    if mode == "LOCAL":
        if area is None:
            raise AppError("A local service needs an area", code="AREA_REQUIRED")
        if body.is_active and not (area.is_active and area.local_services_enabled):
            raise AppError("Local services are not enabled in this area", code="AREA_NOT_LOCAL")
    s.service_mode = mode
    s.service_area_id = area.id if (area and mode == "LOCAL") else None
    s.service_area = area if mode == "LOCAL" else None
    s.requires_file = body.requires_file
    if mode in ("FUTURE", "DISABLED"):
        s.is_active = False  # never orderable
    if mode == "DISABLED":
        s.archived_at = s.archived_at or utcnow()


def _apply(s: Service, body: ServiceIn) -> None:
    if body.ai_capability and body.ai_capability not in CAPABILITIES:
        raise AppError("Unknown AI capability", code="UNKNOWN_CAPABILITY", details={"allowed": list(CAPABILITIES)})
    if body.ai_eligible and not body.ai_capability:
        raise AppError("Select an AI capability for AI-eligible services", code="CAPABILITY_REQUIRED")
    pr = body.pricing
    if pr.pricing_type in (PricingType.FIXED, PricingType.PER_UNIT, PricingType.STARTING_FROM, PricingType.QUANTITY_TIERED) and pr.base_price_minor <= 0:
        raise AppError("A positive base price is required for this pricing type", code="INVALID_PRICING")
    if pr.deposit_type == "PERCENT" and pr.deposit_value > 100:
        raise AppError("Deposit percent must be 0-100", code="INVALID_PRICING")
    if pr.min_quantity > pr.max_quantity:
        raise AppError("Minimum quantity exceeds maximum", code="INVALID_PRICING")
    s.slug, s.category_id = body.slug, body.category_id
    s.name, s.short_description, s.description = body.name.model_dump(), body.short_description.model_dump(), body.description.model_dump()
    s.icon, s.image_attachment_id, s.estimated_delivery, s.estimated_hours = body.icon, body.image_attachment_id, body.estimated_delivery.model_dump(), body.estimated_hours
    s.cover_image_url, s.cover_image_credit = body.cover_image_url or None, (body.cover_image_credit or "").strip() or None
    s.required_fields = [f.model_dump() for f in body.required_fields]
    s.allows_attachments, s.examples, s.is_active, s.is_featured = body.allows_attachments, body.examples, body.is_active, body.is_featured
    s.ai_eligible, s.ai_capability, s.revision_limit, s.sort_order = body.ai_eligible, body.ai_capability, body.revision_limit, body.sort_order
    if s.pricing is None:
        s.pricing = ServicePricing(pricing_type=pr.pricing_type)
    p = s.pricing
    p.pricing_type, p.currency, p.base_price_minor, p.unit_label = pr.pricing_type, pr.currency, pr.base_price_minor, pr.unit_label.model_dump()
    p.min_quantity, p.max_quantity = pr.min_quantity, pr.max_quantity
    p.tiers = [t.model_dump() for t in pr.tiers]
    p.addons = [{"key": a.key, "label": a.label.model_dump(), "price_minor": a.price_minor} for a in pr.addons]
    p.deposit_type, p.deposit_value = pr.deposit_type, pr.deposit_value


@router.post("/services", status_code=201)
def create_service(body: ServiceIn, db: DB = Depends(get_db), auth: Auth = Depends(require("services.manage"))):
    if db.get(ServiceCategory, body.category_id) is None:
        raise NotFound("Category not found")
    if db.scalar(select(Service.id).where(Service.slug == body.slug)):
        raise Conflict("A service with this slug exists", code="DUPLICATE_SLUG")
    s = Service(slug=body.slug, category_id=body.category_id, name={})
    _apply(s, body)
    _apply_mode(db, s, body)
    db.add(s)
    db.flush()
    audit(db, "service.created", actor_id=auth.user.id, actor_type=A.ADMIN, entity_type="service", entity_id=s.id)
    db.commit()
    db.refresh(s)
    return service_out(s, full=True)


@router.put("/services/{sid}")
def update_service(sid: int, body: ServiceIn, db: DB = Depends(get_db), auth: Auth = Depends(require("services.manage"))):
    s = db.get(Service, sid)
    if s is None:
        raise NotFound("Service not found")
    if body.slug != s.slug and db.scalar(select(Service.id).where(Service.slug == body.slug)):
        raise Conflict("A service with this slug exists", code="DUPLICATE_SLUG")
    if db.get(ServiceCategory, body.category_id) is None:
        raise NotFound("Category not found")
    before = {"price": s.pricing.base_price_minor if s.pricing else None, "type": s.pricing.pricing_type if s.pricing else None, "active": s.is_active}
    was_disabled = s.service_mode == "DISABLED"
    _apply(s, body)
    _apply_mode(db, s, body)
    if was_disabled and s.service_mode != "DISABLED":
        s.archived_at = None  # restored from the archive by changing its type
    audit(db, "service.updated", actor_id=auth.user.id, actor_type=A.ADMIN, entity_type="service", entity_id=s.id,
          data={"before": before, "after": {"price": s.pricing.base_price_minor, "type": s.pricing.pricing_type, "active": s.is_active, "mode": s.service_mode}})
    db.commit()
    return service_out(s, full=True)


@router.post("/services/{sid}/archive")
def archive_service(sid: int, db: DB = Depends(get_db), auth: Auth = Depends(require("services.manage"))):
    s = db.get(Service, sid)
    if s is None:
        raise NotFound("Service not found")
    s.archived_at = utcnow()
    s.is_active = False
    audit(db, "service.archived", actor_id=auth.user.id, actor_type=A.ADMIN, entity_type="service", entity_id=s.id)
    db.commit()
    return {"status": "archived"}


@router.post("/services/{sid}/restore")
def restore_service(sid: int, db: DB = Depends(get_db), auth: Auth = Depends(require("services.manage"))):
    s = db.get(Service, sid)
    if s is None:
        raise NotFound("Service not found")
    s.archived_at = None
    audit(db, "service.restored", actor_id=auth.user.id, actor_type=A.ADMIN, entity_type="service", entity_id=s.id)
    db.commit()
    return {"status": "restored"}


@router.delete("/services/{sid}")
def delete_service(sid: int, db: DB = Depends(get_db), auth: Auth = Depends(require("services.manage"))):
    s = db.get(Service, sid)
    if s is None:
        raise NotFound("Service not found")
    if db.scalar(select(func.count()).select_from(Order).where(Order.service_id == sid)):
        raise Conflict("Services with orders cannot be deleted; archive it instead", code="SERVICE_IN_USE")
    db.delete(s)
    audit(db, "service.deleted", actor_id=auth.user.id, actor_type=A.ADMIN, entity_type="service", entity_id=sid)
    db.commit()
    return {"status": "deleted"}


@router.post("/images", status_code=201)
async def upload_image(file: UploadFile = File(...), db: DB = Depends(get_db), auth: Auth = Depends(require("services.manage"))):
    data = await file.read(settings.MAX_UPLOAD_MB * 1024 * 1024 + 1)
    att = store_upload(db, owner_id=auth.user.id, filename=file.filename or "image", data=data, purpose=AttachmentPurpose.SERVICE_IMAGE, images_only=True, is_public=True, enforce_quota=False)
    db.commit()
    return {"attachment_id": att.id, "url": f"{settings.API_URL.rstrip('/')}/api/v1/public-files/{att.id}"}


# ------------------------------------------------------------------ promo codes
def _promo_out(p: PromoCode, uses: int) -> dict:
    return {"id": p.id, "code": p.code, "percent_off": p.percent_off, "amount_off_minor": p.amount_off_minor, "currency": p.currency, "max_uses": p.max_uses,
            "max_uses_per_user": p.max_uses_per_user, "min_order_minor": p.min_order_minor, "valid_from": iso(p.valid_from), "valid_until": iso(p.valid_until),
            "is_active": p.is_active, "service_ids": p.service_ids, "uses": uses}


@router.get("/promo-codes")
def promos(db: DB = Depends(get_db), auth: Auth = Depends(require("services.manage"))):
    uses = dict(db.execute(select(PromoCodeUsage.promo_code_id, func.count()).group_by(PromoCodeUsage.promo_code_id)).all())
    return {"items": [_promo_out(p, uses.get(p.id, 0)) for p in db.scalars(select(PromoCode).order_by(PromoCode.id.desc()))]}


def _apply_promo(p: PromoCode, body: PromoIn) -> None:
    if bool(body.percent_off) == bool(body.amount_off_minor):
        raise AppError("Set either percent_off or amount_off_minor", code="INVALID_PROMO")
    if body.amount_off_minor and not body.currency:
        raise AppError("A fixed discount needs a currency", code="INVALID_PROMO")
    p.code = body.code.upper()
    for f in ("percent_off", "amount_off_minor", "currency", "max_uses", "max_uses_per_user", "min_order_minor", "valid_from", "valid_until", "is_active", "service_ids"):
        setattr(p, f, getattr(body, f))


@router.post("/promo-codes", status_code=201)
def create_promo(body: PromoIn, db: DB = Depends(get_db), auth: Auth = Depends(require("services.manage"))):
    if db.scalar(select(PromoCode.id).where(PromoCode.code == body.code.upper())):
        raise Conflict("Promo code exists", code="DUPLICATE")
    p = PromoCode(code=body.code.upper())
    _apply_promo(p, body)
    db.add(p)
    db.flush()
    audit(db, "promo.created", actor_id=auth.user.id, actor_type=A.ADMIN, entity_type="promo", entity_id=p.id, data={"code": p.code})
    db.commit()
    return _promo_out(p, 0)


@router.put("/promo-codes/{pid}")
def update_promo(pid: int, body: PromoIn, db: DB = Depends(get_db), auth: Auth = Depends(require("services.manage"))):
    p = db.get(PromoCode, pid)
    if p is None:
        raise NotFound("Promo code not found")
    _apply_promo(p, body)
    audit(db, "promo.updated", actor_id=auth.user.id, actor_type=A.ADMIN, entity_type="promo", entity_id=p.id)
    db.commit()
    return _promo_out(p, 0)


# ---------------------------------------------------------------- service areas
@router.get("/areas")
def list_areas(db: DB = Depends(get_db), auth: Auth = Depends(require("orders.view"))):
    rows = db.scalars(select(ServiceArea).order_by(ServiceArea.sort_order, ServiceArea.id)).all()
    counts = dict(db.execute(select(Service.service_area_id, func.count()).where(Service.service_area_id.is_not(None), Service.archived_at.is_(None))
                             .group_by(Service.service_area_id)).all())
    items = []
    for a in rows:
        d = area_admin(a)
        if "settings.manage" not in auth.permissions:
            d.pop("pickup_address")  # private: only the owner/admins who manage settings see it
        items.append({**d, "service_count": counts.get(a.id, 0)})
    return {"items": items}


def _apply_area(db: DB, a: ServiceArea, body: ServiceAreaIn) -> None:
    if body.provider_id is not None:
        u = db.get(User, body.provider_id)
        if u is None or not u.is_staff:
            raise AppError("The provider must be a staff member", code="INVALID_PROVIDER")
    a.slug, a.kind, a.name = body.slug, body.kind, body.name.model_dump()
    a.region, a.district, a.locality = body.region.strip(), body.district.strip(), body.locality.strip()
    a.is_active, a.local_services_enabled, a.provider_id = body.is_active, body.local_services_enabled, body.provider_id
    a.rules, a.pickup_address, a.sort_order = body.rules.model_dump(), body.pickup_address.strip(), body.sort_order


@router.post("/areas", status_code=201)
def create_area(body: ServiceAreaIn, db: DB = Depends(get_db), auth: Auth = Depends(require("settings.manage"))):
    if db.scalar(select(ServiceArea.id).where(ServiceArea.slug == body.slug)):
        raise Conflict("An area with this slug exists", code="DUPLICATE_SLUG")
    a = ServiceArea(slug=body.slug, kind=body.kind, name={})
    _apply_area(db, a, body)
    db.add(a)
    db.flush()
    audit(db, "area.created", actor_id=auth.user.id, actor_type=A.ADMIN, entity_type="service_area", entity_id=a.id, data={"slug": a.slug})
    db.commit()
    return area_admin(a)


@router.put("/areas/{area_id}")
def update_area(area_id: int, body: ServiceAreaIn, db: DB = Depends(get_db), auth: Auth = Depends(require("settings.manage"))):
    a = db.get(ServiceArea, area_id)
    if a is None:
        raise NotFound("Area not found")
    if body.slug != a.slug and db.scalar(select(ServiceArea.id).where(ServiceArea.slug == body.slug)):
        raise Conflict("An area with this slug exists", code="DUPLICATE_SLUG")
    before = {"active": a.is_active, "local": a.local_services_enabled}
    _apply_area(db, a, body)
    # the pickup address itself is not written to the audit log (private), only that it changed
    audit(db, "area.updated", actor_id=auth.user.id, actor_type=A.ADMIN, entity_type="service_area", entity_id=a.id,
          data={"before": before, "after": {"active": a.is_active, "local": a.local_services_enabled}})
    db.commit()
    return area_admin(a)
