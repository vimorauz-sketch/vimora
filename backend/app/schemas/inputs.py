"""Request schemas. `extra='forbid'` everywhere prevents mass-assignment of unexpected fields
(e.g. a client trying to send `status`, `price`, `customer_id` or `sender_id`)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

Lang = Literal["uz", "en", "ru"]
Currency = Literal["UZS", "USD"]
Str200 = Annotated[str, Field(min_length=1, max_length=200)]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Translatable(Strict):
    uz: str = Field("", max_length=20000)
    en: str = Field("", max_length=20000)
    ru: str = Field("", max_length=20000)


# ---------------------------------------------------------------- auth
class RegisterIn(Strict):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)
    full_name: str = Field(min_length=1, max_length=200)
    language: Lang = "uz"
    accept_terms: bool

    @field_validator("accept_terms")
    @classmethod
    def _must_accept(cls, v: bool) -> bool:
        if not v:
            raise ValueError("You must accept the Terms of Service and Privacy Policy")
        return v


class LoginIn(Strict):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class MfaCodeIn(Strict):
    code: str = Field(min_length=6, max_length=20)


class TokenIn(Strict):
    token: str = Field(min_length=10, max_length=200)


class EmailIn(Strict):
    email: EmailStr


class ResetPasswordIn(Strict):
    token: str = Field(min_length=10, max_length=200)
    password: str = Field(min_length=1, max_length=256)


class ChangePasswordIn(Strict):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=1, max_length=256)


class ProfileIn(Strict):
    full_name: str | None = Field(None, min_length=1, max_length=200)
    phone: str | None = Field(None, max_length=40)
    company: str | None = Field(None, max_length=200)
    language: Lang | None = None
    timezone: str | None = Field(None, max_length=64)


class NotificationPrefsIn(Strict):
    email: dict[str, bool] = Field(default_factory=dict)
    telegram: dict[str, bool] = Field(default_factory=dict)


class DeactivateIn(Strict):
    password: str = Field(min_length=1, max_length=256)


# ---------------------------------------------------------------- orders
class PriceQuoteIn(Strict):
    service_slug: str = Field(max_length=120)
    quantity: int = Field(1, ge=1, le=100000)
    addons: list[str] = Field(default_factory=list, max_length=20)
    promo_code: str | None = Field(None, max_length=40)
    language: Lang = "uz"


class OrderCreateIn(Strict):
    service_slug: str | None = Field(None, max_length=120)
    category_slug: str | None = Field(None, max_length=80)
    title: Str200
    description: str = Field(min_length=10, max_length=20000)
    quantity: int = Field(1, ge=1, le=100000)
    addons: list[str] = Field(default_factory=list, max_length=20)
    requirements: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    promo_code: str | None = Field(None, max_length=40)
    attachment_ids: list[int] = Field(default_factory=list, max_length=20)
    deadline: datetime | None = None
    budget_minor: int | None = Field(None, ge=0, le=10**15)
    preferred_language: Lang = "uz"
    contact_phone: str | None = Field(None, max_length=40)
    contact_telegram: str | None = Field(None, max_length=64)
    area: str | None = Field(None, max_length=80)  # ServiceArea slug chosen by the customer (no GPS)
    handover_method: Literal["PICKUP", "MEETUP"] | None = None  # LOCAL services only
    meetup_place: str | None = Field(None, max_length=300)
    meetup_time: datetime | None = None
    meetup_note: str | None = Field(None, max_length=1000)


class QuotationDecisionIn(Strict):
    quotation_id: int
    reason: str = Field("", max_length=2000)


class CancelIn(Strict):
    reason: str = Field("", max_length=1000)


class RevisionIn(Strict):
    note: str = Field(min_length=5, max_length=4000)


class ReviewIn(Strict):
    rating: int = Field(ge=1, le=5)
    text: str = Field("", max_length=3000)


class AttachFilesIn(Strict):
    attachment_ids: list[int] = Field(min_length=1, max_length=20)


class PaymentCreateIn(Strict):
    provider: Literal["CLICK", "PAYME", "STRIPE", "MANUAL"]
    pay_full: bool = False


class MessageIn(Strict):
    body: str = Field("", max_length=8000)
    attachment_ids: list[int] = Field(default_factory=list, max_length=10)


class AssistIn(Strict):
    message: str = Field(min_length=2, max_length=4000)
    history: list[dict] = Field(default_factory=list, max_length=12)
    language: Lang = "uz"
    area: str | None = Field(None, max_length=80)


class ContactIn(Strict):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    subject: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=10, max_length=5000)
    website: str = Field("", max_length=200)  # honeypot


# ---------------------------------------------------------------- admin
class LineItemIn(Strict):
    description: str = Field(min_length=1, max_length=300)
    quantity: int = Field(ge=1, le=100000)
    unit_price_minor: int = Field(ge=0, le=10**13)


class QuotationCreateIn(Strict):
    currency: Currency
    line_items: list[LineItemIn] = Field(min_length=1, max_length=50)
    discount_minor: int = Field(0, ge=0)
    extra_charges_minor: int = Field(0, ge=0)
    deposit_minor: int | None = Field(None, ge=0)
    deposit_percent: int | None = Field(None, ge=0, le=100)
    estimated_delivery_days: int | None = Field(None, ge=0, le=365)
    note: str = Field("", max_length=4000)


class StatusChangeIn(Strict):
    to_status: str = Field(max_length=40)
    message: str = Field("", max_length=2000)
    customer_visible: bool = True


class AdminNotesIn(Strict):
    admin_notes: str | None = Field(None, max_length=20000)
    customer_notes: str | None = Field(None, max_length=20000)
    deadline: datetime | None = None


class DeliverableIn(Strict):
    attachment_id: int
    title: str = Field(min_length=1, max_length=200)
    note: str = Field("", max_length=4000)


class ManualPaymentIn(Strict):
    amount_minor: int = Field(gt=0)
    reference: str = Field(min_length=3, max_length=120)
    note: str = Field("", max_length=500)


class RefundIn(Strict):
    payment_id: int
    amount_minor: int = Field(gt=0)
    reason: str = Field(min_length=3, max_length=2000)


class RefundCompleteIn(Strict):
    provider_refund_id: str = Field(min_length=1, max_length=120)


class AIStartIn(Strict):
    capability: str | None = Field(None, max_length=60)
    instructions: str | None = Field(None, max_length=8000)


class AIReviewIn(Strict):
    comment: str = Field("", max_length=4000)
    attachment_ids: list[int] = Field(default_factory=list, max_length=20)  # AI outputs to promote on approve


class CategoryIn(Strict):
    slug: str = Field(pattern=r"^[a-z0-9-]{2,80}$")
    name: Translatable
    description: Translatable = Field(default_factory=Translatable)
    icon: str = Field("sparkles", max_length=60)
    sort_order: int = 0
    is_active: bool = True


class RequiredFieldIn(Strict):
    key: str = Field(pattern=r"^[a-z0-9_]{1,40}$")
    label: Translatable
    type: Literal["text", "textarea", "number", "url", "select"] = "text"
    required: bool = True
    options: list[str] = Field(default_factory=list, max_length=50)


class TierIn(Strict):
    min_qty: int = Field(ge=1)
    unit_price_minor: int = Field(ge=0)


class AddonIn(Strict):
    key: str = Field(pattern=r"^[a-z0-9_]{1,40}$")
    label: Translatable
    price_minor: int = Field(ge=0)


class PricingIn(Strict):
    pricing_type: Literal["FIXED", "PER_UNIT", "QUANTITY_TIERED", "STARTING_FROM", "CUSTOM_QUOTE"]
    currency: Currency = "UZS"
    base_price_minor: int = Field(0, ge=0, le=10**13)
    unit_label: Translatable = Field(default_factory=Translatable)
    min_quantity: int = Field(1, ge=1)
    max_quantity: int = Field(1000, ge=1, le=100000)
    tiers: list[TierIn] = Field(default_factory=list, max_length=20)
    addons: list[AddonIn] = Field(default_factory=list, max_length=20)
    deposit_type: Literal["PERCENT", "FIXED"] = "PERCENT"
    deposit_value: int = Field(30, ge=0)


class ServiceIn(Strict):
    slug: str = Field(pattern=r"^[a-z0-9-]{2,120}$")
    category_id: int
    name: Translatable
    short_description: Translatable = Field(default_factory=Translatable)
    description: Translatable = Field(default_factory=Translatable)
    icon: str = Field("sparkles", max_length=60)
    image_attachment_id: int | None = None
    cover_image_url: str | None = Field(None, max_length=500, pattern=r"^https://(images\.)?unsplash\.com/[^\s\"'<>]+$")
    cover_image_credit: str | None = Field(None, max_length=200)
    service_mode: Literal["ONLINE", "REMOTE", "LOCAL", "FUTURE", "DISABLED"] | None = None
    service_area_id: int | None = None
    requires_file: bool = False
    estimated_delivery: Translatable = Field(default_factory=Translatable)
    estimated_hours: int | None = Field(None, ge=0, le=10000)
    required_fields: list[RequiredFieldIn] = Field(default_factory=list, max_length=30)
    allows_attachments: bool = True
    examples: list[dict] = Field(default_factory=list, max_length=10)
    is_active: bool = True
    is_featured: bool = False
    ai_eligible: bool = False
    ai_capability: str | None = Field(None, max_length=60)
    revision_limit: int = Field(2, ge=0, le=20)
    sort_order: int = 0
    pricing: PricingIn


class PromoIn(Strict):
    code: str = Field(pattern=r"^[A-Za-z0-9_-]{3,40}$")
    percent_off: int | None = Field(None, gt=0, le=100)
    amount_off_minor: int | None = Field(None, gt=0)
    currency: Currency | None = None
    max_uses: int | None = Field(None, ge=1)
    max_uses_per_user: int = Field(1, ge=1)
    min_order_minor: int = Field(0, ge=0)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    is_active: bool = True
    service_ids: list[int] = Field(default_factory=list)


class SettingsPatchIn(Strict):
    values: dict[str, object]


class AIProviderIn(Strict):
    key: Literal["anthropic", "openai", "openai_compatible"]
    display_name: str = Field(min_length=1, max_length=100)
    base_url: str | None = Field(None, max_length=300, pattern=r"^https://")
    api_key: str | None = Field(None, min_length=8, max_length=500)  # write-only
    is_enabled: bool = False


class AIModelIn(Strict):
    provider_id: int
    purpose: Literal["default", "router", "planner", "executor", "validator", "assistant"]
    model_identifier: str = Field(min_length=1, max_length=120)
    input_cost_per_mtok: float = Field(0, ge=0, le=10000)
    output_cost_per_mtok: float = Field(0, ge=0, le=10000)
    max_tokens: int = Field(4096, ge=64, le=64000)
    temperature: float = Field(0.2, ge=0, le=1)
    is_active: bool = True


class StaticPageIn(Strict):
    title: Translatable
    body: Translatable
    is_published: bool = False


class FAQIn(Strict):
    question: Translatable
    answer: Translatable
    sort_order: int = 0
    is_published: bool = True


class StaffRoleIn(Strict):
    role: Literal["SUPER_ADMIN", "ADMIN", "SUPPORT"]
    grant: bool = True


class ReviewModerationIn(Strict):
    public: bool


class HandoverProposalIn(Strict):
    place: str = Field(min_length=2, max_length=300)
    time: datetime
    note: str = Field("", max_length=1000)


class ServiceAreaIn(Strict):
    slug: str = Field(pattern=r"^[a-z0-9-]{2,80}$")
    kind: Literal["REGION", "DISTRICT", "LOCALITY", "OTHER"]
    name: Translatable
    region: str = Field("", max_length=120)
    district: str = Field("", max_length=120)
    locality: str = Field("", max_length=120)
    is_active: bool = True
    local_services_enabled: bool = False
    provider_id: int | None = None
    rules: Translatable = Field(default_factory=Translatable)
    pickup_address: str = Field("", max_length=1000)
    sort_order: int = 0
