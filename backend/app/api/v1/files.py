from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session as DB

from app.api.deps import Auth, RequestCtx, get_auth, get_ctx, get_db
from app.core.config import settings
from app.core.errors import AppError, Forbidden
from app.models.enums import ActorType as A
from app.models.enums import AttachmentPurpose
from app.schemas.serializers import attachment_out
from app.security.rate_limit import enforce
from app.services.audit import audit
from app.services.files import can_access_attachment, issue_download_link, resolve_download_token, store_upload
from app.storage.backends import get_storage

router = APIRouter(prefix="/files", tags=["files"])


@router.post("", status_code=201)
async def upload(file: UploadFile = File(...), purpose: str = Form("ORDER_INPUT"), db: DB = Depends(get_db), auth: Auth = Depends(get_auth)):
    enforce(f"upload:{auth.user.id}", 60, 3600)
    if purpose not in (AttachmentPurpose.ORDER_INPUT, AttachmentPurpose.MESSAGE):
        raise Forbidden("Invalid upload purpose")
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise AppError(f"File exceeds the {settings.MAX_UPLOAD_MB} MB limit", code="UPLOAD_TOO_LARGE", status_code=413)
    att = store_upload(db, owner_id=auth.user.id, filename=file.filename or "file", data=data, purpose=AttachmentPurpose(purpose))
    db.commit()
    return attachment_out(att)


@router.get("/{attachment_id}/link")
def download_link(attachment_id: int, db: DB = Depends(get_db), auth: Auth = Depends(get_auth), ctx: RequestCtx = Depends(get_ctx)):
    enforce(f"dl:{auth.user.id}", 300, 3600)
    url = issue_download_link(db, attachment_id, user_id=auth.user.id, is_staff=auth.is_staff)
    audit(db, "file.link_issued", actor_id=auth.user.id, actor_type=A.ADMIN if auth.is_staff else A.CUSTOMER, entity_type="attachment", entity_id=attachment_id, ip=ctx.ip)
    db.commit()
    return {"url": url, "expires_in": settings.DOWNLOAD_LINK_TTL_SECONDS}


@router.get("/download")
def download(token: str, db: DB = Depends(get_db)):
    """Signed, expiring link. Re-checks authorization for the user the link was issued to."""
    from app.models import User
    from app.security.crypto import hmac_verify

    att = resolve_download_token(db, token)
    body = hmac_verify(token) or {}
    user = db.get(User, int(body.get("u", 0)))
    if user is None or not user.is_active or not can_access_attachment(db, att, user_id=user.id, is_staff=user.is_staff):
        raise Forbidden("Access denied")
    storage = get_storage()
    presigned = storage.presigned_url(att.storage_key, filename=att.original_name, content_type=att.mime_type, ttl=60)
    if presigned:
        return RedirectResponse(presigned, status_code=302)
    safe = att.original_name.replace('"', "")
    headers = {
        # Always a download, never rendered inline: untrusted content cannot execute in our origin.
        "Content-Disposition": f'attachment; filename="{safe}"',
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "default-src 'none'; sandbox",
        "Cache-Control": "private, no-store",
    }
    return StreamingResponse(storage.open(att.storage_key), media_type="application/octet-stream", headers=headers)
