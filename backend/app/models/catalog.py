from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, IdMixin, TimestampMixin


class ServiceCategory(IdMixin, TimestampMixin, Base):
    __tablename__ = "service_categories"
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    # translatable fields: {"uz": "...", "en": "...", "ru": "..."}
    name: Mapped[dict] = mapped_column(JSONB, nullable=False)
    description: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    icon: Mapped[str] = mapped_column(String(60), default="sparkles", nullable=False)  # lucide icon name
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    services: Mapped[list[Service]] = relationship(back_populates="category")


class ServiceArea(IdMixin, TimestampMixin, Base):
    """Where customers live / where LOCAL services are offered.

    `pickup_address` is private (staff only): it is never returned by public endpoints and is shown
    to a customer only on their own LOCAL pickup order once the work is ready.
    """

    __tablename__ = "service_areas"
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[dict] = mapped_column(JSONB, nullable=False)  # translatable
    region: Mapped[str] = mapped_column(String(120), default="", nullable=False)  # viloyat
    district: Mapped[str] = mapped_column(String(120), default="", nullable=False)  # tuman
    locality: Mapped[str] = mapped_column(String(120), default="", nullable=False)  # qishloq / shahar
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)  # selectable by customers
    local_services_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    provider_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))  # who serves it (future partners)
    rules: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)  # translatable public notes for this area
    pickup_address: Mapped[str] = mapped_column(Text, default="", nullable=False)  # PRIVATE
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Service(IdMixin, TimestampMixin, Base):
    __tablename__ = "services"
    __table_args__ = (CheckConstraint("service_mode IS NULL OR service_mode IN ('ONLINE','REMOTE','LOCAL','FUTURE','DISABLED')", name="mode_valid"),)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("service_categories.id", ondelete="RESTRICT"), index=True, nullable=False)
    name: Mapped[dict] = mapped_column(JSONB, nullable=False)
    short_description: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    description: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    icon: Mapped[str] = mapped_column(String(60), default="sparkles", nullable=False)
    image_attachment_id: Mapped[int | None] = mapped_column(ForeignKey("attachments.id", ondelete="SET NULL", use_alter=True))
    cover_image_url: Mapped[str | None] = mapped_column(String(500))  # default photo (Unsplash); an uploaded image wins
    cover_image_credit: Mapped[str | None] = mapped_column(String(200))
    # business model: ONLINE / REMOTE / LOCAL / FUTURE / DISABLED (NULL = legacy row, treated as ONLINE)
    service_mode: Mapped[str | None] = mapped_column(String(20), index=True)
    service_area_id: Mapped[int | None] = mapped_column(ForeignKey("service_areas.id", ondelete="RESTRICT"))  # required for LOCAL
    requires_file: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # order must include a file
    estimated_delivery: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)  # translatable text
    estimated_hours: Mapped[int | None] = mapped_column(Integer)
    # required customer fields: [{"key": "bot_name", "label": {...}, "type": "text|textarea|number|url|select", "required": true, "options": [...]}]
    required_fields: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    allows_attachments: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    examples: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)  # [{"title": {...}, "text": {...}}]
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)  # availability
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_eligible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_capability: Mapped[str | None] = mapped_column(String(60))  # allowlisted capability key
    revision_limit: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    category: Mapped[ServiceCategory] = relationship(back_populates="services", lazy="joined")
    service_area: Mapped[ServiceArea | None] = relationship(lazy="selectin")
    pricing: Mapped[ServicePricing | None] = relationship(back_populates="service", uselist=False, cascade="all, delete-orphan", lazy="joined")


class ServicePricing(IdMixin, TimestampMixin, Base):
    """Admin-configured pricing. Amounts are integer minor units (tiyin / cents)."""

    __tablename__ = "service_pricing"
    __table_args__ = (
        CheckConstraint("base_price_minor >= 0", name="base_nonneg"),
        CheckConstraint("deposit_value >= 0", name="deposit_nonneg"),
    )
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id", ondelete="CASCADE"), unique=True, nullable=False)
    pricing_type: Mapped[str] = mapped_column(String(30), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="UZS", nullable=False)
    base_price_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)  # fixed / starting / unit price
    unit_label: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)  # e.g. {"en": "page"}
    min_quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    max_quantity: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    # [{"min_qty": 10, "unit_price_minor": 9000}, ...] for QUANTITY_TIERED
    tiers: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    # [{"key": "express", "label": {...}, "price_minor": 20000}] optional add-ons
    addons: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    deposit_type: Mapped[str] = mapped_column(String(10), default="PERCENT", nullable=False)
    deposit_value: Mapped[int] = mapped_column(BigInteger, default=30, nullable=False)  # percent or minor units

    service: Mapped[Service] = relationship(back_populates="pricing")


class PromoCode(IdMixin, TimestampMixin, Base):
    __tablename__ = "promo_codes"
    __table_args__ = (CheckConstraint("percent_off IS NULL OR (percent_off > 0 AND percent_off <= 100)", name="percent_range"),)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)  # stored upper-case
    percent_off: Mapped[int | None] = mapped_column(Integer)
    amount_off_minor: Mapped[int | None] = mapped_column(BigInteger)
    currency: Mapped[str | None] = mapped_column(String(3))
    max_uses: Mapped[int | None] = mapped_column(Integer)
    max_uses_per_user: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    min_order_minor: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    service_ids: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)  # empty = all


class PromoCodeUsage(IdMixin, Base):
    __tablename__ = "promo_code_usages"
    promo_code_id: Mapped[int] = mapped_column(ForeignKey("promo_codes.id", ondelete="RESTRICT"), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), unique=True, nullable=False)
    discount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
