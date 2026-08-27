"""Sliding-window rate limiter.

Two implementations share the same `check(key, max_attempts, window_seconds)
-> bool` interface:

- `InMemoryRateLimiter` — process-local, zero dependencies. Fine for local
  development and single-process deployments, but each process has its own
  counters, so it under-limits behind a multi-worker/multi-instance
  production deployment.
- `RedisRateLimiter` — shared across every process/instance via Redis, using
  a sorted-set sliding window (ZADD + ZREMRANGEBYSCORE + ZCARD in a pipeline)
  so concurrent workers see the same counters.

`get_rate_limiter()` picks the Redis-backed implementation automatically
when `REDIS_URL` is configured, and falls back to the in-memory limiter
otherwise (logging a warning) so the app still runs without Redis in dev.
"""
import logging
import time
from collections import defaultdict
from threading import Lock
from typing import Protocol

logger = logging.getLogger("rockstar_organics")


class RateLimiterProtocol(Protocol):
    def check(self, key: str, max_attempts: int, window_seconds: int) -> bool: ...


class InMemoryRateLimiter:
    def __init__(self):
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def check(self, key: str, max_attempts: int, window_seconds: int) -> bool:
        now = time.time()
        with self._lock:
            hits = [h for h in self._hits[key] if now - h < window_seconds]
            if len(hits) >= max_attempts:
                self._hits[key] = hits
                return False
            hits.append(now)
            self._hits[key] = hits
            return True


class RedisRateLimiter:
    """Sliding-window limiter backed by a Redis sorted set per key.

    Each hit is stored as a sorted-set member scored by its timestamp so
    that expired hits can be trimmed with ZREMRANGEBYSCORE before counting.
    This keeps every worker process/instance consistent, unlike the
    in-memory limiter.
    """

    def __init__(self, redis_client):
        self._redis = redis_client

    def check(self, key: str, max_attempts: int, window_seconds: int) -> bool:
        now = time.time()
        window_start = now - window_seconds
        redis_key = f"ratelimit:{key}"
        pipe = self._redis.pipeline()
        pipe.zremrangebyscore(redis_key, 0, window_start)
        pipe.zcard(redis_key)
        _, count = pipe.execute()
        if count >= max_attempts:
            return False
        pipe = self._redis.pipeline()
        pipe.zadd(redis_key, {f"{now}:{id(object())}": now})
        pipe.expire(redis_key, window_seconds)
        pipe.execute()
        return True


def _build_rate_limiter() -> RateLimiterProtocol:
    import os

    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        return InMemoryRateLimiter()
    try:
        import redis  # type: ignore

        client = redis.from_url(redis_url, socket_connect_timeout=2, socket_timeout=2)
        client.ping()
        logger.info('{"message": "rate limiter using Redis backend", "redis_url_configured": true}')
        return RedisRateLimiter(client)
    except Exception as exc:  # pragma: no cover - exercised only when Redis is misconfigured
        logger.warning(
            '{"message": "REDIS_URL configured but Redis is unreachable; falling back to in-memory rate limiter", "error": "%s"}',
            exc,
        )
        return InMemoryRateLimiter()


# Built once at import time. In tests, `conftest.py` resets in-memory state
# directly (or points REDIS_URL at a test instance); production deployments
# with multiple workers/instances MUST set REDIS_URL so limits are shared.
rate_limiter: RateLimiterProtocol = _build_rate_limiter()
