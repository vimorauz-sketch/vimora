"""Centralised notification service.

Business code calls `notify_customer()` / `notify_admins()` inside its DB transaction.
Rows are deduplicated by `dedupe_key` (unique). After the transaction commits, delivery
jobs are enqueued to the worker; a periodic sweeper retries anything left PENDING/FAILED
(with attempt limits) so a broker hiccup never loses a notification.
"""

from __future__ import annotations

from sqlalchemy import event, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session as DB

from app.core.config import settings
from app.core.db import utcnow
from app.core.i18n import t
from app.core.logging import get_logger
from app.models import Notification, Order, TelegramAccount, User
from app.models.enums import NotificationChannel as Ch
from app.models.enums import NotificationStatus as NS
from app.services.settings_service import get_setting

log = get_logger("notifications")
MAX_ATTEMPTS = 6

# Optional customer notification categories (can be disabled in profile preferences).
OPTIONAL_EVENTS = {"order.status", "message.received", "final_payment.reminder"}


def _queue(db: DB, ids: list[int]) -> None:
    db.info.setdefault("notify_ids", []).extend(ids)


@event.listens_for(DB, "after_commit")
def _after_commit(session: DB) -> None:
    ids = session.info.pop("notify_ids", None)
    realtime = session.info.pop("realtime", None)
    if ids:
        try:
            from app.tasks.jobs import deliver_notification

            for nid in ids:
                deliver_notification.delay(nid)
        except Exception:  # broker down -> sweeper will retry
            log.warning("Could not enqueue %d notifications; sweeper will retry", len(ids))
    if realtime:
        try:
            import json

            from app.core.redis import get_redis

            r = get_redis()
            for channel, payload in realtime:
                r.publish(channel, json.dumps(payload))
        except Exception:
            log.warning("Realtime publish failed")


@event.listens_for(DB, "after_rollback")
def _after_rollback(session: DB) -> None:
    session.info.pop("notify_ids", None)
    session.info.pop("realtime", None)


def publish_realtime(db: DB, channel: str, payload: dict) -> None:
    db.info.setdefault("realtime", []).append((channel, payload))


def _insert(db: DB, *, user_id: int | None, channel: Ch, event_type: str, dedupe_key: str, title: str, body: str, data: dict, status: NS) -> int | None:
    stmt = (
        insert(Notification)
        .values(
            user_id=user_id, channel=channel, event_type=event_type, dedupe_key=dedupe_key[:200], title=title[:300], body=body,
            data=data, status=status, attempts=0, created_at=utcnow(), sent_at=utcnow() if status == NS.SENT else None,
        )
        .on_conflict_do_nothing(index_elements=["dedupe_key"])
        .returning(Notification.id)
    )
    return db.execute(stmt).scalar()


def _prefs_allow(user: User, channel: str, event_type: str) -> bool:
    if event_type not in OPTIONAL_EVENTS:
        return True
    prefs = (user.profile.notification_prefs if user.profile else {}) or {}
    return bool(prefs.get(channel.lower(), {}).get(event_type, True))


def notify_customer(db: DB, user: User, event_type: str, *, key_suffix: str, title_key: str, body_key: str, params: dict, order: Order | None = None, link: str | None = None) -> None:
    lang = user.profile.language if user.profile else settings.DEFAULT_LANGUAGE
    title = t(title_key, lang, **params)
    body = t(body_key, lang, **params)
    data = {"link": link, "order_id": order.id if order else None, "order_number": order.order_number if order else None}
    base = f"{event_type}:{user.id}:{key_suffix}"
    _insert(db, user_id=user.id, channel=Ch.IN_APP, event_type=event_type, dedupe_key=f"in:{base}", title=title, body=body, data=data, status=NS.SENT)
    ids: list[int] = []
    if get_setting(db, "notifications.email_enabled") and _prefs_allow(user, "email", event_type):
        nid = _insert(db, user_id=user.id, channel=Ch.EMAIL, event_type=event_type, dedupe_key=f"em:{base}", title=title, body=body, data=data, status=NS.PENDING)
        if nid:
            ids.append(nid)
    tg = db.scalar(select(TelegramAccount).where(TelegramAccount.user_id == user.id))
    if tg and tg.notifications_enabled and settings.TELEGRAM_BOT_TOKEN and _prefs_allow(user, "telegram", event_type):
        nid = _insert(db, user_id=user.id, channel=Ch.TELEGRAM, event_type=event_type, dedupe_key=f"tg:{base}", title=title, body=body, data=data, status=NS.PENDING)
        if nid:
            ids.append(nid)
    _queue(db, ids)


def notify_admins(db: DB, event_type: str, *, key_suffix: str, title: str, lines: list[tuple[str, str]], order: Order | None = None) -> None:
    """Staff activity feed (always) + Telegram notification to the configured admin chat. Contains no secrets or private files."""
    _insert(
        db, user_id=None, channel=Ch.ADMIN_FEED, event_type=event_type, dedupe_key=f"feed:{event_type}:{key_suffix}", title=title,
        body="\n".join(f"{k}: {v}" for k, v in lines), status=NS.SENT,
        data={"link": f"/admin/orders/{order.id}" if order else ("/admin/content" if key_suffix.startswith("contact:") else "/admin"),
              "order_number": order.order_number if order else None, "lines": lines},
    )
    enabled = get_setting(db, "notifications.telegram_admin_events") or []
    if event_type not in enabled:
        return
    chat = settings.TELEGRAM_NOTIFICATION_CHAT_ID or (str(min(settings.telegram_admin_ids)) if settings.telegram_admin_ids else "")
    if not settings.TELEGRAM_BOT_TOKEN or not chat:
        status = NS.SKIPPED
    else:
        status = NS.PENDING
    link = f"{settings.APP_URL.rstrip('/')}/admin/orders/{order.id}" if order else f"{settings.APP_URL.rstrip('/')}/admin"
    body = "\n".join(f"{k}: {v}" for k, v in lines)
    nid = _insert(
        db, user_id=None, channel=Ch.TELEGRAM, event_type=event_type, dedupe_key=f"adm:{event_type}:{key_suffix}", title=title, body=body,
        data={"chat_id": chat, "link": link, "admin": True, "lines": lines}, status=status,
    )
    if nid and status == NS.PENDING:
        _queue(db, [nid])


def deliver(db: DB, notification_id: int) -> str:
    """Attempt delivery of one notification. Called by the worker. Returns resulting status."""
    from app.services.email import EmailDeliveryError, EmailNotConfigured, send_email
    from app.telegram.client import TelegramError, TelegramNotConfigured, esc, send_message

    n = db.scalar(select(Notification).where(Notification.id == notification_id).with_for_update(skip_locked=True))
    if n is None or n.status in (NS.SENT, NS.SKIPPED, NS.LOGGED_DEV):
        return n.status if n else "MISSING"
    n.attempts += 1
    try:
        if n.channel == Ch.EMAIL:
            user = db.get(User, n.user_id)
            if user is None:
                n.status = NS.SKIPPED
            else:
                link = n.data.get("link")
                res = send_email(user.email, n.title, n.body, cta_url=f"{settings.APP_URL.rstrip('/')}{link}" if link and link.startswith("/") else link, cta_label="VIMORA")
                n.status = NS.LOGGED_DEV if res == "LOGGED_DEV" else NS.SENT
        elif n.channel == Ch.TELEGRAM:
            if n.data.get("admin"):
                chat_id = n.data.get("chat_id")
                text = f"<b>{esc(n.title)}</b>\n\n" + "\n".join(f"{esc(k)}: <b>{esc(v)}</b>" for k, v in n.data.get("lines", []))
                text += f"\n\nOpen Admin Panel: {esc(n.data.get('link'))}"
            else:
                tg = db.scalar(select(TelegramAccount).where(TelegramAccount.user_id == n.user_id))
                if tg is None or not tg.notifications_enabled:
                    n.status = NS.SKIPPED
                    db.commit()
                    return n.status
                chat_id = tg.chat_id
                link = n.data.get("link")
                text = f"<b>{esc(n.title)}</b>\n{esc(n.body)}"
                if link:
                    text += f"\n\n{esc(settings.APP_URL.rstrip('/') + link if link.startswith('/') else link)}"
            send_message(chat_id, text)
            n.status = NS.SENT
        else:
            n.status = NS.SENT
        if n.status in (NS.SENT, NS.LOGGED_DEV):
            n.sent_at = utcnow()
        n.last_error = None
    except (EmailNotConfigured, TelegramNotConfigured) as exc:
        n.status = NS.SKIPPED
        n.last_error = str(exc)
    except (EmailDeliveryError, TelegramError) as exc:
        n.status = NS.FAILED
        n.last_error = str(exc)[:1000]
    db.commit()
    return n.status
