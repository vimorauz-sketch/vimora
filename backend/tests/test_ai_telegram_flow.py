import json

import pytest
from sqlalchemy import text

from app.ai.providers.base import AIProviderError, AIResult
from app.core.config import settings
from app.models import AIExecution, Order
from app.services.settings_service import set_setting
from tests.conftest import Api, accept_quote, place_fixed_order

GOOD_FILES = {"files": [{"filename": "bot.py", "content": "import os\n\ndef main():\n    print('hello')\n"}, {"filename": "README.md", "content": "# FlowerBot\nRun python bot.py"}], "notes": "done"}


class FakeAdapter:
    """Scripted AI provider for tests: responses keyed by the pipeline stage."""

    key = "fake"
    calls: list = []

    def __init__(self, script):
        self.script = script

    def complete(self, *, model, system, user, max_tokens, temperature, timeout):
        FakeAdapter.calls.append({"system": system, "user": user})
        if "classify a customer request" in system:
            out = self.script.get("router", {"capability": "code_generation", "automatable": True, "complexity": "low", "policy_flag": False, "automation_reason": "ok"})
        elif "execution plan" in system:
            out = self.script.get("planner", {"feasible": True, "steps": [{"title": "Write bot", "detail": "x"}], "deliverables": [{"filename": "bot.py"}]})
        elif "carry out the approved plan" in system:
            out = self.script.get("executor", GOOD_FILES)
        elif "satisfy the customer's requirements" in system:
            out = {"overall_pass": True, "requirements": [{"requirement": "bot", "met": True, "comment": ""}], "issues": [], "suggested_next_steps": ["Test with real token"]}
        else:
            out = self.script.get("assistant", {"reply": "Sounds like a Telegram bot.", "suggested_service_slug": "telegram-bot", "complexity": "low", "clarifying_questions": ["What should it do?"]})
        if isinstance(out, Exception):
            raise out
        return AIResult(text=json.dumps(out), input_tokens=100, output_tokens=50, model=model, latency_ms=5)


@pytest.fixture
def ai_on(db, monkeypatch):
    monkeypatch.setattr(settings, "AI_PROVIDER", "anthropic")
    monkeypatch.setattr(settings, "AI_API_KEY", "test-key-xxxxxxxx")
    monkeypatch.setattr(settings, "AI_MODEL", "test-model")
    set_setting(db, "ai.enabled", True, actor_id=None)
    db.commit()
    FakeAdapter.calls = []

    def use(script=None):
        monkeypatch.setattr("app.ai.manager.build_adapter", lambda *a, **k: FakeAdapter(script or {}))

    use()
    return use


def queued_order(api, adm, db):
    o = accept_quote(api, place_fixed_order(api))
    r = adm.post(f"/api/v1/admin/orders/{o['id']}/manual-payment", json={"amount_minor": 30_000_00, "reference": "T-1"})
    assert r.json()["status"] == "QUEUED"
    return o


def test_ai_disabled_returns_configuration_required(customer, admin, catalog, db):
    _, api = customer
    _, adm = admin
    o = queued_order(api, adm, db)
    r = adm.post(f"/api/v1/admin/orders/{o['id']}/ai/start", json={})
    assert r.status_code == 503 and r.json()["error"]["code"] == "CONFIGURATION_REQUIRED"


def test_ai_pipeline_requires_human_approval(ai_on, customer, admin, catalog, db):
    _, api = customer
    _, adm = admin
    o = queued_order(api, adm, db)
    r = adm.post(f"/api/v1/admin/orders/{o['id']}/ai/start", json={})
    assert r.status_code == 200, r.text
    eid = r.json()["execution_id"]  # eager Celery: pipeline already ran
    db.expire_all()
    ex = db.get(AIExecution, eid)
    assert ex.status == "REVIEW_REQUIRED" and ex.input_tokens == 400
    assert db.get(Order, o["id"]).status == "AI_REVIEW_REQUIRED"
    # customer sees no deliverables and no AI output files
    d = api.get(f"/api/v1/orders/{o['id']}").json()
    assert d["deliverables"] == []
    detail = adm.get(f"/api/v1/admin/ai/executions/{eid}").json()
    assert [s["stage"] for s in detail["steps"]] == ["ROUTER", "PLANNER", "EXECUTOR", "VALIDATOR"]
    assert detail["validation_report"]["deterministic_passed"] is True
    files = detail["files"]
    assert len(files) == 2
    # the customer cannot download an unapproved AI output
    assert api.get(f"/api/v1/files/{files[0]['id']}/link").status_code == 404
    # untrusted order content was wrapped as data
    assert all("<untrusted_content" in c["user"] for c in FakeAdapter.calls)
    r = adm.post(f"/api/v1/admin/ai/executions/{eid}/approve", json={"attachment_ids": [f["id"] for f in files]})
    assert r.status_code == 200
    db.expire_all()
    assert db.get(AIExecution, eid).status == "APPROVED"


def test_ai_failure_falls_back_to_manual(ai_on, customer, admin, catalog, db):
    _, api = customer
    _, adm = admin
    o = queued_order(api, adm, db)
    ai_on({"executor": AIProviderError("boom", retryable=False)})
    eid = adm.post(f"/api/v1/admin/orders/{o['id']}/ai/start", json={}).json()["execution_id"]
    db.expire_all()
    ex = db.get(AIExecution, eid)
    assert ex.status == "FAILED" and "boom" in ex.failure_reason
    assert db.get(Order, o["id"]).status == "MANUAL_PROCESSING"
    assert db.execute(text("SELECT count(*) FROM audit_logs WHERE action='ai.execution_failed'")).scalar() == 1
    assert db.execute(text("SELECT count(*) FROM ai_usage_records WHERE success = false")).scalar() >= 1


def test_ai_unsafe_output_rejected(ai_on, customer, admin, catalog, db):
    _, api = customer
    _, adm = admin
    o = queued_order(api, adm, db)
    ai_on({"executor": {"files": [{"filename": "../../etc/cron.d/x.sh", "content": "rm -rf /"}]}})
    eid = adm.post(f"/api/v1/admin/orders/{o['id']}/ai/start", json={}).json()["execution_id"]
    db.expire_all()
    assert db.get(AIExecution, eid).status == "FAILED"
    assert "Unsafe file name" in db.get(AIExecution, eid).failure_reason


def test_ai_not_automatable_routes_to_manual(ai_on, customer, admin, catalog, db):
    _, api = customer
    _, adm = admin
    o = queued_order(api, adm, db)
    ai_on({"router": {"capability": None, "automatable": False, "policy_flag": True, "automation_reason": "needs a phone call"}})
    eid = adm.post(f"/api/v1/admin/orders/{o['id']}/ai/start", json={}).json()["execution_id"]
    db.expire_all()
    assert db.get(AIExecution, eid).status == "FAILED"
    assert db.get(Order, o["id"]).status == "MANUAL_PROCESSING"


def test_ai_budget_limit(ai_on, customer, admin, catalog, db):
    from app.models import AIUsageRecord
    from app.core.db import utcnow

    _, api = customer
    _, adm = admin
    o = queued_order(api, adm, db)
    db.add(AIUsageRecord(purpose="x", provider_key="x", model_identifier="x", cost_usd=999, created_at=utcnow()))
    db.commit()
    r = adm.post(f"/api/v1/admin/orders/{o['id']}/ai/start", json={})
    assert r.status_code == 409 and r.json()["error"]["code"] == "AI_BUDGET_EXCEEDED"


def test_ai_assistant(ai_on, catalog):
    r = Api().post("/api/v1/ai/assist", json={"message": "I need a bot for my telegram shop", "language": "en"})
    body = r.json()
    assert body["ai_available"] is True and body["suggestions"][0]["slug"] == "telegram-bot"
    assert body["indicative_price"]["amount_minor"] == 100_000_00  # from the catalog, not the model


def test_ai_assistant_without_ai_uses_keyword_fallback(catalog):
    body = Api().post("/api/v1/ai/assist", json={"message": "telegram bot development please", "language": "en"}).json()
    assert body["ai_available"] is False and body["recommend_custom_order"] is True
    assert any(s["slug"] == "telegram-bot" for s in body["suggestions"])


# ------------------------------------------------------------------ end-to-end owner workflow
def test_end_to_end_delivery_requires_final_payment(ai_on, customer, admin, catalog, db):
    _, api = customer
    _, adm = admin
    o = queued_order(api, adm, db)
    eid = adm.post(f"/api/v1/admin/orders/{o['id']}/ai/start", json={}).json()["execution_id"]
    files = adm.get(f"/api/v1/admin/ai/executions/{eid}").json()["files"]
    adm.post(f"/api/v1/admin/ai/executions/{eid}/approve", json={"attachment_ids": [files[0]["id"]]})
    r = adm.post(f"/api/v1/admin/orders/{o['id']}/complete")
    assert r.json()["status"] == "FINAL_PAYMENT_PENDING"
    # cannot release before the balance is paid
    assert adm.post(f"/api/v1/admin/orders/{o['id']}/release").status_code == 409
    d = api.get(f"/api/v1/orders/{o['id']}").json()
    assert d["payment_due"]["amount_minor"] == 70_000_00 and d["deliverables"] == []
    adm.post(f"/api/v1/admin/orders/{o['id']}/manual-payment", json={"amount_minor": 70_000_00, "reference": "T-2"})
    assert api.get(f"/api/v1/orders/{o['id']}").json()["status"] == "READY_FOR_DELIVERY"
    assert api.get(f"/api/v1/orders/{o['id']}").json()["deliverables"] == []  # still not released
    assert adm.post(f"/api/v1/admin/orders/{o['id']}/release").json()["status"] == "DELIVERED"
    d = api.get(f"/api/v1/orders/{o['id']}").json()
    assert len(d["deliverables"]) == 1
    link = api.get(f"/api/v1/files/{d['deliverables'][0]['attachment']['id']}/link").json()["url"]
    assert b"def main" in Api().get(link.replace("http://testserver", "")).content
    # revision, review, close
    assert api.post(f"/api/v1/orders/{o['id']}/review", json={"rating": 5, "text": "Great"}).status_code == 200
    assert Api().get("/api/v1/testimonials").json()["items"] == []  # not public until approved
    adm.post(f"/api/v1/admin/orders/{o['id']}/review-visibility", json={"public": True})
    assert len(Api().get("/api/v1/testimonials").json()["items"]) == 1
    assert api.post(f"/api/v1/orders/{o['id']}/close").json()["status"] == "CLOSED"
    # analytics reflect real records
    an = adm.get("/api/v1/admin/analytics").json()
    assert an["orders_total"] == 1 and an["ai"]["by_status"]["APPROVED"] == 1
    fin = adm.get("/api/v1/admin/finance/summary").json()
    assert fin["currencies"]["UZS"]["gross_minor"] == 100_000_00


def test_notifications_created_and_deduplicated(customer, catalog, db):
    _, api = customer
    place_fixed_order(api)
    rows = db.execute(text("SELECT channel, event_type, status FROM notifications ORDER BY id")).all()
    in_app = [r for r in rows if r[0] == "IN_APP"]
    assert {r[1] for r in in_app} == {"order.created", "quotation.available"}
    emails = [r for r in rows if r[0] == "EMAIL"]
    assert all(r[2] == "LOGGED_DEV" for r in emails)  # dev console backend, honestly labelled
    admin_tg = [r for r in rows if r[0] == "TELEGRAM"]
    assert all(r[2] == "SKIPPED" for r in admin_tg)  # bot not configured
    n = api.get("/api/v1/account/notifications").json()
    assert n["unread"] == 2


# ------------------------------------------------------------------ Telegram
@pytest.fixture
def tg(monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setattr(settings, "TELEGRAM_WEBHOOK_SECRET", "hook-secret")
    monkeypatch.setattr(settings, "TELEGRAM_ADMIN_ID", "42")
    monkeypatch.setattr(settings, "TELEGRAM_BOT_USERNAME", "vimora_bot")
    sent = []
    monkeypatch.setattr("app.telegram.bot.send_message", lambda chat, text, **k: sent.append((chat, text)))
    return sent


def tg_update(text_, uid, secret="hook-secret", header=None):
    upd = {"update_id": 1, "message": {"message_id": 1, "text": text_, "chat": {"id": uid, "type": "private"}, "from": {"id": uid, "username": "u"}}}
    return Api().c.post(f"/api/v1/webhooks/telegram/{secret}", json=upd, headers={"X-Telegram-Bot-Api-Secret-Token": header or secret})


def test_telegram_webhook_secret_required(tg):
    assert tg_update("/stats", 42, secret="wrong").status_code == 404
    assert tg_update("/stats", 42, header="wrong").status_code == 404


def test_telegram_admin_commands_access_controlled(tg, db, customer, catalog):
    _, api = customer
    place_fixed_order(api)
    tg_update("/stats", 777)
    assert tg[-1][1] == "This command is restricted."
    assert db.execute(text("SELECT count(*) FROM audit_logs WHERE action='telegram.command_denied'")).scalar() == 1
    tg_update("/pending", 42)
    assert "Nothing pending." in tg[-1][1]  # quotation is waiting on the customer, not the admin
    tg_update("/orders", 42)
    assert "VM-" in tg[-1][1] and "QUOTATION_PENDING" in tg[-1][1]
    tg_update("/stats", 42)
    assert "Orders total: <b>1</b>" in tg[-1][1]
    assert db.execute(text("SELECT count(*) FROM audit_logs WHERE action='telegram.command'")).scalar() == 3


def test_telegram_account_linking(tg, customer, db):
    _, api = customer
    link = api.post("/api/v1/account/telegram/link").json()["deep_link"]
    code = link.split("start=")[1]
    tg_update(f"/start {code}", 555)
    assert "linked" in tg[-1][1]
    assert api.get("/api/v1/account/telegram").json()["linked"] is True
    tg_update(f"/start {code}", 556)  # code is single-use
    assert "invalid or expired" in tg[-1][1]


def test_admin_activity_feed_for_bell_and_sound(customer, admin, support, catalog, db):
    admin = admin[1] if isinstance(admin, tuple) else admin
    customer = customer[1] if isinstance(customer, tuple) else customer
    # the feed works even when Telegram admin events are disabled
    set_setting(db, "notifications.telegram_admin_events", [], actor_id=None)
    db.commit()
    _, support = support
    first = admin.get("/api/v1/admin/activity").json()
    order = place_fixed_order(customer)
    r = admin.get(f"/api/v1/admin/activity?after_id={first['latest_id']}").json()
    assert r["latest_id"] > first["latest_id"]
    assert [i["event_type"] for i in r["items"]] == ["order.created"]
    assert r["items"][0]["link"] == f"/admin/orders/{order['id']}"
    assert r["items"][0]["order_number"] == order["order_number"]
    # polling again with the newest id returns nothing new
    assert admin.get(f"/api/v1/admin/activity?after_id={r['latest_id']}").json()["items"] == []
    # support staff can see it; customers cannot
    assert support.get("/api/v1/admin/activity").status_code == 200
    assert customer.get("/api/v1/admin/activity").status_code == 403
