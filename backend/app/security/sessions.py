"""Server-side session management.

* The session token is a 256-bit random value sent only in an HttpOnly, Secure, SameSite=Lax
  cookie. The DB stores SHA-256(token) so a DB leak does not leak live sessions.
* A per-session CSRF token is delivered in a readable cookie and must be echoed in the
  X-CSRF-Token header on state-changing requests (double submit, bound to the session).
* Sessions rotate on login, privilege change (MFA verification) and password change.
"""

from __future__ import annotations

from datetime import timedelta

from fastapi import Response
from sqlalchemy import select, update
from sqlalchemy.orm import Session as DB

from app.core.config import settings
from app.core.db import utcnow
from app.models import Session, User
from app.security.crypto import new_token, sha256_hex


def _ttl_for(user: User) -> timedelta:
    hours = settings.ADMIN_SESSION_TTL_HOURS if user.is_staff else settings.SESSION_TTL_HOURS
    return timedelta(hours=hours)


def create_session(db: DB, user: User, *, ip: str | None, user_agent: str | None, mfa_verified: bool = False) -> tuple[Session, str, str]:
    token = new_token(32)
    csrf = new_token(24)
    now = utcnow()
    s = Session(
        user_id=user.id,
        token_hash=sha256_hex(token),
        csrf_token_hash=sha256_hex(csrf),
        created_at=now,
        last_seen_at=now,
        expires_at=now + _ttl_for(user),
        mfa_verified=mfa_verified,
        ip_address=ip,
        user_agent=(user_agent or "")[:400] or None,
    )
    db.add(s)
    db.flush()
    return s, token, csrf


def rotate_session(db: DB, old: Session, user: User, *, ip: str | None, user_agent: str | None, mfa_verified: bool) -> tuple[Session, str, str]:
    old.revoked_at = utcnow()
    return create_session(db, user, ip=ip, user_agent=user_agent, mfa_verified=mfa_verified)


def resolve_session(db: DB, token: str | None) -> tuple[Session, User] | None:
    if not token or len(token) > 200:
        return None
    s = db.scalar(select(Session).where(Session.token_hash == sha256_hex(token)))
    if s is None or s.revoked_at is not None:
        return None
    now = utcnow()
    if s.expires_at <= now or s.last_seen_at + timedelta(hours=settings.SESSION_IDLE_TIMEOUT_HOURS) <= now:
        return None
    user = db.get(User, s.user_id)
    if user is None or not user.is_active or user.deleted_at is not None:
        return None
    # throttle last_seen writes to once per 5 minutes
    if (now - s.last_seen_at).total_seconds() > 300:
        s.last_seen_at = now
        db.commit()
    return s, user


def revoke_all_sessions(db: DB, user_id: int, *, except_session_id: int | None = None) -> int:
    stmt = update(Session).where(Session.user_id == user_id, Session.revoked_at.is_(None))
    if except_session_id:
        stmt = stmt.where(Session.id != except_session_id)
    res = db.execute(stmt.values(revoked_at=utcnow()))
    return res.rowcount or 0


def set_session_cookies(response: Response, token: str, csrf: str, session: Session) -> None:
    max_age = int((session.expires_at - utcnow()).total_seconds())
    common = {"secure": settings.cookie_secure, "samesite": "lax", "path": "/", "max_age": max_age}
    if settings.COOKIE_DOMAIN:
        common["domain"] = settings.COOKIE_DOMAIN
    response.set_cookie(settings.SESSION_COOKIE_NAME, token, httponly=True, **common)
    response.set_cookie(settings.CSRF_COOKIE_NAME, csrf, httponly=False, **common)


def clear_session_cookies(response: Response) -> None:
    kwargs = {"path": "/"}
    if settings.COOKIE_DOMAIN:
        kwargs["domain"] = settings.COOKIE_DOMAIN
    response.delete_cookie(settings.SESSION_COOKIE_NAME, **kwargs)
    response.delete_cookie(settings.CSRF_COOKIE_NAME, **kwargs)
