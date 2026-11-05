from __future__ import annotations

from functools import lru_cache

import redis

from app.core.config import settings


@lru_cache
def get_redis() -> redis.Redis:
    return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True, socket_timeout=3, socket_connect_timeout=3)
