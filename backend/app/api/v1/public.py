"""Public endpoints: catalog, price preview, site settings, content pages, stats, contact, AI assistant."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import String, and_, case, cast, func, or_, select
from sqlalchemy.orm import Session as DB

from app.api.deps import Auth, RequestCtx, get_ctx, get_db, get_optional_auth
from app.core.config import settings
from app.core.db import utcnow
from app.core.errors import NotFound
from app.core.i18n import pick
from app.models import Attachment, ContactRequest, FAQItem, Order, Service, ServiceArea, ServiceCategory, StaticPage, User
from app.models.enums import OrderStatus as S
from app.payments.providers import adapters
from app.schemas.inputs import AssistIn, ContactIn, PriceQuoteIn
from app.schemas.serializers import area_public, category_out, service_out
from app.security.rate_limit import enforce
from app.services.local import local_available_in
from app.services.notifications import notify_admins
from app.services.pricing import price_service
from app.services.settings_service import PUBLIC_KEYS, get_many, get_setting

router = APIRouter(tags=["public"])


def _lang(lang: str | None) -> str:
    return lang if lang in ("uz", "en", "ru") else settings.DEFAULT_LANGUAGE


def _image_url(att_id: int | None) -> str | None:
    return f"{settings.API_URL.rstrip('/')}/api/v1/public-files/{att_id}" if att_id else None


@router.get("/catalog/categories")
def categories(lang: str | None = None, db: DB = Depends(get_db)):
    lang = _lang(lang)
    counts = dict(db.execute(select(Service.category_id, func.count()).where(Service.is_active.is_(True), Service.archived_at.is_(None),
                                                                          func.coalesce(Service.service_mode, "ONLINE").in_(["ONLINE", "REMOTE", "LOCAL"])).group_by(Service.category_id)).all())
    rows = db.scalars(select(ServiceCategory).where(ServiceCategory.is_active.is_(True)).order_by(ServiceCategory.sort_order, ServiceCategory.id))
    return {"items": [{**category_out(c, lang), "service_count": counts.get(c.id, 0)} for c in rows]}


@router.get("/catalog/areas")
def areas(lang: str | None = None, db: DB = Depends(get_db)):
    """Areas a customer can choose (manually, no GPS). Pickup addresses are never included."""
    lang = _lang(lang)
    rows = db.scalars(select(ServiceArea).where(ServiceArea.is_active.is_(True)).order_by(ServiceArea.sort_order, ServiceArea.id))
    return {"items": [area_public(a, lang) for a in rows]}


@router.get("/catalog/services")
def services(
    lang: str | None = None,
    q: str | None = Query(None, max_length=100),
    category: str | None = Query(None, max_length=80),
    featured: bool | None = None,
    mode: Literal["ONLINE", "REMOTE", "LOCAL"] | None = None,
    area: str | None = Query(None, max_length=80),
    page: int = Query(1, ge=1, le=1000),
    page_size: int = Query(24, ge=1, le=60),
    db: DB = Depends(get_db),
):
    lang = _lang(lang)
    stmt = select(Service).join(ServiceCategory).where(Service.is_active.is_(True), Service.archived_at.is_(None), ServiceCategory.is_active.is_(True))
    if category:
        stmt = stmt.where(ServiceCategory.slug == category)
    if featured is not None:
        stmt = stmt.where(Service.is_featured.is_(featured))
    mode_col = func.coalesce(Service.service_mode, "ONLINE")
    stmt = stmt.where(mode_col.in_(["ONLINE", "REMOTE", "LOCAL"]))
    if mode:
        stmt = stmt.where(mode_col == mode)
    area_obj = db.scalar(select(ServiceArea).where(ServiceArea.slug == area, ServiceArea.is_active.is_(True))) if area else None
    if area:
        # "available in my area": everything online/remote + local services of exactly this area
        local_ok = and_(mode_col == "LOCAL", Service.service_area_id == (area_obj.id if area_obj and area_obj.local_services_enabled else -1))
        stmt = stmt.where(or_(mode_col.in_(["ONLINE", "REMOTE"]), local_ok))
    rank = None
    term = _search_term(q)
    if term:
        # search in the visitor's language first (name, summary, category), ranked:
        # name starts with > a word in the name starts with > name contains > category matches
        def norm(col):
            return func.translate(func.coalesce(col, ""), _APOS, "'" * len(_APOS))

        def like(col, pattern):
            return col.ilike(pattern, escape="\\")

        nm = norm(func.coalesce(Service.name[lang].astext, Service.name["uz"].astext))
        sd = norm(Service.short_description[lang].astext)
        cn = norm(func.coalesce(ServiceCategory.name[lang].astext, ServiceCategory.name["uz"].astext))
        has = f"%{term}%"
        conds = [like(nm, has), like(sd, has), like(cn, has), like(Service.slug, has)]
        if len(term) >= 3:  # longer queries also match the other languages ("windows", "резюме")
            conds += [like(norm(cast(Service.name, String)), has), like(norm(cast(Service.short_description, String)), has)]
        stmt = stmt.where(or_(*conds))
        rank = case(
            (like(nm, f"{term}%"), 0),
            (or_(like(nm, f"% {term}%"), like(nm, f"%({term}%")), 1),
            (like(nm, has), 2),
            (like(cn, has), 3),
            else_=4,
        )
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    order = ([rank] if rank is not None else []) + [Service.is_featured.desc(), Service.sort_order, Service.id]
    rows = db.scalars(stmt.order_by(*order).offset((page - 1) * page_size).limit(page_size)).unique()
    items = []
    for s in rows:
        d = service_out(s, lang, image_url=_image_url(s.image_attachment_id))
        d.pop("required_fields", None)
        d.pop("examples", None)
        d.pop("description", None)
        if area_obj is not None:
            d["available_in_area"] = d["mode"] != "LOCAL" or local_available_in(s, area_obj)
        items.append(d)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


_APOS = "‘’ʻʼ`"  # Uzbek o‘/g‘ are typed with many different apostrophes


def _search_term(q: str | None) -> str:
    """Trim, unify apostrophes and escape LIKE wildcards so '%' or '_' are searched literally."""
    t = (q or "").strip()[:100]
    for ch in _APOS:
        t = t.replace(ch, "'")
    return t.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@router.get("/catalog/services/{slug}")
def service_detail(slug: str, lang: str | None = None, db: DB = Depends(get_db)):
    s = db.scalar(select(Service).where(Service.slug == slug, Service.archived_at.is_(None)))
    if s is None or not s.category.is_active:
        raise NotFound("Service not found")
    return service_out(s, _lang(lang), image_url=_image_url(s.image_attachment_id))


@router.post("/catalog/price")
def price_preview(body: PriceQuoteIn, db: DB = Depends(get_db), auth: Auth | None = Depends(get_optional_auth), ctx: RequestCtx = Depends(get_ctx)):
    """Server-side price calculation for display; the order endpoint recomputes independently."""
    enforce(f"price:{ctx.ip}", 120, 60)
    s = db.scalar(select(Service).where(Service.slug == body.service_slug, Service.archived_at.is_(None)))
    if s is None:
        raise NotFound("Service not found")
    pr = price_service(db, s, quantity=body.quantity, addon_keys=body.addons, promo_code=body.promo_code if auth else None, user_id=auth.user.id if auth else None, lang=body.language)
    return pr.as_dict()


@router.get("/public-files/{att_id}")
def public_file(att_id: int, db: DB = Depends(get_db)):
    from fastapi.responses import StreamingResponse

    from app.storage.backends import get_storage

    att = db.get(Attachment, att_id)
    if att is None or not att.is_public or att.deleted_at is not None or not att.mime_type.startswith("image/") or att.mime_type == "image/svg+xml":
        raise NotFound("File not found")
    fh = get_storage().open(att.storage_key)
    return StreamingResponse(fh, media_type=att.mime_type, headers={"Cache-Control": "public, max-age=86400", "X-Content-Type-Options": "nosniff", "Content-Security-Policy": "default-src 'none'"})


@router.get("/site")
def site_settings(db: DB = Depends(get_db)):
    values = get_many(db, PUBLIC_KEYS)
    if values.get("platform.logo_attachment_id"):
        values["platform.logo_url"] = _image_url(values["platform.logo_attachment_id"])
    disabled = get_setting(db, "payments.disabled_providers") or []
    instructions = get_setting(db, "payments.manual_instructions") or {}
    providers = adapters(bool(get_setting(db, "payments.manual_enabled")), pick(instructions, "en"))
    values["payments.providers"] = [
        {"key": k, "available": a.configured() and k not in disabled, "currencies": sorted(a.currencies)} for k, a in providers.items()
    ]
    values["integrations"] = {"telegram_linking": bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_BOT_USERNAME)}
    from app.ai.assistant import get_ai_assistant_ready

    values["ai.assistant_ready"] = get_ai_assistant_ready(db)
    return values


@router.get("/stats")
def public_stats(db: DB = Depends(get_db)):
    """Real database values only. The frontend hides zero values rather than inventing numbers."""
    completed = db.scalar(select(func.count()).select_from(Order).where(Order.status.in_([S.DELIVERED, S.CLOSED]))) or 0
    services_count = db.scalar(select(func.count()).select_from(Service).where(Service.is_active.is_(True), Service.archived_at.is_(None))) or 0
    categories_count = db.scalar(select(func.count()).select_from(ServiceCategory).where(ServiceCategory.is_active.is_(True))) or 0
    avg = db.scalar(select(func.avg(Order.review_rating)).where(Order.review_public.is_(True)))
    reviews = db.scalar(select(func.count()).select_from(Order).where(Order.review_public.is_(True))) or 0
    return {"completed_orders": completed, "active_services": services_count, "categories": categories_count,
            "average_rating": round(float(avg), 2) if avg is not None and reviews >= 3 else None, "public_reviews": reviews}


@router.get("/testimonials")
def testimonials(lang: str | None = None, db: DB = Depends(get_db)):
    """Only genuine, customer-written reviews explicitly approved by an administrator."""
    rows = db.execute(
        select(Order, User).join(User, User.id == Order.customer_id).where(Order.review_public.is_(True), Order.review_text.is_not(None)).order_by(Order.reviewed_at.desc()).limit(9)
    ).all()
    out = []
    for o, u in rows:
        name = (u.profile.full_name if u.profile else "").strip()
        first = name.split(" ")[0] if name else "Customer"
        out.append({"rating": o.review_rating, "text": o.review_text, "author": first, "service": pick(db.get(Service, o.service_id).name, _lang(lang)) if o.service_id else None, "date": o.reviewed_at.date().isoformat()})
    return {"items": out}


@router.get("/pages/{slug}")
def static_page(slug: str, lang: str | None = None, db: DB = Depends(get_db)):
    p = db.scalar(select(StaticPage).where(StaticPage.slug == slug))
    if p is None or not p.is_published:
        return {"slug": slug, "published": False, "title": None, "body": None}
    lang = _lang(lang)
    return {"slug": slug, "published": True, "title": pick(p.title, lang), "body": pick(p.body, lang), "updated_at": p.updated_at.isoformat()}


@router.get("/faq")
def faq(lang: str | None = None, db: DB = Depends(get_db)):
    lang = _lang(lang)
    rows = db.scalars(select(FAQItem).where(FAQItem.is_published.is_(True)).order_by(FAQItem.sort_order, FAQItem.id))
    return {"items": [{"id": f.id, "question": pick(f.question, lang), "answer": pick(f.answer, lang)} for f in rows]}


@router.post("/contact", status_code=201)
def contact(body: ContactIn, db: DB = Depends(get_db), ctx: RequestCtx = Depends(get_ctx)):
    enforce(f"contact:{ctx.ip}", 5, 3600)
    if body.website:  # honeypot filled -> silently accept, store nothing
        return {"status": "received"}
    c = ContactRequest(name=body.name, email=body.email.lower(), subject=body.subject, message=body.message, ip_address=ctx.ip, created_at=utcnow())
    db.add(c)
    db.flush()
    notify_admins(db, "message.received", key_suffix=f"contact:{c.id}", title="NEW CONTACT MESSAGE", lines=[("Subject", body.subject[:80]), ("From", body.name[:60])])
    db.commit()
    return {"status": "received"}


@router.post("/ai/assist")
def ai_assist(body: AssistIn, db: DB = Depends(get_db), auth: Auth | None = Depends(get_optional_auth), ctx: RequestCtx = Depends(get_ctx)):
    from app.ai.assistant import assist

    limit = int(get_setting(db, "ai.assistant_daily_limit_per_ip"))
    enforce(f"assist-ip:{ctx.ip}", limit * (3 if auth else 1), 86400, message="Daily assistant limit reached. Please submit a custom request instead.")
    enforce(f"assist-burst:{ctx.ip}", 6, 60)
    return assist(db, message=body.message, history=body.history, lang=body.language, user_id=auth.user.id if auth else None, area=body.area)
