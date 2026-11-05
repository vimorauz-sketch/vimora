from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session as DB

from app.api.deps import Auth, RequestCtx, get_ctx, get_db, require
from app.core.db import utcnow
from app.core.errors import Conflict, NotFound
from app.models import AuditLog, Order, Payment, Role, User, UserProfile, UserRole
from app.models.enums import ActorType as A
from app.schemas.inputs import StaffRoleIn
from app.schemas.serializers import iso, order_summary, payment_out
from app.security.sessions import revoke_all_sessions
from app.services.audit import audit

router = APIRouter(prefix="/admin/customers", tags=["admin:customers"])


def _customer_row(u: User, orders: int, spent: int) -> dict:
    return {"id": u.id, "email": u.email, "full_name": u.profile.full_name if u.profile else "", "is_active": u.is_active, "email_verified": u.email_verified_at is not None,
            "roles": sorted(u.role_names), "created_at": iso(u.created_at), "last_login_at": iso(u.last_login_at), "order_count": orders, "paid_minor": spent}


@router.get("")
def list_customers(q: str | None = Query(None, max_length=100), page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), staff_only: bool = False,
                   db: DB = Depends(get_db), auth: Auth = Depends(require("customers.view"))):
    stmt = select(User).outerjoin(UserProfile).where(User.deleted_at.is_(None))
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(User.email.ilike(like), UserProfile.full_name.ilike(like), UserProfile.phone.ilike(like)))
    if staff_only:
        stmt = stmt.where(User.id.in_(select(UserRole.user_id).join(Role).where(Role.name.in_(["SUPER_ADMIN", "ADMIN", "SUPPORT"]))))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    users = db.scalars(stmt.order_by(User.id.desc()).offset((page - 1) * page_size).limit(page_size)).unique().all()
    ids = [u.id for u in users]
    counts = dict(db.execute(select(Order.customer_id, func.count()).where(Order.customer_id.in_(ids)).group_by(Order.customer_id)).all()) if ids else {}
    spent = dict(db.execute(select(Order.customer_id, func.sum(Order.paid_minor)).where(Order.customer_id.in_(ids)).group_by(Order.customer_id)).all()) if ids else {}
    return {"items": [_customer_row(u, counts.get(u.id, 0), int(spent.get(u.id) or 0)) for u in users], "total": total, "page": page}


@router.get("/{uid}")
def customer_detail(uid: int, db: DB = Depends(get_db), auth: Auth = Depends(require("customers.view"))):
    u = db.get(User, uid)
    if u is None or u.deleted_at:
        raise NotFound("Customer not found")
    orders = db.scalars(select(Order).where(Order.customer_id == uid).order_by(Order.id.desc()).limit(100)).all()
    out = _customer_row(u, len(orders), sum(o.paid_minor for o in orders))
    out.update(phone=u.profile.phone if u.profile else None, company=u.profile.company if u.profile else None, language=u.profile.language if u.profile else None,
               mfa_enabled=u.mfa_enabled, orders=[order_summary(o, staff=True) for o in orders])
    if auth.can("finance.view"):
        out["payments"] = [payment_out(p, staff=True) for p in db.scalars(select(Payment).where(Payment.customer_id == uid).order_by(Payment.id.desc()).limit(100))]
    activity = db.scalars(select(AuditLog).where(AuditLog.actor_id == uid).order_by(AuditLog.id.desc()).limit(50)).all()
    out["activity"] = [{"action": a.action, "ip": a.ip_address, "success": a.success, "created_at": iso(a.created_at)} for a in activity]
    return out


@router.post("/{uid}/disable")
def disable(uid: int, db: DB = Depends(get_db), auth: Auth = Depends(require("customers.manage")), ctx: RequestCtx = Depends(get_ctx)):
    u = db.get(User, uid)
    if u is None:
        raise NotFound("Customer not found")
    if u.id == auth.user.id or "SUPER_ADMIN" in u.role_names:
        raise Conflict("This account cannot be disabled here", code="FORBIDDEN_TARGET")
    if u.is_staff and not auth.can("staff.manage"):
        raise Conflict("Only a super administrator can disable staff", code="FORBIDDEN_TARGET")
    u.is_active = False
    u.deactivated_at = utcnow()
    revoke_all_sessions(db, u.id)
    audit(db, "customer.disabled", actor_id=auth.user.id, actor_type=A.ADMIN, entity_type="user", entity_id=u.id, ip=ctx.ip)
    db.commit()
    return {"status": "disabled"}


@router.post("/{uid}/verify-email")
def verify_email_manually(uid: int, db: DB = Depends(get_db), auth: Auth = Depends(require("customers.manage")), ctx: RequestCtx = Depends(get_ctx)):
    """Owner confirms a customer's email by hand (e.g. checked by phone) when the email didn't arrive."""
    u = db.get(User, uid)
    if u is None:
        raise NotFound("Customer not found")
    if u.email_verified_at is None:
        u.email_verified_at = utcnow()
        audit(db, "customer.email_verified_manually", actor_id=auth.user.id, actor_type=A.ADMIN, entity_type="user", entity_id=u.id, ip=ctx.ip)
        db.commit()
    return {"status": "verified"}


@router.post("/{uid}/restore")
def restore(uid: int, db: DB = Depends(get_db), auth: Auth = Depends(require("customers.manage")), ctx: RequestCtx = Depends(get_ctx)):
    u = db.get(User, uid)
    if u is None:
        raise NotFound("Customer not found")
    u.is_active = True
    u.deactivated_at = None
    audit(db, "customer.restored", actor_id=auth.user.id, actor_type=A.ADMIN, entity_type="user", entity_id=u.id, ip=ctx.ip)
    db.commit()
    return {"status": "active"}


@router.post("/{uid}/roles")
def set_role(uid: int, body: StaffRoleIn, db: DB = Depends(get_db), auth: Auth = Depends(require("staff.manage")), ctx: RequestCtx = Depends(get_ctx)):
    u = db.get(User, uid)
    if u is None:
        raise NotFound("User not found")
    if u.id == auth.user.id:
        raise Conflict("You cannot change your own roles", code="FORBIDDEN_TARGET")
    role = db.scalar(select(Role).where(Role.name == body.role))
    existing = db.get(UserRole, (u.id, role.id))
    if body.grant and existing is None:
        if u.email_verified_at is None:
            raise Conflict("Staff accounts must have a verified email", code="EMAIL_NOT_VERIFIED")
        db.add(UserRole(user_id=u.id, role_id=role.id, granted_by_id=auth.user.id, created_at=utcnow()))
    elif not body.grant and existing is not None:
        if body.role == "SUPER_ADMIN":
            remaining = db.scalar(select(func.count()).select_from(UserRole).where(UserRole.role_id == role.id)) or 0
            if remaining <= 1:
                raise Conflict("At least one super administrator must remain", code="LAST_SUPER_ADMIN")
        db.delete(existing)
    revoke_all_sessions(db, u.id)  # privilege change -> force re-authentication
    audit(db, "staff.role_changed", actor_id=auth.user.id, actor_type=A.ADMIN, entity_type="user", entity_id=u.id, ip=ctx.ip, data={"role": body.role, "grant": body.grant})
    db.commit()
    return {"status": "ok"}
