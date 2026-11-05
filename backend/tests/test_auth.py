import pyotp
import pytest
from sqlalchemy import select, text

from app.models import User
from tests.conftest import PASSWORD, Api, login, make_user


@pytest.fixture
def captured(monkeypatch):
    sent = []

    def fake_send(to, subject, body, **kw):
        sent.append({"to": to, "subject": subject, "body": body, "link": kw.get("cta_url")})
        return "SENT"

    monkeypatch.setattr("app.api.v1.auth.send_email", fake_send)
    return sent


def test_register_verify_login_logout(captured, db):
    api = Api()
    r = api.post("/api/v1/auth/register", json={"email": "New@Example.com", "password": PASSWORD, "full_name": "New", "language": "uz", "accept_terms": True})
    assert r.status_code == 201
    assert "vimora_session" not in api.c.cookies  # no session until login
    assert len(captured) == 1 and captured[0]["to"] == "new@example.com"
    token = captured[0]["link"].split("token=")[1]

    r = api.post("/api/v1/auth/login", json={"email": "new@example.com", "password": PASSWORD})
    assert r.status_code == 200
    me = api.get("/api/v1/auth/me").json()
    assert me["user"]["email_verified"] is False
    # unverified users cannot place orders
    r = api.post("/api/v1/orders", json={"title": "x", "description": "a" * 40})
    assert r.status_code == 403 and r.json()["error"]["code"] == "EMAIL_NOT_VERIFIED"

    assert api.post("/api/v1/auth/verify-email", json={"token": token}).json()["status"] == "verified"
    # one-time token
    assert api.post("/api/v1/auth/verify-email", json={"token": token}).status_code == 400
    assert api.get("/api/v1/auth/me").json()["user"]["email_verified"] is True

    assert api.post("/api/v1/auth/logout").status_code == 200
    assert api.get("/api/v1/auth/me").status_code == 401


def test_register_does_not_enumerate(captured, db):
    make_user(db, "taken@example.com")
    api = Api()
    r1 = api.post("/api/v1/auth/register", json={"email": "taken@example.com", "password": PASSWORD, "full_name": "X", "accept_terms": True})
    r2 = api.post("/api/v1/auth/register", json={"email": "fresh@example.com", "password": PASSWORD, "full_name": "X", "accept_terms": True})
    assert r1.status_code == r2.status_code == 201
    assert r1.json()["status"] == r2.json()["status"]


def test_weak_password_and_terms(captured):
    api = Api()
    r = api.post("/api/v1/auth/register", json={"email": "w@example.com", "password": "short", "full_name": "W", "accept_terms": True})
    assert r.status_code == 400 and r.json()["error"]["code"] == "WEAK_PASSWORD"
    r = api.post("/api/v1/auth/register", json={"email": "w@example.com", "password": PASSWORD, "full_name": "W", "accept_terms": False})
    assert r.status_code == 422


def test_password_hash_is_argon2id(db):
    u = make_user(db, "hash@example.com")
    assert u.password_hash.startswith("$argon2id$")
    assert PASSWORD not in u.password_hash


def test_session_cookie_flags_and_db_stores_only_hash(db):
    u = make_user(db, "cookie@example.com")
    api = Api()
    r = api.post("/api/v1/auth/login", json={"email": u.email, "password": PASSWORD})
    set_cookie = r.headers.get_list("set-cookie") if hasattr(r.headers, "get_list") else [v for k, v in r.headers.multi_items() if k == "set-cookie"]
    sess = next(c for c in set_cookie if c.startswith("vimora_session="))
    assert "HttpOnly" in sess and "SameSite=lax" in sess.replace("Lax", "lax")
    raw = api.c.cookies.get("vimora_session")
    stored = db.execute(text("SELECT token_hash FROM sessions")).scalars().all()
    assert raw not in stored and len(stored[0]) == 64


def test_bad_credentials_generic_and_audited(db):
    make_user(db, "a@example.com")
    api = Api()
    r1 = api.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "wrong-password"})
    r2 = api.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrong-password"})
    assert r1.status_code == r2.status_code == 401
    assert r1.json()["error"]["message"] == r2.json()["error"]["message"]
    n = db.execute(text("SELECT count(*) FROM audit_logs WHERE action='auth.login_failed'")).scalar()
    assert n == 2


def test_progressive_login_throttle_is_per_ip(db):
    make_user(db, "victim@example.com")
    attacker = Api()
    codes = [attacker.post("/api/v1/auth/login", json={"email": "victim@example.com", "password": "nope-nope"}).status_code for _ in range(7)]
    assert 429 in codes
    # the legitimate user from a different IP is not locked out (no trivial DoS)
    from app.security import rate_limit

    assert rate_limit.login_failure_count("victim@example.com", "10.9.9.9") == 0


def test_csrf_required_for_state_changes(customer):
    _, api = customer
    r = api.c.post("/api/v1/auth/logout")  # raw client: no CSRF header
    assert r.status_code == 403 and r.json()["error"]["code"] == "CSRF_FAILED"
    r = api.c.post("/api/v1/auth/logout", headers={"X-CSRF-Token": "forged"})
    assert r.status_code == 403
    r = api.post("/api/v1/auth/logout", headers={"Origin": "https://evil.example"})
    assert r.status_code == 403


def test_password_reset_flow(monkeypatch, db):
    sent = []
    monkeypatch.setattr("app.api.v1.auth.send_email", lambda to, s, b, **kw: sent.append(kw["cta_url"]) or "SENT")
    u = make_user(db, "reset@example.com")
    other = login(u.email)
    api = Api()
    assert api.post("/api/v1/auth/forgot-password", json={"email": "reset@example.com"}).json() == {"status": "ok"}
    assert api.post("/api/v1/auth/forgot-password", json={"email": "ghost@example.com"}).json() == {"status": "ok"}
    assert len(sent) == 1
    token = sent[0].split("token=")[1]
    new_pw = "An0ther!Strong#Pass"
    assert api.post("/api/v1/auth/reset-password", json={"token": token, "password": new_pw}).status_code == 200
    assert api.post("/api/v1/auth/reset-password", json={"token": token, "password": new_pw}).status_code == 400  # one-time
    assert other.get("/api/v1/auth/me").status_code == 401  # all sessions invalidated
    assert api.post("/api/v1/auth/login", json={"email": u.email, "password": new_pw}).status_code == 200


def test_expired_reset_token_rejected(monkeypatch, db):
    sent = []
    monkeypatch.setattr("app.api.v1.auth.send_email", lambda to, s, b, **kw: sent.append(kw["cta_url"]) or "SENT")
    make_user(db, "exp@example.com")
    api = Api()
    api.post("/api/v1/auth/forgot-password", json={"email": "exp@example.com"})
    db.execute(text("UPDATE password_resets SET expires_at = now() - interval '1 minute'"))
    db.commit()
    r = api.post("/api/v1/auth/reset-password", json={"token": sent[0].split("token=")[1], "password": "An0ther!Strong#Pass"})
    assert r.status_code == 400


def test_mfa_enroll_and_login(admin, db):
    u, api = admin
    setup = api.post("/api/v1/account/mfa/setup").json()
    code = pyotp.TOTP(setup["secret"]).now()
    rec = api.post("/api/v1/account/mfa/enable", json={"code": code}).json()["recovery_codes"]
    assert len(rec) == 8
    # new login now requires the second factor
    api2 = Api()
    r = api2.post("/api/v1/auth/login", json={"email": u.email, "password": PASSWORD})
    assert r.json()["mfa_required"] is True
    assert api2.get("/api/v1/admin/overview").status_code == 401
    assert api2.post("/api/v1/auth/mfa/verify", json={"code": "000000"}).status_code == 401
    assert api2.post("/api/v1/auth/mfa/verify", json={"code": pyotp.TOTP(setup["secret"]).now()}).status_code == 200
    assert api2.get("/api/v1/admin/overview").status_code == 200
    # recovery code works once
    api3 = Api()
    api3.post("/api/v1/auth/login", json={"email": u.email, "password": PASSWORD})
    assert api3.post("/api/v1/auth/mfa/verify", json={"code": rec[0]}).status_code == 200
    api4 = Api()
    api4.post("/api/v1/auth/login", json={"email": u.email, "password": PASSWORD})
    assert api4.post("/api/v1/auth/mfa/verify", json={"code": rec[0]}).status_code == 401


def test_admin_mfa_enforced_when_required(admin, monkeypatch):
    from app.core.config import settings

    _, api = admin
    monkeypatch.setattr(type(settings), "admin_mfa_required", property(lambda self: True))
    r = api.get("/api/v1/admin/overview")
    assert r.status_code == 403 and r.json()["error"]["code"] == "MFA_REQUIRED"


def test_change_password_rotates_and_revokes(customer, db):
    u, api = customer
    other = login(u.email)
    old_cookie = api.c.cookies.get("vimora_session")
    r = api.post("/api/v1/account/change-password", json={"current_password": PASSWORD, "new_password": "Brand!New#Passw0rd"})
    assert r.status_code == 200
    assert api.c.cookies.get("vimora_session") != old_cookie
    assert api.get("/api/v1/auth/me").status_code == 200
    assert other.get("/api/v1/auth/me").status_code == 401


def test_disabled_account_cannot_login(db, admin):
    u = make_user(db, "bad@example.com")
    sess = login(u.email)
    _, adm = admin
    assert adm.post(f"/api/v1/admin/customers/{u.id}/disable").status_code == 200
    assert sess.get("/api/v1/auth/me").status_code == 401
    r = Api().post("/api/v1/auth/login", json={"email": u.email, "password": PASSWORD})
    assert r.status_code == 401
    assert db.scalar(select(User.is_active).where(User.id == u.id)) is False


def test_weak_password_returns_rule_codes_for_translation(db):
    from tests.conftest import Api

    api = Api()
    r = api.post("/api/v1/auth/register", json={"email": "weak@example.com", "password": "abcdefghij", "full_name": "W", "language": "uz", "accept_terms": True})
    err = r.json()["error"]
    assert r.status_code == 400 and err["code"] == "WEAK_PASSWORD" and err["number"] == "E1103"
    assert err["details"] == ["classes"]
    r = api.post("/api/v1/auth/register", json={"email": "weak2@example.com", "password": "Ab1!", "full_name": "W", "language": "uz", "accept_terms": True})
    assert r.status_code in (400, 422)


def test_local_install_without_smtp_can_still_verify(db, monkeypatch):
    """On a development computer without SMTP the link goes to the dev mailbox and is shown once; never in production."""
    from app.core.config import settings
    from tests.conftest import Api

    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "EMAIL_BACKEND", "smtp")
    monkeypatch.setattr(settings, "EMAIL_HOST", "")
    api = Api()
    r = api.post("/api/v1/auth/register", json={"email": "local@example.com", "password": "Qarapchi-2026!", "full_name": "L", "language": "uz", "accept_terms": True})
    body = r.json()
    assert r.status_code == 201 and body["email_delivery"] == "PENDING" and "/verify-email?token=" in body["dev_verify_url"]
    token = body["dev_verify_url"].split("token=")[1]
    assert api.post("/api/v1/auth/verify-email", json={"token": token}).status_code == 200
    # production never returns the link and never falls back to the dev mailbox
    monkeypatch.setattr(settings, "APP_ENV", "production")
    r = api.post("/api/v1/auth/register", json={"email": "prod@example.com", "password": "Qarapchi-2026!", "full_name": "P", "language": "uz", "accept_terms": True})
    assert "dev_verify_url" not in r.json() and r.json()["email_delivery"] == "NOT_CONFIGURED"


def test_admin_can_verify_a_customer_email_by_hand(db, admin, support, customer):
    from app.models import User

    u, _ = customer
    u.email_verified_at = None
    db.commit()
    _, sup = support
    _, adm = admin
    _, cust_api = customer
    assert cust_api.post(f"/api/v1/admin/customers/{u.id}/verify-email").status_code == 403
    r = adm.post(f"/api/v1/admin/customers/{u.id}/verify-email")
    assert r.status_code == 200
    db.expire_all()
    assert db.get(User, u.id).email_verified_at is not None
