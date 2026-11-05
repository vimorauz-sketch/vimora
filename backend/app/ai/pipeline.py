"""AI task execution pipeline: Router -> Planner -> Executor -> Validator -> (admin review) / Fallback.

Runs in the background worker. Each stage commits an AIExecutionStep so the admin can follow
real progress. Any failure transfers the order to MANUAL_PROCESSING with the reason preserved
(rule 10: failed AI jobs never silently disappear). AI can never approve its own output: the
pipeline ends at REVIEW_REQUIRED and only an admin action creates customer deliverables.
"""

from __future__ import annotations

import csv
import io
import json
import re
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DB

from app.ai import manager, prompts, sandbox
from app.ai.capabilities import CAPABILITIES, MAX_INPUT_CHARS, TEXT_INPUT_MIME, Capability, get_capability
from app.ai.providers.base import AIProviderError
from app.core.db import utcnow
from app.core.errors import AppError, ConfigurationRequired, Conflict
from app.core.i18n import pick
from app.core.logging import get_logger
from app.models import AIExecution, AIExecutionStep, Attachment, Order, OrderEvent, Service, User
from app.models.enums import ActorType as A
from app.models.enums import AIExecutionStatus as X
from app.models.enums import AttachmentPurpose, ExecutionMethod
from app.models.enums import OrderStatus as S
from app.services import order_state
from app.services.audit import audit
from app.services.notifications import notify_admins
from app.services.settings_service import get_setting
from app.storage.backends import get_storage

log = get_logger("ai.pipeline")
SAFE_NAME = re.compile(r"^[A-Za-z0-9_\-]+(/[A-Za-z0-9_\-]+)?\.[A-Za-z0-9]{1,8}$")


class StageFailure(Exception):
    def __init__(self, stage: str, reason: str):
        super().__init__(reason)
        self.stage = stage
        self.reason = reason


class Cancelled(Exception):
    pass


# ---------------------------------------------------------------------------------- start
def start_execution(db: DB, order: Order, admin: User | None, *, capability: str | None = None, instructions: str | None = None, ip: str | None = None) -> AIExecution:
    if not get_setting(db, "ai.enabled"):
        raise ConfigurationRequired("AI processing is disabled in the AI Control Center")
    try:
        manager.resolve_model(db, "executor")
    except ConfigurationRequired:
        raise
    if order.status not in (S.QUEUED, S.MANUAL_PROCESSING, S.REVISION_REQUESTED, S.AI_REVIEW_REQUIRED):
        raise Conflict("AI can only be started for queued or in-progress orders", code="INVALID_STATE")
    svc = db.get(Service, order.service_id) if order.service_id else None
    cap = capability or (svc.ai_capability if svc and svc.ai_eligible else None)
    if cap is not None and cap not in CAPABILITIES:
        raise AppError("Unknown AI capability", code="UNKNOWN_CAPABILITY")
    if svc and not svc.ai_eligible and not capability:
        raise Conflict("This service is not enabled for AI processing", code="AI_NOT_ELIGIBLE")
    previous = db.scalar(select(func.count()).select_from(AIExecution).where(AIExecution.order_id == order.id)) or 0
    max_retries = int(get_setting(db, "ai.max_retries"))
    if previous > max_retries + 3:  # hard ceiling on attempts per order (initial + retries + revisions)
        raise Conflict("Maximum number of AI attempts for this order reached", code="AI_ATTEMPTS_EXCEEDED")
    if manager.executions_today(db) >= int(get_setting(db, "ai.max_executions_per_day")):
        raise Conflict("Daily AI execution limit reached", code="AI_DAILY_LIMIT")
    try:
        manager.check_budget(db)
    except manager.BudgetExceeded as e:
        raise Conflict(str(e), code="AI_BUDGET_EXCEEDED") from None

    ex = AIExecution(order_id=order.id, attempt=previous + 1, status=X.PENDING, capability=cap, revision_instructions=(instructions or "")[:8000] or None,
                     triggered_by_id=admin.id if admin else None)
    db.add(ex)
    db.flush()
    order_state.transition(db, order, S.AI_PROCESSING, actor_type=A.ADMIN if admin else A.SYSTEM, actor_id=admin.id if admin else None, ip=ip,
                           data={"execution_id": ex.id}, message="Processing started")
    order.execution_method = ExecutionMethod.AI
    order.ai_status = X.PENDING
    audit(db, "ai.execution_started", actor_id=admin.id if admin else None, actor_type=A.ADMIN if admin else A.SYSTEM, entity_type="ai_execution", entity_id=ex.id, ip=ip, data={"order_id": order.id, "capability": cap})
    notify_admins(db, "ai.started", key_suffix=str(ex.id), title="AI EXECUTION STARTED", lines=[("Order", f"#{order.order_number}"), ("Attempt", str(ex.attempt)), ("Capability", cap or "auto")], order=order)
    return ex


# ------------------------------------------------------------------------------- helpers
def _step(db: DB, ex: AIExecution, stage: str, status: str, summary: str, detail: dict | None = None) -> None:
    seq = (db.scalar(select(func.max(AIExecutionStep.seq)).where(AIExecutionStep.execution_id == ex.id)) or 0) + 1
    db.add(AIExecutionStep(execution_id=ex.id, seq=seq, stage=stage, status=status, summary=summary[:2000], detail=detail or {}, created_at=utcnow()))


def _check_cancel(db: DB, ex: AIExecution) -> None:
    db.refresh(ex, ["cancel_requested"])
    order = db.get(Order, ex.order_id)
    db.refresh(order, ["status"])
    if ex.cancel_requested or order.status != S.AI_PROCESSING:
        raise Cancelled()


def _gather_inputs(db: DB, order: Order, ex: AIExecution) -> str:
    parts = [f"Title: {order.title}", f"Description:\n{order.description}"]
    if order.requirements:
        parts.append("Answers to service questions:\n" + "\n".join(f"- {k}: {v}" for k, v in order.requirements.items()))
    budget = MAX_INPUT_CHARS - sum(len(p) for p in parts)
    atts = db.scalars(select(Attachment).where(Attachment.order_id == order.id, Attachment.purpose.in_([AttachmentPurpose.ORDER_INPUT, AttachmentPurpose.MESSAGE]), Attachment.deleted_at.is_(None)))
    storage = get_storage()
    for a in atts:
        if a.mime_type in TEXT_INPUT_MIME and budget > 500:
            with storage.open(a.storage_key) as fh:
                text = fh.read(min(budget, 200_000)).decode("utf-8", errors="replace")
            parts.append(f"File {a.original_name}:\n{text[:budget]}")
            budget -= len(text)
        else:
            parts.append(f"File {a.original_name} ({a.mime_type}) is attached but cannot be read by the AI.")
    revision_notes = db.scalars(select(OrderEvent.message).where(OrderEvent.order_id == order.id, OrderEvent.to_status == S.REVISION_REQUESTED).order_by(OrderEvent.id.desc()).limit(1)).first()
    body = prompts.wrap_untrusted("customer_order", "\n\n".join(parts))
    if revision_notes:
        body += "\n\n" + prompts.wrap_untrusted("customer_revision_request", revision_notes)
    if ex.revision_instructions:
        body += f"\n\nAdministrator instructions (trusted):\n{ex.revision_instructions}"
    return body


def _catalog(db: DB) -> str:
    rows = db.scalars(select(Service).where(Service.is_active.is_(True), Service.archived_at.is_(None)).limit(200))
    return "; ".join(f"{s.slug}: {pick(s.name, 'en')}" for s in rows)


def _sanitize_files(cap: Capability, files: object) -> dict[str, str]:
    if not isinstance(files, list) or not files:
        raise StageFailure("EXECUTOR", "The model returned no files")
    if len(files) > cap.max_files:
        raise StageFailure("EXECUTOR", f"Too many files ({len(files)} > {cap.max_files})")
    out: dict[str, str] = {}
    for f in files:
        if not isinstance(f, dict):
            raise StageFailure("EXECUTOR", "Malformed file entry")
        name, content = str(f.get("filename", "")), f.get("content")
        if not SAFE_NAME.match(name) or ".." in name:
            raise StageFailure("EXECUTOR", f"Unsafe file name rejected: {name[:80]}")
        if name.rsplit(".", 1)[-1].lower() not in cap.output_extensions:
            raise StageFailure("EXECUTOR", f"File type not allowed for this capability: {name}")
        if not isinstance(content, str) or len(content.encode()) > cap.max_file_bytes:
            raise StageFailure("EXECUTOR", f"File too large or invalid: {name}")
        out[name] = content
    return out


def deterministic_checks(cap: Capability, files: dict[str, str]) -> list[dict]:
    results: list[dict] = []
    for v in cap.validators:
        if v == "non_empty":
            empty = [n for n, c in files.items() if not c.strip()]
            results.append({"check": "non_empty", "passed": not empty, "detail": f"Empty files: {empty}" if empty else "All files have content"})
        elif v == "min_length":
            total = sum(len(c) for c in files.values())
            results.append({"check": "min_length", "passed": total >= 50, "detail": f"{total} characters"})
        elif v == "python_syntax":
            import ast

            bad = []
            for n, c in files.items():
                if n.endswith(".py"):
                    try:
                        ast.parse(c)  # parse only; never executed here
                    except SyntaxError as e:
                        bad.append(f"{n}:{e.lineno}: {e.msg}")
            results.append({"check": "python_syntax", "passed": not bad, "detail": "; ".join(bad) or "OK"})
        elif v == "json_parses":
            bad = []
            for n, c in files.items():
                if n.endswith(".json"):
                    try:
                        json.loads(c)
                    except json.JSONDecodeError as e:
                        bad.append(f"{n}: {e.msg}")
            results.append({"check": "json_parses", "passed": not bad, "detail": "; ".join(bad) or "OK"})
        elif v == "csv_or_json_parses":
            bad = []
            for n, c in files.items():
                try:
                    if n.endswith(".json"):
                        json.loads(c)
                    elif n.endswith(".csv"):
                        rows = list(csv.reader(io.StringIO(c)))
                        if not rows:
                            raise ValueError("no rows")
                except (ValueError, csv.Error) as e:
                    bad.append(f"{n}: {e}")
            results.append({"check": "csv_or_json_parses", "passed": not bad, "detail": "; ".join(bad) or "OK"})
        elif v == "sandbox_python":
            py = {n: c for n, c in files.items() if n.endswith(".py")}
            if py:
                r = sandbox.run_python_compile_check(py)
                results.append({"check": "sandbox_python", "passed": r["status"] in ("PASSED", "SKIPPED"), "skipped": r["status"] == "SKIPPED", "detail": r})
    return results


def _fallback(db: DB, ex: AIExecution, order: Order, stage: str, reason: str) -> None:
    manager.sync_execution_totals(db, ex)
    ex.status = X.FAILED
    ex.failure_reason = f"[{stage}] {reason}"[:4000]
    ex.fallback_reason = reason[:4000]
    ex.finished_at = utcnow()
    _step(db, ex, "FALLBACK", "OK", f"Transferred to manual processing: {reason}")
    db.refresh(order, ["status"])
    if order.status == S.AI_PROCESSING:
        order_state.transition(db, order, S.MANUAL_PROCESSING, actor_type=A.AI, message="Transferred to specialist", customer_visible=True,
                               data={"execution_id": ex.id, "reason": reason[:500]})
    order.execution_method = ExecutionMethod.MANUAL
    order.ai_status = X.FAILED
    audit(db, "ai.execution_failed", actor_type=A.AI, entity_type="ai_execution", entity_id=ex.id, success=False, data={"stage": stage, "reason": reason[:500]})
    notify_admins(db, "ai.failed", key_suffix=str(ex.id), title="AI EXECUTION FAILED — MANUAL HANDLING REQUIRED",
                  lines=[("Order", f"#{order.order_number}"), ("Stage", stage), ("Reason", reason[:150])], order=order)
    db.commit()


# --------------------------------------------------------------------------------- main
def run(db: DB, execution_id: int) -> str:
    ex = db.scalar(select(AIExecution).where(AIExecution.id == execution_id).with_for_update(skip_locked=True))
    if ex is None or ex.status != X.PENDING:
        return "SKIPPED"
    order = db.get(Order, ex.order_id)
    customer = db.get(User, order.customer_id)
    lang = order.preferred_language
    ex.started_at = utcnow()
    db.commit()
    stage = "ROUTER"
    try:
        _check_cancel(db, ex)
        task_input = _gather_inputs(db, order, ex)

        # ---- ROUTER
        ex.status = X.PLANNING
        order.ai_status = X.PLANNING
        caps_desc = ", ".join(f"{k} ({c.description})" for k, c in CAPABILITIES.items())
        res = manager.call(db, purpose="router", system=prompts.ROUTER.format(capabilities=caps_desc, catalog=_catalog(db)), user=task_input, execution=ex, order_id=order.id, max_tokens=1200)
        try:
            cls = manager.parse_json(res.text)
        except (ValueError, json.JSONDecodeError):
            raise StageFailure("ROUTER", "Router returned unparseable output") from None
        ex.classification = cls
        order.ai_classification = cls
        if cls.get("policy_flag"):
            raise StageFailure("ROUTER", f"Flagged for human review: {cls.get('automation_reason', '')}")
        cap = get_capability(ex.capability or cls.get("capability"))
        if cap is None or not cls.get("automatable", False) and ex.capability is None:
            raise StageFailure("ROUTER", f"Not automatable: {cls.get('automation_reason') or 'no matching capability'}")
        ex.capability = cap.key
        _step(db, ex, "ROUTER", "OK", f"Capability: {cap.key}; complexity {cls.get('complexity')}", {"classification": cls})
        db.commit()
        _check_cancel(db, ex)

        # ---- PLANNER
        stage = "PLANNER"
        res = manager.call(db, purpose="planner", system=prompts.PLANNER.format(capability=cap.key, capability_description=cap.description, extensions=", ".join(cap.output_extensions), max_files=cap.max_files),
                           user=task_input, execution=ex, order_id=order.id, max_tokens=2000)
        try:
            plan = manager.parse_json(res.text)
        except (ValueError, json.JSONDecodeError):
            raise StageFailure("PLANNER", "Planner returned unparseable output") from None
        if not plan.get("feasible", False):
            raise StageFailure("PLANNER", f"Planner judged task infeasible: {plan.get('infeasible_reason')}")
        ex.plan = plan
        _step(db, ex, "PLANNER", "OK", f"{len(plan.get('steps', []))} steps, {len(plan.get('deliverables', []))} deliverables", {"plan": plan})
        db.commit()
        _check_cancel(db, ex)

        # ---- EXECUTOR
        stage = "EXECUTOR"
        ex.status = X.RUNNING
        order.ai_status = X.RUNNING
        exec_user = task_input + "\n\nApproved plan (trusted, produced by the planner):\n" + json.dumps(plan, ensure_ascii=False)[:20000]
        res = manager.call(db, purpose="executor", system=prompts.EXECUTOR.format(capability=cap.key, extensions=", ".join(cap.output_extensions), max_files=cap.max_files, language={"uz": "Uzbek", "en": "English", "ru": "Russian"}.get(lang, "Uzbek")),
                           user=exec_user, execution=ex, order_id=order.id)
        try:
            out = manager.parse_json(res.text)
        except (ValueError, json.JSONDecodeError):
            raise StageFailure("EXECUTOR", "Executor returned unparseable output") from None
        files = _sanitize_files(cap, out.get("files"))
        stored = []
        for name, content in files.items():
            att = _store_generated(db, order, name, content)
            stored.append({"attachment_id": att.id, "filename": name, "bytes": att.size_bytes})
        _step(db, ex, "EXECUTOR", "OK", f"Generated {len(stored)} file(s)", {"files": stored, "notes": str(out.get("notes", ""))[:2000]})
        db.commit()
        _check_cancel(db, ex)

        # ---- VALIDATOR
        stage = "VALIDATOR"
        ex.status = X.VALIDATING
        order.ai_status = X.VALIDATING
        checks = deterministic_checks(cap, files)
        file_dump = "\n\n".join(f"=== {n} ===\n{c[:15000]}" for n, c in files.items())
        res = manager.call(db, purpose="validator", system=prompts.VALIDATOR, user=task_input + "\n\nProduced files:\n" + prompts.wrap_untrusted("generated_output", file_dump),
                           execution=ex, order_id=order.id, max_tokens=1500)
        try:
            review = manager.parse_json(res.text)
        except (ValueError, json.JSONDecodeError):
            review = {"overall_pass": False, "issues": ["Validator output unparseable"], "requirements": []}
        reqs = review.get("requirements") or []
        met = sum(1 for r in reqs if isinstance(r, dict) and r.get("met"))
        report = {
            "deterministic_checks": checks,
            "deterministic_passed": all(c["passed"] for c in checks),
            "ai_requirement_review": review,
            "requirements_met": f"{met}/{len(reqs)}" if reqs else "n/a",
            # an AI self-assessment, not a calibrated confidence score
            "note": "Requirement coverage is the model's own assessment and must be verified by the administrator.",
            "sandbox": "enabled" if sandbox.enabled() else "not configured (code was not executed)",
        }
        ex.validation_report = report
        _step(db, ex, "VALIDATOR", "OK" if report["deterministic_passed"] else "ERROR", f"Deterministic checks {'passed' if report['deterministic_passed'] else 'FAILED'}; requirements {report['requirements_met']}", report)
        db.commit()
        _check_cancel(db, ex)

        # ---- hand over to the administrator (never auto-approved)
        ex.status = X.REVIEW_REQUIRED
        ex.finished_at = utcnow()
        order.ai_status = X.REVIEW_REQUIRED
        order_state.transition(db, order, S.AI_REVIEW_REQUIRED, actor_type=A.AI, data={"execution_id": ex.id}, message="Quality review")
        notify_admins(db, "ai.completed", key_suffix=str(ex.id), title="AI EXECUTION COMPLETED",
                      lines=[("Order", f"#{order.order_number}"), ("Files", str(len(stored))), ("Checks", "passed" if report["deterministic_passed"] else "FAILED"), ("Cost", f"${Decimal(str(ex.cost_usd)):.4f}")], order=order)
        notify_admins(db, "review.required", key_suffix=str(ex.id), title="MANUAL REVIEW REQUIRED", lines=[("Order", f"#{order.order_number}")], order=order)
        db.commit()
        return X.REVIEW_REQUIRED
    except Cancelled:
        db.rollback()
        ex = db.get(AIExecution, execution_id)
        ex.status = X.CANCELLED
        ex.finished_at = utcnow()
        _step(db, ex, stage, "SKIPPED", "Execution cancelled")
        db.commit()
        return X.CANCELLED
    except StageFailure as e:
        db.rollback()
        _step(db, db.get(AIExecution, execution_id), e.stage, "ERROR", e.reason)
        _fallback(db, db.get(AIExecution, execution_id), db.get(Order, order.id), e.stage, e.reason)
        return X.FAILED
    except (AIProviderError, manager.BudgetExceeded, manager.AIDisabled, ConfigurationRequired) as e:
        db.rollback()
        _step(db, db.get(AIExecution, execution_id), stage, "ERROR", str(e))
        _fallback(db, db.get(AIExecution, execution_id), db.get(Order, order.id), stage, str(e))
        return X.FAILED
    except Exception as e:  # unexpected: still fall back, never lose the job
        log.exception("AI pipeline crashed")
        db.rollback()
        _step(db, db.get(AIExecution, execution_id), stage, "ERROR", f"Internal error: {type(e).__name__}")
        _fallback(db, db.get(AIExecution, execution_id), db.get(Order, order.id), stage, f"Internal error: {type(e).__name__}")
        return X.FAILED
    finally:
        _ = customer  # customer data is only read via the order's own inputs


def _store_generated(db: DB, order: Order, name: str, content: str) -> Attachment:
    """AI output is stored privately (staff-only) without the user upload validator's MIME sniffing."""
    import hashlib

    from app.security.crypto import new_token

    data = content.encode()
    key = f"ai_output/{utcnow():%Y/%m}/{new_token(24)}"
    get_storage().put(key, data, "application/octet-stream")
    att = Attachment(owner_id=None, order_id=order.id, purpose=AttachmentPurpose.AI_OUTPUT, storage_key=key, original_name=name.replace("/", "__"),
                     mime_type="text/plain", size_bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), scan_status="NOT_SCANNED", created_at=utcnow())
    db.add(att)
    db.flush()
    return att
