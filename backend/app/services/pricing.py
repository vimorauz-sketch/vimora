"""Server-side pricing engine.

All amounts are integers in minor units (tiyin for UZS, cents for USD). No floats.
Client-submitted prices are never accepted; the client only sends a service, quantity,
add-on keys and an optional promo code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DB

from app.core.db import utcnow
from app.core.errors import AppError
from app.models import PromoCode, PromoCodeUsage, Service
from app.models.enums import DepositType, PricingType

MINOR_PER_MAJOR = {"UZS": 100, "USD": 100}
SUPPORTED_CURRENCIES = set(MINOR_PER_MAJOR)


@dataclass
class LineItem:
    description: str
    quantity: int
    unit_price_minor: int
    total_minor: int

    def as_dict(self) -> dict:
        return {"description": self.description, "quantity": self.quantity, "unit_price_minor": self.unit_price_minor, "total_minor": self.total_minor}


@dataclass
class PriceResult:
    currency: str
    line_items: list[LineItem] = field(default_factory=list)
    subtotal_minor: int = 0
    discount_minor: int = 0
    extra_charges_minor: int = 0
    total_minor: int = 0
    deposit_minor: int = 0
    requires_quote: bool = False  # admin must issue the quotation
    is_starting_price: bool = False
    promo_code_id: int | None = None
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "currency": self.currency,
            "line_items": [li.as_dict() for li in self.line_items],
            "subtotal_minor": self.subtotal_minor,
            "discount_minor": self.discount_minor,
            "extra_charges_minor": self.extra_charges_minor,
            "total_minor": self.total_minor,
            "deposit_minor": self.deposit_minor,
            "remaining_minor": self.total_minor - self.deposit_minor,
            "requires_quote": self.requires_quote,
            "is_starting_price": self.is_starting_price,
            "notes": self.notes,
        }


def pct_of(amount_minor: int, percent: int) -> int:
    """Integer percentage, rounded half-up to the minor unit."""
    if not 0 <= percent <= 100:
        raise ValueError("percent out of range")
    return (amount_minor * percent + 50) // 100


def round_to_major(amount_minor: int, currency: str) -> int:
    """UZS is in practice priced in whole sums; round deposits up to a whole major unit."""
    step = MINOR_PER_MAJOR.get(currency, 100)
    return -(-amount_minor // step) * step


def compute_deposit(total_minor: int, deposit_type: str, deposit_value: int, currency: str) -> int:
    if total_minor <= 0:
        return 0
    if deposit_type == DepositType.PERCENT:
        dep = round_to_major(pct_of(total_minor, int(deposit_value)), currency)
    else:
        dep = int(deposit_value)
    return max(0, min(dep, total_minor))


def _unit_label(service: Service, lang: str) -> str:
    lbl = service.pricing.unit_label if service.pricing else {}
    return lbl.get(lang) or lbl.get("en") or "unit"


def _name(service: Service, lang: str) -> str:
    return service.name.get(lang) or service.name.get("en") or service.slug


def validate_promo(db: DB, code: str, *, user_id: int, service_id: int | None, subtotal_minor: int, currency: str, now: datetime | None = None) -> PromoCode:
    now = now or utcnow()
    promo = db.scalar(select(PromoCode).where(PromoCode.code == code.strip().upper()))
    if promo is None or not promo.is_active:
        raise AppError("Promo code is not valid", code="PROMO_INVALID")
    if (promo.valid_from and now < promo.valid_from) or (promo.valid_until and now > promo.valid_until):
        raise AppError("Promo code is not currently valid", code="PROMO_EXPIRED")
    if promo.service_ids and service_id not in promo.service_ids:
        raise AppError("Promo code does not apply to this service", code="PROMO_NOT_APPLICABLE")
    if promo.amount_off_minor and promo.currency != currency:
        raise AppError("Promo code does not apply to this currency", code="PROMO_NOT_APPLICABLE")
    if subtotal_minor < promo.min_order_minor:
        raise AppError("Order total is below the promo code minimum", code="PROMO_MINIMUM")
    total_uses = db.scalar(select(func.count()).select_from(PromoCodeUsage).where(PromoCodeUsage.promo_code_id == promo.id)) or 0
    if promo.max_uses is not None and total_uses >= promo.max_uses:
        raise AppError("Promo code usage limit reached", code="PROMO_EXHAUSTED")
    user_uses = db.scalar(select(func.count()).select_from(PromoCodeUsage).where(PromoCodeUsage.promo_code_id == promo.id, PromoCodeUsage.user_id == user_id)) or 0
    if user_uses >= promo.max_uses_per_user:
        raise AppError("You have already used this promo code", code="PROMO_EXHAUSTED")
    return promo


def promo_discount(promo: PromoCode, subtotal_minor: int) -> int:
    if promo.percent_off:
        d = pct_of(subtotal_minor, promo.percent_off)
    else:
        d = int(promo.amount_off_minor or 0)
    return max(0, min(d, subtotal_minor))


def price_service(
    db: DB,
    service: Service,
    *,
    quantity: int = 1,
    addon_keys: list[str] | None = None,
    promo_code: str | None = None,
    user_id: int | None = None,
    lang: str = "en",
) -> PriceResult:
    p = service.pricing
    if p is None:
        return PriceResult(currency="UZS", requires_quote=True, notes=["No pricing configured; an administrator will prepare a quotation."])
    if quantity < p.min_quantity or quantity > p.max_quantity:
        raise AppError(f"Quantity must be between {p.min_quantity} and {p.max_quantity}", code="INVALID_QUANTITY")

    res = PriceResult(currency=p.currency)
    ptype = p.pricing_type
    if ptype == PricingType.CUSTOM_QUOTE:
        res.requires_quote = True
        res.notes.append("This service is priced individually. An administrator will send you a quotation.")
        return res

    name = _name(service, lang)
    if ptype == PricingType.FIXED:
        res.line_items.append(LineItem(name, 1, p.base_price_minor, p.base_price_minor))
    elif ptype in (PricingType.PER_UNIT, PricingType.STARTING_FROM):
        unit = p.base_price_minor
        res.line_items.append(LineItem(f"{name} ({quantity} × {_unit_label(service, lang)})", quantity, unit, unit * quantity))
        if ptype == PricingType.STARTING_FROM:
            res.is_starting_price = True
            res.requires_quote = True  # final price confirmed by the administrator
            res.notes.append("This is a starting price. The final quotation is confirmed by an administrator after review.")
    elif ptype == PricingType.QUANTITY_TIERED:
        unit = p.base_price_minor
        for tier in sorted(p.tiers or [], key=lambda t: int(t["min_qty"])):
            if quantity >= int(tier["min_qty"]):
                unit = int(tier["unit_price_minor"])
        res.line_items.append(LineItem(f"{name} ({quantity} × {_unit_label(service, lang)})", quantity, unit, unit * quantity))
    else:
        raise AppError("Unsupported pricing type", code="PRICING_ERROR")

    available = {a["key"]: a for a in (p.addons or [])}
    for key in addon_keys or []:
        addon = available.get(key)
        if addon is None:
            raise AppError(f"Unknown add-on: {key}", code="INVALID_ADDON")
        label = addon.get("label", {}).get(lang) or addon.get("label", {}).get("en") or key
        amt = int(addon["price_minor"])
        res.line_items.append(LineItem(label, 1, amt, amt))
        res.extra_charges_minor += amt

    res.subtotal_minor = sum(li.total_minor for li in res.line_items) - res.extra_charges_minor
    gross = res.subtotal_minor + res.extra_charges_minor
    if promo_code and user_id is not None:
        promo = validate_promo(db, promo_code, user_id=user_id, service_id=service.id, subtotal_minor=gross, currency=p.currency)
        res.discount_minor = promo_discount(promo, gross)
        res.promo_code_id = promo.id
    res.total_minor = gross - res.discount_minor
    res.deposit_minor = compute_deposit(res.total_minor, p.deposit_type, int(p.deposit_value), p.currency)
    return res


def build_manual_quote(line_items: list[dict], *, currency: str, discount_minor: int = 0, extra_charges_minor: int = 0, deposit_minor: int | None = None, deposit_percent: int | None = None) -> PriceResult:
    """Admin-authored quotation. Totals are always recomputed server-side from line items."""
    if currency not in SUPPORTED_CURRENCIES:
        raise AppError("Unsupported currency", code="INVALID_CURRENCY")
    items: list[LineItem] = []
    for li in line_items:
        qty, unit = int(li["quantity"]), int(li["unit_price_minor"])
        if qty <= 0 or unit < 0:
            raise AppError("Line items need a positive quantity and non-negative price", code="INVALID_LINE_ITEM")
        items.append(LineItem(str(li["description"])[:300], qty, unit, qty * unit))
    if not items:
        raise AppError("A quotation needs at least one line item", code="INVALID_LINE_ITEM")
    subtotal = sum(i.total_minor for i in items)
    if discount_minor < 0 or extra_charges_minor < 0:
        raise AppError("Discounts and charges must be non-negative", code="INVALID_AMOUNT")
    total = subtotal + extra_charges_minor - discount_minor
    if total < 0:
        raise AppError("Discount exceeds the quotation total", code="INVALID_AMOUNT")
    if deposit_minor is not None:
        if not 0 <= deposit_minor <= total:
            raise AppError("Deposit must be between 0 and the total", code="INVALID_AMOUNT")
        dep = deposit_minor
    else:
        dep = compute_deposit(total, DepositType.PERCENT, 30 if deposit_percent is None else deposit_percent, currency)
    return PriceResult(currency=currency, line_items=items, subtotal_minor=subtotal, discount_minor=discount_minor, extra_charges_minor=extra_charges_minor, total_minor=total, deposit_minor=dep)


def format_money(amount_minor: int, currency: str) -> str:
    major, minor = divmod(abs(amount_minor), MINOR_PER_MAJOR.get(currency, 100))
    sign = "-" if amount_minor < 0 else ""
    if currency == "UZS":
        return f"{sign}{major:,} UZS".replace(",", " ") if minor == 0 else f"{sign}{major:,}.{minor:02d} UZS".replace(",", " ")
    return f"{sign}${major:,}.{minor:02d}"
