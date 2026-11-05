"""Inbound provider webhooks. Each verifies the provider's signature/auth before touching data."""

from __future__ import annotations

import hmac
import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session as DB

from app.api.deps import get_db
from app.core.config import settings
from app.core.errors import ConfigurationRequired, Forbidden, NotFound
from app.core.logging import get_logger
from app.payments import click, payme, stripe_webhook
from app.services.audit import audit

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
log = get_logger("webhooks")
MAX_BODY = 256 * 1024


async def _form(request: Request) -> dict:
    body = await request.body()
    if len(body) > MAX_BODY:
        raise Forbidden("Payload too large")
    form = await request.form()
    return {k: str(v) for k, v in form.items()}


@router.post("/click/prepare")
async def click_prepare(request: Request, db: DB = Depends(get_db)):
    if not settings.CLICK_SECRET_KEY:
        raise ConfigurationRequired("Click is not configured")
    params = await _form(request)
    res = click.handle(db, params, action_expected=0)
    if res["error"] == click.SIGN_FAILED:
        audit(db, "webhook.signature_invalid", success=False, ip=request.client.host if request.client else None, data={"provider": "CLICK"})
        db.commit()
    return res


@router.post("/click/complete")
async def click_complete(request: Request, db: DB = Depends(get_db)):
    if not settings.CLICK_SECRET_KEY:
        raise ConfigurationRequired("Click is not configured")
    params = await _form(request)
    res = click.handle(db, params, action_expected=1)
    if res["error"] == click.SIGN_FAILED:
        audit(db, "webhook.signature_invalid", success=False, ip=request.client.host if request.client else None, data={"provider": "CLICK"})
        db.commit()
    return res


@router.post("/payme")
async def payme_rpc(request: Request, db: DB = Depends(get_db)):
    raw = await request.body()
    try:
        body = json.loads(raw) if len(raw) <= MAX_BODY else {}
    except json.JSONDecodeError:
        return JSONResponse(payme.err(None, payme.ERR_PARSE, "Parse error"))
    if not payme.check_auth(request.headers.get("authorization")):
        audit(db, "webhook.signature_invalid", success=False, ip=request.client.host if request.client else None, data={"provider": "PAYME"})
        db.commit()
        return JSONResponse(payme.err(body.get("id"), payme.ERR_AUTH, "Insufficient privileges"))
    return JSONResponse(payme.handle(db, body))


@router.post("/stripe")
async def stripe(request: Request, db: DB = Depends(get_db)):
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise ConfigurationRequired("Stripe is not configured")
    payload = await request.body()
    if len(payload) > MAX_BODY:
        raise Forbidden("Payload too large")
    try:
        return stripe_webhook.handle(db, payload, request.headers.get("stripe-signature"))
    except stripe_webhook.SignatureError:
        db.rollback()
        audit(db, "webhook.signature_invalid", success=False, ip=request.client.host if request.client else None, data={"provider": "STRIPE"})
        db.commit()
        return JSONResponse({"error": "invalid signature"}, status_code=400)


@router.post("/telegram/{path_secret}")
async def telegram(path_secret: str, request: Request, db: DB = Depends(get_db)):
    secret = settings.TELEGRAM_WEBHOOK_SECRET
    header = request.headers.get("x-telegram-bot-api-secret-token", "")
    # both the secret path segment and Telegram's secret header must match
    if not secret or not hmac.compare_digest(path_secret, secret) or not hmac.compare_digest(header, secret):
        raise NotFound("Not found")
    raw = await request.body()
    if len(raw) > MAX_BODY:
        return {"ok": True}
    try:
        update = json.loads(raw)
    except json.JSONDecodeError:
        return {"ok": True}
    from app.telegram.bot import handle_update

    try:
        handle_update(db, update)
    except Exception:
        log.exception("Telegram update handling failed")
        db.rollback()
    return {"ok": True}
