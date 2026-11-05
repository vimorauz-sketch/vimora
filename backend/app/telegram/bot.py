"""Telegram bot update handling.

Privileged commands require the sender's Telegram *user id* to be in TELEGRAM_ADMIN_ID.
Every privileged command is rate limited and audited. The bot is read-only for business
data: it cannot confirm payments, change statuses or touch infrastructure.
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DB

from app.core.config import settings
from app.core.db import utcnow
from app.core.errors import RateLimited
from app.models import AIExecution, Order, TelegramAccount, TelegramLinkCode, User
from app.models.enums import ActorType as A
from app.models.enums import AIExecutionStatus as X
from app.models.enums import OrderStatus as S
from app.security.crypto import sha256_hex
from app.security.rate_limit import enforce
from app.services.audit import audit
from app.services.pricing import format_money
from app.services.settings_service import get_setting
from app.telegram.client import esc, send_message

ADMIN_COMMANDS = {"/orders", "/pending", "/stats", "/ai_status", "/maintenance"}
PENDING_STATES = [S.SUBMITTED, S.UNDER_REVIEW, S.AI_REVIEW_REQUIRED, S.MANUAL_PROCESSING, S.REVISION_REQUESTED, S.READY_FOR_DELIVERY]


def is_admin(tg_user_id: int | None) -> bool:
    return tg_user_id is not None and tg_user_id in settings.telegram_admin_ids


def _link(path: str) -> str:
    return f"{settings.APP_URL.rstrip('/')}{path}"


def _order_line(o: Order) -> str:
    amt = format_money(o.total_minor, o.currency) if o.total_minor else "—"
    return f"• <b>#{esc(o.order_number)}</b> {esc(o.title[:40])}\n  {esc(o.status)} · {esc(amt)}\n  {esc(_link(f'/admin/orders/{o.id}'))}"


def admin_reply(db: DB, cmd: str) -> str:
    if cmd == "/orders":
        rows = db.scalars(select(Order).order_by(Order.id.desc()).limit(10)).all()
        return "<b>Latest orders</b>\n\n" + ("\n".join(_order_line(o) for o in rows) or "No orders yet.")
    if cmd == "/pending":
        rows = db.scalars(select(Order).where(Order.status.in_(PENDING_STATES)).order_by(Order.updated_at).limit(15)).all()
        return "<b>Needs attention</b>\n\n" + ("\n".join(_order_line(o) for o in rows) or "Nothing pending.")
    if cmd == "/stats":
        since = utcnow() - timedelta(days=30)
        total = db.scalar(select(func.count()).select_from(Order)) or 0
        recent = db.scalar(select(func.count()).select_from(Order).where(Order.created_at >= since)) or 0
        active = db.scalar(select(func.count()).select_from(Order).where(Order.status.in_(PENDING_STATES + [S.QUEUED, S.AI_PROCESSING]))) or 0
        rev = db.execute(select(Order.currency, func.sum(Order.paid_minor - Order.refunded_minor)).group_by(Order.currency)).all()
        rev_s = ", ".join(format_money(int(v or 0), c) for c, v in rev) or "0"
        return f"<b>VIMORA stats</b>\n\nOrders total: <b>{total}</b>\nLast 30 days: <b>{recent}</b>\nActive: <b>{active}</b>\nNet received: <b>{esc(rev_s)}</b>\n\n{esc(_link('/admin'))}"
    if cmd == "/ai_status":
        from app.ai.manager import ai_available, spent_today

        running = db.scalar(select(func.count()).select_from(AIExecution).where(AIExecution.status.in_([X.PENDING, X.PLANNING, X.RUNNING, X.VALIDATING]))) or 0
        review = db.scalar(select(func.count()).select_from(AIExecution).where(AIExecution.status == X.REVIEW_REQUIRED)) or 0
        failed = db.scalar(select(func.count()).select_from(AIExecution).where(AIExecution.status == X.FAILED, AIExecution.created_at >= utcnow() - timedelta(days=1))) or 0
        return (f"<b>AI status</b>\n\nEnabled & configured: <b>{'yes' if ai_available(db) else 'no'}</b>\nRunning: <b>{running}</b>\n"
                f"Awaiting review: <b>{review}</b>\nFailed (24h): <b>{failed}</b>\nSpent today: <b>${spent_today(db):.4f}</b> / ${esc(get_setting(db, 'ai.daily_budget_usd'))}")
    if cmd == "/maintenance":
        on = bool(get_setting(db, "platform.maintenance_mode"))
        return f"Maintenance mode is <b>{'ON' if on else 'OFF'}</b>.\nChange it in the admin panel: {esc(_link('/admin/settings'))}"
    return "Unknown command"


def _link_account(db: DB, code: str, tg_user: dict, chat_id: int) -> str:
    row = db.scalar(select(TelegramLinkCode).where(TelegramLinkCode.code_hash == sha256_hex(code)).with_for_update())
    if row is None or row.used_at is not None or row.expires_at < utcnow():
        return "This link code is invalid or expired. Generate a new one in your VIMORA dashboard."
    existing = db.scalar(select(TelegramAccount).where(TelegramAccount.telegram_user_id == int(tg_user["id"])))
    if existing and existing.user_id != row.user_id:
        return "This Telegram account is already linked to another VIMORA account."
    acct = db.scalar(select(TelegramAccount).where(TelegramAccount.user_id == row.user_id))
    if acct is None:
        acct = TelegramAccount(user_id=row.user_id, telegram_user_id=int(tg_user["id"]), chat_id=chat_id, linked_at=utcnow())
        db.add(acct)
    acct.telegram_user_id = int(tg_user["id"])
    acct.chat_id = chat_id
    acct.username = (tg_user.get("username") or "")[:64] or None
    acct.notifications_enabled = True
    row.used_at = utcnow()
    audit(db, "telegram.linked", actor_id=row.user_id, actor_type=A.CUSTOMER, entity_type="user", entity_id=row.user_id)
    db.commit()
    return "✅ Your Telegram account is linked. You will receive VIMORA order updates here. You can turn them off in your dashboard."


def handle_update(db: DB, update: dict) -> None:
    msg = update.get("message") or {}
    text = (msg.get("text") or "").strip()
    chat = msg.get("chat") or {}
    tg_user = msg.get("from") or {}
    if not text.startswith("/") or not chat.get("id") or not tg_user.get("id"):
        return
    if chat.get("type") not in ("private",) and not is_admin(tg_user.get("id")):
        return
    cmd, _, arg = text.partition(" ")
    cmd = cmd.split("@")[0].lower()
    uid = int(tg_user["id"])
    try:
        enforce(f"tg:{uid}", 20, 60)
    except RateLimited:
        return

    if cmd == "/start":
        if arg.strip():
            reply = _link_account(db, arg.strip()[:64], tg_user, int(chat["id"]))
        elif is_admin(uid):
            reply = "Welcome, administrator. Commands: /orders /pending /stats /ai_status /maintenance /help"
        else:
            reply = "Welcome to VIMORA. To receive order updates, open your dashboard → Profile → Telegram and press “Link Telegram”."
    elif cmd == "/help":
        reply = ("Admin commands:\n/orders — latest orders\n/pending — orders needing action\n/stats — key numbers\n/ai_status — AI system\n/maintenance — maintenance mode"
                 if is_admin(uid) else "Link your account from the VIMORA dashboard to receive order notifications.")
    elif cmd in ADMIN_COMMANDS:
        if not is_admin(uid):
            audit(db, "telegram.command_denied", actor_type=A.SYSTEM, success=False, data={"tg_user_id": uid, "command": cmd})
            db.commit()
            reply = "This command is restricted."
        else:
            reply = admin_reply(db, cmd)
            audit(db, "telegram.command", actor_type=A.ADMIN, data={"tg_user_id": uid, "command": cmd})
            db.commit()
    else:
        return
    try:
        send_message(chat["id"], reply)
    except Exception:
        pass


def create_link_code(db: DB, user: User) -> str:
    from app.security.crypto import new_token

    code = new_token(12)
    db.add(TelegramLinkCode(user_id=user.id, code_hash=sha256_hex(code), expires_at=utcnow() + timedelta(minutes=15)))
    return code
