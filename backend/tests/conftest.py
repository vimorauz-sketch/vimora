"""Test harness: isolated PostgreSQL database (vimora_test) migrated with Alembic, Redis DB 15."""

from __future__ import annotations

import os
import tempfile

os.environ.update(
    APP_ENV="test",
    DATABASE_URL=os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg://vimora:vimora_dev@127.0.0.1:5432/vimora_test"),
    REDIS_URL=os.environ.get("TEST_REDIS_URL", "redis://127.0.0.1:6379/15"),
    SECRET_KEY="test-secret-key-0123456789abcdef0123456789",
    EMAIL_BACKEND="console",
    LOCAL_STORAGE_PATH=tempfile.mkdtemp(prefix="vimora-test-"),
    CELERY_TASK_ALWAYS_EAGER="true",
    ADMIN_MFA_REQUIRED="false",
    APP_URL="http://testserver",
    FRONTEND_URL="http://testserver",
    API_URL="http://testserver",
    TELEGRAM_BOT_TOKEN="",
    LOG_LEVEL="WARNING",
)
assert "vimora_test" in os.environ["DATABASE_URL"] or os.environ.get("ALLOW_NONSTANDARD_TEST_DB"), "Refusing to run tests against a non-test database"

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select, text  # noqa: E402

from app.core.db import SessionLocal, engine, utcnow  # noqa: E402
from app.core.redis import get_redis  # noqa: E402

KEEP = {"roles", "permissions", "role_permissions", "alembic_version"}


@pytest.fixture(scope="session", autouse=True)
def _migrate():
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "migrations"))
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def _clean():
    with engine.begin() as conn:
        tables = [r[0] for r in conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'")) if r[0] not in KEEP]
        conn.execute(text(f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE"))
    get_redis().flushdb()
    yield


@pytest.fixture
def db():
    s = SessionLocal()
    yield s
    s.close()


class Api:
    """TestClient wrapper that echoes the CSRF cookie like the real frontend does."""

    def __init__(self):
        from app.main import app

        self.c = TestClient(app)

    def _h(self, headers=None):
        h = dict(headers or {})
        tok = self.c.cookies.get("vimora_csrf")
        if tok:
            h["X-CSRF-Token"] = tok
        return h

    def get(self, url, **kw):
        return self.c.get(url, **kw)

    def post(self, url, json=None, headers=None, **kw):
        return self.c.post(url, json=json, headers=self._h(headers), **kw)

    def put(self, url, json=None, headers=None, **kw):
        return self.c.put(url, json=json, headers=self._h(headers), **kw)

    def patch(self, url, json=None, headers=None, **kw):
        return self.c.patch(url, json=json, headers=self._h(headers), **kw)

    def delete(self, url, headers=None, **kw):
        return self.c.delete(url, headers=self._h(headers), **kw)


PASSWORD = "Str0ng!Passw0rd#2026"


def make_user(db, email: str, *, roles: tuple[str, ...] = ("CUSTOMER",), verified: bool = True, name: str = "Test User"):
    from app.models import Role, User, UserProfile, UserRole
    from app.security.crypto import hash_password

    u = User(email=email, password_hash=hash_password(PASSWORD), email_verified_at=utcnow() if verified else None)
    u.profile = UserProfile(full_name=name, language="en")
    db.add(u)
    db.flush()
    for r in roles:
        role = db.scalar(select(Role).where(Role.name == r))
        db.add(UserRole(user_id=u.id, role_id=role.id, created_at=utcnow()))
    db.commit()
    return u


def login(email: str) -> Api:
    api = Api()
    r = api.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return api


@pytest.fixture
def customer(db):
    u = make_user(db, "alice@example.com", name="Alice")
    return u, login(u.email)


@pytest.fixture
def customer2(db):
    u = make_user(db, "bob@example.com", name="Bob")
    return u, login(u.email)


@pytest.fixture
def admin(db):
    u = make_user(db, "owner@example.com", roles=("SUPER_ADMIN",), name="Owner")
    return u, login(u.email)


@pytest.fixture
def support(db):
    u = make_user(db, "support@example.com", roles=("SUPPORT",), name="Support")
    return u, login(u.email)


@pytest.fixture
def catalog(db):
    """One active fixed-price service, one custom-quote service, one disabled service."""
    from app.models import Service, ServiceCategory, ServicePricing

    cat = ServiceCategory(slug="telegram-automation", name={"en": "Telegram & Automation", "uz": "Telegram"}, description={})
    db.add(cat)
    db.flush()
    fixed = Service(slug="telegram-bot", category_id=cat.id, name={"en": "Telegram Bot Development"}, is_active=True, ai_eligible=True, ai_capability="code_generation",
                    required_fields=[{"key": "bot_name", "label": {"en": "Bot name"}, "type": "text", "required": True}])
    fixed.pricing = ServicePricing(pricing_type="FIXED", currency="UZS", base_price_minor=100_000_00, deposit_type="PERCENT", deposit_value=30)
    custom = Service(slug="custom-dev", category_id=cat.id, name={"en": "Custom Development"}, is_active=True)
    custom.pricing = ServicePricing(pricing_type="CUSTOM_QUOTE", currency="UZS")
    disabled = Service(slug="old-service", category_id=cat.id, name={"en": "Old"}, is_active=False)
    disabled.pricing = ServicePricing(pricing_type="FIXED", currency="UZS", base_price_minor=5000_00)
    usd = Service(slug="usd-writing", category_id=cat.id, name={"en": "Writing (USD)"}, is_active=True, ai_eligible=True, ai_capability="document_writing")
    usd.pricing = ServicePricing(pricing_type="PER_UNIT", currency="USD", base_price_minor=1500, unit_label={"en": "page"}, deposit_type="PERCENT", deposit_value=50)
    db.add_all([fixed, custom, disabled, usd])
    db.commit()
    return {"fixed": fixed, "custom": custom, "disabled": disabled, "usd": usd, "category": cat}


def place_fixed_order(api: Api) -> dict:
    r = api.post("/api/v1/orders", json={"service_slug": "telegram-bot", "title": "My shop bot", "description": "A bot that takes orders for my flower shop.",
                                           "requirements": {"bot_name": "FlowerBot"}, "preferred_language": "en"})
    assert r.status_code == 201, r.text
    return r.json()


def accept_quote(api: Api, order: dict) -> dict:
    q = order["quotations"][0]
    r = api.post(f"/api/v1/orders/{order['id']}/quotation/accept", json={"quotation_id": q["id"]})
    assert r.status_code == 200, r.text
    return r.json()
