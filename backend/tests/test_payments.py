import base64
import hashlib
import hmac
import json
import time

import pytest
from sqlalchemy import text

from app.core.config import settings
from app.models import Order
from tests.conftest import Api, accept_quote, place_fixed_order


@pytest.fixture
def providers(monkeypatch):
    monkeypatch.setattr(settings, "CLICK_MERCHANT_ID", "111")
    monkeypatch.setattr(settings, "CLICK_SERVICE_ID", "222")
    monkeypatch.setattr(settings, "CLICK_SECRET_KEY", "click-secret")
    monkeypatch.setattr(settings, "PAYME_MERCHANT_ID", "payme-merchant")
    monkeypatch.setattr(settings, "PAYME_SECRET_KEY", "payme-key")
    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_x")
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_test")


def deposit_order(api):
    return accept_quote(api, place_fixed_order(api))


def start(api, order_id, provider, **kw):
    r = api.post(f"/api/v1/orders/{order_id}/payments", json={"provider": provider, **kw})
    assert r.status_code == 201, r.text
    return r.json()


# ------------------------------------------------------------------ Click
def click_sign(p: dict, complete: bool) -> str:
    s = f"{p['click_trans_id']}{p['service_id']}click-secret{p['merchant_trans_id']}{p.get('merchant_prepare_id', '') if complete else ''}{p['amount']}{p['action']}{p['sign_time']}"
    return hashlib.md5(s.encode()).hexdigest()


def click_call(action: int, ref: str, amount: str, prepare_id=None, txn="9001", error="0"):
    p = {"click_trans_id": txn, "service_id": "222", "click_paydoc_id": "77", "merchant_trans_id": ref, "amount": amount, "action": str(action), "error": error, "error_note": "", "sign_time": "2026-11-01 10:00:00"}
    if prepare_id is not None:
        p["merchant_prepare_id"] = str(prepare_id)
    p["sign_string"] = click_sign(p, action == 1)
    return Api().c.post(f"/api/v1/webhooks/click/{'complete' if action else 'prepare'}", data=p).json()


def test_unconfigured_provider_is_unavailable(customer, catalog):
    _, api = customer
    o = deposit_order(api)
    r = api.post(f"/api/v1/orders/{o['id']}/payments", json={"provider": "CLICK"})
    assert r.status_code == 503 and r.json()["error"]["code"] == "CONFIGURATION_REQUIRED"
    site = Api().get("/api/v1/site").json()
    assert all(p["available"] is False for p in site["payments.providers"])


def test_click_full_flow_and_replay(providers, customer, catalog, db):
    _, api = customer
    o = deposit_order(api)
    pay = start(api, o["id"], "CLICK")
    assert pay["redirect_url"].startswith("https://my.click.uz/services/pay?")
    assert "amount=30000.00" in pay["redirect_url"]
    ref = pay["payment"]["reference"]
    # the browser return URL alone never marks anything paid
    assert api.get(f"/api/v1/orders/{o['id']}/payments/{ref}").json()["confirmed"] is False

    r = click_call(0, ref, "30000.00")
    assert r["error"] == 0
    prep = r["merchant_prepare_id"]
    r = click_call(1, ref, "30000.00", prepare_id=prep)
    assert r["error"] == 0
    detail = api.get(f"/api/v1/orders/{o['id']}").json()
    assert detail["status"] == "QUEUED" and detail["paid_minor"] == 30_000_00 and detail["payment_status"] == "DEPOSIT_PAID"
    # replayed completion: no double counting
    r = click_call(1, ref, "30000.00", prepare_id=prep)
    assert r["error"] == -4
    db.expire_all()
    assert db.get(Order, o["id"]).paid_minor == 30_000_00
    assert db.execute(text("SELECT count(*) FROM invoices")).scalar() == 1


def test_click_bad_signature_and_amount(providers, customer, catalog, db):
    _, api = customer
    o = deposit_order(api)
    ref = start(api, o["id"], "CLICK")["payment"]["reference"]
    p = {"click_trans_id": "1", "service_id": "222", "merchant_trans_id": ref, "amount": "30000.00", "action": "0", "sign_time": "t", "sign_string": "deadbeef"}
    assert Api().c.post("/api/v1/webhooks/click/prepare", data=p).json()["error"] == -1
    assert db.execute(text("SELECT count(*) FROM audit_logs WHERE action='webhook.signature_invalid'")).scalar() == 1
    assert click_call(0, ref, "1.00")["error"] == -2  # amount manipulation
    assert click_call(0, "NOPE", "30000.00")["error"] == -5


def test_click_complete_with_error_cancels(providers, customer, catalog, db):
    _, api = customer
    o = deposit_order(api)
    ref = start(api, o["id"], "CLICK")["payment"]["reference"]
    prep = click_call(0, ref, "30000.00")["merchant_prepare_id"]
    assert click_call(1, ref, "30000.00", prepare_id=prep, error="-5017")["error"] == -9
    assert db.execute(text("SELECT status FROM payments")).scalar() == "FAILED"
    assert api.get(f"/api/v1/orders/{o['id']}").json()["status"] == "DEPOSIT_PENDING"


# ------------------------------------------------------------------ Payme
def payme(method, params, key="payme-key", rid=1):
    auth = base64.b64encode(f"Paycom:{key}".encode()).decode()
    return Api().c.post("/api/v1/webhooks/payme", json={"jsonrpc": "2.0", "id": rid, "method": method, "params": params}, headers={"Authorization": f"Basic {auth}"}).json()


def test_payme_flow(providers, customer, catalog, db):
    _, api = customer
    o = deposit_order(api)
    pay = start(api, o["id"], "PAYME")
    assert pay["redirect_url"].startswith("https://checkout.paycom.uz/")
    ref = pay["payment"]["reference"]
    acct = {"payment_ref": ref}
    assert payme("CheckPerformTransaction", {"amount": 30_000_00, "account": acct}, key="wrong")["error"]["code"] == -32504
    assert payme("CheckPerformTransaction", {"amount": 1, "account": acct})["error"]["code"] == -31001
    assert payme("CheckPerformTransaction", {"amount": 30_000_00, "account": {"payment_ref": "X"}})["error"]["code"] == -31050
    assert payme("CheckPerformTransaction", {"amount": 30_000_00, "account": acct})["result"]["allow"] is True
    r = payme("CreateTransaction", {"id": "pm-1", "time": int(time.time() * 1000), "amount": 30_000_00, "account": acct})
    assert r["result"]["state"] == 1
    # a second, different Payme transaction for the same payment is refused
    assert "error" in payme("CreateTransaction", {"id": "pm-2", "time": 1, "amount": 30_000_00, "account": acct})
    # repeated CreateTransaction with the same id is idempotent
    assert payme("CreateTransaction", {"id": "pm-1", "time": 1, "amount": 30_000_00, "account": acct})["result"]["state"] == 1
    r = payme("PerformTransaction", {"id": "pm-1"})
    assert r["result"]["state"] == 2
    assert payme("PerformTransaction", {"id": "pm-1"})["result"]["state"] == 2  # idempotent
    db.expire_all()
    assert db.get(Order, o["id"]).paid_minor == 30_000_00
    assert payme("CheckTransaction", {"id": "pm-1"})["result"]["state"] == 2
    # Payme reverses after perform -> recorded as refund
    r = payme("CancelTransaction", {"id": "pm-1", "reason": 5})
    assert r["result"]["state"] == -2
    db.expire_all()
    assert db.get(Order, o["id"]).refunded_minor == 30_000_00
    assert payme("PerformTransaction", {"id": "unknown"})["error"]["code"] == -31003


# ------------------------------------------------------------------ Stripe
def stripe_post(payload: dict, secret="whsec_test", ts=None):
    body = json.dumps(payload).encode()
    ts = ts or int(time.time())
    sig = hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
    return Api().c.post("/api/v1/webhooks/stripe", content=body, headers={"Stripe-Signature": f"t={ts},v1={sig}", "Content-Type": "application/json"})


def stripe_event(ref, amount, eid="evt_1", currency="usd"):
    return {"id": eid, "type": "checkout.session.completed", "data": {"object": {"id": "cs_1", "payment_status": "paid", "amount_total": amount, "currency": currency,
                                                                             "payment_intent": "pi_1", "metadata": {"payment_ref": ref}}}}


def test_stripe_webhook(providers, customer, catalog, db, monkeypatch):
    _, api = customer
    o = api.post("/api/v1/orders", json={"service_slug": "usd-writing", "title": "Essay", "description": "Write an essay about tea.", "quantity": 2}).json()
    o = accept_quote(api, o)

    class R:
        status_code = 200

        def json(self):
            return {"id": "cs_1", "url": "https://checkout.stripe.com/c/pay/cs_1"}

    monkeypatch.setattr("app.payments.providers.httpx.post", lambda *a, **k: R())
    pay = start(api, o["id"], "STRIPE")
    ref = pay["payment"]["reference"]
    assert stripe_post(stripe_event(ref, 1500), secret="whsec_wrong").status_code == 400
    assert stripe_post(stripe_event(ref, 1500), ts=int(time.time()) - 3600).status_code == 400  # stale timestamp
    assert stripe_post(stripe_event(ref, 1, eid="evt_bad")).json()["status"] == "rejected"  # amount mismatch
    assert stripe_post(stripe_event(ref, 1500, eid="evt_ok")).json()["status"] == "ok"
    assert stripe_post(stripe_event(ref, 1500, eid="evt_ok")).json()["status"] == "duplicate"  # replay
    db.expire_all()
    order = db.get(Order, o["id"])
    assert order.paid_minor == 1500 and order.status == "QUEUED"
    assert db.execute(text("SELECT count(*) FROM payment_events WHERE event_type='AMOUNT_MISMATCH'")).scalar() == 1


def test_confirmed_payment_is_immutable(providers, customer, catalog, db):
    _, api = customer
    o = deposit_order(api)
    ref = start(api, o["id"], "CLICK")["payment"]["reference"]
    prep = click_call(0, ref, "30000.00")["merchant_prepare_id"]
    click_call(1, ref, "30000.00", prepare_id=prep)
    with pytest.raises(Exception):
        db.execute(text("UPDATE payments SET amount_minor = 1"))
    db.rollback()
    with pytest.raises(Exception):
        db.execute(text("DELETE FROM payments"))
    db.rollback()
    with pytest.raises(Exception):
        db.execute(text("UPDATE payment_events SET event_type='X'"))
    db.rollback()


def test_manual_payment_by_finance_admin(customer, admin, catalog, db, monkeypatch):
    _, api = customer
    _, adm = admin
    o = deposit_order(api)
    r = adm.post(f"/api/v1/admin/orders/{o['id']}/manual-payment", json={"amount_minor": 12345, "reference": "BANK-1"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "AMOUNT_MISMATCH"
    r = adm.post(f"/api/v1/admin/orders/{o['id']}/manual-payment", json={"amount_minor": 30_000_00, "reference": "BANK-1"})
    assert r.status_code == 201 and r.json()["status"] == "QUEUED"
    assert db.execute(text("SELECT count(*) FROM audit_logs WHERE action='payment.manual_recorded'")).scalar() == 1


def test_payment_reuse_and_idempotency(providers, customer, catalog, db):
    _, api = customer
    o = deposit_order(api)
    p1 = start(api, o["id"], "CLICK")["payment"]
    p2 = start(api, o["id"], "CLICK")["payment"]
    assert p1["id"] == p2["id"]
    r1 = api.post(f"/api/v1/orders/{o['id']}/payments", json={"provider": "PAYME"}, headers={"Idempotency-Key": "abc"}).json()
    r2 = api.post(f"/api/v1/orders/{o['id']}/payments", json={"provider": "PAYME"}, headers={"Idempotency-Key": "abc"}).json()
    assert r1["payment"]["id"] == r2["payment"]["id"]
    assert db.execute(text("SELECT count(*) FROM payments")).scalar() == 2


def test_no_payment_when_nothing_due(providers, customer, catalog):
    _, api = customer
    o = place_fixed_order(api)  # quotation not accepted yet
    r = api.post(f"/api/v1/orders/{o['id']}/payments", json={"provider": "CLICK"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "NO_PAYMENT_DUE"
