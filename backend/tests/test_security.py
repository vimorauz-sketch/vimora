"""Authorization, IDOR, file upload and download security tests."""

import io
import zipfile

from sqlalchemy import text

from tests.conftest import Api, place_fixed_order

PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"


def upload(api: Api, name: str, data: bytes, purpose="ORDER_INPUT"):
    return api.c.post("/api/v1/files", files={"file": (name, data)}, data={"purpose": purpose}, headers={"X-CSRF-Token": api.c.cookies.get("vimora_csrf")})


# ------------------------------------------------------------------ IDOR / cross-user
def test_customer_cannot_read_other_customers_order(customer, customer2, catalog):
    _, alice = customer
    _, bob = customer2
    o = place_fixed_order(alice)
    for url in (f"/api/v1/orders/{o['id']}", f"/api/v1/orders/{o['id']}/messages"):
        r = bob.get(url)
        assert r.status_code == 404  # indistinguishable from non-existent
    assert bob.post(f"/api/v1/orders/{o['id']}/quotation/accept", json={"quotation_id": o["quotations"][0]["id"]}).status_code == 404
    assert bob.post(f"/api/v1/orders/{o['id']}/cancel", json={}).status_code == 404
    assert bob.post(f"/api/v1/orders/{o['id']}/messages", json={"body": "hi"}).status_code == 404
    assert bob.post(f"/api/v1/orders/{o['id']}/payments", json={"provider": "CLICK"}).status_code == 404
    assert bob.get("/api/v1/orders").json()["total"] == 0


def test_cannot_attach_someone_elses_file(customer, customer2, catalog):
    _, alice = customer
    _, bob = customer2
    att = upload(alice, "brief.txt", b"my private brief").json()
    r = bob.post("/api/v1/orders", json={"service_slug": "telegram-bot", "title": "Bot", "description": "A bot for my shop please.", "requirements": {"bot_name": "B"}, "attachment_ids": [att["id"]]})
    assert r.status_code == 403
    assert bob.get(f"/api/v1/files/{att['id']}/link").status_code == 404


def test_message_ownership_not_spoofable(customer, catalog, db):
    u, alice = customer
    o = place_fixed_order(alice)
    r = alice.post(f"/api/v1/orders/{o['id']}/messages", json={"body": "Hello", "sender_id": 999, "sender_is_staff": True})
    assert r.status_code == 422
    r = alice.post(f"/api/v1/orders/{o['id']}/messages", json={"body": "Hello"})
    assert r.status_code == 201 and r.json()["sender_is_staff"] is False
    assert db.execute(text("SELECT sender_id FROM messages")).scalar() == u.id


# ------------------------------------------------------------------ admin access control
ADMIN_GETS = ["/api/v1/admin/overview", "/api/v1/admin/orders", "/api/v1/admin/customers", "/api/v1/admin/finance/summary", "/api/v1/admin/ai/overview",
              "/api/v1/admin/settings", "/api/v1/admin/audit-logs", "/api/v1/admin/analytics", "/api/v1/admin/services"]


def test_customers_cannot_access_admin(customer):
    _, api = customer
    for url in ADMIN_GETS:
        assert api.get(url).status_code == 403, url


def test_anonymous_cannot_access_admin_or_account():
    api = Api()
    for url in ADMIN_GETS + ["/api/v1/orders", "/api/v1/account/sessions"]:
        assert api.get(url).status_code == 401, url


def test_support_role_least_privilege(support, customer, catalog):
    _, sup = support
    _, alice = customer
    o = place_fixed_order(alice)
    assert sup.get("/api/v1/admin/orders").status_code == 200
    assert sup.get(f"/api/v1/admin/orders/{o['id']}").status_code == 200
    assert sup.post(f"/api/v1/admin/orders/{o['id']}/messages", json={"body": "Hi from support"}).status_code == 201
    # no finance, pricing, settings, secrets, AI configuration or staff management
    assert sup.get("/api/v1/admin/finance/summary").status_code == 403
    assert sup.get("/api/v1/admin/settings").status_code == 403
    assert sup.get("/api/v1/admin/ai/providers").status_code == 403
    assert sup.post(f"/api/v1/admin/orders/{o['id']}/manual-payment", json={"amount_minor": 1, "reference": "abc"}).status_code == 403
    assert sup.post(f"/api/v1/admin/orders/{o['id']}/quotations", json={"currency": "UZS", "line_items": [{"description": "x", "quantity": 1, "unit_price_minor": 1}]}).status_code == 403
    assert sup.post("/api/v1/admin/customers/1/roles", json={"role": "SUPER_ADMIN"}).status_code == 403


def test_privilege_escalation_blocked(admin, customer, db):

    adm_user, adm = admin
    cust, _ = customer
    # an ADMIN (not SUPER_ADMIN) cannot grant roles

    from tests.conftest import login, make_user

    plain_admin = make_user(db, "admin2@example.com", roles=("ADMIN",))
    a2 = login(plain_admin.email)
    assert a2.post(f"/api/v1/admin/customers/{cust.id}/roles", json={"role": "ADMIN"}).status_code == 403
    assert a2.post(f"/api/v1/admin/customers/{adm_user.id}/disable").status_code == 409  # cannot disable owner
    # super admin cannot remove the last super admin (self-change forbidden too)
    assert adm.post(f"/api/v1/admin/customers/{adm_user.id}/roles", json={"role": "SUPER_ADMIN", "grant": False}).status_code == 409


def test_admin_settings_never_return_secrets(admin, db):
    _, adm = admin
    r = adm.post("/api/v1/admin/ai/providers", json={"key": "anthropic", "display_name": "Anthropic", "api_key": "sk-ant-secret-value-1234", "is_enabled": True})
    assert r.status_code == 201
    body = adm.get("/api/v1/admin/ai/providers").text
    assert "sk-ant-secret-value-1234" not in body and "1234" in body  # only last4 hint
    stored = db.execute(text("SELECT api_key_encrypted FROM ai_providers")).scalar()
    assert "sk-ant" not in stored


# ------------------------------------------------------------------ uploads
def test_upload_validation(customer):
    _, api = customer
    assert upload(api, "a.png", PNG).status_code == 201
    r = upload(api, "evil.exe", b"MZ\x90\x00binary")
    assert r.status_code == 400 and r.json()["error"]["code"] == "UPLOAD_TYPE_NOT_ALLOWED"
    r = upload(api, "fake.pdf", PNG)
    assert r.json()["error"]["code"] == "UPLOAD_CONTENT_MISMATCH"
    r = upload(api, "page.txt", b"<html><script>alert(1)</script></html>")
    assert r.status_code == 400
    r = upload(api, "x.svg", b"<svg onload=alert(1)>")
    assert r.status_code == 400
    r = upload(api, "../../etc/passwd.txt", b"plain text")
    assert r.status_code == 201 and r.json()["name"] == "passwd.txt"
    r = upload(api, "empty.txt", b"")
    assert r.json()["error"]["code"] == "UPLOAD_EMPTY"
    r = upload(api, "x.txt", b"hello", purpose="DELIVERABLE")
    assert r.status_code == 403


def test_macro_office_file_rejected(customer):
    _, api = customer
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("word/document.xml", "<doc/>")
        z.writestr("word/vbaProject.bin", "macro")
    r = upload(api, "doc.docx", buf.getvalue())
    assert r.status_code == 400


def test_oversize_upload_rejected(customer, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "MAX_UPLOAD_MB", 1)
    _, api = customer
    r = upload(api, "big.txt", b"a" * (1024 * 1024 + 10))
    assert r.status_code == 413


def test_storage_name_is_random_and_private(customer, db):
    _, api = customer
    upload(api, "brief.txt", b"content")
    key = db.execute(text("SELECT storage_key FROM attachments")).scalar()
    assert "brief" not in key and len(key.rsplit("/", 1)[-1]) >= 30


def test_signed_download_link(customer, customer2):
    _, alice = customer
    _, bob = customer2
    att = upload(alice, "brief.txt", b"secret brief").json()
    url = alice.get(f"/api/v1/files/{att['id']}/link").json()["url"]
    path = url.replace("http://testserver", "")
    r = Api().get(path)  # bearer link works without cookie for the issued user
    assert r.status_code == 200 and r.content == b"secret brief"
    assert r.headers["content-disposition"].startswith("attachment")
    assert r.headers["x-content-type-options"] == "nosniff"
    # tampered token
    tampered = path[:-3] + ("AAA" if not path.endswith("AAA") else "BBB")
    assert Api().get(tampered).status_code == 403


def test_expired_download_link(customer, monkeypatch):
    import time

    _, alice = customer
    att = upload(alice, "brief.txt", b"secret").json()
    url = alice.get(f"/api/v1/files/{att['id']}/link").json()["url"]
    real = time.time
    monkeypatch.setattr(time, "time", lambda: real() + 10_000)
    assert Api().get(url.replace("http://testserver", "")).status_code == 403


def test_security_headers(customer):
    _, api = customer
    r = api.get("/api/v1/auth/me")
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["x-content-type-options"] == "nosniff"
    assert "no-store" in r.headers["cache-control"]
    assert "default-src 'none'" in r.headers["content-security-policy"]


def test_errors_do_not_leak_internals():
    api = Api()
    r = api.get("/api/v1/orders/not-a-number")
    assert r.status_code in (401, 422)
    assert "Traceback" not in r.text


def test_rate_limit_on_price_preview(catalog):
    api = Api()
    codes = [api.post("/api/v1/catalog/price", json={"service_slug": "usd-writing", "quantity": 1}).status_code for _ in range(125)]
    assert codes.count(429) >= 1


def test_public_stats_are_real(catalog):
    s = Api().get("/api/v1/stats").json()
    assert s["completed_orders"] == 0 and s["active_services"] == 3 and s["average_rating"] is None
    assert Api().get("/api/v1/testimonials").json()["items"] == []


def test_account_cross_order_views_are_scoped(customer, customer2, catalog):
    _, alice = customer
    _, bob = customer2
    o = place_fixed_order(alice)
    alice.post(f"/api/v1/orders/{o['id']}/messages", json={"body": "hi"})
    assert len(alice.get("/api/v1/account/conversations").json()["items"]) == 1
    assert bob.get("/api/v1/account/conversations").json()["items"] == []
    assert bob.get("/api/v1/account/payments").json()["items"] == []
    assert bob.get("/api/v1/account/deliverables").json()["items"] == []


def test_every_error_code_has_a_stable_number_and_request_id(customer):
    """Users see 'E7003 · SERVICE_NOT_IN_AREA · request id' — every code raised in the app must be catalogued."""
    import pathlib
    import re

    from app.core.errors import ERROR_NUMBERS

    src = "".join(p.read_text() for p in pathlib.Path("app").rglob("*.py"))
    used = set(re.findall(r'code="([A-Z_]+)"', src)) | {"NOT_FOUND", "FORBIDDEN", "UNAUTHORIZED", "CONFLICT", "RATE_LIMITED", "VALIDATION_ERROR", "INTERNAL_ERROR"}
    assert sorted(used - set(ERROR_NUMBERS)) == []
    assert len(set(ERROR_NUMBERS.values())) == len(ERROR_NUMBERS)  # numbers are unique
    _, api = customer
    r = api.post("/api/v1/orders", json={"title": "", "description": "x"})
    body = r.json()["error"]
    assert r.status_code == 422 and body["code"] == "VALIDATION_ERROR" and body["number"] == "E1001" and body["request_id"]
    fields = {d["field"]: d for d in body["details"]}
    assert fields["description"]["type"] == "string_too_short" and fields["description"]["ctx"] == {"min_length": 10}
    assert "input" not in str(body)  # submitted values are never echoed back
    r = api.get("/api/v1/catalog/services/does-not-exist").json()["error"]
    assert r["code"] == "NOT_FOUND" and r["number"] == "E1004"


def test_unexpected_errors_get_an_id_that_is_in_the_server_log(monkeypatch):
    """A 500 never leaks details but always carries an ID; the same ID is logged with the traceback."""
    from fastapi.testclient import TestClient

    from app.core import errors as errmod
    from app.main import app

    logged: list[str] = []
    monkeypatch.setattr(errmod.log, "exception", lambda msg, *a: logged.append(msg % a))

    @app.get("/api/v1/__boom")
    def _boom():
        raise RuntimeError("secret internal detail")

    try:
        c = TestClient(app, raise_server_exceptions=False)
        r = c.get("/api/v1/__boom")
        err = r.json()["error"]
        assert r.status_code == 500 and err["code"] == "INTERNAL_ERROR" and err["number"] == "E1012"
        assert err["request_id"] and "secret internal detail" not in r.text
        assert any(err["request_id"] in m and "/api/v1/__boom" in m for m in logged)
    finally:
        app.router.routes = [rt for rt in app.router.routes if getattr(rt, "path", "") != "/api/v1/__boom"]
