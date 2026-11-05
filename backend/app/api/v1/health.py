"""Health endpoints. Public ones reveal only up/down; details require auth or a token."""

from __future__ import annotations

import hmac
import shutil
import time

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session as DB

from app.api.deps import get_db
from app.core.config import settings
from app.core.redis import get_redis
from app.storage.backends import get_storage

router = APIRouter(tags=["health"])


@router.get("/health/live")
def live():
    return {"status": "ok"}


@router.get("/health/ready")
def ready(db: DB = Depends(get_db)):
    ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        ok = False
    try:
        get_redis().ping()
    except Exception:
        ok = False
    return JSONResponse({"status": "ok" if ok else "unavailable"}, status_code=200 if ok else 503)


def detailed(db: DB) -> dict:
    checks: dict[str, dict] = {}
    t0 = time.monotonic()
    try:
        db.execute(text("SELECT 1"))
        rev = db.execute(text("SELECT version_num FROM alembic_version")).scalar()
        checks["database"] = {"ok": True, "latency_ms": int((time.monotonic() - t0) * 1000), "migration": rev}
    except Exception as e:
        checks["database"] = {"ok": False, "error": type(e).__name__}
    try:
        r = get_redis()
        r.ping()
        hb = r.get("worker:heartbeat")
        checks["redis"] = {"ok": True}
        checks["worker"] = {"ok": bool(hb and time.time() - int(hb) < 180), "last_heartbeat_age_s": int(time.time() - int(hb)) if hb else None}
    except Exception as e:
        checks["redis"] = {"ok": False, "error": type(e).__name__}
        checks["worker"] = {"ok": False}
    checks["storage"] = {"ok": get_storage().healthy(), "backend": settings.STORAGE_BACKEND}
    if settings.STORAGE_BACKEND == "local":
        du = shutil.disk_usage(settings.LOCAL_STORAGE_PATH)
        checks["disk"] = {"ok": du.free / du.total > 0.1, "free_percent": round(100 * du.free / du.total, 1)}
    from app.models import AIProvider
    from sqlalchemy import select

    checks["ai_providers"] = {p.key: {"enabled": p.is_enabled, "last_ok": p.last_health_ok} for p in db.scalars(select(AIProvider))}
    checks["integrations"] = settings.integration_status()
    return {"status": "ok" if all(c.get("ok", True) for c in checks.values() if isinstance(c, dict) and "ok" in c) else "degraded", "checks": checks}


@router.get("/health/details")
def health_token(x_health_token: str | None = Header(None), db: DB = Depends(get_db)):
    if not settings.HEALTH_DETAILS_TOKEN or not x_health_token or not hmac.compare_digest(x_health_token, settings.HEALTH_DETAILS_TOKEN):
        return JSONResponse({"error": {"code": "NOT_FOUND", "message": "Not found"}}, status_code=404)
    return detailed(db)
