"""Suggested starting prices for the default catalog (UZS, whole so'm).

These are the owner's own suggested prices, chosen in November 2026 from public
listings for comparable work in Uzbekistan (OLX.uz, prom.uz, glotr.uz, workspace.ru),
priced a little below Tashkent agencies because VIMORA is a small one-person service.
They are only applied to services that still have no price ("individual price"),
never on top of a price the owner already set, and can be changed any time in
Admin -> Prices.

Format: slug -> (pricing type, price, unit, min qty, max qty, tiers[(from qty, price)])
STARTING_FROM always means "from"; the final price is confirmed in a quotation.
"""

from __future__ import annotations

from app.catalog_data import T

U = {
    "page": T("sahifa", "page", "страница"),
    "sheet": T("bet", "page", "лист"),
    "slide": T("slayd", "slide", "слайд"),
    "photo": T("rasm", "image", "изображение"),
    "video": T("video", "video", "видео"),
    "minute": T("daqiqa", "minute", "минута"),
    "file": T("fayl", "file", "файл"),
    "post": T("post", "post", "пост"),
    "hour": T("soat", "hour", "час"),
    "lesson": T("dars", "lesson", "урок"),
    "app": T("dastur", "program", "программа"),
    "rows": T("100 qator", "100 rows", "100 строк"),
    "form": T("anketa", "form", "анкета"),
}

F, P, Q, S = "FIXED", "PER_UNIT", "QUANTITY_TIERED", "STARTING_FROM"

PRICES: dict[str, tuple] = {
    # computer help (remote)
    "windows-install": (S, 100_000, None, 1, 1, []),
    "drivers-install": (F, 50_000, None, 1, 1, []),
    "virus-removal": (F, 80_000, None, 1, 1, []),
    "pc-speedup": (F, 70_000, None, 1, 1, []),
    "software-install": (P, 30_000, "app", 1, 20, []),
    "data-recovery": (S, 150_000, None, 1, 1, []),
    "printer-setup": (F, 60_000, None, 1, 1, []),
    "wifi-network-setup": (F, 60_000, None, 1, 1, []),
    "backup-setup": (F, 80_000, None, 1, 1, []),
    "remote-help": (P, 50_000, "hour", 1, 8, []),
    # documents & PDF
    "typing": (Q, 8_000, "page", 1, 500, [(20, 7_000), (50, 6_000)]),
    "word-formatting": (Q, 5_000, "page", 1, 500, [(30, 4_000)]),
    "cv-resume": (F, 80_000, None, 1, 1, []),
    "cover-letter": (F, 60_000, None, 1, 1, []),
    "pdf-convert": (P, 10_000, "file", 1, 100, []),
    "scan-digitize": (P, 6_000, "page", 1, 500, []),
    "contracts-templates": (S, 100_000, None, 1, 1, []),
    # printing in Qarapchi (Canon PIXMA G3410, A4); black & white price, colour is confirmed in the quote
    "document-printing": (S, 1_000, "sheet", 1, 1000, []),
    "photocopy": (Q, 1_000, "sheet", 1, 1000, [(50, 800)]),
    "scanning": (P, 2_000, "sheet", 1, 500, []),
    "book-printing": (S, 900, "sheet", 10, 2000, []),
    # Excel & Office
    "excel-tables": (S, 80_000, None, 1, 1, []),
    "excel-formulas-automation": (S, 150_000, None, 1, 1, []),
    "excel-charts-reports": (S, 100_000, None, 1, 1, []),
    "powerpoint-presentation": (Q, 15_000, "slide", 5, 100, [(15, 12_000)]),
    "google-workspace": (S, 70_000, None, 1, 1, []),
    # text & translation
    "translation": (Q, 35_000, "page", 1, 200, [(10, 30_000)]),
    "copywriting": (S, 50_000, None, 1, 1, []),
    "proofreading": (P, 10_000, "page", 1, 300, []),
    "transliteration": (P, 5_000, "page", 1, 500, []),
    "summary-report": (S, 60_000, None, 1, 1, []),
    # graphic design
    "logo-design": (S, 400_000, None, 1, 1, []),
    "business-card": (F, 100_000, None, 1, 1, []),
    "banner-poster": (S, 80_000, None, 1, 1, []),
    "invitation-design": (F, 70_000, None, 1, 1, []),
    "brand-identity": (S, 1_500_000, None, 1, 1, []),
    "menu-price-list": (S, 150_000, None, 1, 1, []),
    "packaging-label": (S, 200_000, None, 1, 1, []),
    # photos & images
    "photo-retouch": (P, 20_000, "photo", 1, 100, []),
    "background-removal": (Q, 10_000, "photo", 1, 200, [(10, 7_000)]),
    "document-photo": (F, 20_000, None, 1, 1, []),
    "old-photo-restoration": (P, 50_000, "photo", 1, 50, []),
    "product-photos": (Q, 15_000, "photo", 1, 200, [(10, 12_000)]),
    "collage-photobook": (S, 100_000, None, 1, 1, []),
    # video & audio
    "video-editing": (S, 150_000, None, 1, 1, []),
    "reels-shorts": (Q, 60_000, "video", 1, 30, [(5, 50_000)]),
    "subtitles": (P, 20_000, "minute", 1, 180, []),
    "audio-cleanup": (S, 50_000, None, 1, 1, []),
    "transcription": (P, 10_000, "minute", 1, 300, []),
    "video-convert": (P, 15_000, "file", 1, 50, []),
    "animation-intro": (S, 300_000, None, 1, 1, []),
    # social media
    "instagram-design": (Q, 30_000, "post", 1, 60, [(10, 25_000)]),
    "social-setup": (F, 150_000, None, 1, 1, []),
    "content-plan": (S, 300_000, None, 1, 1, []),
    "youtube-channel": (F, 200_000, None, 1, 1, []),
    "google-maps-business": (F, 150_000, None, 1, 1, []),
    # websites
    "landing-page": (S, 1_500_000, None, 1, 1, []),
    "business-website": (S, 3_000_000, None, 1, 1, []),
    "online-store": (S, 6_000_000, None, 1, 1, []),
    "website-fixes": (S, 150_000, None, 1, 1, []),
    "wordpress": (S, 2_000_000, None, 1, 1, []),
    "seo-basic": (S, 500_000, None, 1, 1, []),
    # Telegram & automation
    "telegram-bot-development": (S, 1_500_000, None, 1, 1, []),
    "telegram-channel-setup": (F, 150_000, None, 1, 1, []),
    "telegram-mini-app": (S, 4_000_000, None, 1, 1, []),
    "process-automation": (S, 800_000, None, 1, 1, []),
    # software
    "python-script": (S, 300_000, None, 1, 1, []),
    "desktop-app": (S, 3_000_000, None, 1, 1, []),
    "mobile-app": (S, 8_000_000, None, 1, 1, []),
    "bug-fixing": (S, 200_000, None, 1, 1, []),
    "student-projects": (S, 150_000, None, 1, 1, []),
    # data
    "data-entry": (P, 15_000, "rows", 1, 200, []),
    "data-cleanup": (S, 150_000, None, 1, 1, []),
    "database-setup": (S, 800_000, None, 1, 1, []),
    "data-analysis": (S, 400_000, None, 1, 1, []),
    # hosting (VIMORA's work only; domain / hosting fees are paid to the provider)
    "domain-hosting": (F, 150_000, None, 1, 1, []),
    "corporate-email": (F, 200_000, None, 1, 1, []),
    "vps-deployment": (S, 400_000, None, 1, 1, []),
    "ssl-security": (F, 150_000, None, 1, 1, []),
    # integrations
    "payment-integration": (S, 1_000_000, None, 1, 1, []),
    "api-integration-custom": (S, 1_000_000, None, 1, 1, []),
    "sms-notifications": (S, 600_000, None, 1, 1, []),
    # AI
    "ai-chatbot": (S, 2_000_000, None, 1, 1, []),
    "ai-images": (P, 25_000, "photo", 1, 50, []),
    "ai-training": (P, 100_000, "lesson", 1, 20, []),
    # online applications (state fees are not included)
    "gov-services": (F, 50_000, None, 1, 1, []),
    "e-signature": (F, 60_000, None, 1, 1, []),
    "visa-forms": (S, 150_000, None, 1, 1, []),
    "green-card": (P, 50_000, "form", 1, 10, []),
    "university-applications": (F, 100_000, None, 1, 1, []),
    "online-accounts": (F, 40_000, None, 1, 1, []),
    "marketplace-seller": (S, 400_000, None, 1, 1, []),
    # lessons & advice
    "computer-basics": (P, 80_000, "lesson", 1, 20, []),
    "office-lessons": (P, 100_000, "lesson", 1, 20, []),
    "programming-lessons": (P, 120_000, "lesson", 1, 40, []),
    "it-consulting": (P, 100_000, "hour", 1, 10, []),
    "pc-buying-advice": (F, 80_000, None, 1, 1, []),
    # "custom-task" stays an individual quote on purpose
}


def suggestion(slug: str) -> dict | None:
    """The suggested pricing for a slug as API/DB-shaped values (amounts in minor units)."""
    row = PRICES.get(slug)
    if row is None:
        return None
    ptype, price, unit, lo, hi, tiers = row
    return {
        "pricing_type": ptype, "currency": "UZS", "base_price_minor": price * 100,
        "unit_label": U[unit] if unit else {}, "min_quantity": lo, "max_quantity": hi,
        "tiers": [{"min_qty": q, "unit_price_minor": p * 100} for q, p in tiers],
    }


def is_unpriced(pricing) -> bool:
    return pricing is None or (pricing.pricing_type == "CUSTOM_QUOTE" and not pricing.base_price_minor)


def apply_suggestion(service) -> bool:
    """Set the suggested price on an unpriced service. Keeps its deposit settings and add-ons."""
    from app.models import ServicePricing

    sug = suggestion(service.slug)
    if sug is None:
        return False
    if service.pricing is None:
        service.pricing = ServicePricing(pricing_type=sug["pricing_type"], deposit_type="PERCENT",
                                         deposit_value=0 if service.service_mode == "LOCAL" else 30)
    p = service.pricing
    p.pricing_type, p.currency, p.base_price_minor, p.unit_label = sug["pricing_type"], "UZS", sug["base_price_minor"], sug["unit_label"]
    p.min_quantity, p.max_quantity, p.tiers = sug["min_quantity"], sug["max_quantity"], sug["tiers"]
    return True
