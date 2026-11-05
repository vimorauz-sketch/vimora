"""AI Control Center + AI Review Dashboard endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DB

from app.ai import manager
from app.ai.capabilities import CAPABILITIES
from app.ai.providers.adapters import build_adapter
from app.ai.providers.base import AIProviderError
from app.api.deps import Auth, RequestCtx, get_ctx, get_db, require
from app.core.config import settings
from app.core.db import utcnow
from app.core.errors import Conflict, NotFound
from app.models import AIExecution, AIExecutionStep, AIModelConfiguration, AIProvider, AIReview, AIUsageRecord, Attachment, Deliverable, Order
from app.models.enums import ActorType as A
from app.models.enums import AIExecutionStatus as X
from app.models.enums import AttachmentPurpose
from app.models.enums import OrderStatus as S
from app.schemas.inputs import AIModelIn, AIProviderIn, AIReviewIn, AIStartIn
from app.schemas.serializers import attachment_out, execution_out, iso
from app.services import order_state
from app.services.audit import audit
from app.services.settings_service import get_setting
from app.security.crypto import decrypt_secret, encrypt_secret

router = APIRouter(prefix="/admin/ai", tags=["admin:ai"])


def _provider_out(p: AIProvider) -> dict:
    return {"id": p.id, "key": p.key, "display_name": p.display_name, "base_url": p.base_url, "has_api_key": bool(p.api_key_encrypted),
            "api_key_hint": f"••••{p.api_key_last4}" if p.api_key_last4 else None, "is_enabled": p.is_enabled,
            "last_health_ok": p.last_health_ok, "last_health_at": iso(p.last_health_at), "last_error": p.last_error}


def _model_out(m: AIModelConfiguration) -> dict:
    return {"id": m.id, "provider_id": m.provider_id, "purpose": m.purpose, "model_identifier": m.model_identifier, "input_cost_per_mtok": str(m.input_cost_per_mtok),
            "output_cost_per_mtok": str(m.output_cost_per_mtok), "max_tokens": m.max_tokens, "temperature": str(m.temperature), "is_active": m.is_active}


@router.get("/overview")
def overview(db: DB = Depends(get_db), auth: Auth = Depends(require("ai.view"))):
    start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    by_status = dict(db.execute(select(AIExecution.status, func.count()).group_by(AIExecution.status)).all())
    last30 = utcnow() - timedelta(days=30)
    finished = db.execute(select(AIExecution.status, func.count()).where(AIExecution.created_at >= last30, AIExecution.status.in_([X.APPROVED, X.REJECTED, X.FAILED, X.REVIEW_REQUIRED])).group_by(AIExecution.status)).all()
    fin = dict(finished)
    total_fin = sum(fin.values())
    tokens = db.execute(select(func.coalesce(func.sum(AIUsageRecord.input_tokens), 0), func.coalesce(func.sum(AIUsageRecord.output_tokens), 0)).where(AIUsageRecord.created_at >= start)).one()
    env_fallback = bool(settings.AI_PROVIDER and settings.AI_API_KEY and settings.AI_MODEL)
    return {
        "enabled": bool(get_setting(db, "ai.enabled")), "configured": manager.ai_available(db) or (env_fallback and bool(get_setting(db, "ai.enabled"))),
        "env_provider_configured": env_fallback,
        "spent_today_usd": f"{manager.spent_today(db):.4f}", "daily_budget_usd": str(get_setting(db, "ai.daily_budget_usd")),
        "per_execution_budget_usd": str(get_setting(db, "ai.per_execution_budget_usd")), "max_retries": get_setting(db, "ai.max_retries"),
        "max_executions_per_day": get_setting(db, "ai.max_executions_per_day"), "executions_today": manager.executions_today(db),
        "tokens_today": {"input": int(tokens[0]), "output": int(tokens[1])}, "by_status": by_status,
        "last_30_days": {"finished": total_fin, "approved": fin.get(X.APPROVED, 0), "failed": fin.get(X.FAILED, 0),
                         "success_rate": round(fin.get(X.APPROVED, 0) / total_fin, 3) if total_fin else None,
                         "fallback_rate": round(fin.get(X.FAILED, 0) / total_fin, 3) if total_fin else None},
        "capabilities": {k: {"description": c.description, "outputs": c.output_extensions} for k, c in CAPABILITIES.items()},
        "sandbox_enabled": settings.SANDBOX_ENABLED and bool(settings.SANDBOX_DOCKER_HOST),
    }


@router.get("/providers")
def providers(db: DB = Depends(get_db), auth: Auth = Depends(require("ai.configure"))):
    return {"providers": [_provider_out(p) for p in db.scalars(select(AIProvider).order_by(AIProvider.id))],
            "models": [_model_out(m) for m in db.scalars(select(AIModelConfiguration).order_by(AIModelConfiguration.id))]}


@router.post("/providers", status_code=201)
def upsert_provider(body: AIProviderIn, db: DB = Depends(get_db), auth: Auth = Depends(require("ai.configure")), ctx: RequestCtx = Depends(get_ctx)):
    p = db.scalar(select(AIProvider).where(AIProvider.key == body.key))
    if p is None:
        p = AIProvider(key=body.key, display_name=body.display_name)
        db.add(p)
    p.display_name, p.base_url, p.is_enabled = body.display_name, body.base_url, body.is_enabled
    if body.api_key:
        # write-only: stored encrypted, never returned
        p.api_key_encrypted = encrypt_secret(body.api_key)
        p.api_key_last4 = body.api_key[-4:]
    db.flush()
    audit(db, "ai.provider_configured", actor_id=auth.user.id, actor_type=A.ADMIN, entity_type="ai_provider", entity_id=p.id, ip=ctx.ip, data={"key": p.key, "enabled": p.is_enabled, "api_key_changed": bool(body.api_key)})
    db.commit()
    return _provider_out(p)


@router.post("/providers/{pid}/test")
def test_provider(pid: int, db: DB = Depends(get_db), auth: Auth = Depends(require("ai.configure"))):
    p = db.get(AIProvider, pid)
    if p is None:
        raise NotFound("Provider not found")
    key = decrypt_secret(p.api_key_encrypted)
    model = db.scalar(select(AIModelConfiguration).where(AIModelConfiguration.provider_id == p.id, AIModelConfiguration.is_active.is_(True)))
    if not key or model is None:
        raise Conflict("Configure an API key and at least one model first", code="CONFIGURATION_REQUIRED")
    try:
        res = build_adapter(p.key, key, p.base_url).complete(model=model.model_identifier, system="Reply with the single word OK.", user="ping", max_tokens=16, temperature=0, timeout=30)
        p.last_health_ok, p.last_error = True, None
        db.add(AIUsageRecord(purpose="health_check", provider_key=p.key, model_identifier=model.model_identifier, input_tokens=res.input_tokens, output_tokens=res.output_tokens,
                             cost_usd=manager.cost_of(manager.ModelChoice(p.key, "", None, model.model_identifier, Decimal(str(model.input_cost_per_mtok)), Decimal(str(model.output_cost_per_mtok)), 16, 0), res),
                             success=True, latency_ms=res.latency_ms, created_at=utcnow()))
        result = {"ok": True, "latency_ms": res.latency_ms, "model": res.model}
    except AIProviderError as e:
        p.last_health_ok, p.last_error = False, str(e)[:500]
        result = {"ok": False, "error": str(e)[:500]}
    p.last_health_at = utcnow()
    db.commit()
    return result


@router.post("/models", status_code=201)
def create_model(body: AIModelIn, db: DB = Depends(get_db), auth: Auth = Depends(require("ai.configure"))):
    if db.get(AIProvider, body.provider_id) is None:
        raise NotFound("Provider not found")
    m = AIModelConfiguration(**body.model_dump())
    db.add(m)
    db.flush()
    audit(db, "ai.model_configured", actor_id=auth.user.id, actor_type=A.ADMIN, entity_type="ai_model", entity_id=m.id, data={"model": m.model_identifier, "purpose": m.purpose})
    db.commit()
    return _model_out(m)


@router.put("/models/{mid}")
def update_model(mid: int, body: AIModelIn, db: DB = Depends(get_db), auth: Auth = Depends(require("ai.configure"))):
    m = db.get(AIModelConfiguration, mid)
    if m is None:
        raise NotFound("Model not found")
    for k, v in body.model_dump().items():
        setattr(m, k, v)
    audit(db, "ai.model_configured", actor_id=auth.user.id, actor_type=A.ADMIN, entity_type="ai_model", entity_id=m.id, data={"model": m.model_identifier, "purpose": m.purpose})
    db.commit()
    return _model_out(m)


@router.delete("/models/{mid}")
def delete_model(mid: int, db: DB = Depends(get_db), auth: Auth = Depends(require("ai.configure"))):
    m = db.get(AIModelConfiguration, mid)
    if m:
        db.delete(m)
        audit(db, "ai.model_deleted", actor_id=auth.user.id, actor_type=A.ADMIN, entity_type="ai_model", entity_id=mid)
        db.commit()
    return {"status": "ok"}


@router.get("/executions")
def executions(status: str | None = Query(None, max_length=30), page: int = Query(1, ge=1), db: DB = Depends(get_db), auth: Auth = Depends(require("ai.view"))):
    q = select(AIExecution, Order.order_number).join(Order, Order.id == AIExecution.order_id)
    if status:
        q = q.where(AIExecution.status.in_(status.split(",")))
    rows = db.execute(q.order_by(AIExecution.id.desc()).offset((page - 1) * 30).limit(30)).all()
    return {"items": [{**execution_out(e), "order_number": n} for e, n in rows]}


@router.get("/executions/{eid}")
def execution_detail(eid: int, db: DB = Depends(get_db), auth: Auth = Depends(require("ai.view"))):
    ex = db.get(AIExecution, eid)
    if ex is None:
        raise NotFound("Execution not found")
    order = db.get(Order, ex.order_id)
    steps = db.scalars(select(AIExecutionStep).where(AIExecutionStep.execution_id == eid).order_by(AIExecutionStep.seq)).all()
    reviews = db.scalars(select(AIReview).where(AIReview.execution_id == eid).order_by(AIReview.id)).all()
    usage = db.scalars(select(AIUsageRecord).where(AIUsageRecord.execution_id == eid).order_by(AIUsageRecord.id)).all()
    file_ids = [f["attachment_id"] for s in steps if s.stage == "EXECUTOR" for f in (s.detail or {}).get("files", [])]
    files = db.scalars(select(Attachment).where(Attachment.id.in_(file_ids))).all() if file_ids else []
    promoted = set(db.scalars(select(Deliverable.attachment_id).where(Deliverable.attachment_id.in_(file_ids)))) if file_ids else set()
    retries = db.scalars(select(AIExecution).where(AIExecution.order_id == ex.order_id).order_by(AIExecution.id)).all()
    return {
        **execution_out(ex, detail=True),
        "order": {"id": order.id, "order_number": order.order_number, "title": order.title, "description": order.description, "requirements": order.requirements, "status": order.status},
        "steps": [{"seq": s.seq, "stage": s.stage, "status": s.status, "summary": s.summary, "detail": s.detail, "created_at": iso(s.created_at)} for s in steps],
        "reviews": [{"decision": r.decision, "comment": r.comment, "reviewer_id": r.reviewer_id, "created_at": iso(r.created_at)} for r in reviews],
        "usage": [{"purpose": u.purpose, "model": u.model_identifier, "input_tokens": u.input_tokens, "output_tokens": u.output_tokens, "cost_usd": str(u.cost_usd), "success": u.success, "error": u.error, "latency_ms": u.latency_ms} for u in usage],
        "files": [{**attachment_out(a), "promoted": a.id in promoted} for a in files],
        "retry_history": [execution_out(r) for r in retries],
        "suggested_next_steps": ((ex.validation_report or {}).get("ai_requirement_review") or {}).get("suggested_next_steps", []),
    }


def _review(db: DB, ex: AIExecution, auth: Auth, decision: str, comment: str) -> None:
    db.add(AIReview(execution_id=ex.id, reviewer_id=auth.user.id, decision=decision, comment=comment, created_at=utcnow()))
    audit(db, f"ai.review_{decision.lower()}", actor_id=auth.user.id, actor_type=A.ADMIN, entity_type="ai_execution", entity_id=ex.id, data={"order_id": ex.order_id})


def _get_open(db: DB, eid: int) -> tuple[AIExecution, Order]:
    ex = db.scalar(select(AIExecution).where(AIExecution.id == eid).with_for_update())
    if ex is None:
        raise NotFound("Execution not found")
    order = db.scalar(select(Order).where(Order.id == ex.order_id).with_for_update())
    return ex, order


@router.post("/executions/{eid}/approve")
def approve(eid: int, body: AIReviewIn, db: DB = Depends(get_db), auth: Auth = Depends(require("ai.operate", "deliverables.manage"))):
    """Human approval: selected AI outputs become deliverables (not yet released to the customer)."""
    ex, order = _get_open(db, eid)
    if ex.status != X.REVIEW_REQUIRED or order.status != S.AI_REVIEW_REQUIRED:
        raise Conflict("Only executions awaiting review can be approved", code="INVALID_STATE")
    if not body.attachment_ids:
        raise Conflict("Select the output files to approve", code="NO_FILES_SELECTED")
    for aid in body.attachment_ids:
        att = db.get(Attachment, aid)
        if att is None or att.order_id != order.id or att.purpose != AttachmentPurpose.AI_OUTPUT:
            raise NotFound(f"AI output {aid} not found for this order")
        att.purpose = AttachmentPurpose.DELIVERABLE
        db.add(Deliverable(order_id=order.id, attachment_id=att.id, title=att.original_name, source="AI", ai_execution_id=ex.id, approved_by_id=auth.user.id, approved_at=utcnow(), revision_round=order.revision_count))
    ex.status = X.APPROVED
    order.ai_status = X.APPROVED
    _review(db, ex, auth, "APPROVE", body.comment)
    db.commit()
    return {"status": ex.status, "next": "Use 'Complete work' on the order to request the final payment or prepare delivery."}


@router.post("/executions/{eid}/reject")
def reject(eid: int, body: AIReviewIn, db: DB = Depends(get_db), auth: Auth = Depends(require("ai.operate"))):
    ex, order = _get_open(db, eid)
    if ex.status != X.REVIEW_REQUIRED:
        raise Conflict("Only executions awaiting review can be rejected", code="INVALID_STATE")
    ex.status = X.REJECTED
    order.ai_status = X.REJECTED
    if order.status == S.AI_REVIEW_REQUIRED:
        order_state.transition(db, order, S.MANUAL_PROCESSING, actor_type=A.ADMIN, actor_id=auth.user.id, message="Continuing with specialist", data={"execution_id": ex.id})
        order.execution_method = "MANUAL"
    _review(db, ex, auth, "REJECT", body.comment)
    db.commit()
    return {"status": ex.status}


@router.post("/executions/{eid}/revise")
def revise(eid: int, body: AIStartIn, db: DB = Depends(get_db), auth: Auth = Depends(require("ai.operate")), ctx: RequestCtx = Depends(get_ctx)):
    """Request an AI revision (new attempt with admin instructions) or a plain retry."""
    from app.ai.pipeline import start_execution
    from app.tasks.jobs import run_ai_execution

    ex, order = _get_open(db, eid)
    if ex.status not in (X.REVIEW_REQUIRED, X.FAILED, X.REJECTED, X.CANCELLED):
        raise Conflict("This execution cannot be retried now", code="INVALID_STATE")
    if ex.status == X.REVIEW_REQUIRED:
        ex.status = X.REJECTED
    _review(db, ex, auth, "REVISE" if body.instructions else "RETRY", body.instructions or "")
    new = start_execution(db, order, auth.user, capability=body.capability or ex.capability, instructions=body.instructions, ip=ctx.ip)
    db.commit()
    try:
        run_ai_execution.delay(new.id)
    except Exception:
        pass
    return {"execution_id": new.id}


@router.post("/executions/{eid}/take-over")
def take_over(eid: int, body: AIReviewIn, db: DB = Depends(get_db), auth: Auth = Depends(require("ai.operate"))):
    ex, order = _get_open(db, eid)
    if ex.status in (X.PENDING, X.PLANNING, X.RUNNING, X.VALIDATING):
        ex.cancel_requested = True
        ex.status = X.CANCELLED
    elif ex.status == X.REVIEW_REQUIRED:
        ex.status = X.REJECTED
    if order.status in (S.AI_PROCESSING, S.AI_REVIEW_REQUIRED):
        order_state.transition(db, order, S.MANUAL_PROCESSING, actor_type=A.ADMIN, actor_id=auth.user.id, message="Taken over by specialist")
    order.execution_method = "MANUAL"
    _review(db, ex, auth, "TAKE_OVER", body.comment)
    db.commit()
    return {"status": "manual"}


@router.post("/executions/{eid}/cancel")
def cancel(eid: int, body: AIReviewIn, db: DB = Depends(get_db), auth: Auth = Depends(require("ai.operate"))):
    ex, order = _get_open(db, eid)
    if ex.status not in (X.PENDING, X.PLANNING, X.RUNNING, X.VALIDATING):
        raise Conflict("Execution is not running", code="INVALID_STATE")
    ex.cancel_requested = True
    if ex.status == X.PENDING:
        ex.status = X.CANCELLED
        ex.finished_at = utcnow()
    if order.status == S.AI_PROCESSING:
        order_state.transition(db, order, S.MANUAL_PROCESSING, actor_type=A.ADMIN, actor_id=auth.user.id, message="AI execution cancelled")
        order.execution_method = "MANUAL"
    _review(db, ex, auth, "CANCEL", body.comment)
    db.commit()
    return {"status": "cancel_requested"}


@router.get("/outputs/{attachment_id}/preview")
def preview_output(attachment_id: int, db: DB = Depends(get_db), auth: Auth = Depends(require("ai.view"))):
    """Text preview for the review dashboard (returned as JSON string; rendered as text, never HTML)."""
    from app.storage.backends import get_storage

    att = db.get(Attachment, attachment_id)
    if att is None or att.purpose not in (AttachmentPurpose.AI_OUTPUT, AttachmentPurpose.DELIVERABLE) or att.size_bytes > 2_000_000:
        raise NotFound("Preview not available")
    with get_storage().open(att.storage_key) as fh:
        text = fh.read(200_000).decode("utf-8", errors="replace")
    return {"name": att.original_name, "content": text, "truncated": att.size_bytes > 200_000}
