"""Process-local TTL cache for hot read paths (latest telemetry, dashboard KPIs)."""
from __future__ import annotations

import time
from threading import Lock
from typing import Any, Hashable, Optional

_lock = Lock()
_store: dict[Hashable, tuple[float, Any]] = {}


def cache_get(key: Hashable) -> Optional[Any]:
    now = time.monotonic()
    with _lock:
        hit = _store.get(key)
        if not hit:
            return None
        expires_at, value = hit
        if now >= expires_at:
            _store.pop(key, None)
            return None
        return value


def cache_set(key: Hashable, value: Any, ttl_seconds: float) -> None:
    if ttl_seconds <= 0:
        return
    with _lock:
        _store[key] = (time.monotonic() + ttl_seconds, value)


def cache_delete(key: Hashable) -> None:
    with _lock:
        _store.pop(key, None)


def cache_clear(prefix: Optional[str] = None) -> None:
    with _lock:
        if prefix is None:
            _store.clear()
            return
        for key in [k for k in _store if isinstance(k, tuple) and k and k[0] == prefix]:
            _store.pop(key, None)
        for key in [k for k in _store if isinstance(k, str) and k.startswith(prefix)]:
            _store.pop(key, None)
