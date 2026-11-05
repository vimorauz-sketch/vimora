from __future__ import annotations

from datetime import timedelta

import pyotp
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select, update
from sqlalchemy.orm import Session as DB

from app.api.deps import Auth, RequestCtx, get_ctx, get_db, get_optional_auth
from app.core.config import settings
from app.core.db import utcnow
from app.core.errors import AppError, Forbidden, Unauthorized
from app.core.i18n import t
from app.core.logging import get_logger
from app.models import EmailVerification, PasswordReset, Role, User, UserProfile, UserRole
from app.models.enums import ActorType as A
from app.models.enums import RoleName
from app.schemas.inputs import EmailIn, LoginIn, MfaCodeIn, RegisterIn, ResetPasswordIn, TokenIn
from app.schemas.serializers import user_public
from app.security.crypto import (
    decrypt_secret,
    hash_password,
    new_token,
    password_needs_rehash,
    sha256_hex,
    validate_password_strength,
    verify_password,
)
from app.security.rate_limit import check_login_allowed, clear_login_failures, enforce, record_login_failure
from app.security.sessions import clear_session_cookies, create_session, revoke_all_sessions, rotate_session, set_session_cookies
from app.services.audit import audit
from app.services.email import EmailDeliveryError, EmailNotConfigured, send_email
from app.services.settings_service import get_setting

router = APIRouter(prefix="/auth", tags=["auth"])
log = get_logger("auth")


def _send_verification(db: DB, user: User) -> tuple[str, str | None]:
    """Returns (delivery status, dev link). The link is returned ONLY on a local development
    install whose email goes to the dev mailbox, so the owner can test without SMTP."""
    token = new_token(32)
    db.add(EmailVerification(user_id=user.id, token_hash=sha256_hex(token), expires_at=utcnow() + timedelta(hours=settings.EMAIL_VERIFICATION_TTL_HOURS), created_at=utcnow()))
    db.commit()
    lang = user.profile.language if user.profile else "uz"
    link = f"{settings.APP_URL.rstrip('/')}/verify-email?token={token}"
    try:
        status = send_email(user.email, t("email.verify.subject", lang), t("email.verify.body", lang, link=link, hours=settings.EMAIL_VERIFICATION_TTL_HOURS), cta_url=link, cta_label="Verify")
        return status, (link if status == "LOGGED_DEV" and not settings.is_production else None)
    except EmailNotConfigured:
        log.error("Verification email not sent: email is not configured")
        return "NOT_CONFIGURED", None
    except EmailDeliveryError:
        log.error("Verification email delivery failed")
        return "FAILED", None


@router.post("/register", status_code=201)
def register(body: RegisterIn, db: DB = Depends(get_db), ctx: RequestCtx = Depends(get_ctx)):
    enforce(f"register:{ctx.ip}", 5, 3600, message="Too many registrations from this network")
    if not get_setting(db, "auth.registration_enabled"):
        raise Forbidden("Registration is currently closed", code="REGISTRATION_CLOSED")
    email = body.email.lower()
    problems = validate_password_strength(body.password, email)
    if problems:
        raise AppError("Password does not meet requirements", code="WEAK_PASSWORD", details=problems)
    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        # Do not reveal that the account exists; respond identically.
        audit(db, "auth.register_duplicate", actor_type=A.SYSTEM, ip=ctx.ip, data={"email_hash": sha256_hex(email)[:16]})
        db.commit()
        return {"status": "verification_sent", "email_delivery": "PENDING"}
    user = User(email=email, password_hash=hash_password(body.password), password_changed_at=utcnow())
    user.profile = UserProfile(full_name=body.full_name, language=body.language)
    db.add(user)
    db.flush()
    role = db.scalar(select(Role).where(Role.name == RoleName.CUSTOMER))
    if role:
        db.add(UserRole(user_id=user.id, role_id=role.id, created_at=utcnow()))
    audit(db, "auth.registered", actor_id=user.id, actor_type=A.CUSTOMER, entity_type="user", entity_id=user.id, ip=ctx.ip, user_agent=ctx.user_agent)
    db.commit()
    delivery, dev_link = _send_verification(db, user)
    out = {"status": "verification_sent", "email_delivery": "PENDING" if delivery in ("SENT", "LOGGED_DEV") else delivery}
    if dev_link:
        out["dev_verify_url"] = dev_link  # development only (see _send_verification)
    return out


@router.post("/verify-email")
def verify_email(body: TokenIn, db: DB = Depends(get_db), ctx: RequestCtx = Depends(get_ctx)):
    enforce(f"verify:{ctx.ip}", 20, 3600)
    row = db.scalar(select(EmailVerification).where(EmailVerification.token_hash == sha256_hex(body.token)).with_for_update())
    if row is None or row.used_at is not None or row.expires_at < utcnow():
        raise AppError("This verification link is invalid or has expired", code="TOKEN_INVALID")
    row.used_at = utcnow()
    user = db.get(User, row.user_id)
    if user.email_verified_at is None:
        user.email_verified_at = utcnow()
    db.execute(update(EmailVerification).where(EmailVerification.user_id == user.id, EmailVerification.used_at.is_(None)).values(used_at=utcnow()))
    audit(db, "auth.email_verified", actor_id=user.id, actor_type=A.CUSTOMER, entity_type="user", entity_id=user.id, ip=ctx.ip)
    db.commit()
    return {"status": "verified"}


@router.post("/resend-verification")
def resend_verification(body: EmailIn, db: DB = Depends(get_db), ctx: RequestCtx = Depends(get_ctx)):
    enforce(f"resend:{ctx.ip}", 5, 3600)
    enforce(f"resend-email:{body.email.lower()}", 3, 3600)
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user and user.email_verified_at is None and user.is_active:
        _, dev_link = _send_verification(db, user)
        if dev_link:
            return {"status": "ok", "dev_verify_url": dev_link}
    return {"status": "ok"}


@router.post("/login")
def login(body: LoginIn, response: Response, db: DB = Depends(get_db), ctx: RequestCtx = Depends(get_ctx)):
    email = body.email.lower()
    ip = ctx.ip or "unknown"
    check_login_allowed(email, ip)
    user = db.scalar(select(User).where(User.email == email))
    ok = verify_password(user.password_hash if user else None, body.password)
    if not ok or user is None or not user.is_active or user.deleted_at is not None:
        record_login_failure(email, ip)
        audit(db, "auth.login_failed", actor_id=user.id if user else None, actor_type=A.SYSTEM, ip=ctx.ip, user_agent=ctx.user_agent, success=False,
              data={"email_hash": sha256_hex(email)[:16], "reason": "inactive" if (ok and user and not user.is_active) else "bad_credentials"})
        db.commit()
        raise Unauthorized("Invalid email or password", code="INVALID_CREDENTIALS")
    clear_login_failures(email, ip)
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(body.password)
    session, token, csrf = create_session(db, user, ip=ctx.ip, user_agent=ctx.user_agent, mfa_verified=False)
    if not user.mfa_enabled:
        # MFA not enrolled: session is fully authenticated for customers; staff must enroll MFA.
        session.mfa_verified = not user.is_staff
    user.last_login_at = utcnow()
    audit(db, "auth.login", actor_id=user.id, actor_type=A.ADMIN if user.is_staff else A.CUSTOMER, entity_type="user", entity_id=user.id, ip=ctx.ip, user_agent=ctx.user_agent,
          data={"mfa_pending": user.mfa_enabled})
    db.commit()
    set_session_cookies(response, token, csrf, session)
    return {"user": user_public(user), "mfa_required": user.mfa_enabled, "mfa_enrollment_required": user.is_staff and not user.mfa_enabled and settings.admin_mfa_required}


def _verify_totp_or_recovery(user: User, code: str) -> bool:
    secret = decrypt_secret(user.mfa_secret_encrypted)
    code = code.replace(" ", "")
    if secret and code.isdigit() and len(code) == 6 and pyotp.TOTP(secret).verify(code, valid_window=1):
        return True
    hashes = list(user.mfa_recovery_hashes or [])
    h = sha256_hex(code.upper())
    if h in hashes:
        hashes.remove(h)
        user.mfa_recovery_hashes = hashes  # recovery codes are single-use
        return True
    return False


@router.post("/mfa/verify")
def mfa_verify(body: MfaCodeIn, request: Request, response: Response, db: DB = Depends(get_db), auth: Auth | None = Depends(get_optional_auth), ctx: RequestCtx = Depends(get_ctx)):
    if auth is None:
        raise Unauthorized("Authentication required")
    enforce(f"mfa:{auth.user.id}", 10, 300, fail_closed=True, message="Too many MFA attempts")
    if not auth.user.mfa_enabled:
        raise AppError("MFA is not enabled", code="MFA_NOT_ENABLED")
    if not _verify_totp_or_recovery(auth.user, body.code):
        audit(db, "auth.mfa_failed", actor_id=auth.user.id, actor_type=A.SYSTEM, ip=ctx.ip, success=False)
        db.commit()
        raise Unauthorized("Invalid authentication code", code="MFA_INVALID")
    session, token, csrf = rotate_session(db, auth.session, auth.user, ip=ctx.ip, user_agent=ctx.user_agent, mfa_verified=True)
    audit(db, "auth.mfa_verified", actor_id=auth.user.id, actor_type=A.ADMIN if auth.is_staff else A.CUSTOMER, ip=ctx.ip)
    db.commit()
    set_session_cookies(response, token, csrf, session)
    return {"user": user_public(auth.user)}


@router.post("/logout")
def logout(response: Response, db: DB = Depends(get_db), auth: Auth | None = Depends(get_optional_auth)):
    if auth:
        auth.session.revoked_at = utcnow()
        audit(db, "auth.logout", actor_id=auth.user.id, actor_type=A.CUSTOMER)
        db.commit()
    clear_session_cookies(response)
    return {"status": "ok"}


@router.get("/me")
def me(auth: Auth | None = Depends(get_optional_auth)):
    if auth is None:
        raise Unauthorized("Not signed in")
    mfa_pending = auth.user.mfa_enabled and not auth.session.mfa_verified
    return {
        "user": user_public(auth.user),
        "mfa_pending": mfa_pending,
        "mfa_enrollment_required": auth.is_staff and not auth.user.mfa_enabled and settings.admin_mfa_required,
        "permissions": sorted(auth.permissions) if auth.is_staff and not mfa_pending else [],
    }


@router.post("/forgot-password")
def forgot_password(body: EmailIn, db: DB = Depends(get_db), ctx: RequestCtx = Depends(get_ctx)):
    enforce(f"forgot:{ctx.ip}", 5, 3600)
    enforce(f"forgot-email:{body.email.lower()}", 3, 3600)
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user and user.is_active:
        token = new_token(32)
        db.execute(update(PasswordReset).where(PasswordReset.user_id == user.id, PasswordReset.used_at.is_(None)).values(used_at=utcnow()))
        db.add(PasswordReset(user_id=user.id, token_hash=sha256_hex(token), expires_at=utcnow() + timedelta(minutes=settings.PASSWORD_RESET_TTL_MINUTES), created_at=utcnow(), ip_address=ctx.ip))
        audit(db, "auth.password_reset_requested", actor_id=user.id, actor_type=A.SYSTEM, ip=ctx.ip)
        db.commit()
        lang = user.profile.language if user.profile else "uz"
        link = f"{settings.APP_URL.rstrip('/')}/reset-password?token={token}"
        try:
            send_email(user.email, t("email.reset.subject", lang), t("email.reset.body", lang, link=link, minutes=settings.PASSWORD_RESET_TTL_MINUTES), cta_url=link, cta_label="Reset password")
        except (EmailNotConfigured, EmailDeliveryError):
            log.error("Password reset email could not be delivered")
    # identical response whether or not the account exists
    return {"status": "ok"}


@router.post("/reset-password")
def reset_password(body: ResetPasswordIn, db: DB = Depends(get_db), ctx: RequestCtx = Depends(get_ctx)):
    enforce(f"reset:{ctx.ip}", 10, 3600)
    row = db.scalar(select(PasswordReset).where(PasswordReset.token_hash == sha256_hex(body.token)).with_for_update())
    if row is None or row.used_at is not None or row.expires_at < utcnow():
        raise AppError("This reset link is invalid or has expired", code="TOKEN_INVALID")
    user = db.get(User, row.user_id)
    problems = validate_password_strength(body.password, user.email)
    if problems:
        raise AppError("Password does not meet requirements", code="WEAK_PASSWORD", details=problems)
    row.used_at = utcnow()
    user.password_hash = hash_password(body.password)
    user.password_changed_at = utcnow()
    if user.email_verified_at is None:
        user.email_verified_at = utcnow()  # possession of the inbox is proven
    revoke_all_sessions(db, user.id)
    audit(db, "auth.password_reset", actor_id=user.id, actor_type=A.SYSTEM, ip=ctx.ip)
    db.commit()
    return {"status": "ok"}
