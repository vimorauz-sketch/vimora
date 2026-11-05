"""Structured JSON logging with secret redaction."""

from __future__ import annotations

import json
import logging
import re
import sys
from contextvars import ContextVar
from datetime import UTC, datetime

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)

_SECRET_PATTERNS = [
    re.compile(r"(?i)(password|passwd|secret|token|api[_-]?key|authorization|cookie)(\"?\s*[:=]\s*\"?)([^\s\",&]+)"),
    re.compile(r"\b\d{6,10}:[A-Za-z0-9_-]{30,}\b"),  # telegram bot tokens
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),  # openai/anthropic style keys
    re.compile(r"\bsk_(live|test)_[A-Za-z0-9]{10,}\b"),  # stripe
]


def redact(text: str) -> str:
    for pattern in _SECRET_PATTERNS:
        if pattern.groups >= 3:
            text = pattern.sub(lambda m: f"{m.group(1)}{m.group(2)}[REDACTED]", text)
        else:
            text = pattern.sub("[REDACTED]", text)
    return text


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": redact(record.getMessage()),
        }
        rid = request_id_ctx.get()
        if rid:
            payload["request_id"] = rid
        extra = getattr(record, "extra_fields", None)
        if isinstance(extra, dict):
            payload.update({k: redact(str(v)) for k, v in extra.items()})
        if record.exc_info:
            payload["exc"] = redact(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())
    for noisy in ("uvicorn.access",):
        logging.getLogger(noisy).setLevel("WARNING")


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
