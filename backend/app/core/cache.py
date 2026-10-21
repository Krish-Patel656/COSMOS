"""Cache abstraction with an in-process default and a Redis backend.

The explorer endpoints run the same filtered aggregate queries repeatedly as
users drag sliders, so caching them matters. But requiring a Redis server to run
the project locally does not, hence the two interchangeable backends behind one
interface. ``REDIS_URL`` picks the Redis implementation; its absence falls back
to a bounded TTL dictionary that is perfectly adequate for a single process.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from typing import Any

from app.core.config import settings


class CacheBackend:
    async def get(self, key: str) -> Any | None:  # pragma: no cover - interface
        raise NotImplementedError

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:  # pragma: no cover
        raise NotImplementedError

    async def delete_prefix(self, prefix: str) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    async def close(self) -> None:  # pragma: no cover - interface
        return None


class InMemoryCache(CacheBackend):
    """TTL cache with naive size capping.

    When the cache is full we drop the entries closest to expiry rather than
    implementing true LRU; for read-heavy catalogue queries the difference is
    not worth the bookkeeping.
    """

    def __init__(self, max_entries: int, default_ttl: int) -> None:
        self._store: dict[str, tuple[float, Any]] = {}
        self._max_entries = max_entries
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if expires_at < time.monotonic():
                self._store.pop(key, None)
                return None
            return value

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        async with self._lock:
            if len(self._store) >= self._max_entries:
                for stale in sorted(self._store, key=lambda k: self._store[k][0])[
                    : max(1, self._max_entries // 8)
                ]:
                    self._store.pop(stale, None)
            self._store[key] = (time.monotonic() + (ttl or self._default_ttl), value)

    async def delete_prefix(self, prefix: str) -> None:
        async with self._lock:
            for key in [k for k in self._store if k.startswith(prefix)]:
                self._store.pop(key, None)


class RedisCache(CacheBackend):
    def __init__(self, url: str, default_ttl: int) -> None:
        import redis.asyncio as redis  # imported lazily so redis stays optional

        self._client = redis.from_url(url, encoding="utf-8", decode_responses=True)
        self._default_ttl = default_ttl

    async def get(self, key: str) -> Any | None:
        raw = await self._client.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        await self._client.set(key, json.dumps(value, default=str), ex=ttl or self._default_ttl)

    async def delete_prefix(self, prefix: str) -> None:
        async for key in self._client.scan_iter(match=f"{prefix}*", count=500):
            await self._client.delete(key)

    async def close(self) -> None:
        await self._client.aclose()


_backend: CacheBackend | None = None


def get_cache() -> CacheBackend:
    global _backend
    if _backend is None:
        if settings.redis_url:
            try:
                _backend = RedisCache(settings.redis_url, settings.cache_ttl_seconds)
            except Exception:  # noqa: BLE001 - never let caching break a request
                _backend = InMemoryCache(settings.cache_max_entries, settings.cache_ttl_seconds)
        else:
            _backend = InMemoryCache(settings.cache_max_entries, settings.cache_ttl_seconds)
    return _backend


async def close_cache() -> None:
    global _backend
    if _backend is not None:
        await _backend.close()
        _backend = None


def cache_key(namespace: str, **parts: Any) -> str:
    """Stable cache key from a namespace and arbitrary query parameters."""
    payload = json.dumps(parts, sort_keys=True, default=str)
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]
    return f"cosmos:{namespace}:{digest}"
