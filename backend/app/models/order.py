from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, IdMixin, TimestampMixin


class Order(IdMixin, TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("total_minor >= 0", name="total_nonneg"),
        CheckConstraint("deposit_minor >= 0 AND deposit_minor <= total_minor", name="deposit_range"),
        CheckConstraint("paid_minor >= 0", name="paid_nonneg"),
        CheckConstraint("refunded_minor >= 0", name="refunded_nonneg"),
        Index("ix_orders_status_created", "status", "created_at"),
        Index("ix_orders_local_handover", "is_local", "handover_method", "handover_status"),
        CheckConstraint("handover_method IS NULL OR handover_method IN ('PICKUP','MEETUP')", name="handover_method_valid"),
        CheckConstraint("NOT is_local OR handover_method IS NOT NULL", name="local_has_handover"),
    )

    order_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False)
    service_id: Mapped[int | None] = mapped_column(ForeignKey("services.id", ondelete="RESTRICT"), index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("service_categories.id", ondelete="SET NULL"))
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    requirements: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)  # answers to required_fields
    preferred_language: Mapped[str] = mapped_column(String(5), default="uz", nullable=False)
    contact_info: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    budget_minor: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="UZS", nullable=False)
    # Money snapshot from the ACCEPTED quotation. Never recomputed from current prices.
    total_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    deposit_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    paid_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    refunded_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    payment_status: Mapped[str] = mapped_column(String(20), default="UNPAID", nullable=False)  # UNPAID|DEPOSIT_PAID|PAID|REFUNDED|PARTIALLY_REFUNDED
    accepted_quotation_id: Mapped[int | None] = mapped_column(ForeignKey("quotations.id", ondelete="SET NULL", use_alter=True))
    execution_method: Mapped[str] = mapped_column(String(20), default="UNASSIGNED", nullable=False)
    ai_status: Mapped[str | None] = mapped_column(String(30))
    admin_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)  # private, staff-only
    customer_notes: Mapped[str] = mapped_column(Text, default="", nullable=False)  # visible to customer
    revision_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ai_classification: Mapped[dict | None] = mapped_column(JSONB)
    review_rating: Mapped[int | None] = mapped_column(Integer)
    review_text: Mapped[str | None] = mapped_column(Text)
    review_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # admin-approved for display
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # optimistic concurrency
    # where the customer is (chosen manually, no GPS) and, for LOCAL orders, how the result is handed over
    service_area_id: Mapped[int | None] = mapped_column(ForeignKey("service_areas.id", ondelete="RESTRICT"), index=True)
    is_local: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    handover_method: Mapped[str | None] = mapped_column(String(10))  # PICKUP | MEETUP (LOCAL only)
    handover_status: Mapped[str | None] = mapped_column(String(30))  # see HandoverStatus; independent of status/payment
    handover: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)  # proposals, agreed place/time, history

    items: Mapped[list[OrderItem]] = relationship(back_populates="order", cascade="all, delete-orphan", lazy="selectin")
    events: Mapped[list[OrderEvent]] = relationship(back_populates="order", order_by="OrderEvent.id", lazy="raise")

    @property
    def remaining_minor(self) -> int:
        return max(self.total_minor - self.paid_minor, 0)


class OrderItem(IdMixin, Base):
    __tablename__ = "order_items"
    __table_args__ = (CheckConstraint("quantity > 0", name="qty_pos"),)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False)
    service_id: Mapped[int | None] = mapped_column(ForeignKey("services.id", ondelete="RESTRICT"))
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_price_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    addons: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    order: Mapped[Order] = relationship(back_populates="items")


class OrderEvent(IdMixin, Base):
    """Timeline entry. Append-only (enforced by DB trigger)."""

    __tablename__ = "order_events"
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(40))
    to_status: Mapped[str | None] = mapped_column(String(40))
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    customer_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)

    order: Mapped[Order] = relationship(back_populates="events")


class Quotation(IdMixin, TimestampMixin, Base):
    __tablename__ = "quotations"
    __table_args__ = (
        CheckConstraint("total_minor >= 0", name="total_nonneg"),
        CheckConstraint("deposit_minor >= 0 AND deposit_minor <= total_minor", name="deposit_range"),
    )
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    # [{"description": str, "quantity": int, "unit_price_minor": int, "total_minor": int}]
    line_items: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    subtotal_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    discount_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    extra_charges_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    total_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    deposit_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    promo_code_id: Mapped[int | None] = mapped_column(ForeignKey("promo_codes.id", ondelete="SET NULL"))
    estimated_delivery_days: Mapped[int | None] = mapped_column(Integer)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))  # None = pricing engine
    source: Mapped[str] = mapped_column(String(20), default="ADMIN", nullable=False)  # ADMIN | PRICING_ENGINE
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)


class Invoice(IdMixin, TimestampMixin, Base):
    __tablename__ = "invoices"
    invoice_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="RESTRICT"), index=True, nullable=False)
    payment_id: Mapped[int | None] = mapped_column(ForeignKey("payments.id", ondelete="RESTRICT"), unique=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ISSUED", nullable=False)  # ISSUED|PAID|VOID
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
