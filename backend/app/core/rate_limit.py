"""
Sliding-window rate limiter for auth endpoints.

Production: set REDIS_URL to share counters across instances.
Falls back to in-process memory when Redis is unset/unreachable so
single-instance demos keep working with zero config (see docs/production.md).
"""
from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from threading import Lock


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()
        self._redis = self._connect_redis()

    def _connect_redis(self):  # type: ignore[no-untyped-def]
        url = os.getenv("REDIS_URL", "")
        if not url:
            return None
        try:
            import redis  # type: ignore

            client = redis.Redis.from_url(url, socket_connect_timeout=2)
            client.ping()
            return client
        except Exception:
            return None

    def _redis_allow(self, key: str) -> bool | None:
        """Fixed-window counter in Redis. None = Redis unavailable, use memory."""
        if self._redis is None:
            return None
        try:
            rkey = f"ratelimit:{key}"
            count = self._redis.incr(rkey)
            if count == 1:
                self._redis.expire(rkey, self.window_seconds)
            return count <= self.max_requests
        except Exception:
            return None

    def allow(self, key: str) -> bool:
        decided = self._redis_allow(key)
        if decided is not None:
            return decided
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > self.window_seconds:
                q.popleft()
            if len(q) >= self.max_requests:
                return False
            q.append(now)
            return True

    def reset(self) -> None:
        """Clear local counters (tests) and best-effort Redis keys."""
        with self._lock:
            self._hits.clear()
        if self._redis is not None:
            try:
                for k in self._redis.scan_iter("ratelimit:*"):
                    self._redis.delete(k)
            except Exception:
                pass

    def remaining(self, key: str) -> int:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > self.window_seconds:
                q.popleft()
            return max(0, self.max_requests - len(q))