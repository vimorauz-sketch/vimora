"""Operational CLI.

  python -m app.cli create-admin --email owner@example.com        (password prompted, never logged)
  python -m app.cli seed-categories
  python -m app.cli seed-service-drafts                            (inactive drafts, no prices)
  python -m app.cli seed-content                                   (FAQ + unpublished policy pages)
  python -m app.cli check-config
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys

from sqlalchemy import select

from app.core.db import SessionLocal, utcnow
from app.models import FAQItem, Role, Service, ServiceCategory, ServicePricing, StaticPage, User, UserProfile, UserRole
from app.models.enums import ActorType, RoleName
from app.security.crypto import PASSWORD_RULES, hash_password, validate_password_strength
from app.services.audit import audit


def T(uz: str, en: str, ru: str) -> dict:
    return {"uz": uz, "en": en, "ru": ru}


CATEGORIES = [
    ("ai-services", "brain-circuit", T("AI xizmatlari", "AI Services", "AI-сервисы")),
    ("telegram-automation", "send", T("Telegram va avtomatlashtirish", "Telegram & Automation", "Telegram и автоматизация")),
    ("software-development", "code-xml", T("Dasturiy ta'minot", "Software Development", "Разработка ПО")),
    ("web-development", "globe", T("Veb-ishlab chiqish", "Web Development", "Веб-разработка")),
    ("excel-office", "sheet", T("Excel va Office", "Excel & Office", "Excel и Office")),
    ("graphic-design", "pen-tool", T("Grafik dizayn", "Graphic Design", "Графический дизайн")),
    ("image-processing", "image", T("Rasmlarga ishlov berish", "Image Processing", "Обработка изображений")),
    ("video-audio", "clapperboard", T("Video va audio", "Video & Audio", "Видео и аудио")),
    ("documents-pdf", "file-text", T("Hujjatlar va PDF", "Documents & PDF", "Документы и PDF")),
    ("data-processing", "database", T("Ma'lumotlarni qayta ishlash", "Data Processing", "Обработка данных")),
    ("hosting-deployment", "server", T("Hosting va joylashtirish", "Hosting & Deployment", "Хостинг и развёртывание")),
    ("computer-assistance", "monitor-cog", T("Kompyuter yordami", "Computer Assistance", "Компьютерная помощь")),
    ("api-integration", "plug", T("API integratsiya", "API Integration", "API-интеграция")),
    ("custom-digital-tasks", "sparkles", T("Maxsus raqamli vazifalar", "Custom Digital Tasks", "Индивидуальные задачи")),
]

# (slug, category, name, short description, ai capability or None)
SERVICE_DRAFTS = [
    ("telegram-bot-development", "telegram-automation", T("Telegram bot yaratish", "Telegram Bot Development", "Разработка Telegram-бота"),
     T("Biznesingiz uchun Telegram bot", "A Telegram bot for your business", "Telegram-бот для вашего бизнеса"), "code_generation"),
    ("document-translation", "documents-pdf", T("Hujjat tarjimasi", "Document Translation", "Перевод документов"),
     T("O'zbek, ingliz va rus tillari o'rtasida tarjima", "Translation between Uzbek, English and Russian", "Перевод между узбекским, английским и русским"), "translation"),
    ("text-writing", "ai-services", T("Matn yozish", "Text Writing", "Написание текстов"),
     T("Maqolalar, tavsiflar, xatlar", "Articles, descriptions, letters", "Статьи, описания, письма"), "document_writing"),
    ("excel-automation", "excel-office", T("Excel jadval va formulalar", "Excel Sheets & Formulas", "Таблицы и формулы Excel"),
     T("Jadval, formula va hisobotlar", "Spreadsheets, formulas and reports", "Таблицы, формулы и отчёты"), None),
    ("landing-page", "web-development", T("Landing sahifa", "Landing Page", "Лендинг"),
     T("Bir sahifali veb-sayt", "A single-page website", "Одностраничный сайт"), None),
    ("logo-design", "graphic-design", T("Logotip dizayni", "Logo Design", "Дизайн логотипа"),
     T("Brendingiz uchun logotip", "A logo for your brand", "Логотип для вашего бренда"), None),
    ("data-cleanup", "data-processing", T("Ma'lumotlarni tozalash", "Data Cleanup", "Очистка данных"),
     T("CSV/JSON ma'lumotlarini tartibga solish", "Clean and restructure CSV/JSON data", "Очистка и структурирование CSV/JSON"), "data_transformation"),
    ("vps-deployment", "hosting-deployment", T("Serverga joylashtirish", "VPS Deployment", "Развёртывание на VPS"),
     T("Loyihangizni serverga joylashtirish", "Deploy your project to a server", "Развёртывание проекта на сервере"), None),
]

FAQ = [
    (T("VIMORA qanday ishlaydi?", "How does VIMORA work?", "Как работает VIMORA?"),
     T("Xizmatni tanlang yoki vazifangizni tasvirlab bering. Biz narx taklifini yuboramiz, siz oldindan to'lov qilasiz, ish bajariladi va tekshiriladi, so'ng qolgan summani to'lab natijani olasiz.",
       "Choose a service or describe your task. We send a quotation, you pay a deposit, the work is completed and reviewed, then you pay the remaining balance and receive the result.",
       "Выберите услугу или опишите задачу. Мы отправим предложение, вы внесёте предоплату, работа будет выполнена и проверена, затем вы оплатите остаток и получите результат.")),
    (T("Sun'iy intellekt ishimni bajaradimi?", "Does AI do my work?", "Выполняет ли мою работу ИИ?"),
     T("Ayrim vazifalar sun'iy intellekt yordamida bajariladi. Har bir natija sizga yuborilishidan oldin mutaxassis tomonidan tekshiriladi.",
       "Some tasks are completed with AI assistance. Every result is reviewed and approved by a specialist before it is delivered to you.",
       "Некоторые задачи выполняются с помощью ИИ. Каждый результат проверяется специалистом перед передачей вам.")),
    (T("To'lov qanday amalga oshiriladi?", "How do payments work?", "Как происходит оплата?"),
     T("Narx taklifini qabul qilganingizdan so'ng oldindan to'lov qilasiz. Qolgan summa ish yakunlangandan keyin to'lanadi. To'lov holati faqat to'lov tizimi tasdiqlaganidan keyin yangilanadi.",
       "After accepting a quotation you pay a deposit. The remaining balance is paid after the work is completed. Payment status updates only after the payment provider confirms it.",
       "После принятия предложения вы вносите предоплату. Остаток оплачивается после завершения работы. Статус оплаты обновляется только после подтверждения платёжной системой.")),
    (T("Fayllarim xavfsizmi?", "Are my files safe?", "Безопасны ли мои файлы?"),
     T("Fayllar shaxsiy saqlashda turadi va faqat sizga hamda buyurtmangiz ustida ishlovchi xodimlarga vaqtinchalik havolalar orqali ochiladi.",
       "Files are kept in private storage and are accessible only to you and the staff working on your order, through short-lived links.",
       "Файлы хранятся в закрытом хранилище и доступны только вам и сотрудникам, работающим над заказом, через временные ссылки.")),
]

PAGES = ["terms", "privacy", "refund-policy", "service-policy", "about", "ai-notice"]


def create_admin(email: str, password_env: str | None) -> int:
    from email_validator import EmailNotValidError, validate_email

    try:
        # same rules as the login API, otherwise the admin could never sign in
        email = validate_email(email.strip(), check_deliverability=False).normalized.lower()
    except EmailNotValidError as exc:
        print(f"Invalid email: {exc}", file=sys.stderr)
        return 2
    password = os.environ.get(password_env) if password_env else None
    if not password:
        if not sys.stdin.isatty():
            print("Refusing to read a password from a non-interactive stdin; use --password-env VAR", file=sys.stderr)
            return 2
        password = getpass.getpass("Admin password: ")
        if password != getpass.getpass("Repeat password: "):
            print("Passwords do not match", file=sys.stderr)
            return 2
    problems = [PASSWORD_RULES[p] for p in validate_password_strength(password, email)]
    if len(password) < 14:
        problems.append("Admin passwords must be at least 14 characters")
    if problems:
        print("Password rejected:\n - " + "\n - ".join(problems), file=sys.stderr)
        return 2
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        role = db.scalar(select(Role).where(Role.name == RoleName.SUPER_ADMIN))
        if role is None:
            print("Roles missing — run migrations first (alembic upgrade head)", file=sys.stderr)
            return 2
        if user is None:
            user = User(email=email, password_hash=hash_password(password), email_verified_at=utcnow(), password_changed_at=utcnow())
            user.profile = UserProfile(full_name="Administrator", language="uz")
            db.add(user)
            db.flush()
            created = True
        else:
            user.password_hash = hash_password(password)
            user.password_changed_at = utcnow()
            user.is_active = True
            created = False
        if db.get(UserRole, (user.id, role.id)) is None:
            db.add(UserRole(user_id=user.id, role_id=role.id, created_at=utcnow()))
        audit(db, "admin.bootstrap", actor_type=ActorType.SYSTEM, entity_type="user", entity_id=user.id, data={"created": created})
        db.commit()
    print(f"{'Created' if created else 'Updated'} SUPER_ADMIN {email}. Sign in and enroll MFA (required for admin access in production).")
    return 0


def seed_categories() -> int:
    with SessionLocal() as db:
        n = 0
        for i, (slug, icon, name) in enumerate(CATEGORIES):
            if db.scalar(select(ServiceCategory.id).where(ServiceCategory.slug == slug)) is None:
                db.add(ServiceCategory(slug=slug, icon=icon, name=name, description={}, sort_order=i))
                n += 1
        db.commit()
    print(f"Seeded {n} categories")
    return 0


def seed_service_drafts() -> int:
    with SessionLocal() as db:
        cats = {c.slug: c for c in db.scalars(select(ServiceCategory))}
        if not cats:
            print("Run seed-categories first", file=sys.stderr)
            return 2
        n = 0
        for i, (slug, cat, name, short, cap) in enumerate(SERVICE_DRAFTS):
            if db.scalar(select(Service.id).where(Service.slug == slug)):
                continue
            s = Service(slug=slug, category_id=cats[cat].id, name=name, short_description=short, description=short, icon=cats[cat].icon,
                        is_active=False, ai_eligible=False, ai_capability=cap, sort_order=i)
            # No business prices are invented: drafts use CUSTOM_QUOTE until the owner sets pricing.
            s.pricing = ServicePricing(pricing_type="CUSTOM_QUOTE", currency="UZS", base_price_minor=0, deposit_type="PERCENT", deposit_value=30)
            db.add(s)
            n += 1
        db.commit()
    print(f"Seeded {n} INACTIVE service drafts. Review, price and activate them in Admin → Services.")
    return 0


def seed_content() -> int:
    with SessionLocal() as db:
        if not db.scalar(select(FAQItem.id).limit(1)):
            for i, (q, a) in enumerate(FAQ):
                db.add(FAQItem(question=q, answer=a, sort_order=i, is_published=True))
        for slug in PAGES:
            if db.scalar(select(StaticPage.id).where(StaticPage.slug == slug)) is None:
                # Unpublished: legal texts must be written/approved by the owner.
                db.add(StaticPage(slug=slug, title={}, body={}, is_published=False))
        db.commit()
    print("Seeded FAQ and unpublished policy pages (publish them from Admin → Content after writing).")
    return 0


def apply_prices() -> int:
    """Suggested starting prices for unpriced catalog services. Never overwrites a price the owner set."""
    from app.catalog_prices import apply_suggestion, is_unpriced

    with SessionLocal() as db:
        n = 0
        for s in db.scalars(select(Service).where(Service.archived_at.is_(None))):
            if is_unpriced(s.pricing) and apply_suggestion(s):
                n += 1
        db.commit()
    print(f"Suggested prices set on {n} service(s). Review them in Admin -> Prices.")
    return 0


def seed_catalog(inactive: bool = False) -> int:
    """Full computer-services catalog. Safe to re-run: never touches priced, edited-into-use or ordered services."""
    from sqlalchemy import func

    from app.catalog_data import CATEGORIES as CATS
    from app.catalog_prices import apply_suggestion
    from app.catalog_data import FEATURED, LOCAL_AREA, LOCAL_FIELDS, MODIFIED_TEXT, REQUIRES_FILE, SERVICES, mode_for
    from app.models import ServiceArea
    from app.catalog_photos import LEGACY_DEFAULT_URLS
    from app.models import Order

    with SessionLocal() as db:
        cats: dict[str, ServiceCategory] = {c.slug: c for c in db.scalars(select(ServiceCategory))}
        new_cats = 0
        for i, (slug, icon, name) in enumerate(CATS):
            c = cats.get(slug)
            if c is None:
                c = ServiceCategory(slug=slug, icon=icon, name=name, description={}, sort_order=i)
                db.add(c)
                cats[slug] = c
                new_cats += 1
            else:
                old_seed_names = [n for sl, _, n in CATEGORIES if sl == slug]
                if old_seed_names and c.name == old_seed_names[0]:
                    c.name = name  # still the original seed wording -> use the improved name
                c.sort_order, c.icon, c.is_active = i, icon, True
        db.flush()
        existing = {s.slug: s for s in db.scalars(select(Service))}
        from app.services.local import ensure_default_areas

        ensure_default_areas(db)
        areas = {a.slug: a for a in db.scalars(select(ServiceArea))}
        local_area = areas.get(LOCAL_AREA)
        created = updated = classified = 0
        for i, (slug, cat, name, short, cap) in enumerate(SERVICES):
            mode = mode_for(slug)
            if slug in MODIFIED_TEXT:
                new_name, new_short = MODIFIED_TEXT[slug]
            else:
                new_name, new_short = name, short
            svc = existing.get(slug)
            if svc is None:
                svc = Service(slug=slug, category_id=cats[cat].id, name=new_name, short_description=new_short, description=new_short, icon=cats[cat].icon,
                              is_active=not inactive and mode in ("ONLINE", "REMOTE", "LOCAL"), is_featured=slug in FEATURED, ai_eligible=False,
                              ai_capability=cap, sort_order=i)
                svc.pricing = ServicePricing(pricing_type="CUSTOM_QUOTE", currency="UZS", base_price_minor=0, deposit_type="PERCENT",
                                             deposit_value=0 if mode == "LOCAL" else 30)  # LOCAL: cash on handover is allowed
                apply_suggestion(svc)  # suggested starting price; the owner can change it in Admin -> Prices
                db.add(svc)
                existing[slug] = svc
                created += 1
            elif (svc.service_mode is None and not svc.is_active and svc.archived_at is None and svc.pricing and svc.pricing.pricing_type == "CUSTOM_QUOTE"
                  and not db.scalar(select(func.count()).select_from(Order).where(Order.service_id == svc.id))):
                # an untouched hidden seed draft from an older version: refresh texts and make it visible
                svc.category_id, svc.name, svc.short_description, svc.description = cats[cat].id, new_name, new_short, new_short
                svc.icon, svc.ai_capability, svc.sort_order, svc.is_featured = cats[cat].icon, cap, i, slug in FEATURED
                svc.is_active = svc.is_active or not inactive
                updated += 1
            elif slug in MODIFIED_TEXT and svc.name == name and svc.short_description == short:
                # still the original seed wording -> use the audited, honest wording
                svc.name, svc.short_description = new_name, new_short
                if svc.description == short:
                    svc.description = new_short
                updated += 1
            if svc.service_mode is None:  # classify once; later changes belong to the admin
                svc.service_mode = mode
                classified += 1
                if mode == "LOCAL":
                    svc.service_area = local_area
                    svc.requires_file = slug in REQUIRES_FILE
                    if not svc.required_fields:
                        svc.required_fields = LOCAL_FIELDS.get(slug, [])
                elif mode == "FUTURE":
                    svc.is_active = False
                elif mode == "DISABLED":
                    svc.is_active = False
                    svc.archived_at = svc.archived_at or utcnow()
        # services show hand-drawn illustrations; drop the automatic stock photos added by an earlier version
        photos = 0
        for svc in existing.values():
            if svc.cover_image_url in LEGACY_DEFAULT_URLS:
                svc.cover_image_url = svc.cover_image_credit = None
                photos += 1
        # retire superseded early drafts that were never priced or ordered
        catalog_slugs = {row[0] for row in SERVICES}
        for slug in ("excel-automation", "document-translation", "text-writing"):
            svc = existing.get(slug)
            if svc and slug not in catalog_slugs and not svc.is_active and svc.archived_at is None and (not svc.pricing or svc.pricing.pricing_type == "CUSTOM_QUOTE"):
                svc.archived_at = utcnow()
        db.commit()
    print(f"Catalog: {new_cats} new categories, {created} new services, {updated} updated, {classified} classified "
          f"(ONLINE/REMOTE/LOCAL/FUTURE/DISABLED), {photos} old stock photos replaced by illustrations. "
          f"New services get suggested starting prices; review them in Admin -> Prices.")
    return 0


def check_config() -> int:
    from app.core.config import settings

    problems = settings.validate_for_production()
    print("Integrations:", {k: ("configured" if v else "CONFIGURATION REQUIRED") for k, v in settings.integration_status().items()})
    if problems:
        print("Production readiness problems:\n - " + "\n - ".join(problems))
        return 1
    print("Production configuration OK")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="vimora")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("create-admin")
    a.add_argument("--email", required=True)
    a.add_argument("--password-env", help="read the password from this environment variable instead of prompting")
    sub.add_parser("seed-categories")
    sub.add_parser("seed-service-drafts")
    sub.add_parser("seed-content")
    sub.add_parser("apply-prices", help="set suggested starting prices on services that still have no price")
    sc = sub.add_parser("seed-catalog", help="full computer-services catalog (individual pricing, visible)")
    sc.add_argument("--inactive", action="store_true", help="create services hidden until you activate them")
    sub.add_parser("check-config")
    args = ap.parse_args()
    if args.cmd == "create-admin":
        return create_admin(args.email, args.password_env)
    if args.cmd == "apply-prices":
        return apply_prices()
    if args.cmd == "seed-catalog":
        return seed_catalog(args.inactive)
    return {"seed-categories": seed_categories, "seed-service-drafts": seed_service_drafts, "seed-content": seed_content, "check-config": check_config}[args.cmd]()


if __name__ == "__main__":
    raise SystemExit(main())
