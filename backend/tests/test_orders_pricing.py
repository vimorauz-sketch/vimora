import pytest
from sqlalchemy import select, text

from app.models import Order, PromoCode
from app.models.enums import ActorType as A
from app.models.enums import OrderStatus as S
from app.services import order_state
from app.services.pricing import build_manual_quote, compute_deposit, format_money, pct_of
from tests.conftest import accept_quote, place_fixed_order


# ------------------------------------------------------------------ pricing unit tests
def test_integer_money_math():
    assert pct_of(100_000_00, 30) == 30_000_00
    assert pct_of(333, 50) == 167  # half-up
    assert compute_deposit(100_000_00, "PERCENT", 30, "UZS") == 30_000_00
    assert compute_deposit(10_051, "PERCENT", 30, "UZS") == 3100  # 30.153 sum -> rounded up to 31 sum
    assert compute_deposit(5000, "FIXED", 999999, "UZS") == 5000  # never above total
    assert format_money(100_000_00, "UZS") == "100 000 UZS"
    assert format_money(1999, "USD") == "$19.99"


def test_manual_quote_recomputes_totals():
    pr = build_manual_quote([{"description": "Bot", "quantity": 2, "unit_price_minor": 50_000_00}], currency="UZS", discount_minor=10_000_00, extra_charges_minor=5_000_00, deposit_percent=30)
    assert pr.subtotal_minor == 100_000_00 and pr.total_minor == 95_000_00 and pr.deposit_minor == 28_500_00
    with pytest.raises(Exception):
        build_manual_quote([{"description": "x", "quantity": 1, "unit_price_minor": 100}], currency="UZS", discount_minor=1000)
    with pytest.raises(Exception):
        build_manual_quote([{"description": "x", "quantity": 1, "unit_price_minor": 100}], currency="EUR")


def test_price_preview_is_server_side(customer, catalog):
    _, api = customer
    r = api.post("/api/v1/catalog/price", json={"service_slug": "usd-writing", "quantity": 4})
    body = r.json()
    assert body["total_minor"] == 6000 and body["deposit_minor"] == 3000 and body["currency"] == "USD"
    # clients cannot submit prices: unknown fields are rejected
    r = api.post("/api/v1/catalog/price", json={"service_slug": "usd-writing", "quantity": 4, "price": 1})
    assert r.status_code == 422


def test_promo_code_applied_once_per_user(customer, catalog, db):
    u, api = customer
    db.add(PromoCode(code="WELCOME10", percent_off=10, max_uses_per_user=1))
    db.commit()
    o = api.post("/api/v1/orders", json={"service_slug": "telegram-bot", "title": "Bot", "description": "A bot for my shop please.", "requirements": {"bot_name": "B"}, "promo_code": "welcome10"}).json()
    q = o["quotations"][0]
    assert q["discount_minor"] == 10_000_00 and q["total_minor"] == 90_000_00
    accept_quote(api, o)
    r = api.post("/api/v1/orders", json={"service_slug": "telegram-bot", "title": "Bot2", "description": "A second bot for my shop.", "requirements": {"bot_name": "B"}, "promo_code": "WELCOME10"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "PROMO_EXHAUSTED"


# ------------------------------------------------------------------ order lifecycle
def test_fixed_service_order_gets_engine_quotation(customer, catalog, db):
    _, api = customer
    o = place_fixed_order(api)
    assert o["status"] == S.QUOTATION_PENDING
    assert o["order_number"].startswith("VM-") and len(o["order_number"]) == 13
    q = o["quotations"][0]
    assert q["total_minor"] == 100_000_00 and q["deposit_minor"] == 30_000_00 and q["source"] == "PRICING_ENGINE"
    o = accept_quote(api, o)
    assert o["status"] == S.DEPOSIT_PENDING
    assert o["payment_due"] == {"kind": "DEPOSIT", "amount_minor": 30_000_00, "currency": "UZS", "full_amount_minor": 100_000_00}
    # every status change produced an event and an audit entry
    events = db.execute(text("SELECT count(*) FROM order_events WHERE event_type='STATUS_CHANGED'")).scalar()
    audits = db.execute(text("SELECT count(*) FROM audit_logs WHERE action='order.status_changed'")).scalar()
    assert events == audits == 5  # DRAFT>SUBMITTED>UNDER_REVIEW>QUOTATION_PENDING>QUOTATION_ACCEPTED>DEPOSIT_PENDING


def test_accepted_quotation_not_changed_by_later_price_change(customer, catalog, db, admin):
    _, api = customer
    o = accept_quote(api, place_fixed_order(api))
    catalog["fixed"].pricing.base_price_minor = 999_999_00
    db.commit()
    again = api.get(f"/api/v1/orders/{o['id']}").json()
    assert again["total_minor"] == 100_000_00


def test_required_fields_enforced(customer, catalog):
    _, api = customer
    r = api.post("/api/v1/orders", json={"service_slug": "telegram-bot", "title": "Bot", "description": "A bot that does things."})
    assert r.status_code == 400 and r.json()["error"]["code"] == "MISSING_REQUIREMENT"


def test_disabled_service_rejects_orders(customer, catalog):
    _, api = customer
    r = api.post("/api/v1/orders", json={"service_slug": "old-service", "title": "x", "description": "Something to do here."})
    assert r.status_code == 400 and r.json()["error"]["code"] == "SERVICE_UNAVAILABLE"


def test_custom_order_requires_admin_quotation(customer, admin, catalog):
    _, api = customer
    o = api.post("/api/v1/orders", json={"title": "Scrape my supplier site", "description": "I need a script that collects product prices daily from a site.", "category_slug": "telegram-automation"}).json()
    assert o["status"] == S.SUBMITTED and o["is_custom"] and o["quotations"] == []
    _, adm = admin
    r = adm.post(f"/api/v1/admin/orders/{o['id']}/quotations", json={"currency": "UZS", "line_items": [{"description": "Scraper", "quantity": 1, "unit_price_minor": 250_000_00}], "deposit_percent": 40})
    assert r.status_code == 201, r.text
    o = api.get(f"/api/v1/orders/{o['id']}").json()
    assert o["status"] == S.QUOTATION_PENDING and o["quotations"][0]["deposit_minor"] == 100_000_00
    # customer rejects -> back to review; then a new quote supersedes
    q = o["quotations"][0]
    assert api.post(f"/api/v1/orders/{o['id']}/quotation/reject", json={"quotation_id": q["id"], "reason": "Too expensive"}).json()["status"] == S.UNDER_REVIEW
    adm.post(f"/api/v1/admin/orders/{o['id']}/quotations", json={"currency": "UZS", "line_items": [{"description": "Scraper", "quantity": 1, "unit_price_minor": 200_000_00}]})
    o = api.get(f"/api/v1/orders/{o['id']}").json()
    assert o["quotations"][0]["total_minor"] == 200_000_00
    # old rejected quote cannot be accepted
    r = api.post(f"/api/v1/orders/{o['id']}/quotation/accept", json={"quotation_id": q["id"]})
    assert r.status_code == 409


def test_customer_cannot_set_status_or_prices(customer, catalog):
    _, api = customer
    r = api.post("/api/v1/orders", json={"service_slug": "telegram-bot", "title": "Bot", "description": "A bot for my shop.", "requirements": {"bot_name": "B"},
                                          "status": "PAID", "total_minor": 1})
    assert r.status_code == 422  # mass assignment blocked
    o = place_fixed_order(api)
    # no customer endpoint changes status arbitrarily
    assert api.post(f"/api/v1/admin/orders/{o['id']}/status", json={"to_status": "PAID"}).status_code == 403


def test_state_machine_rejects_invalid_and_payment_only_transitions(customer, catalog, db):
    _, api = customer
    o = accept_quote(api, place_fixed_order(api))
    order = db.get(Order, o["id"])
    with pytest.raises(Exception) as e:
        order_state.transition(db, order, S.PAID, actor_type=A.ADMIN)  # admins cannot mark paid
    assert "Cannot move" in str(e.value)
    with pytest.raises(Exception):
        order_state.transition(db, order, S.DELIVERED, actor_type=A.ADMIN)
    assert order_state.can_transition(S.DEPOSIT_PENDING, S.PARTIALLY_PAID, A.PAYMENT)
    assert not order_state.can_transition(S.DEPOSIT_PENDING, S.PARTIALLY_PAID, A.CUSTOMER)
    assert not order_state.can_transition(S.CANCELLED, S.QUEUED, A.ADMIN)  # rule 14


def test_admin_dedicated_actions_required(customer, admin, catalog):
    _, api = customer
    o = accept_quote(api, place_fixed_order(api))
    _, adm = admin
    r = adm.post(f"/api/v1/admin/orders/{o['id']}/status", json={"to_status": "DELIVERED"})
    assert r.status_code == 409
    r = adm.post(f"/api/v1/admin/orders/{o['id']}/status", json={"to_status": "QUEUED"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"


def test_customer_cancel_rules(customer, catalog):
    _, api = customer
    o = place_fixed_order(api)
    r = api.post(f"/api/v1/orders/{o['id']}/cancel", json={"reason": "changed my mind"})
    assert r.json()["status"] == S.CANCELLED
    assert api.post(f"/api/v1/orders/{o['id']}/quotation/accept", json={"quotation_id": o["quotations"][0]["id"]}).status_code == 409


def test_audit_and_event_tables_are_append_only(customer, catalog, db):
    _, api = customer
    place_fixed_order(api)
    for stmt in ("UPDATE audit_logs SET action='x'", "DELETE FROM audit_logs", "UPDATE order_events SET message='x'", "DELETE FROM order_events"):
        with pytest.raises(Exception) as e:
            db.execute(text(stmt))
        assert "append-only" in str(e.value)
        db.rollback()


def test_customer_overview_counts_real_records(customer, catalog):
    _, api = customer
    place_fixed_order(api)
    ov = api.get("/api/v1/orders/overview").json()
    assert ov["total"] == 1 and ov["action_needed"] == 1


def test_seed_catalog_is_visible_idempotent_and_uses_only_the_owners_suggested_prices(db):
    from app.cli import seed_catalog
    from app.catalog_data import SERVICES
    from app.models import Service

    assert seed_catalog() == 0
    assert seed_catalog() == 0  # re-run is safe
    rows = db.scalars(select(Service)).unique().all()
    assert len(rows) == len(SERVICES) >= 90
    from app.catalog_prices import PRICES, suggestion
    # prices come only from the owner's suggested price list; everything else stays an individual quote
    for s in rows:
        sug = suggestion(s.slug)
        if sug is None:
            assert s.pricing.pricing_type == "CUSTOM_QUOTE" and s.pricing.base_price_minor == 0
        else:
            assert (s.pricing.pricing_type, s.pricing.base_price_minor) == (sug["pricing_type"], sug["base_price_minor"])
    assert set(PRICES) <= {s.slug for s in rows}  # no suggestion for a slug that does not exist
    assert db.get(Service, next(r.id for r in rows if r.slug == "custom-task")).pricing.pricing_type == "CUSTOM_QUOTE"
    # business model: every service is classified; only ONLINE / REMOTE / LOCAL services are orderable
    from app.catalog_data import mode_for
    assert all(s.service_mode == mode_for(s.slug) for s in rows)
    assert all(s.is_active == (s.service_mode in ("ONLINE", "REMOTE", "LOCAL")) for s in rows)
    assert all((s.archived_at is not None) == (s.service_mode == "DISABLED") for s in rows)
    assert all(s.service_area is not None and s.service_area.slug == "qarapchi" for s in rows if s.service_mode == "LOCAL")
    assert all(s.service_area_id is None for s in rows if s.service_mode != "LOCAL")
    rows = [r for r in rows if r.is_active]
    # owner edits to an active service survive a re-run
    s = rows[0]
    s.name = {"uz": "Mening nomim", "en": "x", "ru": "x"}
    db.commit()
    seed_catalog()
    db.expire_all()
    assert db.get(Service, s.id).name["uz"] == "Mening nomim"
    # no automatic stock photos (services use illustrations); old automatic ones are removed, an admin's own choice is kept
    from app.catalog_photos import LEGACY_DEFAULT_URLS
    assert all(r.cover_image_url is None for r in rows)
    other = rows[1]
    other.cover_image_url = next(iter(LEGACY_DEFAULT_URLS))
    db.commit()
    seed_catalog()
    db.expire_all()
    assert db.get(Service, other.id).cover_image_url is None
    svc = db.get(Service, s.id)
    svc.cover_image_url = "https://images.unsplash.com/photo-own?w=900"
    db.commit()
    seed_catalog()
    db.expire_all()
    assert db.get(Service, s.id).cover_image_url == "https://images.unsplash.com/photo-own?w=900"


def test_admin_prices_page_edit_and_suggestions(db, admin):
    from app.cli import seed_catalog
    from app.models import Service

    seed_catalog()
    _, api = admin
    data = api.get("/api/v1/admin/pricing?lang=uz").json()
    assert data["suggestable"] == 0  # the seed already priced everything it has a suggestion for
    row = next(i for i in data["items"] if i["slug"] == "logo-design")
    assert row["pricing"]["pricing_type"] == "STARTING_FROM" and row["suggested"]["base_price_minor"] == 400_000_00
    # quick edit, validated and audited
    body = {**row["pricing"], "base_price_minor": 550_000_00, "addons": []}
    r = api.put(f"/api/v1/admin/pricing/{row['id']}", json=body)
    assert r.status_code == 200 and r.json()["pricing"]["base_price_minor"] == 550_000_00
    assert api.put(f"/api/v1/admin/pricing/{row['id']}", json={**body, "pricing_type": "FIXED", "base_price_minor": 0}).json()["error"]["code"] == "INVALID_PRICING"
    # "fill unpriced" never overwrites the owner's price; choosing the suggestion for one service does
    svc = db.scalars(select(Service).where(Service.slug == "translation")).one()
    svc.pricing.pricing_type, svc.pricing.base_price_minor = "CUSTOM_QUOTE", 0
    db.commit()
    r = api.post("/api/v1/admin/pricing/apply-suggested", json={}).json()
    assert r["service_ids"] == [svc.id]
    db.expire_all()
    assert db.get(Service, row["id"]).pricing.base_price_minor == 550_000_00
    assert api.post("/api/v1/admin/pricing/apply-suggested", json={"service_ids": [row["id"]]}).json()["changed"] == 1
    db.expire_all()
    assert db.get(Service, row["id"]).pricing.base_price_minor == 400_000_00
    # the public price follows
    assert api.post("/api/v1/catalog/price", json={"service_slug": "translation", "quantity": 12}).json()["total_minor"] == 12 * 30_000_00


def test_prices_page_needs_permission(db, customer, support):
    _, c = customer
    assert c.get("/api/v1/admin/pricing").status_code in (401, 403)
    assert c.post("/api/v1/admin/pricing/apply-suggested", json={}).status_code in (401, 403)
    _, s = support  # staff without services.manage may look but not change prices
    assert s.post("/api/v1/admin/pricing/apply-suggested", json={}).status_code == 403
