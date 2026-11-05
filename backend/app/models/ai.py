from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, TimestampMixin


class AIProvider(IdMixin, TimestampMixin, Base):
    __tablename__ = "ai_providers"
    key: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)  # anthropic | openai | openai_compatible
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(300))
    api_key_encrypted: Mapped[str | None] = mapped_column(Text)  # never returned by API
    api_key_last4: Mapped[str | None] = mapped_column(String(4))
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_health_ok: Mapped[bool | None] = mapped_column(Boolean)
    last_health_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class AIModelConfiguration(IdMixin, TimestampMixin, Base):
    __tablename__ = "ai_model_configurations"
    provider_id: Mapped[int] = mapped_column(ForeignKey("ai_providers.id", ondelete="CASCADE"), index=True, nullable=False)
    purpose: Mapped[str] = mapped_column(String(40), nullable=False)  # default | router | planner | executor | validator | assistant
    model_identifier: Mapped[str] = mapped_column(String(120), nullable=False)
    # USD per 1M tokens — admin configured so cost estimates match the provider's current price list
    input_cost_per_mtok: Mapped[float] = mapped_column(Numeric(12, 4), default=0, nullable=False)
    output_cost_per_mtok: Mapped[float] = mapped_column(Numeric(12, 4), default=0, nullable=False)
    max_tokens: Mapped[int] = mapped_column(Integer, default=4096, nullable=False)
    temperature: Mapped[float] = mapped_column(Numeric(3, 2), default=0.2, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AIExecution(IdMixin, TimestampMixin, Base):
    __tablename__ = "ai_executions"
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    capability: Mapped[str | None] = mapped_column(String(60))
    classification: Mapped[dict | None] = mapped_column(JSONB)
    plan: Mapped[dict | None] = mapped_column(JSONB)
    validation_report: Mapped[dict | None] = mapped_column(JSONB)
    revision_instructions: Mapped[str | None] = mapped_column(Text)
    failure_reason: Mapped[str | None] = mapped_column(Text)
    fallback_reason: Mapped[str | None] = mapped_column(Text)
    triggered_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    celery_task_id: Mapped[str | None] = mapped_column(String(80))
    input_tokens: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Numeric(12, 6), default=0, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class AIExecutionStep(IdMixin, Base):
    __tablename__ = "ai_execution_steps"
    execution_id: Mapped[int] = mapped_column(ForeignKey("ai_executions.id", ondelete="CASCADE"), index=True, nullable=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    stage: Mapped[str] = mapped_column(String(30), nullable=False)  # ROUTER | PLANNER | EXECUTOR | VALIDATOR | FALLBACK
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # OK | ERROR | SKIPPED
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    detail: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AIUsageRecord(IdMixin, Base):
    __tablename__ = "ai_usage_records"
    __table_args__ = (Index("ix_ai_usage_created", "created_at"),)
    execution_id: Mapped[int | None] = mapped_column(ForeignKey("ai_executions.id", ondelete="SET NULL"), index=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    purpose: Mapped[str] = mapped_column(String(40), nullable=False)
    provider_key: Mapped[str] = mapped_column(String(40), nullable=False)
    model_identifier: Mapped[str] = mapped_column(String(120), nullable=False)
    input_tokens: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Numeric(12, 6), default=0, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AIReview(IdMixin, Base):
    __tablename__ = "ai_reviews"
    execution_id: Mapped[int] = mapped_column(ForeignKey("ai_executions.id", ondelete="CASCADE"), index=True, nullable=False)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    decision: Mapped[str] = mapped_column(String(30), nullable=False)  # APPROVE | REJECT | REVISE | TAKE_OVER | RETRY | CANCEL
    comment: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
