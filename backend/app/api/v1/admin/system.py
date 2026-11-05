from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session as DB

from app.ai.manager import spent_today
from app.api.deps import Auth, RequestCtx, get_ctx, get_db, get_staff, require
from app.core.config import settings
from app.core.db import utcnow
from app.core.errors import ConfigurationRequired, NotFound
from app.models import AIExecution, AIUsageRecord, AuditLog, ContactRequest, FAQItem, Notification, Order, Payment, Service, StaticPage, User
from app.models.enums import ActorType as A
from app.models.enums import AIExecutionStatus as X
from app.models.enums import NotificationChannel
from app.models.enums import OrderStatus as S
from app.models.enums import PaymentKind, PaymentStatus
from app.schemas.inputs import FAQIn, SettingsPatchIn, StaticPageIn
from app.schemas.serializers import iso
from app.services.audit import audit
from app.services.settings_service import DEFAULTS, SECRET_KEYS, get_many, set_setting

router = APIRouter(prefix="/admin", tags=["admin:system"])
PROCESSING = [S.QUEUED, S.AI_PROCESSING, S.AI_REVIEW_REQUIRED, S.MANUAL_PROCESSING, S.REVISION_REQUESTED]


@router.get("/activity")
def activity(after_id: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=50), db: DB = Depends(get_db), auth: Auth = Depends(require("orders.view"))):
    """Staff activity feed for the admin bell. Poll with after_id to receive only new events."""
    q = select(Notification).where(Notification.channel == NotificationChannel.ADMIN_FEED)
    if "finance.view" not in auth.permissions:
        q = q.where(~Notification.event_type.startswith("payment."))
    latest_id = db.scalar(select(func.max(Notification.id)).where(q.whereclause)) or 0
    rows = db.scalars(q.where(Notification.id > after_id).order_by(Notification.id.desc()).limit(limit)).all()
    items = [{"id": n.id, "event_type": n.event_type, "title": n.title, "order_number": (n.data or {}).get("order_number"),
              "lines": (n.data or {}).get("lines") or [], "link": (n.data or {}).get("link") or "/admin", "created_at": iso(n.created_at)} for n in rows]
    return {"items": items, "latest_id": latest_id}


@router.get("/overview")
def overview(db: DB = Depends(get_db), auth: Auth = Depends(get_staff)):
    """Real-time metrics from the database. No fabricated values."""
    count = lambda *conds: db.scalar(select(func.count()).select_from(Order).where(*conds)) or 0  # noqa: E731
    since_day = utcnow() - timedelta(days=1)
    out = {
        "customers": db.scalar(select(func.count()).select_from(User).where(User.deleted_at.is_(None))) or 0,
        "orders_total": count(),
        "orders_new_24h": count(Order.created_at >= since_day),
        "awaiting_review": count(Order.status.in_([S.SUBMITTED, S.UNDER_REVIEW, S.AI_REVIEW_REQUIRED])),
        "processing": count(Order.status.in_(PROCESSING)),
        "completed": count(Order.status.in_([S.DELIVERED, S.CLOSED])),
        "cancelled": count(Order.status == S.CANCELLED),
        "ready_for_delivery": count(Order.status == S.READY_FOR_DELIVERY),
        "ai_jobs_running": db.scalar(select(func.count()).select_from(AIExecution).where(AIExecution.status.in_([X.PENDING, X.PLANNING, X.RUNNING, X.VALIDATING]))) or 0,
        "ai_failures_7d": db.scalar(select(func.count()).select_from(AIExecution).where(AIExecution.status == X.FAILED, AIExecution.created_at >= utcnow() - timedelta(days=7))) or 0,
        "ai_spent_today_usd": f"{spent_today(db):.4f}",
        "integrations": settings.integration_status(),
    }
    if auth.can("finance.view"):
        money: dict[str, dict] = {}
        for ccy, kind, amt in db.execute(select(Payment.currency, Payment.kind, func.sum(Payment.amount_minor)).where(Payment.status == PaymentStatus.SUCCEEDED).group_by(Payment.currency, Payment.kind)):
            m = money.setdefault(ccy, {"revenue_minor": 0, "deposits_minor": 0, "outstanding_minor": 0, "refunded_minor": 0})
            m["revenue_minor"] += int(amt or 0)
            if kind == PaymentKind.DEPOSIT:
                m["deposits_minor"] += int(amt or 0)
        for ccy, out_, ref in db.execute(select(Order.currency, func.sum(Order.total_minor - Order.paid_minor), func.sum(Order.refunded_minor)).where(Order.status.not_in([S.CANCELLED, S.REFUNDED, S.DRAFT])).group_by(Order.currency)):
            m = money.setdefault(ccy, {"revenue_minor": 0, "deposits_minor": 0, "outstanding_minor": 0, "refunded_minor": 0})
            m["outstanding_minor"] += max(int(out_ or 0), 0)
            m["refunded_minor"] += int(ref or 0)
        ai_total = Decimal(str(db.scalar(select(func.coalesce(func.sum(AIUsageRecord.cost_usd), 0))) or 0))
        out["finance"] = {"by_currency": money, "ai_expenses_total_usd": f"{ai_total:.4f}"}
    recent = db.execute(select(Order, User.email).join(User, User.id == Order.customer_id).order_by(Order.id.desc()).limit(8)).all()
    out["recent_orders"] = [{"id": o.id, "order_number": o.order_number, "title": o.title, "status": o.status, "customer_email": e, "created_at": iso(o.created_at), "total_minor": o.total_minor, "currency": o.currency} for o, e in recent]
    return out


@router.get("/analytics")
def analytics(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    service_id: int | None = None,
    currency: str | None = Query(None, pattern="^(UZS|USD)$"),
    status: str | None = Query(None, max_length=40),
    granularity: str = Query("day", pattern="^(day|week|month)$"),
    db: DB = Depends(get_db),
    auth: Auth = Depends(require("analytics.view")),
):
    end = date_to or utcnow()
    start = date_from or end - timedelta(days=30)
    conds = [Order.created_at.between(start, end)]
    if service_id:
        conds.append(Order.service_id == service_id)
    if currency:
        conds.append(Order.currency == currency)
    if status:
        conds.append(Order.status == status)
    bucket = func.date_trunc(granularity, Order.created_at)
    orders_series = db.execute(select(cast(bucket, Date), func.count()).where(*conds).group_by(cast(bucket, Date)).order_by(cast(bucket, Date))).all()
    pconds = [Payment.status == PaymentStatus.SUCCEEDED, Payment.confirmed_at.between(start, end)]
    if currency:
        pconds.append(Payment.currency == currency)
    pbucket = func.date_trunc(granularity, Payment.confirmed_at)
    rev_series = db.execute(select(cast(pbucket, Date), Payment.currency, func.sum(Payment.amount_minor)).join(Order, Order.id == Payment.order_id)
                            .where(*pconds, *( [Order.service_id == service_id] if service_id else [])).group_by(cast(pbucket, Date), Payment.currency).order_by(cast(pbucket, Date))).all()
    popular = db.execute(select(Service.slug, Service.name, func.count(Order.id)).join(Order, Order.service_id == Service.id).where(*conds).group_by(Service.id).order_by(func.count(Order.id).desc()).limit(10)).all()
    total = db.scalar(select(func.count()).select_from(Order).where(*conds)) or 0
    cancelled = db.scalar(select(func.count()).select_from(Order).where(*conds, Order.status == S.CANCELLED)) or 0
    avg_hours = db.scalar(select(func.avg(func.extract("epoch", Order.completed_at - Order.submitted_at) / 3600)).where(*conds, Order.completed_at.is_not(None)))
    ex_conds = [AIExecution.created_at.between(start, end)]
    ai = dict(db.execute(select(AIExecution.status, func.count()).where(*ex_conds).group_by(AIExecution.status)).all())
    ai_done = sum(ai.get(k, 0) for k in (X.APPROVED, X.REJECTED, X.FAILED))
    ai_cost = Decimal(str(db.scalar(select(func.coalesce(func.sum(AIUsageRecord.cost_usd), 0)).where(AIUsageRecord.created_at.between(start, end))) or 0))
    ai_orders = db.scalar(select(func.count(func.distinct(AIUsageRecord.order_id))).where(AIUsageRecord.created_at.between(start, end), AIUsageRecord.order_id.is_not(None))) or 0
    outstanding = db.execute(select(Order.currency, func.sum(Order.total_minor - Order.paid_minor)).where(*conds, Order.status.in_([S.DEPOSIT_PENDING, S.PARTIALLY_PAID, S.FINAL_PAYMENT_PENDING, *PROCESSING]), Order.total_minor > Order.paid_minor).group_by(Order.currency)).all()
    return {
        "from": iso(start), "to": iso(end), "granularity": granularity,
        "orders": [{"date": d.isoformat(), "count": c} for d, c in orders_series],
        "revenue": [{"date": d.isoformat(), "currency": ccy, "amount_minor": int(a or 0)} for d, ccy, a in rev_series],
        "popular_services": [{"slug": s, "name": n.get("en") if isinstance(n, dict) else s, "orders": c} for s, n, c in popular],
        "orders_total": total, "cancellation_rate": round(cancelled / total, 3) if total else None,
        "avg_completion_hours": round(float(avg_hours), 1) if avg_hours is not None else None,
        "ai": {"by_status": ai, "success_rate": round(ai.get(X.APPROVED, 0) / ai_done, 3) if ai_done else None,
               "fallback_rate": round(ai.get(X.FAILED, 0) / ai_done, 3) if ai_done else None,
               "cost_usd": f"{ai_cost:.4f}", "cost_per_ai_order_usd": f"{(ai_cost / ai_orders):.4f}" if ai_orders else None},
        "outstanding": [{"currency": c, "amount_minor": int(a or 0)} for c, a in outstanding],
        "profit_note": "Estimated profit = revenue − refunds − AI costs (AI costs are in USD; convert at your own rate).",
    }


@router.get("/settings")
def get_settings(db: DB = Depends(get_db), auth: Auth = Depends(require("settings.manage"))):
    return {"values": get_many(db, set(DEFAULTS) | SECRET_KEYS), "integrations": settings.integration_status(),
            "environment": {"app_env": settings.APP_ENV, "app_url": settings.APP_URL, "max_upload_mb_server": settings.MAX_UPLOAD_MB,
                            "telegram_admin_ids_configured": len(settings.telegram_admin_ids), "email_backend": settings.EMAIL_BACKEND, "storage_backend": settings.STORAGE_BACKEND},
            "production_problems": settings.validate_for_production() if settings.is_production else []}


@router.patch("/settings")
def patch_settings(body: SettingsPatchIn, db: DB = Depends(get_db), auth: Auth = Depends(require("settings.manage")), ctx: RequestCtx = Depends(get_ctx)):
    for key, value in body.values.items():
        if key in SECRET_KEYS and not auth.can("secrets.manage"):
            from app.core.errors import Forbidden

            raise Forbidden("Secret settings require the secrets.manage permission")
        if key.startswith("ai.") and not auth.can("ai.configure"):
            from app.core.errors import Forbidden

            raise Forbidden("AI settings require the ai.configure permission")
        set_setting(db, key, value, actor_id=auth.user.id)
    audit(db, "settings.changed", actor_id=auth.user.id, actor_type=A.ADMIN, ip=ctx.ip, data={"keys": sorted(body.values), "values": {k: ("***" if k in SECRET_KEYS else v) for k, v in body.values.items()}})
    db.commit()
    return {"values": get_many(db, set(DEFAULTS) | SECRET_KEYS)}


@router.post("/telegram/setup-webhook")
def telegram_setup(db: DB = Depends(get_db), auth: Auth = Depends(require("secrets.manage"))):
    from app.telegram.client import TelegramError, set_commands, set_webhook

    if not (settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_WEBHOOK_SECRET):
        raise ConfigurationRequired("Set TELEGRAM_BOT_TOKEN and TELEGRAM_WEBHOOK_SECRET first")
    url = settings.TELEGRAM_WEBHOOK_URL or f"{settings.API_URL.rstrip('/')}/api/v1/webhooks/telegram/{settings.TELEGRAM_WEBHOOK_SECRET}"
    try:
        set_webhook(url, settings.TELEGRAM_WEBHOOK_SECRET)
        set_commands()
    except TelegramError as e:
        return {"ok": False, "error": str(e)}
    audit(db, "telegram.webhook_configured", actor_id=auth.user.id, actor_type=A.ADMIN)
    db.commit()
    return {"ok": True}


@router.post("/telegram/test")
def telegram_test(db: DB = Depends(get_db), auth: Auth = Depends(require("settings.manage"))):
    from app.telegram.client import TelegramError, TelegramNotConfigured, send_message

    chat = settings.TELEGRAM_NOTIFICATION_CHAT_ID or (str(min(settings.telegram_admin_ids)) if settings.telegram_admin_ids else "")
    if not chat:
        raise ConfigurationRequired("Set TELEGRAM_ADMIN_ID or TELEGRAM_NOTIFICATION_CHAT_ID")
    try:
        send_message(chat, "✅ VIMORA test notification")
        return {"ok": True}
    except (TelegramError, TelegramNotConfigured) as e:
        return {"ok": False, "error": str(e)}


@router.post("/email/test")
def email_test(db: DB = Depends(get_db), auth: Auth = Depends(require("settings.manage"))):
    from app.services.email import EmailDeliveryError, EmailNotConfigured, send_email

    try:
        res = send_email(auth.user.email, "VIMORA test email", "This is a test message from your VIMORA installation.")
        return {"ok": res == "SENT", "result": res}
    except (EmailNotConfigured, EmailDeliveryError) as e:
        return {"ok": False, "error": str(e)}


# ------------------------------------------------------------------ content
@router.get("/pages")
def pages(db: DB = Depends(get_db), auth: Auth = Depends(require("settings.manage"))):
    return {"items": [{"slug": p.slug, "title": p.title, "body": p.body, "is_published": p.is_published, "updated_at": iso(p.updated_at)} for p in db.scalars(select(StaticPage).order_by(StaticPage.slug))]}


@router.put("/pages/{slug}")
def put_page(slug: str, body: StaticPageIn, db: DB = Depends(get_db), auth: Auth = Depends(require("settings.manage"))):
    if slug not in ("terms", "privacy", "refund-policy", "service-policy", "about", "ai-notice"):
        raise NotFound("Unknown page")
    p = db.scalar(select(StaticPage).where(StaticPage.slug == slug))
    if p is None:
        p = StaticPage(slug=slug)
        db.add(p)
    p.title, p.body, p.is_published, p.updated_by_id = body.title.model_dump(), body.body.model_dump(), body.is_published, auth.user.id
    audit(db, "page.updated", actor_id=auth.user.id, actor_type=A.ADMIN, entity_type="page", entity_id=slug, data={"published": body.is_published})
    db.commit()
    return {"status": "ok"}


@router.get("/faq")
def faq(db: DB = Depends(get_db), auth: Auth = Depends(require("settings.manage"))):
    return {"items": [{"id": f.id, "question": f.question, "answer": f.answer, "sort_order": f.sort_order, "is_published": f.is_published} for f in db.scalars(select(FAQItem).order_by(FAQItem.sort_order, FAQItem.id))]}


@router.post("/faq", status_code=201)
def create_faq(body: FAQIn, db: DB = Depends(get_db), auth: Auth = Depends(require("settings.manage"))):
    f = FAQItem(question=body.question.model_dump(), answer=body.answer.model_dump(), sort_order=body.sort_order, is_published=body.is_published)
    db.add(f)
    db.commit()
    return {"id": f.id}


@router.put("/faq/{fid}")
def update_faq(fid: int, body: FAQIn, db: DB = Depends(get_db), auth: Auth = Depends(require("settings.manage"))):
    f = db.get(FAQItem, fid)
    if f is None:
        raise NotFound("FAQ not found")
    f.question, f.answer, f.sort_order, f.is_published = body.question.model_dump(), body.answer.model_dump(), body.sort_order, body.is_published
    db.commit()
    return {"id": f.id}


@router.delete("/faq/{fid}")
def delete_faq(fid: int, db: DB = Depends(get_db), auth: Auth = Depends(require("settings.manage"))):
    f = db.get(FAQItem, fid)
    if f:
        db.delete(f)
        db.commit()
    return {"status": "ok"}


@router.get("/contact-requests")
def contact_requests(db: DB = Depends(get_db), auth: Auth = Depends(require("orders.view"))):
    rows = db.scalars(select(ContactRequest).order_by(ContactRequest.id.desc()).limit(200))
    return {"items": [{"id": c.id, "name": c.name, "email": c.email, "subject": c.subject, "message": c.message, "handled_at": iso(c.handled_at), "created_at": iso(c.created_at)} for c in rows]}


@router.post("/contact-requests/{cid}/handled")
def contact_handled(cid: int, db: DB = Depends(get_db), auth: Auth = Depends(require("orders.view"))):
    c = db.get(ContactRequest, cid)
    if c is None:
        raise NotFound("Not found")
    c.handled_at = utcnow()
    db.commit()
    return {"status": "ok"}


@router.get("/reviews")
def reviews(db: DB = Depends(get_db), auth: Auth = Depends(require("orders.view"))):
    rows = db.execute(select(Order, User.email).join(User, User.id == Order.customer_id).where(Order.reviewed_at.is_not(None)).order_by(Order.reviewed_at.desc()).limit(200)).all()
    return {"items": [{"order_id": o.id, "order_number": o.order_number, "rating": o.review_rating, "text": o.review_text, "public": o.review_public, "customer_email": e, "reviewed_at": iso(o.reviewed_at)} for o, e in rows]}


@router.get("/audit-logs")
def audit_logs(action: str | None = Query(None, max_length=80), actor_id: int | None = None, entity_type: str | None = Query(None, max_length=60), entity_id: str | None = Query(None, max_length=60),
               page: int = Query(1, ge=1), db: DB = Depends(get_db), auth: Auth = Depends(require("audit.view"))):
    q = select(AuditLog)
    if action:
        q = q.where(AuditLog.action.ilike(f"{action}%"))
    if actor_id:
        q = q.where(AuditLog.actor_id == actor_id)
    if entity_type:
        q = q.where(AuditLog.entity_type == entity_type)
    if entity_id:
        q = q.where(AuditLog.entity_id == entity_id)
    rows = db.scalars(q.order_by(AuditLog.id.desc()).offset((page - 1) * 50).limit(50))
    return {"items": [{"id": a.id, "action": a.action, "actor_id": a.actor_id, "actor_type": a.actor_type, "entity_type": a.entity_type, "entity_id": a.entity_id,
                       "ip": a.ip_address, "success": a.success, "data": a.data, "created_at": iso(a.created_at)} for a in rows], "page": page}


@router.get("/health")
def health_details(db: DB = Depends(get_db), auth: Auth = Depends(require("settings.manage"))):
    from app.api.v1.health import detailed

    return detailed(db)
