from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, TimestampMixin


class Payment(IdMixin, TimestampMixin, Base):
    """A payment attempt for an order.

    The amount is fixed at creation from the order's server-side balance and is the
    amount the provider callback must match. Status changes are recorded in
    PaymentEvent (append-only, DB-enforced).
    """

    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount_minor > 0", name="amount_pos"),
        UniqueConstraint("provider", "provider_transaction_id", name="uq_payments_provider_txn"),
    )
    reference: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)  # public id sent to providers
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="RESTRICT"), index=True, nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    provider_transaction_id: Mapped[str | None] = mapped_column(String(120))
    provider_state: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)  # e.g. payme state/time fields
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_reason: Mapped[str | None] = mapped_column(Text)
    recorded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))  # manual payments


class PaymentEvent(IdMixin, Base):
    """Immutable payment history (UPDATE/DELETE blocked by trigger)."""

    __tablename__ = "payment_events"
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id", ondelete="RESTRICT"), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(20))
    to_status: Mapped[str | None] = mapped_column(String(20))
    provider_event_id: Mapped[str | None] = mapped_column(String(160))
    data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProcessedWebhookEvent(IdMixin, Base):
    """Replay protection for provider webhooks (unique provider+event id)."""

    __tablename__ = "processed_webhook_events"
    __table_args__ = (UniqueConstraint("provider", "event_id", name="uq_processed_webhook"),)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    event_id: Mapped[str] = mapped_column(String(160), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Refund(IdMixin, TimestampMixin, Base):
    __tablename__ = "refunds"
    __table_args__ = (CheckConstraint("amount_minor > 0", name="amount_pos"),)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="RESTRICT"), index=True, nullable=False)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id", ondelete="RESTRICT"), index=True, nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    requested_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    processed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    provider_refund_id: Mapped[str | None] = mapped_column(String(120))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
