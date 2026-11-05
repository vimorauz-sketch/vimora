"""Request dependencies: DB session, authentication, CSRF and permission checks.

Authorization is always enforced server-side here; the frontend never decides access.
"""

from __future__ import annotations

import hmac
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, Request
from sqlalchemy.orm import Session as DB

from app.core.config import settings
from app.core.db import get_db
from app.core.errors import Forbidden, Unauthorized
from app.models import Session, User
from app.security.crypto import sha256_hex
from app.security.permissions import permissions_for
from app.security.sessions import resolve_session

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


@dataclass
class RequestCtx:
    ip: str | None
    user_agent: str | None


def get_ctx(request: Request) -> RequestCtx:
    return RequestCtx(ip=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))


@dataclass
class Auth:
    user: User
    session: Session
    permissions: set[str]

    @property
    def is_staff(self) -> bool:
        return self.user.is_staff

    def can(self, perm: str) -> bool:
        return perm in self.permissions


def _check_csrf(request: Request, session: Session) -> None:
    if request.method in SAFE_METHODS:
        return
    header = request.headers.get("x-csrf-token", "")
    if not header or not hmac.compare_digest(sha256_hex(header), session.csrf_token_hash):
        raise Forbidden("CSRF token missing or invalid", code="CSRF_FAILED")
    origin = request.headers.get("origin")
    if origin and origin.rstrip("/") not in settings.cors_origins and origin.rstrip("/") != settings.APP_URL.rstrip("/"):
        raise Forbidden("Cross-origin request rejected", code="CSRF_FAILED")


def get_optional_auth(request: Request, db: DB = Depends(get_db)) -> Auth | None:
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    resolved = resolve_session(db, token)
    if not resolved:
        return None
    session, user = resolved
    _check_csrf(request, session)
    return Auth(user=user, session=session, permissions=permissions_for(user.role_names))


def get_auth(auth: Auth | None = Depends(get_optional_auth)) -> Auth:
    if auth is None:
        raise Unauthorized("Authentication required")
    if auth.user.mfa_enabled and not auth.session.mfa_verified:
        raise Unauthorized("Multi-factor verification required", code="MFA_PENDING")
    return auth


def get_verified_auth(auth: Auth = Depends(get_auth)) -> Auth:
    if auth.user.email_verified_at is None:
        raise Forbidden("Please verify your email address first", code="EMAIL_NOT_VERIFIED")
    return auth


def get_staff(auth: Auth = Depends(get_auth)) -> Auth:
    if not auth.is_staff:
        raise Forbidden("Administrator access required")
    if settings.admin_mfa_required and not auth.session.mfa_verified:
        # admin accounts must enroll and verify MFA before any admin operation
        raise Forbidden("Multi-factor authentication is required for admin access", code="MFA_REQUIRED")
    return auth


def require(*perms: str) -> Callable[[Auth], Auth]:
    def _dep(auth: Auth = Depends(get_staff)) -> Auth:
        missing = [p for p in perms if p not in auth.permissions]
        if missing:
            raise Forbidden("You do not have permission for this action", details={"missing": missing})
        return auth

    return _dep
