"""Business model: ONLINE / REMOTE for all of Uzbekistan, LOCAL (printing etc.) only in Qarapchi, pickup & meetup handover."""

import json
from datetime import timedelta

import pytest

from app.core.db import utcnow
from app.models.enums import OrderStatus as S
from tests.conftest import Api, make_user, login

SECRET_ADDRESS = "Qarapchi, Bog'ishamol ko'chasi 17-uy"


def upload(api: Api, name: str, data: bytes):
    return api.c.post("/api/v1/files", files={"file": (name, data)}, data={"purpose": "ORDER_INPUT"}, headers={"X-CSRF-Token": api.c.cookies.get("vimora_csrf")})


@pytest.fixture
def biz(db):
    """The real catalog (100 services, 5 areas) and a pickup address only the owner knows."""
    from app.cli import seed_catalog
    from app.models import ServiceArea

    assert seed_catalog() == 0
    q = db.query(ServiceArea).filter_by(slug="qarapchi").one()
    q.pickup_address = SECRET_ADDRESS
    db.commit()
    return db


def soon(hours=30):
    return (utcnow() + timedelta(hours=hours)).isoformat()


def pdf(api):
    r = upload(api, "kurs-ishi.pdf", b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n")
    assert r.status_code == 201, r.text
    return r.json()["id"]


def local_order(api, *, area="qarapchi", method="PICKUP", **extra):
    body = {"service_slug": "document-printing", "title": "Kurs ishi", "description": "20 betlik kurs ishini chop etish kerak.",
            "requirements": {"copies": 2, "color": "bw"}, "attachment_ids": [pdf(api)], "area": area, "handover_method": method, **extra}
    return api.post("/api/v1/orders", json=body)


def quote_and_accept(adm: Api, api: Api, oid: int, total=20_000_00):
    r = adm.post(f"/api/v1/admin/orders/{oid}/quotations", json={"currency": "UZS", "line_items": [{"description": "Print", "quantity": 1, "unit_price_minor": total}], "deposit_percent": 0})
    assert r.status_code == 201, r.text
    o = api.get(f"/api/v1/orders/{oid}").json()
    r = api.post(f"/api/v1/orders/{oid}/quotation/accept", json={"quotation_id": o["quotations"][0]["id"]})
    assert r.status_code == 200, r.text
    return r.json()


def start_and_complete(adm: Api, oid: int):
    assert adm.post(f"/api/v1/admin/orders/{oid}/status", json={"to_status": S.MANUAL_PROCESSING}).status_code == 200
    r = adm.post(f"/api/v1/admin/orders/{oid}/complete")
    assert r.status_code == 200, r.text
    return r.json()


# 1, 2 -------------------------------------------------------------- ONLINE / REMOTE from anywhere
@pytest.mark.parametrize("slug,area", [("translation", "other"), ("logo-design", "zomin-city"), ("windows-install", "other"), ("drivers-install", "jizzakh-region")])
def test_online_and_remote_services_can_be_ordered_from_any_area(biz, customer, slug, area):
    _, api = customer
    r = api.post("/api/v1/orders", json={"service_slug": slug, "title": "Ish", "description": "Toshkentdan buyurtma, masofadan bajarilsin.", "area": area})
    assert r.status_code == 201, r.text
    assert r.json()["is_local"] is False and r.json()["handover"] is None and r.json()["area"]["slug"] == area


# 3, 6 -------------------------------------------------------------- LOCAL from Qarapchi, pickup
def test_local_pickup_order_from_qarapchi_full_flow_with_cash(biz, customer, admin):
    _, api = customer
    _, adm = admin
    r = local_order(api)
    assert r.status_code == 201, r.text
    o = r.json()
    assert o["is_local"] and o["handover_method"] == "PICKUP" and o["handover"]["status"] == "WAITING"
    assert o["handover"]["pickup_address"] is None  # private until the work is ready
    quote_and_accept(adm, api, o["id"])
    d = start_and_complete(adm, o["id"])  # paper result: no digital deliverable needed
    assert d["status"] == S.FINAL_PAYMENT_PENDING and d["handover"]["status"] == "READY_FOR_PICKUP"
    o = api.get(f"/api/v1/orders/{o['id']}").json()
    assert o["handover"]["pickup_address"] == SECRET_ADDRESS  # now the customer may come
    # 9. handing over before the money is recorded is refused
    r = adm.post(f"/api/v1/admin/orders/{o['id']}/handover/complete")
    assert r.status_code == 409 and r.json()["error"]["code"] == "BALANCE_OUTSTANDING"
    # cash at pickup is recorded as a manual payment (verified path, never by the customer)
    assert adm.post(f"/api/v1/admin/orders/{o['id']}/manual-payment", json={"amount_minor": 20_000_00, "reference": "NAQD-001"}).status_code == 201
    assert api.get(f"/api/v1/orders/{o['id']}").json()["status"] == S.READY_FOR_DELIVERY
    # 10. handed over -> completed
    r = adm.post(f"/api/v1/admin/orders/{o['id']}/handover/complete")
    assert r.status_code == 200, r.text
    o = api.get(f"/api/v1/orders/{o['id']}").json()
    assert o["status"] == S.DELIVERED and o["handover"]["status"] == "HANDED_OVER" and o["payment_status"] == "PAID"
    assert o["handover"]["pickup_address"] is None  # not shown any more after the handover
    assert api.post(f"/api/v1/orders/{o['id']}/close").status_code == 200


# 4, 5, 11 ---------------------------------------------------------- LOCAL refused outside Qarapchi
@pytest.mark.parametrize("area", ["zomin-city", "zomin-district", "other", "jizzakh-region"])
def test_local_order_from_outside_qarapchi_is_rejected_by_the_backend(biz, customer, db, area):
    from app.models import Order

    _, api = customer
    r = local_order(api, area=area)
    assert r.status_code == 400 and r.json()["error"]["code"] == "SERVICE_NOT_IN_AREA"
    assert db.query(Order).count() == 0  # nothing was created


def test_local_order_needs_an_area_and_a_valid_handover(biz, customer):
    _, api = customer
    body = {"service_slug": "photocopy", "title": "Nusxa", "description": "Pasport nusxasi kerak, 3 ta.", "requirements": {"copies": 3, "color": "bw", "originals": "pasport"}}
    assert api.post("/api/v1/orders", json=body).json()["error"]["code"] == "AREA_REQUIRED"
    assert api.post("/api/v1/orders", json={**body, "area": "qarapchi"}).json()["error"]["code"] == "HANDOVER_REQUIRED"
    assert api.post("/api/v1/orders", json={**body, "area": "nowhere", "handover_method": "PICKUP"}).json()["error"]["code"] == "INVALID_AREA"
    # pickup/meetup make no sense for online services
    r = api.post("/api/v1/orders", json={"service_slug": "translation", "title": "T", "description": "Tarjima kerak, 3 bet.", "area": "qarapchi", "handover_method": "PICKUP"})
    assert r.json()["error"]["code"] == "HANDOVER_NOT_APPLICABLE"
    # a local area that has local services switched off rejects too (admin closes Qarapchi temporarily)
    assert api.post("/api/v1/orders", json={**body, "area": "qarapchi", "handover_method": "PICKUP"}).status_code == 201


# 7, 8 -------------------------------------------------------------- meetup: propose, counter, confirm
def test_meetup_order_proposal_counter_proposal_and_confirmation(biz, customer, admin):
    _, api = customer
    _, adm = admin
    r = local_order(api, method="MEETUP")
    assert r.json()["error"]["code"] == "INVALID_MEETUP"  # place and time are required
    r = local_order(api, method="MEETUP", meetup_place="Maktab oldida", meetup_time=soon())
    assert r.status_code == 201, r.text
    o = r.json()
    assert o["handover"]["status"] == "PROPOSED_BY_CUSTOMER" and o["handover"]["proposal"]["place"] == "Maktab oldida"
    assert o["handover"]["pickup_address"] is None  # meetup orders never see the home address
    # owner suggests another place
    r = adm.post(f"/api/v1/admin/orders/{o['id']}/handover/propose", json={"place": "Guzar, do'kon yonida", "time": soon(48)})
    assert r.status_code == 200 and r.json()["handover"]["status"] == "PROPOSED_BY_ADMIN"
    assert adm.post(f"/api/v1/admin/orders/{o['id']}/handover/confirm").status_code == 409  # nothing from the customer to confirm now
    # customer accepts
    r = api.post(f"/api/v1/orders/{o['id']}/handover/accept")
    assert r.status_code == 200 and r.json()["handover"]["status"] == "CONFIRMED" and r.json()["handover"]["agreed"]["place"] == "Guzar, do'kon yonida"
    # customer can re-propose; owner confirms
    assert api.post(f"/api/v1/orders/{o['id']}/handover/propose", json={"place": "Maktab oldida", "time": soon(50)}).json()["handover"]["status"] == "PROPOSED_BY_CUSTOMER"
    assert adm.post(f"/api/v1/admin/orders/{o['id']}/handover/confirm").json()["handover"]["status"] == "CONFIRMED"
    # past times are refused
    assert api.post(f"/api/v1/orders/{o['id']}/handover/propose", json={"place": "X joy", "time": (utcnow() - timedelta(days=1)).isoformat()}).status_code == 400
    assert api.get(f"/api/v1/orders/{o['id']}").json()["handover"]["status"] == "CONFIRMED"
    # full flow: quote, work, cash, hand over at the agreed place
    quote_and_accept(adm, api, o["id"])
    start_and_complete(adm, o["id"])
    adm.post(f"/api/v1/admin/orders/{o['id']}/manual-payment", json={"amount_minor": 20_000_00, "reference": "NAQD-002"})
    assert adm.post(f"/api/v1/admin/orders/{o['id']}/handover/complete").status_code == 200
    assert api.get(f"/api/v1/orders/{o['id']}").json()["status"] == S.DELIVERED


def test_meetup_must_be_confirmed_before_handover(biz, customer, admin):
    _, api = customer
    _, adm = admin
    o = local_order(api, method="MEETUP", meetup_place="Maktab oldida", meetup_time=soon()).json()
    quote_and_accept(adm, api, o["id"])
    start_and_complete(adm, o["id"])
    adm.post(f"/api/v1/admin/orders/{o['id']}/manual-payment", json={"amount_minor": 20_000_00, "reference": "NAQD-003"})
    r = adm.post(f"/api/v1/admin/orders/{o['id']}/handover/complete")
    assert r.status_code == 409 and r.json()["error"]["code"] == "MEETUP_NOT_CONFIRMED"
    # local orders cannot be "released" like digital ones, and DELIVERED cannot be forced
    assert adm.post(f"/api/v1/admin/orders/{o['id']}/release").json()["error"]["code"] == "USE_HANDOVER"
    assert adm.post(f"/api/v1/admin/orders/{o['id']}/status", json={"to_status": S.DELIVERED}).status_code == 409


def test_other_customers_cannot_touch_a_handover(biz, customer, customer2):
    _, api = customer
    _, other = customer2
    o = local_order(api, method="MEETUP", meetup_place="Maktab oldida", meetup_time=soon()).json()
    assert other.get(f"/api/v1/orders/{o['id']}").status_code == 404
    assert other.post(f"/api/v1/orders/{o['id']}/handover/propose", json={"place": "Boshqa joy", "time": soon()}).status_code == 404


# 11 ----------------------------------------------------------------- catalog & areas
def test_catalog_filters_and_area_availability(biz, customer):
    _, api = customer
    areas = api.get("/api/v1/catalog/areas").json()["items"]
    assert [a["slug"] for a in areas] == ["qarapchi", "zomin-city", "zomin-district", "jizzakh-region", "other"]
    assert [a["slug"] for a in areas if a["local_services_enabled"]] == ["qarapchi"]
    local = api.get("/api/v1/catalog/services?mode=LOCAL&page_size=60").json()
    assert sorted(s["slug"] for s in local["items"]) == ["book-printing", "document-printing", "photocopy", "scanning"]
    assert all(s["service_area"]["slug"] == "qarapchi" for s in local["items"])
    remote = api.get("/api/v1/catalog/services?mode=REMOTE&page_size=60").json()
    assert remote["total"] == 13 and all(s["mode"] == "REMOTE" for s in remote["items"])
    everything = api.get("/api/v1/catalog/services?page_size=60").json()["total"]
    in_tashkent = api.get("/api/v1/catalog/services?area=other&page_size=60").json()
    in_qarapchi = api.get("/api/v1/catalog/services?area=qarapchi&page_size=60").json()
    assert in_qarapchi["total"] == everything == in_tashkent["total"] + 4
    assert all(s["available_in_area"] for s in in_tashkent["items"]) and not any(s["mode"] == "LOCAL" for s in in_tashkent["items"])
    # FUTURE / DISABLED are never listed or orderable
    slugs = {s["slug"] for p in (1, 2) for s in api.get(f"/api/v1/catalog/services?page_size=60&page={p}").json()["items"]}
    assert "phone-setup" not in slugs and "ai-text" not in slugs
    r = api.post("/api/v1/orders", json={"service_slug": "phone-setup", "title": "Tel", "description": "Telefon sozlash kerak edi."})
    assert r.json()["error"]["code"] == "SERVICE_UNAVAILABLE"


def test_owner_home_address_never_leaks_through_public_endpoints(biz, customer):
    _, api = customer
    blobs = [api.get("/api/v1/catalog/areas").text, api.get("/api/v1/catalog/services?mode=LOCAL").text,
             api.get("/api/v1/catalog/services/document-printing").text, api.get("/api/v1/public/settings").text if api.get("/api/v1/public/settings").status_code == 200 else ""]
    assert all(SECRET_ADDRESS not in b and "pickup_address" not in b for b in blobs)


# 12 ----------------------------------------------------------------- admin permissions
def test_area_and_service_admin_changes_are_permission_checked(biz, customer, support, admin):
    from app.models import ServiceArea

    _, api = customer
    _, sup = support
    _, adm = admin
    qid = biz.query(ServiceArea).filter_by(slug="qarapchi").one().id
    body = {"slug": "qarapchi", "kind": "LOCALITY", "name": {"uz": "Qarapchi", "en": "Qarapchi", "ru": "Карапчи"}, "local_services_enabled": True}
    assert api.get("/api/v1/admin/areas").status_code == 403
    assert api.put(f"/api/v1/admin/areas/{qid}", json=body).status_code == 403
    assert sup.put(f"/api/v1/admin/areas/{qid}", json=body).status_code == 403  # support may view, not change
    assert all("pickup_address" not in a for a in sup.get("/api/v1/admin/areas").json()["items"])
    owner_view = adm.get("/api/v1/admin/areas").json()["items"]
    assert next(a for a in owner_view if a["slug"] == "qarapchi")["pickup_address"] == SECRET_ADDRESS
    # owner opens Zomin for local services later -> only then is a Zomin order accepted (here: still closed)
    zomin = next(a for a in owner_view if a["slug"] == "zomin-city")
    assert zomin["local_services_enabled"] is False
    # a LOCAL service cannot be pointed at an area without local services
    svc = adm.get("/api/v1/admin/services?q=document-printing").json()["items"][0]
    full = adm.get(f"/api/v1/admin/services/{svc['id']}").json()
    payload = {k: v for k, v in full.items() if k not in ("id", "category", "image_url", "image_credit", "archived_at", "order_count", "capabilities", "mode",
                                                            "availability_status", "service_area")}
    payload["service_area_id"] = zomin["id"]
    r = adm.put(f"/api/v1/admin/services/{svc['id']}", json=payload)
    assert r.status_code == 400 and r.json()["error"]["code"] == "AREA_NOT_LOCAL"
    assert sup.put(f"/api/v1/admin/services/{svc['id']}", json=payload).status_code == 403


# 13 ----------------------------------------------------------------- files
def test_printing_requires_a_file_and_rejects_dangerous_files(biz, customer):
    _, api = customer
    body = {"service_slug": "document-printing", "title": "Chop", "description": "Hujjat chop etish kerak, 2 nusxa.", "requirements": {"copies": 2, "color": "color"},
            "area": "qarapchi", "handover_method": "PICKUP"}
    assert api.post("/api/v1/orders", json=body).json()["error"]["code"] == "FILE_REQUIRED"
    r = upload(api, "virus.exe", b"MZ\x90\x00" + b"\x00" * 200)
    assert r.status_code in (400, 415, 422)
    r = upload(api, "fake.pdf", b"MZ\x90\x00" + b"\x00" * 200)  # disguised executable
    assert r.status_code in (400, 415, 422)
    # wrong option values are refused
    r = api.post("/api/v1/orders", json={**body, "requirements": {"copies": 2, "color": "rainbow"}, "attachment_ids": [pdf(api)]})
    assert r.json()["error"]["code"] == "INVALID_REQUIREMENT"


# 14 ----------------------------------------------------------------- payments
def test_cash_payment_reference_cannot_be_counted_twice(biz, customer, admin):
    _, api = customer
    _, adm = admin
    o = local_order(api).json()
    quote_and_accept(adm, api, o["id"])
    start_and_complete(adm, o["id"])
    # cash must match what is due: no arbitrary amounts
    r = adm.post(f"/api/v1/admin/orders/{o['id']}/manual-payment", json={"amount_minor": 5_000_00, "reference": "NAQD-777"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "AMOUNT_MISMATCH"
    assert api.get(f"/api/v1/orders/{o['id']}").json()["paid_minor"] == 0  # not marked as paid
    assert adm.post(f"/api/v1/admin/orders/{o['id']}/manual-payment", json={"amount_minor": 20_000_00, "reference": "NAQD-777"}).status_code == 201
    r = adm.post(f"/api/v1/admin/orders/{o['id']}/manual-payment", json={"amount_minor": 20_000_00, "reference": "NAQD-777"})
    assert r.status_code == 409  # the same cash is never counted twice
    d = api.get(f"/api/v1/orders/{o['id']}").json()
    assert d["paid_minor"] == 20_000_00 and d["status"] == S.READY_FOR_DELIVERY
    # the customer cannot record payments or hand over
    assert api.post(f"/api/v1/admin/orders/{o['id']}/manual-payment", json={"amount_minor": 15_000_00, "reference": "FAKE-1"}).status_code == 403
    assert api.post(f"/api/v1/admin/orders/{o['id']}/handover/complete").status_code == 403


# 15 ----------------------------------------------------------------- AI must respect the area rule
def test_assistant_never_offers_qarapchi_printing_elsewhere(biz, monkeypatch):
    from app.ai import assistant
    from app.ai import manager as ai_manager

    api = Api()
    # keyword fallback (AI off)
    r = api.post("/api/v1/ai/assist", json={"message": "Kitob chop etish kerak", "language": "uz", "area": "other"}).json()
    assert all(s["slug"] not in ("book-printing", "document-printing") for s in r["suggestions"])
    assert r["area_notice"] and "Qarapchi" in r["area_notice"]
    r = api.post("/api/v1/ai/assist", json={"message": "Kitob chop etish kerak", "language": "uz", "area": "qarapchi"}).json()
    assert any(s["slug"] == "book-printing" for s in r["suggestions"]) and not r["area_notice"]

    # AI on, and the model "wrongly" recommends the local service to a Tashkent customer
    class Res:
        text = json.dumps({"reply": "Albatta, kitobingizni chop etib beramiz!", "suggested_service_slug": "book-printing", "category_slug": "printing-local",
                           "recommend_custom_order": False, "complexity": "low", "clarifying_questions": []})

    monkeypatch.setattr(assistant, "get_ai_assistant_ready", lambda db: True)
    monkeypatch.setattr(ai_manager, "call", lambda *a, **k: Res())
    r = api.post("/api/v1/ai/assist", json={"message": "Toshkentdaman, kitob chiqarib bering", "language": "uz", "area": "other"}).json()
    assert [s["slug"] for s in r["suggestions"]] == ["word-formatting", "pdf-convert"]
    assert "chop etib beramiz" not in r["reply"] and "faqat Qarapchi" in r["reply"]
    assert r["indicative_price"]["type"] == "QUANTITY_TIERED"  # the catalog price of the suggested service; the AI never sets prices


def test_admin_local_board_counts_and_filters(biz, customer, admin):
    _, api = customer
    _, adm = admin
    local_order(api)
    local_order(api, method="MEETUP", meetup_place="Maktab oldida", meetup_time=soon())
    api.post("/api/v1/orders", json={"service_slug": "translation", "title": "T", "description": "Online tarjima kerak, 2 bet.", "area": "other"})
    s = adm.get("/api/v1/admin/orders/local-summary").json()
    assert s["new"] == 2 and s["arranging"] == 1
    assert adm.get("/api/v1/admin/orders?local=true").json()["total"] == 2
    assert adm.get("/api/v1/admin/orders?local=true&handover_method=MEETUP").json()["total"] == 1
    assert adm.get("/api/v1/admin/orders?local=true&local_stage=arranging").json()["total"] == 1
    feed = adm.get("/api/v1/admin/activity").json()["items"]
    assert any(i["event_type"] == "order.created" for i in feed)


def test_new_admin_and_customer_notifications(biz, customer, admin, db):
    from app.models import Notification

    _, api = customer
    _, adm = admin
    o = local_order(api, method="MEETUP", meetup_place="Maktab oldida", meetup_time=soon()).json()
    api.post(f"/api/v1/orders/{o['id']}/handover/propose", json={"place": "Guzar", "time": soon(40)})
    adm.post(f"/api/v1/admin/orders/{o['id']}/handover/confirm")
    att = pdf(api)
    assert api.post(f"/api/v1/orders/{o['id']}/attachments", json={"attachment_ids": [att]}).status_code == 200
    events = {n.event_type for n in db.query(Notification).all()}
    assert {"order.created", "handover.proposed", "handover.confirmed", "file.received"} <= events
    # deadline reminder job
    from app.models import Order
    from app.tasks.jobs import deadline_reminders

    od = db.get(Order, o["id"])
    od.deadline = utcnow() + timedelta(hours=5)
    db.commit()
    assert deadline_reminders() == 1
    deadline_reminders()  # idempotent per order/deadline
    assert db.query(Notification).filter_by(event_type="order.deadline_soon").count() == 1


def test_owner_can_open_another_area_later(biz, admin, db):
    """Expansion path: when the owner enables local services in Zomin and points a service there, Zomin can order it."""
    from app.models import Service, ServiceArea

    _, adm = admin
    z = db.query(ServiceArea).filter_by(slug="zomin-city").one()
    z.local_services_enabled = True
    svc = db.query(Service).filter_by(slug="photocopy").one()
    svc.service_area_id = z.id
    db.commit()
    u = make_user(db, "zomin@example.com", name="Z")
    api = login(u.email)
    body = {"service_slug": "photocopy", "title": "Nusxa", "description": "Pasport nusxasi kerak, 3 ta.", "requirements": {"copies": 3, "color": "bw", "originals": "pasport"},
            "handover_method": "PICKUP"}
    assert api.post("/api/v1/orders", json={**body, "area": "zomin-city"}).status_code == 201
    assert api.post("/api/v1/orders", json={**body, "area": "qarapchi"}).json()["error"]["code"] == "SERVICE_NOT_IN_AREA"


def test_catalog_search_is_case_insensitive_ranked_and_safe(biz, customer):
    _, api = customer
    def names(q, lang="uz"):
        return [s["name"] for s in api.get("/api/v1/catalog/services", params={"q": q, "lang": lang, "page_size": 60}).json()["items"]]
    # a single first letter already finds services, upper/lower case alike, names starting with it first
    first = names("w")
    assert first and first == names("W")
    assert first[0].lower().startswith("w")
    # any apostrophe works for Uzbek o'/g'
    assert names("o‘rnat") == names("o'rnat") and names("o'rnat")
    # LIKE wildcards are searched literally
    assert names("%") == [] and names("_") == []
    # longer queries also match other languages
    assert names("print", "uz")
