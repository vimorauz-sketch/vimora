from __future__ import annotations

import pyotp
from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session as DB

from app.api.deps import Auth, RequestCtx, get_auth, get_ctx, get_db
from app.core.config import settings
from app.core.db import utcnow
from app.core.errors import AppError, Conflict, NotFound, Unauthorized
from app.models import Notification, Session, TelegramAccount
from app.models.enums import ActorType as A
from app.models.enums import NotificationChannel
from app.schemas.inputs import ChangePasswordIn, DeactivateIn, MfaCodeIn, NotificationPrefsIn, ProfileIn
from app.schemas.serializers import iso, notification_out, user_public
from app.security.crypto import (
    decrypt_secret,
    encrypt_secret,
    hash_password,
    new_token,
    sha256_hex,
    validate_password_strength,
    verify_password,
)
from app.security.rate_limit import enforce
from app.security.sessions import clear_session_cookies, revoke_all_sessions, rotate_session, set_session_cookies
from app.services.audit import audit
from app.services.notifications import OPTIONAL_EVENTS

router = APIRouter(prefix="/account", tags=["account"])


@router.patch("/profile")
def update_profile(body: ProfileIn, db: DB = Depends(get_db), auth: Auth = Depends(get_auth)):
    p = auth.user.profile
    for field in ("full_name", "phone", "company", "language", "timezone"):
        val = getattr(body, field)
        if val is not None:
            setattr(p, field, val)
    db.commit()
    return {"user": user_public(auth.user)}


@router.put("/notification-preferences")
def update_prefs(body: NotificationPrefsIn, db: DB = Depends(get_db), auth: Auth = Depends(get_auth)):
    # only optional categories may be switched off; essential notifications always go out
    clean = {ch: {k: bool(v) for k, v in getattr(body, ch).items() if k in OPTIONAL_EVENTS} for ch in ("email", "telegram")}
    auth.user.profile.notification_prefs = clean
    db.commit()
    return {"notification_prefs": clean, "optional_events": sorted(OPTIONAL_EVENTS)}


@router.post("/change-password")
def change_password(body: ChangePasswordIn, response: Response, db: DB = Depends(get_db), auth: Auth = Depends(get_auth), ctx: RequestCtx = Depends(get_ctx)):
    enforce(f"chpw:{auth.user.id}", 5, 900, fail_closed=True)
    if not verify_password(auth.user.password_hash, body.current_password):
        raise Unauthorized("Current password is incorrect", code="INVALID_CREDENTIALS")
    problems = validate_password_strength(body.new_password, auth.user.email)
    if problems:
        raise AppError("Password does not meet requirements", code="WEAK_PASSWORD", details=problems)
    auth.user.password_hash = hash_password(body.new_password)
    auth.user.password_changed_at = utcnow()
    revoke_all_sessions(db, auth.user.id, except_session_id=auth.session.id)
    session, token, csrf = rotate_session(db, auth.session, auth.user, ip=ctx.ip, user_agent=ctx.user_agent, mfa_verified=auth.session.mfa_verified)
    audit(db, "auth.password_changed", actor_id=auth.user.id, actor_type=A.CUSTOMER, ip=ctx.ip)
    db.commit()
    set_session_cookies(response, token, csrf, session)
    return {"status": "ok"}


@router.get("/sessions")
def list_sessions(db: DB = Depends(get_db), auth: Auth = Depends(get_auth)):
    rows = db.scalars(select(Session).where(Session.user_id == auth.user.id, Session.revoked_at.is_(None), Session.expires_at > utcnow()).order_by(Session.last_seen_at.desc()).limit(50))
    return {"items": [{"id": s.id, "current": s.id == auth.session.id, "ip_address": s.ip_address, "user_agent": s.user_agent, "created_at": iso(s.created_at), "last_seen_at": iso(s.last_seen_at)} for s in rows]}


@router.delete("/sessions/{session_id}")
def revoke_session(session_id: int, db: DB = Depends(get_db), auth: Auth = Depends(get_auth)):
    s = db.scalar(select(Session).where(Session.id == session_id, Session.user_id == auth.user.id))
    if s is None:
        raise NotFound("Session not found")
    s.revoked_at = utcnow()
    audit(db, "auth.session_revoked", actor_id=auth.user.id, actor_type=A.CUSTOMER, data={"session_id": session_id})
    db.commit()
    return {"status": "ok"}


@router.post("/sessions/revoke-others")
def revoke_others(db: DB = Depends(get_db), auth: Auth = Depends(get_auth)):
    n = revoke_all_sessions(db, auth.user.id, except_session_id=auth.session.id)
    db.commit()
    return {"revoked": n}


# ---------------------------------------------------------------- MFA (TOTP)
@router.post("/mfa/setup")
def mfa_setup(db: DB = Depends(get_db), auth: Auth = Depends(get_auth)):
    if auth.user.mfa_enabled:
        raise Conflict("MFA is already enabled", code="MFA_ALREADY_ENABLED")
    secret = pyotp.random_base32()
    auth.user.mfa_secret_encrypted = encrypt_secret(secret)
    db.commit()
    uri = pyotp.TOTP(secret).provisioning_uri(name=auth.user.email, issuer_name=settings.APP_NAME)
    return {"secret": secret, "otpauth_uri": uri}


@router.post("/mfa/enable")
def mfa_enable(body: MfaCodeIn, response: Response, db: DB = Depends(get_db), auth: Auth = Depends(get_auth), ctx: RequestCtx = Depends(get_ctx)):
    enforce(f"mfa-enable:{auth.user.id}", 10, 300, fail_closed=True)
    secret = decrypt_secret(auth.user.mfa_secret_encrypted)
    if not secret:
        raise AppError("Start MFA setup first", code="MFA_NOT_SETUP")
    if not pyotp.TOTP(secret).verify(body.code.replace(" ", ""), valid_window=1):
        raise Unauthorized("Invalid authentication code", code="MFA_INVALID")
    codes = [new_token(6).upper().replace("-", "X").replace("_", "Y")[:10] for _ in range(8)]
    auth.user.mfa_recovery_hashes = [sha256_hex(c) for c in codes]
    auth.user.mfa_enabled = True
    session, token, csrf = rotate_session(db, auth.session, auth.user, ip=ctx.ip, user_agent=ctx.user_agent, mfa_verified=True)
    audit(db, "auth.mfa_enabled", actor_id=auth.user.id, actor_type=A.ADMIN if auth.is_staff else A.CUSTOMER, ip=ctx.ip)
    db.commit()
    set_session_cookies(response, token, csrf, session)
    return {"recovery_codes": codes}


@router.post("/mfa/disable")
def mfa_disable(body: DeactivateIn, db: DB = Depends(get_db), auth: Auth = Depends(get_auth), ctx: RequestCtx = Depends(get_ctx)):
    if auth.is_staff and settings.admin_mfa_required:
        raise Conflict("MFA is mandatory for administrator accounts", code="MFA_REQUIRED")
    if not verify_password(auth.user.password_hash, body.password):
        raise Unauthorized("Password is incorrect", code="INVALID_CREDENTIALS")
    auth.user.mfa_enabled = False
    auth.user.mfa_secret_encrypted = None
    auth.user.mfa_recovery_hashes = None
    audit(db, "auth.mfa_disabled", actor_id=auth.user.id, actor_type=A.CUSTOMER, ip=ctx.ip)
    db.commit()
    return {"status": "ok"}


@router.post("/deactivate")
def deactivate(body: DeactivateIn, response: Response, db: DB = Depends(get_db), auth: Auth = Depends(get_auth), ctx: RequestCtx = Depends(get_ctx)):
    if not verify_password(auth.user.password_hash, body.password):
        raise Unauthorized("Password is incorrect", code="INVALID_CREDENTIALS")
    if "SUPER_ADMIN" in auth.user.role_names:
        raise Conflict("The super administrator account cannot be self-deactivated", code="FORBIDDEN_FOR_OWNER")
    auth.user.is_active = False
    auth.user.deactivated_at = utcnow()
    revoke_all_sessions(db, auth.user.id)
    audit(db, "account.deactivated", actor_id=auth.user.id, actor_type=A.CUSTOMER, ip=ctx.ip)
    db.commit()
    clear_session_cookies(response)
    return {"status": "deactivated"}


# ---------------------------------------------------------------- notifications (in-app)
@router.get("/notifications")
def list_notifications(page: int = 1, unread: bool = False, db: DB = Depends(get_db), auth: Auth = Depends(get_auth)):
    page = max(page, 1)
    q = select(Notification).where(Notification.user_id == auth.user.id, Notification.channel == NotificationChannel.IN_APP)
    if unread:
        q = q.where(Notification.read_at.is_(None))
    rows = db.scalars(q.order_by(Notification.id.desc()).offset((page - 1) * 30).limit(30))
    unread_count = db.scalar(select(func.count()).select_from(Notification).where(Notification.user_id == auth.user.id, Notification.channel == NotificationChannel.IN_APP, Notification.read_at.is_(None))) or 0
    return {"items": [notification_out(n) for n in rows], "unread": unread_count, "page": page}


@router.post("/notifications/read-all")
def read_all(db: DB = Depends(get_db), auth: Auth = Depends(get_auth)):
    db.execute(update(Notification).where(Notification.user_id == auth.user.id, Notification.channel == NotificationChannel.IN_APP, Notification.read_at.is_(None)).values(read_at=utcnow()))
    db.commit()
    return {"status": "ok"}


@router.post("/notifications/{nid}/read")
def read_one(nid: int, db: DB = Depends(get_db), auth: Auth = Depends(get_auth)):
    db.execute(update(Notification).where(Notification.id == nid, Notification.user_id == auth.user.id).values(read_at=utcnow()))
    db.commit()
    return {"status": "ok"}


# ---------------------------------------------------------------- Telegram linking
@router.get("/telegram")
def telegram_status(db: DB = Depends(get_db), auth: Auth = Depends(get_auth)):
    acct = db.scalar(select(TelegramAccount).where(TelegramAccount.user_id == auth.user.id))
    return {"configured": bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_BOT_USERNAME), "linked": acct is not None,
            "username": acct.username if acct else None, "notifications_enabled": acct.notifications_enabled if acct else False}


@router.post("/telegram/link")
def telegram_link(db: DB = Depends(get_db), auth: Auth = Depends(get_auth)):
    if not (settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_BOT_USERNAME):
        from app.core.errors import ConfigurationRequired

        raise ConfigurationRequired("Telegram bot is not configured")
    enforce(f"tglink:{auth.user.id}", 5, 3600)
    from app.telegram.bot import create_link_code

    code = create_link_code(db, auth.user)
    db.commit()
    return {"deep_link": f"https://t.me/{settings.TELEGRAM_BOT_USERNAME}?start={code}", "expires_in_seconds": 900}


@router.post("/telegram/toggle")
def telegram_toggle(enabled: bool, db: DB = Depends(get_db), auth: Auth = Depends(get_auth)):
    acct = db.scalar(select(TelegramAccount).where(TelegramAccount.user_id == auth.user.id))
    if acct is None:
        raise NotFound("Telegram is not linked")
    acct.notifications_enabled = enabled
    db.commit()
    return {"notifications_enabled": enabled}


@router.delete("/telegram")
def telegram_unlink(db: DB = Depends(get_db), auth: Auth = Depends(get_auth)):
    acct = db.scalar(select(TelegramAccount).where(TelegramAccount.user_id == auth.user.id))
    if acct:
        db.delete(acct)
        audit(db, "telegram.unlinked", actor_id=auth.user.id, actor_type=A.CUSTOMER)
        db.commit()
    return {"status": "ok"}


# ---------------------------------------------------------------- cross-order views (own records only)
@router.get("/payments")
def my_payments(page: int = 1, db: DB = Depends(get_db), auth: Auth = Depends(get_auth)):
    from app.models import Order, Payment
    from app.schemas.serializers import payment_out

    page = max(page, 1)
    rows = db.execute(select(Payment, Order.order_number).join(Order, Order.id == Payment.order_id).where(Payment.customer_id == auth.user.id)
                      .order_by(Payment.id.desc()).offset((page - 1) * 30).limit(30)).all()
    return {"items": [{**payment_out(p), "order_number": n} for p, n in rows], "page": page}


@router.get("/deliverables")
def my_deliverables(db: DB = Depends(get_db), auth: Auth = Depends(get_auth)):
    from app.models import Attachment, Deliverable, Order
    from app.schemas.serializers import deliverable_out
    from app.services.order_state import DELIVERY_VISIBLE_STATES

    rows = db.execute(select(Deliverable, Order).join(Order, Order.id == Deliverable.order_id).where(
        Order.customer_id == auth.user.id, Deliverable.released_at.is_not(None), Order.status.in_(list(DELIVERY_VISIBLE_STATES))).order_by(Deliverable.id.desc()).limit(200)).all()
    return {"items": [{**deliverable_out(d, db.get(Attachment, d.attachment_id), staff=False), "order_id": o.id, "order_number": o.order_number, "order_title": o.title} for d, o in rows]}


@router.get("/conversations")
def my_conversations(db: DB = Depends(get_db), auth: Auth = Depends(get_auth)):
    from app.models import Conversation, Message, Order

    convs = db.execute(select(Conversation, Order).join(Order, Order.id == Conversation.order_id).where(Conversation.customer_id == auth.user.id)
                       .order_by(Conversation.last_message_at.desc().nulls_last()).limit(100)).all()
    out = []
    for c, o in convs:
        unread = db.scalar(select(func.count()).select_from(Message).where(Message.conversation_id == c.id, Message.sender_is_staff.is_(True), Message.read_by_customer_at.is_(None))) or 0
        last = db.scalar(select(Message).where(Message.conversation_id == c.id).order_by(Message.id.desc()).limit(1))
        out.append({"order_id": o.id, "order_number": o.order_number, "title": o.title, "unread": unread, "last_message": last.body[:140] if last else None, "last_message_at": iso(c.last_message_at)})
    return {"items": out}
