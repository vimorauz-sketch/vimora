"""Minimal official Telegram Bot API client (https://core.telegram.org/bots/api)."""

from __future__ import annotations

import html

import httpx

from app.core.config import settings


class TelegramNotConfigured(Exception):
    pass


class TelegramError(Exception):
    pass


def esc(value: object) -> str:
    return html.escape(str(value), quote=False)


def _url(method: str) -> str:
    if not settings.TELEGRAM_BOT_TOKEN:
        raise TelegramNotConfigured("CONFIGURATION REQUIRED: TELEGRAM_BOT_TOKEN is not set")
    return f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/{method}"


def call(method: str, payload: dict, *, timeout: float = 15) -> dict:
    try:
        resp = httpx.post(_url(method), json=payload, timeout=timeout)
        data = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        # never include the URL (contains the token) in the error
        raise TelegramError(f"Telegram request failed: {type(exc).__name__}") from None
    if not data.get("ok"):
        raise TelegramError(f"Telegram API error {data.get('error_code')}: {data.get('description')}")
    return data.get("result", {})


def send_message(chat_id: int | str, text: str, *, buttons: list[tuple[str, str]] | None = None) -> dict:
    payload: dict = {"chat_id": chat_id, "text": text[:4096], "parse_mode": "HTML", "disable_web_page_preview": True}
    if buttons:
        # only https URLs are allowed in inline keyboards
        payload["reply_markup"] = {"inline_keyboard": [[{"text": t, "url": u}] for t, u in buttons if u.startswith("https://")]}
        if not payload["reply_markup"]["inline_keyboard"]:
            payload.pop("reply_markup")
    return call("sendMessage", payload)


def set_webhook(url: str, secret: str) -> dict:
    return call("setWebhook", {"url": url, "secret_token": secret, "allowed_updates": ["message"], "drop_pending_updates": True})


def set_commands() -> dict:
    cmds = [
        ("start", "Start / link account"), ("help", "Help"), ("orders", "Latest orders"), ("pending", "Orders needing action"),
        ("stats", "Business stats"), ("ai_status", "AI system status"), ("maintenance", "Maintenance mode status"),
    ]
    return call("setMyCommands", {"commands": [{"command": c, "description": d} for c, d in cmds]})
