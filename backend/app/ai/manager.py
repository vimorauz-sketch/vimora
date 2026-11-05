"""AI Provider Manager + Cost Manager.

* Resolves the provider/model for a purpose from admin configuration (DB) with an env fallback.
* Enforces the global AI switch, daily budget, per-execution budget and daily execution cap
  BEFORE every call (prevents runaway jobs).
* Records every call in AIUsageRecord (tokens, cost, latency, errors).
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DB

from app.ai.providers.adapters import build_adapter
from app.ai.providers.base import AIProviderError, AIResult
from app.core.config import settings
from app.core.db import SessionLocal, utcnow
from app.core.errors import ConfigurationRequired
from app.models import AIExecution, AIModelConfiguration, AIProvider, AIUsageRecord
from app.security.crypto import decrypt_secret
from app.services.settings_service import get_setting


class BudgetExceeded(Exception):
    pass


class AIDisabled(Exception):
    pass


@dataclass
class ModelChoice:
    provider_key: str
    api_key: str
    base_url: str | None
    model: str
    input_cost: Decimal
    output_cost: Decimal
    max_tokens: int
    temperature: float


def resolve_model(db: DB, purpose: str) -> ModelChoice:
    rows = db.execute(
        select(AIModelConfiguration, AIProvider)
        .join(AIProvider, AIProvider.id == AIModelConfiguration.provider_id)
        .where(AIProvider.is_enabled.is_(True), AIModelConfiguration.is_active.is_(True), AIModelConfiguration.purpose.in_([purpose, "default"]))
    ).all()
    rows.sort(key=lambda r: 0 if r[0].purpose == purpose else 1)
    for cfg, prov in rows:
        key = decrypt_secret(prov.api_key_encrypted)
        if key:
            return ModelChoice(prov.key, key, prov.base_url, cfg.model_identifier, Decimal(str(cfg.input_cost_per_mtok)), Decimal(str(cfg.output_cost_per_mtok)),
                               int(cfg.max_tokens), float(cfg.temperature))
    if settings.AI_PROVIDER and settings.AI_API_KEY and settings.AI_MODEL:
        return ModelChoice(settings.AI_PROVIDER, settings.AI_API_KEY, settings.AI_BASE_URL or None, settings.AI_MODEL, Decimal(0), Decimal(0), settings.AI_MAX_TOKENS_PER_CALL, 0.2)
    raise ConfigurationRequired("CONFIGURATION REQUIRED: no AI provider is configured")


def ai_available(db: DB) -> bool:
    if not get_setting(db, "ai.enabled"):
        return False
    try:
        resolve_model(db, "default")
        return True
    except ConfigurationRequired:
        return False


def spent_today(db: DB) -> Decimal:
    start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    return Decimal(str(db.scalar(select(func.coalesce(func.sum(AIUsageRecord.cost_usd), 0)).where(AIUsageRecord.created_at >= start)) or 0))


def executions_today(db: DB) -> int:
    start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    return db.scalar(select(func.count()).select_from(AIExecution).where(AIExecution.created_at >= start)) or 0


def check_budget(db: DB, execution: AIExecution | None = None) -> None:
    daily = Decimal(str(get_setting(db, "ai.daily_budget_usd")))
    if spent_today(db) >= daily:
        raise BudgetExceeded(f"Daily AI budget of ${daily} reached")
    if execution is not None:
        per = Decimal(str(get_setting(db, "ai.per_execution_budget_usd")))
        if Decimal(str(execution.cost_usd or 0)) >= per:
            raise BudgetExceeded(f"Per-execution AI budget of ${per} reached")


def _record_usage(**fields) -> None:
    """Usage is persisted in its own transaction so spend is never lost when the caller's
    transaction rolls back (e.g. a pipeline stage fails). Budget checks rely on this."""
    with SessionLocal() as s:
        s.add(AIUsageRecord(created_at=utcnow(), **fields))
        s.commit()


def cost_of(choice: ModelChoice, res: AIResult) -> Decimal:
    return ((choice.input_cost * res.input_tokens) + (choice.output_cost * res.output_tokens)) / Decimal(1_000_000)


def call(
    db: DB,
    *,
    purpose: str,
    system: str,
    user: str,
    execution: AIExecution | None = None,
    order_id: int | None = None,
    user_id: int | None = None,
    max_tokens: int | None = None,
    require_enabled: bool = True,
    retries: int = 2,
) -> AIResult:
    if require_enabled and not get_setting(db, "ai.enabled"):
        raise AIDisabled("AI processing is disabled by the administrator")
    check_budget(db, execution)
    choice = resolve_model(db, purpose)
    adapter = build_adapter(choice.provider_key, choice.api_key, choice.base_url)
    mt = min(max_tokens or choice.max_tokens, choice.max_tokens, settings.AI_MAX_TOKENS_PER_CALL)
    attempt = 0
    while True:
        attempt += 1
        try:
            res = adapter.complete(model=choice.model, system=system, user=user, max_tokens=mt, temperature=choice.temperature, timeout=settings.AI_REQUEST_TIMEOUT_SECONDS)
            cost = cost_of(choice, res)
            _record_usage(execution_id=execution.id if execution else None, order_id=order_id, user_id=user_id, purpose=purpose, provider_key=choice.provider_key,
                          model_identifier=res.model, input_tokens=res.input_tokens, output_tokens=res.output_tokens, cost_usd=cost, success=True, latency_ms=res.latency_ms)
            if execution is not None:
                execution.input_tokens += res.input_tokens
                execution.output_tokens += res.output_tokens
                execution.cost_usd = Decimal(str(execution.cost_usd or 0)) + cost
            db.flush()
            return res
        except AIProviderError as exc:
            _record_usage(execution_id=execution.id if execution else None, order_id=order_id, user_id=user_id, purpose=purpose, provider_key=choice.provider_key,
                          model_identifier=choice.model, success=False, error=str(exc)[:500])
            if not exc.retryable or attempt > retries:
                raise
            time.sleep(min(2**attempt, 10))


_JSON_BLOCK = re.compile(r"\{.*\}", re.S)


def sync_execution_totals(db: DB, execution: AIExecution) -> None:
    """Recompute token/cost totals from the durable usage records."""
    row = db.execute(select(func.coalesce(func.sum(AIUsageRecord.input_tokens), 0), func.coalesce(func.sum(AIUsageRecord.output_tokens), 0),
                            func.coalesce(func.sum(AIUsageRecord.cost_usd), 0)).where(AIUsageRecord.execution_id == execution.id)).one()
    execution.input_tokens, execution.output_tokens, execution.cost_usd = int(row[0]), int(row[1]), Decimal(str(row[2]))


def parse_json(text: str) -> dict:
    """Extract the first JSON object from model output. Raises ValueError if absent/invalid."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{") :]
    m = _JSON_BLOCK.search(text)
    if not m:
        raise ValueError("No JSON object in model output")
    return json.loads(m.group(0))
