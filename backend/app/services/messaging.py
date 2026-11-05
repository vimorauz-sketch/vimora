from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.orm import Session as DB

from app.core.db import utcnow
from app.core.errors import AppError, Forbidden
from app.models import Attachment, Conversation, Message, Order, User
from app.models.enums import AttachmentPurpose
from app.schemas.serializers import message_out
from app.services.notifications import notify_admins, notify_customer, publish_realtime


def conversation_for(db: DB, order: Order) -> Conversation:
    conv = db.scalar(select(Conversation).where(Conversation.order_id == order.id))
    if conv is None:
        conv = Conversation(order_id=order.id, customer_id=order.customer_id)
        db.add(conv)
        db.flush()
    return conv


def list_messages(db: DB, order: Order, *, viewer_is_staff: bool, before_id: int | None = None, limit: int = 50) -> list[dict]:
    conv = conversation_for(db, order)
    q = select(Message).where(Message.conversation_id == conv.id)
    if before_id:
        q = q.where(Message.id < before_id)
    rows = list(reversed(db.scalars(q.order_by(Message.id.desc()).limit(min(limit, 100))).all()))
    now = utcnow()
    # mark the other side's messages as read
    if viewer_is_staff:
        db.execute(update(Message).where(Message.conversation_id == conv.id, Message.sender_is_staff.is_(False), Message.read_by_staff_at.is_(None)).values(read_by_staff_at=now))
    else:
        db.execute(update(Message).where(Message.conversation_id == conv.id, Message.sender_is_staff.is_(True), Message.read_by_customer_at.is_(None)).values(read_by_customer_at=now))
    out = []
    for m in rows:
        atts = db.scalars(select(Attachment).where(Attachment.message_id == m.id, Attachment.deleted_at.is_(None))).all()
        sender = db.get(User, m.sender_id) if m.sender_id else None
        name = "VIMORA" if m.sender_is_staff else (sender.profile.full_name if sender and sender.profile else None)
        out.append(message_out(m, atts, name))
    return out


def post_message(db: DB, order: Order, sender: User, *, as_staff: bool, body: str, attachment_ids: list[int]) -> dict:
    body = body.strip()
    if not body and not attachment_ids:
        raise AppError("Message cannot be empty", code="EMPTY_MESSAGE")
    conv = conversation_for(db, order)
    # sender identity comes from the authenticated session, never from the request body
    m = Message(conversation_id=conv.id, sender_id=sender.id, sender_is_staff=as_staff, body=body, created_at=utcnow())
    db.add(m)
    db.flush()
    atts: list[Attachment] = []
    if attachment_ids:
        atts = list(db.scalars(select(Attachment).where(Attachment.id.in_(attachment_ids))))
        if len(atts) != len(set(attachment_ids)):
            raise AppError("Attachment not found", code="ATTACHMENT_NOT_FOUND")
        for a in atts:
            if a.owner_id != sender.id or a.message_id is not None or a.purpose != AttachmentPurpose.MESSAGE or (a.order_id not in (None, order.id)):
                raise Forbidden("Attachment cannot be used")
            a.message_id = m.id
            a.order_id = order.id
    conv.last_message_at = m.created_at
    out = message_out(m, atts, "VIMORA" if as_staff else (sender.profile.full_name if sender.profile else None))
    publish_realtime(db, f"order:{order.id}", {"type": "message", "message": out})
    if as_staff:
        customer = db.get(User, order.customer_id)
        notify_customer(db, customer, "message.received", key_suffix=str(m.id), title_key="n.message.title", body_key="n.message.body",
                        params={"order": order.order_number}, order=order, link=f"/dashboard/orders/{order.id}?tab=messages")
    else:
        notify_admins(db, "message.received", key_suffix=str(m.id), title="NEW CUSTOMER MESSAGE", lines=[("Order", f"#{order.order_number}")], order=order)
    return out
