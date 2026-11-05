from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session as DB

from app.api.deps import Auth, get_auth, get_db
from app.core.config import settings
from app.core.db import SessionLocal
from app.core.errors import AppError
from app.schemas.inputs import MessageIn
from app.security.permissions import permissions_for
from app.security.rate_limit import enforce
from app.security.sessions import resolve_session
from app.services import orders as order_svc
from app.services.messaging import list_messages, post_message

router = APIRouter(tags=["messages"])


@router.get("/orders/{order_id}/messages")
def customer_messages(order_id: int, before_id: int | None = Query(None), db: DB = Depends(get_db), auth: Auth = Depends(get_auth)):
    o = order_svc.get_order_for_customer(db, order_id, auth.user.id)
    items = list_messages(db, o, viewer_is_staff=False, before_id=before_id)
    db.commit()
    return {"items": items}


@router.post("/orders/{order_id}/messages", status_code=201)
def customer_post(order_id: int, body: MessageIn, db: DB = Depends(get_db), auth: Auth = Depends(get_auth)):
    enforce(f"msg:{auth.user.id}", 30, 300)
    o = order_svc.get_order_for_customer(db, order_id, auth.user.id)
    out = post_message(db, o, auth.user, as_staff=False, body=body.body, attachment_ids=body.attachment_ids)
    db.commit()
    return out


@router.websocket("/ws/orders/{order_id}")
async def order_socket(websocket: WebSocket, order_id: int):
    """Near-real-time order updates (messages, status). Authenticated by the session cookie;
    the order must belong to the user unless they are staff. Origin is checked."""
    origin = (websocket.headers.get("origin") or "").rstrip("/")
    if origin and origin not in settings.cors_origins and origin != settings.APP_URL.rstrip("/"):
        await websocket.close(code=4403)
        return
    token = websocket.cookies.get(settings.SESSION_COOKIE_NAME)
    with SessionLocal() as db:
        resolved = resolve_session(db, token)
        if not resolved:
            await websocket.close(code=4401)
            return
        session, user = resolved
        if user.mfa_enabled and not session.mfa_verified:
            await websocket.close(code=4401)
            return
        try:
            if user.is_staff and "orders.view" in permissions_for(user.role_names):
                order_svc.get_order(db, order_id)
            else:
                order_svc.get_order_for_customer(db, order_id, user.id)
        except AppError:
            await websocket.close(code=4404)
            return
    await websocket.accept()
    import redis.asyncio as aioredis

    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe(f"order:{order_id}")
    try:
        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=20)
            if msg and msg.get("type") == "message":
                await websocket.send_text(msg["data"])
            else:
                await websocket.send_text(json.dumps({"type": "ping"}))
            await asyncio.sleep(0.05)
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        await pubsub.unsubscribe()
        await r.aclose()
