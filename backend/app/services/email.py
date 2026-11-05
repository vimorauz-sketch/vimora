"""Transactional email delivery. Never reports success unless the SMTP server accepted the message."""

from __future__ import annotations

import html
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("email")


class EmailNotConfigured(Exception):
    pass


class EmailDeliveryError(Exception):
    pass


def email_configured() -> bool:
    return settings.EMAIL_BACKEND == "smtp" and bool(settings.EMAIL_HOST and settings.EMAIL_FROM)


def render_html(subject: str, body_text: str, *, cta_url: str | None = None, cta_label: str | None = None) -> str:
    paras = "".join(f'<p style="margin:0 0 14px;line-height:1.6">{html.escape(p).replace(chr(10), "<br>")}</p>' for p in body_text.split("\n\n"))
    cta = (
        f'<p style="margin:24px 0"><a href="{html.escape(cta_url, quote=True)}" style="background:#D6F36A;color:#11110F;padding:12px 20px;text-decoration:none;font-weight:600;border-radius:6px;display:inline-block">{html.escape(cta_label or "Open")}</a></p>'
        if cta_url
        else ""
    )
    return f"""<!doctype html><html><body style="margin:0;background:#F5F1E8;font-family:Inter,Segoe UI,Arial,sans-serif;color:#11110F">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:32px 16px">
<table role="presentation" width="560" cellpadding="0" cellspacing="0" style="max-width:560px;background:#FFFFFF;border:1px solid #E4DFD2">
<tr><td style="background:#11110F;padding:20px 28px"><span style="color:#F5F1E8;font-size:18px;letter-spacing:.18em;font-weight:700">VIMORA</span><span style="display:inline-block;width:8px;height:8px;background:#D6F36A;margin-left:6px"></span></td></tr>
<tr><td style="padding:28px"><h1 style="font-size:20px;margin:0 0 18px">{html.escape(subject)}</h1>{paras}{cta}</td></tr>
<tr><td style="padding:16px 28px;border-top:1px solid #EEE9DC;color:#77766d;font-size:12px">VIMORA — Every task. One intelligent platform.</td></tr>
</table></td></tr></table></body></html>"""


def send_email(to: str, subject: str, body_text: str, *, cta_url: str | None = None, cta_label: str | None = None) -> str:
    """Returns 'SENT' or 'LOGGED_DEV'. Raises EmailNotConfigured / EmailDeliveryError otherwise."""
    if settings.EMAIL_BACKEND == "disabled":
        raise EmailNotConfigured("Email delivery is disabled (EMAIL_BACKEND=disabled)")
    dev_fallback = settings.APP_ENV == "development" and settings.EMAIL_BACKEND == "smtp" and not email_configured()
    if settings.EMAIL_BACKEND == "console" or dev_fallback:  # local computer without SMTP: use the dev mailbox
        if settings.is_production:
            raise EmailNotConfigured("Console email backend is not allowed in production")
        # Development only: the message is NOT delivered. It is appended to a local dev mailbox
        # file (links contain one-time tokens, so they are deliberately kept out of the logs).
        import os
        from datetime import UTC, datetime

        path = os.environ.get("DEV_MAILBOX_PATH", "./var/dev-mailbox.log")
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"--- {datetime.now(UTC).isoformat()} to={to}\nSubject: {subject}\n\n{body_text}\n{cta_url or ''}\n\n")
        log.info("DEV EMAIL written to dev mailbox (not delivered) to=%s subject=%s", to, subject)
        return "LOGGED_DEV"
    if not email_configured():
        raise EmailNotConfigured("CONFIGURATION REQUIRED: EMAIL_HOST and EMAIL_FROM must be set")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr((settings.APP_NAME, settings.EMAIL_FROM))
    msg["To"] = to
    msg["Message-ID"] = make_msgid(domain=settings.EMAIL_FROM.split("@")[-1])
    msg.set_content(body_text + (f"\n\n{cta_url}" if cta_url and cta_url not in body_text else ""))
    msg.add_alternative(render_html(subject, body_text, cta_url=cta_url, cta_label=cta_label), subtype="html")
    try:
        ctx = ssl.create_default_context()
        if settings.EMAIL_USE_SSL:
            server: smtplib.SMTP = smtplib.SMTP_SSL(settings.EMAIL_HOST, settings.EMAIL_PORT, context=ctx, timeout=20)
        else:
            server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT, timeout=20)
        with server:
            if settings.EMAIL_USE_TLS and not settings.EMAIL_USE_SSL:
                server.starttls(context=ctx)
            if settings.EMAIL_USERNAME:
                server.login(settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD)
            refused = server.send_message(msg)
        if refused:
            raise EmailDeliveryError(f"Recipient refused: {list(refused)}")
        return "SENT"
    except (smtplib.SMTPException, OSError) as exc:
        raise EmailDeliveryError(f"SMTP delivery failed: {type(exc).__name__}") from exc
