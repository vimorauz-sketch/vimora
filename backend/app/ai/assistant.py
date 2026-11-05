"""Customer-facing AI task assistant (public AI Assistant page).

Never promises completion or a guaranteed price. Price information shown to customers comes
from the admin-configured catalog, not from the model.
"""

from __future__ import annotations

import json
import re

from sqlalchemy import String, cast, or_, select
from sqlalchemy.orm import Session as DB

from app.ai import manager, prompts
from app.core.errors import ConfigurationRequired
from app.core.i18n import pick
from app.models import Service, ServiceCategory
from app.services.pricing import format_money

LANG_NAME = {"uz": "Uzbek", "en": "English", "ru": "Russian"}


def _catalog_rows(db: DB) -> list[Service]:
    return list(db.scalars(select(Service).where(Service.is_active.is_(True), Service.archived_at.is_(None)).order_by(Service.sort_order).limit(150)).unique())


def _price_info(s: Service, lang: str) -> dict | None:
    p = s.pricing
    if not p or p.pricing_type == "CUSTOM_QUOTE":
        return {"type": "CUSTOM_QUOTE", "label": None}
    return {"type": p.pricing_type, "amount_minor": p.base_price_minor, "currency": p.currency, "label": format_money(p.base_price_minor, p.currency),
            "unit": pick(p.unit_label, lang) or None}


def _keyword_rows(db: DB, text: str, limit: int = 3) -> list[Service]:
    words = re.findall(r"\w{4,}", text.lower())[:12]
    if not words:
        return []
    conds = [cast(Service.name, String).ilike(f"%{w}%") for w in words] + [cast(Service.short_description, String).ilike(f"%{w}%") for w in words]
    return list(db.scalars(select(Service).where(Service.is_active.is_(True), Service.archived_at.is_(None), or_(*conds)).limit(limit)).unique())


def keyword_suggestions(db: DB, text: str, lang: str, limit: int = 3) -> list[dict]:
    """Non-AI fallback: simple keyword match across service names/descriptions."""
    return [_service_card(s, lang) for s in _keyword_rows(db, text, limit)]


def _service_card(s: Service, lang: str) -> dict:
    return {"slug": s.slug, "name": pick(s.name, lang), "category": s.category.slug, "price": _price_info(s, lang), "estimated_delivery": pick(s.estimated_delivery, lang),
            "mode": s.service_mode or "ONLINE"}


# ONLINE services offered instead of a LOCAL one when the customer is outside the local area
LOCAL_ALTERNATIVES = {
    "document-printing": ["pdf-convert", "word-formatting"],
    "book-printing": ["word-formatting", "pdf-convert"],
    "photocopy": ["pdf-convert", "scan-digitize"],
    "scanning": ["scan-digitize", "pdf-convert"],
}
AREA_NOTICE = {
    "uz": "«{service}» xizmati hozircha faqat {area} mavjud. Lekin sizga faylni tayyorlash, sahifalash yoki formatlash xizmatini butun O'zbekiston bo'ylab onlayn taklif qila olamiz.",
    "en": "“{service}” is currently available only in {area}. We can still prepare, lay out or format your file online anywhere in Uzbekistan.",
    "ru": "Услуга «{service}» пока доступна только: {area}. Но мы можем онлайн подготовить, сверстать или оформить ваш файл в любом регионе Узбекистана.",
}


def _area_guard(db: DB, cards: list[Service], area_slug: str | None, lang: str) -> tuple[list[Service], str | None]:
    """Deterministic region rule applied to every suggestion (AI or keyword): AI cannot bypass it."""
    from app.models import ServiceArea
    from app.services.local import effective_mode, local_available_in

    area = db.scalar(select(ServiceArea).where(ServiceArea.slug == area_slug)) if area_slug else None
    kept: list[Service] = []
    notice = None
    for s in cards:
        if effective_mode(s) == "LOCAL" and not local_available_in(s, area):
            sa = s.service_area
            notice = AREA_NOTICE.get(lang, AREA_NOTICE["uz"]).format(service=pick(s.name, lang), area=pick(sa.name, lang) if sa else "—")
            for alt in LOCAL_ALTERNATIVES.get(s.slug, []):
                a = db.scalar(select(Service).where(Service.slug == alt, Service.is_active.is_(True), Service.archived_at.is_(None)))
                if a and a not in kept:
                    kept.append(a)
        elif s not in kept:
            kept.append(s)
    return kept, notice


def assist(db: DB, *, message: str, history: list[dict], lang: str, user_id: int | None, area: str | None = None) -> dict:
    services = _catalog_rows(db)
    if not get_ai_assistant_ready(db):
        cards, notice = _area_guard(db, _keyword_rows(db, message), area, lang)
        return {"ai_available": False, "reply": notice, "area_notice": notice, "suggestions": [_service_card(s, lang) for s in cards[:3]], "recommend_custom_order": True}
    catalog = "\n".join(
        f"{s.slug} | {pick(s.name, 'en')} | {s.category.slug} | {s.service_mode or 'ONLINE'} | {s.service_area.slug if s.service_area else 'all Uzbekistan'} | "
        + ((_price_info(s, 'en') or {}).get("label") or "custom quote")
        for s in services
    )
    convo = "\n".join(f"{h.get('role', 'user')}: {str(h.get('content', ''))[:2000]}" for h in history[-6:])
    user = prompts.wrap_untrusted("customer_chat", (convo + "\nuser: " if convo else "") + message[:4000])
    try:
        res = manager.call(db, purpose="assistant", system=prompts.ASSISTANT.format(language=LANG_NAME.get(lang, "Uzbek"), catalog=catalog, area=area or "unknown"), user=user, user_id=user_id, max_tokens=900, retries=1)
        data = manager.parse_json(res.text)
    except (ValueError, json.JSONDecodeError):
        cards, notice = _area_guard(db, _keyword_rows(db, message), area, lang)
        return {"ai_available": True, "reply": notice, "area_notice": notice, "error": "AI_OUTPUT_INVALID", "suggestions": [_service_card(s, lang) for s in cards[:3]],
                "recommend_custom_order": True}
    except ConfigurationRequired:
        cards, notice = _area_guard(db, _keyword_rows(db, message), area, lang)
        return {"ai_available": False, "reply": notice, "area_notice": notice, "suggestions": [_service_card(s, lang) for s in cards[:3]], "recommend_custom_order": True}
    db.commit()
    slug = data.get("suggested_service_slug")
    svc = next((s for s in services if s.slug == slug), None)
    cards, notice = _area_guard(db, [svc] if svc else [], area, lang)
    if notice:  # the AI's text may have offered the local service: replace it with the rule-based answer
        data["reply"] = notice
    svc = cards[0] if cards else None
    category = db.scalar(select(ServiceCategory).where(ServiceCategory.slug == data.get("category_slug"))) if data.get("category_slug") else None
    return {
        "ai_available": True,
        "reply": str(data.get("reply", ""))[:2000],
        "area_notice": notice,
        "category": {"slug": category.slug, "name": pick(category.name, lang)} if category else None,
        "suggestions": [_service_card(s, lang) for s in cards[:3]],
        "recommend_custom_order": bool(data.get("recommend_custom_order", svc is None)),
        "complexity": data.get("complexity") if data.get("complexity") in ("low", "medium", "high") else None,
        "clarifying_questions": [str(q)[:300] for q in (data.get("clarifying_questions") or [])][:4],
        "missing_information": [str(q)[:300] for q in (data.get("missing_information") or [])][:6],
        "required_information": [str(q)[:300] for q in (data.get("required_information") or [])][:6],
        # Price shown only from the configured catalog, labelled as indicative.
        "indicative_price": _price_info(svc, lang) if svc else None,
        "disclaimer": "indicative",
    }


def get_ai_assistant_ready(db: DB) -> bool:
    from app.services.settings_service import get_setting

    return bool(get_setting(db, "ai.enabled") and get_setting(db, "ai.assistant_enabled") and manager.ai_available(db))
