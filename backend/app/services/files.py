"""Upload validation, storage, malware scan hook, and download authorization."""

from __future__ import annotations

import hashlib
import re
import socket
import struct
import unicodedata
import zipfile
from io import BytesIO

import magic
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DB

from app.core.config import settings
from app.core.db import utcnow
from app.core.errors import AppError, Forbidden, NotFound
from app.core.logging import get_logger
from app.models import Attachment, Deliverable, Order
from app.models.enums import AttachmentPurpose, OrderStatus, ScanStatus
from app.security.crypto import hmac_sign, hmac_verify, new_token
from app.storage.backends import get_storage

log = get_logger("files")

# extension -> set of acceptable sniffed MIME types
ALLOWED_TYPES: dict[str, set[str]] = {
    "pdf": {"application/pdf"},
    "png": {"image/png"},
    "jpg": {"image/jpeg"},
    "jpeg": {"image/jpeg"},
    "webp": {"image/webp"},
    "gif": {"image/gif"},
    "txt": {"text/plain"},
    "md": {"text/plain", "text/markdown"},
    "csv": {"text/plain", "text/csv", "application/csv"},
    "json": {"application/json", "text/plain"},
    "docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/zip"},
    "xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/zip"},
    "pptx": {"application/vnd.openxmlformats-officedocument.presentationml.presentation", "application/zip"},
    "zip": {"application/zip"},
    "mp3": {"audio/mpeg"},
    "wav": {"audio/x-wav", "audio/wav"},
    "mp4": {"video/mp4"},
    "mov": {"video/quicktime"},
}
IMAGE_EXTS = {"png", "jpg", "jpeg", "webp"}
# Never accepted regardless of extension
DANGEROUS_MIME = re.compile(r"(x-(ms)?dos(exec)?|x-executable|x-sharedlib|x-mach-binary|x-msdownload|javascript|x-sh|x-php|text/html|image/svg)")


def sanitize_filename(name: str) -> str:
    name = unicodedata.normalize("NFKC", name or "file").replace("\\", "/").split("/")[-1]
    name = re.sub(r"[^\w.\- ()]+", "_", name, flags=re.UNICODE).strip(" .")
    return (name or "file")[:200]


def _extension(name: str) -> str:
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def _office_zip_ok(data: bytes, ext: str) -> bool:
    """OOXML files must be zips containing [Content_Types].xml and no macros."""
    try:
        with zipfile.ZipFile(BytesIO(data)) as zf:
            names = zf.namelist()
            if len(names) > 5000:
                return False
            total = sum(i.file_size for i in zf.infolist())
            if total > 500 * 1024 * 1024:  # zip-bomb guard
                return False
            if ext in {"docx", "xlsx", "pptx"}:
                return "[Content_Types].xml" in names and not any(n.lower().endswith("vbaproject.bin") for n in names)
            return all(".." not in n and not n.startswith("/") for n in names)
    except zipfile.BadZipFile:
        return False


def scan_bytes(data: bytes) -> str:
    """ClamAV INSTREAM scan when CLAMAV_HOST is configured; otherwise NOT_SCANNED."""
    if not settings.CLAMAV_HOST:
        return ScanStatus.NOT_SCANNED
    try:
        with socket.create_connection((settings.CLAMAV_HOST, settings.CLAMAV_PORT), timeout=30) as s:
            s.sendall(b"zINSTREAM\0")
            for i in range(0, len(data), 8192):
                chunk = data[i : i + 8192]
                s.sendall(struct.pack("!L", len(chunk)) + chunk)
            s.sendall(struct.pack("!L", 0))
            reply = s.recv(4096).decode(errors="replace")
        if "FOUND" in reply:
            return ScanStatus.INFECTED
        return ScanStatus.CLEAN if "OK" in reply else ScanStatus.ERROR
    except OSError:
        log.warning("ClamAV scan failed")
        return ScanStatus.ERROR


def validate_upload(filename: str, data: bytes, *, images_only: bool = False) -> tuple[str, str]:
    """Return (safe_name, mime) or raise AppError."""
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if not data:
        raise AppError("The file is empty", code="UPLOAD_EMPTY")
    if len(data) > max_bytes:
        raise AppError(f"File exceeds the {settings.MAX_UPLOAD_MB} MB limit", code="UPLOAD_TOO_LARGE", status_code=413)
    safe = sanitize_filename(filename)
    ext = _extension(safe)
    allowed = IMAGE_EXTS if images_only else set(ALLOWED_TYPES)
    if ext not in allowed:
        raise AppError("This file type is not allowed", code="UPLOAD_TYPE_NOT_ALLOWED", details={"allowed": sorted(allowed)})
    sniffed = magic.from_buffer(data[:8192], mime=True)
    if DANGEROUS_MIME.search(sniffed):
        raise AppError("This file content is not allowed", code="UPLOAD_CONTENT_REJECTED")
    if sniffed not in ALLOWED_TYPES[ext]:
        raise AppError("File content does not match its extension", code="UPLOAD_CONTENT_MISMATCH", details={"detected": sniffed})
    if ext in {"docx", "xlsx", "pptx", "zip"} and not _office_zip_ok(data, ext):
        raise AppError("Archive or document structure is not allowed", code="UPLOAD_CONTENT_REJECTED")
    if ext in {"txt", "md", "csv", "json"}:
        head = data[:4096].lower()
        if b"<script" in head or b"<html" in head:
            raise AppError("This file content is not allowed", code="UPLOAD_CONTENT_REJECTED")
    return safe, sniffed


def store_upload(
    db: DB,
    *,
    owner_id: int | None,
    filename: str,
    data: bytes,
    purpose: AttachmentPurpose,
    order_id: int | None = None,
    images_only: bool = False,
    is_public: bool = False,
    enforce_quota: bool = True,
) -> Attachment:
    safe, mime = validate_upload(filename, data, images_only=images_only)
    if enforce_quota and owner_id is not None:
        used = db.scalar(select(func.coalesce(func.sum(Attachment.size_bytes), 0)).where(Attachment.owner_id == owner_id, Attachment.deleted_at.is_(None))) or 0
        if used + len(data) > settings.USER_STORAGE_QUOTA_MB * 1024 * 1024:
            raise AppError("Storage quota exceeded", code="STORAGE_QUOTA_EXCEEDED", status_code=413)
    scan = scan_bytes(data)
    if scan == ScanStatus.INFECTED:
        raise AppError("The file was rejected by the malware scanner", code="UPLOAD_MALWARE")
    now = utcnow()
    key = f"{purpose.lower()}/{now:%Y/%m}/{new_token(24)}"
    get_storage().put(key, data, "application/octet-stream")
    att = Attachment(
        owner_id=owner_id,
        order_id=order_id,
        purpose=purpose,
        storage_key=key,
        original_name=safe,
        mime_type=mime,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        scan_status=scan,
        is_public=is_public,
        created_at=now,
    )
    db.add(att)
    db.flush()
    return att


def can_access_attachment(db: DB, att: Attachment, *, user_id: int, is_staff: bool) -> bool:
    """File ownership / authorization policy."""
    if att.deleted_at is not None:
        return False
    if att.is_public:
        return True
    if is_staff:
        return True
    if att.order_id is None:
        return att.owner_id == user_id
    order = db.get(Order, att.order_id)
    if order is None or order.customer_id != user_id:
        return False
    if att.purpose in (AttachmentPurpose.ORDER_INPUT, AttachmentPurpose.MESSAGE):
        return True
    if att.purpose == AttachmentPurpose.DELIVERABLE:
        # released deliverables only, and only once the order is in a delivery state
        d = db.scalar(select(Deliverable).where(Deliverable.attachment_id == att.id))
        return bool(d and d.released_at and order.status in {OrderStatus.DELIVERED, OrderStatus.CLOSED, OrderStatus.REVISION_REQUESTED})
    return False  # AI_OUTPUT is staff-only until promoted to a deliverable


def issue_download_link(db: DB, attachment_id: int, *, user_id: int, is_staff: bool) -> str:
    att = db.get(Attachment, attachment_id)
    if att is None or not can_access_attachment(db, att, user_id=user_id, is_staff=is_staff):
        raise NotFound("File not found")  # do not reveal existence
    ttl = settings.DOWNLOAD_LINK_TTL_SECONDS
    presigned = get_storage().presigned_url(att.storage_key, filename=att.original_name, content_type=att.mime_type, ttl=ttl)
    if presigned:
        return presigned
    token = hmac_sign({"a": att.id, "u": user_id}, ttl)
    return f"{settings.API_URL.rstrip('/')}/api/v1/files/download?token={token}"


def resolve_download_token(db: DB, token: str) -> Attachment:
    body = hmac_verify(token)
    if not body:
        raise Forbidden("Download link is invalid or expired", code="LINK_EXPIRED")
    att = db.get(Attachment, int(body["a"]))
    if att is None or att.deleted_at is not None:
        raise NotFound("File not found")
    return att
