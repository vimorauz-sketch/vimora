"""Provider adapters: checkout creation and availability. Webhook handlers live in api/v1/payments.py.

Each adapter reports `configured()`; the UI disables unconfigured providers and the API refuses
to create payments for them. No adapter ever simulates success.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.core.errors import AppError, ConfigurationRequired
from app.models import Payment
from app.models.enums import PaymentProvider


@dataclass
class Checkout:
    redirect_url: str | None
    instructions: str | None = None


def _major_str(amount_minor: int) -> str:
    major, minor = divmod(amount_minor, 100)
    return f"{major}.{minor:02d}"


class ClickAdapter:
    key = PaymentProvider.CLICK
    currencies = {"UZS"}

    def configured(self) -> bool:
        return bool(settings.CLICK_MERCHANT_ID and settings.CLICK_SERVICE_ID and settings.CLICK_SECRET_KEY)

    def checkout(self, p: Payment, return_url: str) -> Checkout:
        from urllib.parse import urlencode

        q = urlencode({
            "service_id": settings.CLICK_SERVICE_ID, "merchant_id": settings.CLICK_MERCHANT_ID,
            "amount": _major_str(p.amount_minor), "transaction_param": p.reference, "return_url": return_url,
        })
        return Checkout(redirect_url=f"https://my.click.uz/services/pay?{q}")


class PaymeAdapter:
    key = PaymentProvider.PAYME
    currencies = {"UZS"}

    def configured(self) -> bool:
        return bool(settings.PAYME_MERCHANT_ID and settings.PAYME_SECRET_KEY)

    def checkout(self, p: Payment, return_url: str) -> Checkout:
        # Payme amounts are in tiyin, which equals our UZS minor unit.
        params = f"m={settings.PAYME_MERCHANT_ID};ac.payment_ref={p.reference};a={p.amount_minor};c={return_url}"
        token = base64.b64encode(params.encode()).decode()
        return Checkout(redirect_url=f"{settings.PAYME_CHECKOUT_URL.rstrip('/')}/{token}")


class StripeAdapter:
    key = PaymentProvider.STRIPE
    currencies = {"USD"}

    def configured(self) -> bool:
        return bool(settings.STRIPE_SECRET_KEY and settings.STRIPE_WEBHOOK_SECRET)

    def checkout(self, p: Payment, return_url: str) -> Checkout:
        data = {
            "mode": "payment",
            "success_url": f"{return_url}{'&' if '?' in return_url else '?'}stripe=success",
            "cancel_url": f"{return_url}{'&' if '?' in return_url else '?'}stripe=cancelled",
            "client_reference_id": p.reference,
            "metadata[payment_ref]": p.reference,
            "payment_intent_data[metadata][payment_ref]": p.reference,
            "line_items[0][quantity]": "1",
            "line_items[0][price_data][currency]": p.currency.lower(),
            "line_items[0][price_data][unit_amount]": str(p.amount_minor),
            "line_items[0][price_data][product_data][name]": f"VIMORA payment {p.reference}",
        }
        try:
            r = httpx.post("https://api.stripe.com/v1/checkout/sessions", data=data, auth=(settings.STRIPE_SECRET_KEY, ""),
                           headers={"Idempotency-Key": p.idempotency_key}, timeout=20)
        except httpx.HTTPError:
            raise AppError("Payment provider is unreachable, please try again", code="PROVIDER_UNAVAILABLE", status_code=502) from None
        if r.status_code >= 400:
            raise AppError("Payment provider rejected the request", code="PROVIDER_ERROR", status_code=502)
        body = r.json()
        p.provider_state = {**(p.provider_state or {}), "checkout_session_id": body.get("id")}
        return Checkout(redirect_url=body.get("url"))


class ManualAdapter:
    key = PaymentProvider.MANUAL
    currencies = {"UZS", "USD"}

    def __init__(self, enabled: bool, instructions: str):
        self.enabled = enabled
        self.instructions = instructions

    def configured(self) -> bool:
        return self.enabled and bool(self.instructions.strip())

    def checkout(self, p: Payment, return_url: str) -> Checkout:
        return Checkout(redirect_url=None, instructions=self.instructions)


def adapters(manual_enabled: bool = False, manual_instructions: str = "") -> dict[str, object]:
    return {
        PaymentProvider.CLICK: ClickAdapter(),
        PaymentProvider.PAYME: PaymeAdapter(),
        PaymentProvider.STRIPE: StripeAdapter(),
        PaymentProvider.MANUAL: ManualAdapter(manual_enabled, manual_instructions),
    }


def get_adapter(key: str, *, disabled: list[str], manual_enabled: bool, manual_instructions: str, currency: str):
    a = adapters(manual_enabled, manual_instructions).get(key)
    if a is None:
        raise AppError("Unknown payment provider", code="UNKNOWN_PROVIDER")
    if key in disabled or not a.configured():
        raise ConfigurationRequired(f"{key} payments are not available", details={"provider": key})
    if currency not in a.currencies:
        raise AppError(f"{key} does not support {currency}", code="CURRENCY_NOT_SUPPORTED")
    return a
