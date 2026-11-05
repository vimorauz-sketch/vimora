"""Hashing, token generation, symmetric encryption for stored secrets, and HMAC signing."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

# Argon2id with OWASP-recommended baseline parameters (m=19 MiB, t=2, p=1) raised slightly.
_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2, hash_len=32, salt_len=16)
_DUMMY_HASH = _hasher.hash("vimora-timing-equaliser")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    """Constant-ish time verification; also burns time when the user does not exist."""
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def new_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _secret_key() -> bytes:
    key = settings.SECRET_KEY
    if not key:
        if settings.is_production:
            raise RuntimeError("SECRET_KEY is not configured")
        key = "dev-insecure-secret-key-change-me-0000000000"
    return key.encode()


def _fernet() -> Fernet:
    key = settings.SETTINGS_ENCRYPTION_KEY
    if not key:
        if settings.is_production:
            raise RuntimeError("SETTINGS_ENCRYPTION_KEY is not configured")
        # deterministic dev-only key derived from SECRET_KEY
        key = base64.urlsafe_b64encode(hashlib.sha256(b"dev-fernet:" + _secret_key()).digest()).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_secret(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(token: str | None) -> str | None:
    if not token:
        return None
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        return None


def hmac_sign(payload: dict, ttl_seconds: int) -> str:
    """Compact signed token: base64(json).base64(hmac). Includes expiry."""
    body = dict(payload)
    body["exp"] = int(time.time()) + ttl_seconds
    raw = base64.urlsafe_b64encode(json.dumps(body, separators=(",", ":"), sort_keys=True).encode()).rstrip(b"=")
    sig = base64.urlsafe_b64encode(hmac.new(_secret_key(), raw, hashlib.sha256).digest()).rstrip(b"=")
    return f"{raw.decode()}.{sig.decode()}"


def hmac_verify(token: str) -> dict | None:
    try:
        raw, sig = token.split(".", 1)
        expected = base64.urlsafe_b64encode(hmac.new(_secret_key(), raw.encode(), hashlib.sha256).digest()).rstrip(b"=").decode()
        if not hmac.compare_digest(expected, sig):
            return None
        body = json.loads(base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)))
        if int(body.get("exp", 0)) < int(time.time()):
            return None
        return body
    except (ValueError, json.JSONDecodeError):
        return None


PASSWORD_RULES = {
    "too_short": "Password must be at least 10 characters long",
    "too_long": "Password must be at most 256 characters long",
    "classes": "Password must contain at least three of: lowercase, uppercase, digits, symbols",
    "contains_email": "Password must not contain your email name",
    "too_common": "Password is too common",
}


def validate_password_strength(password: str, email: str | None = None) -> list[str]:
    """Returns rule codes (see PASSWORD_RULES); the client shows them in the user's language."""
    problems: list[str] = []
    if len(password) < 10:
        problems.append("too_short")
    if len(password) > 256:
        problems.append("too_long")
    classes = sum([any(c.islower() for c in password), any(c.isupper() for c in password), any(c.isdigit() for c in password), any(not c.isalnum() for c in password)])
    if classes < 3:
        problems.append("classes")
    if email and email.split("@")[0].lower() in password.lower() and len(email.split("@")[0]) >= 4:
        problems.append("contains_email")
    if password.lower() in {"password123!", "qwerty12345", "1234567890a", "admin123456"}:
        problems.append("too_common")
    return problems
