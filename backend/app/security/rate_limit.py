"""Redis fixed-window rate limiting.

Failure mode: if Redis is unreachable we fail *open* for ordinary endpoints (availability)
but callers may pass fail_closed=True for sensitive endpoints such as login.
"""

from __future__ import annotations

import time

import redis

from app.core.errors import RateLimited
from app.core.logging import get_logger
from app.core.redis import get_redis

log = get_logger("ratelimit")


def hit(key: str, limit: int, window_seconds: int, *, fail_closed: bool = False) -> tuple[bool, int]:
    """Increment counter; returns (allowed, retry_after_seconds)."""
    bucket = int(time.time() // window_seconds)
    rkey = f"rl:{key}:{bucket}"
    try:
        r = get_redis()
        pipe = r.pipeline()
        pipe.incr(rkey)
        pipe.expire(rkey, window_seconds + 1)
        count, _ = pipe.execute()
    except redis.RedisError:
        log.warning("Rate limiter unavailable for key prefix %s", key.split(":")[0])
        return (not fail_closed, 5)
    retry_after = window_seconds - int(time.time() % window_seconds)
    return (int(count) <= limit, retry_after)


def enforce(key: str, limit: int, window_seconds: int, *, fail_closed: bool = False, message: str = "Too many requests") -> None:
    allowed, retry_after = hit(key, limit, window_seconds, fail_closed=fail_closed)
    if not allowed:
        raise RateLimited(message, details={"retry_after": retry_after})


# --- Login throttling -----------------------------------------------------------------
# Progressive delay keyed on (account, ip) so an attacker cannot lock a legitimate user out
# from a different IP, plus a looser per-account ceiling to slow distributed guessing.

def login_failure_count(email: str, ip: str) -> int:
    try:
        return int(get_redis().get(f"lf:{email}:{ip}") or 0)
    except redis.RedisError:
        return 0


def record_login_failure(email: str, ip: str) -> None:
    try:
        r = get_redis()
        pipe = r.pipeline()
        pipe.incr(f"lf:{email}:{ip}")
        pipe.expire(f"lf:{email}:{ip}", 3600)
        pipe.incr(f"lfa:{email}")
        pipe.expire(f"lfa:{email}", 3600)
        pipe.execute()
    except redis.RedisError:
        pass


def clear_login_failures(email: str, ip: str) -> None:
    try:
        get_redis().delete(f"lf:{email}:{ip}")
    except redis.RedisError:
        pass


def check_login_allowed(email: str, ip: str) -> None:
    enforce(f"login-ip:{ip}", 30, 300, fail_closed=True, message="Too many login attempts from this network. Try again later.")
    try:
        r = get_redis()
        pair = int(r.get(f"lf:{email}:{ip}") or 0)
        acct = int(r.get(f"lfa:{email}") or 0)
        ttl = r.ttl(f"lf:{email}:{ip}")
    except redis.RedisError:
        raise RateLimited("Login temporarily unavailable", details={"retry_after": 5}) from None
    # after 5 failures for this account from this IP: exponential back-off, capped at 15 minutes
    if pair >= 5:
        backoff = min(2 ** (pair - 5) * 30, 900)
        last = f"lfl:{email}:{ip}"
        try:
            if r.set(last, "1", ex=backoff, nx=True) is None:
                raise RateLimited("Too many failed attempts. Please wait before trying again.", details={"retry_after": max(r.ttl(last), 1)})
        except redis.RedisError:
            pass
    if acct >= 100:
        raise RateLimited("This account is temporarily protected due to unusual activity.", details={"retry_after": max(ttl, 60)})
