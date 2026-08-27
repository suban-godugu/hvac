"""Process-local ring buffer for recent canonical telemetry samples.

DB remains the durable historian. Buffer accelerates hot windows for AI.
Never invents values — only stores what record_point already accepted.
"""
from __future__ import annotations

import os
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, Iterable, List, Optional, Union

_LOCK = threading.RLock()
_BUFFERS: Dict[str, Deque[Dict[str, Any]]] = {}

_DEFAULT_SECONDS = int(os.getenv("HVAC_TS_BUFFER_SECONDS", "7200") or "7200")
_DEFAULT_MAX = int(os.getenv("HVAC_TS_BUFFER_MAX", "720") or "720")


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _parse_ts(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    s = str(value).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        return dt.replace(tzinfo=None) if dt.tzinfo else dt
    except Exception:
        try:
            return datetime.utcfromtimestamp(float(s))
        except Exception:
            return None


def buffer_limits() -> tuple[int, int]:
    seconds = int(os.getenv("HVAC_TS_BUFFER_SECONDS", str(_DEFAULT_SECONDS)) or _DEFAULT_SECONDS)
    maxlen = int(os.getenv("HVAC_TS_BUFFER_MAX", str(_DEFAULT_MAX)) or _DEFAULT_MAX)
    return max(60, seconds), max(10, maxlen)


def clear() -> None:
    with _LOCK:
        _BUFFERS.clear()


def push(point_id: str, sample: Dict[str, Any]) -> None:
    pid = (point_id or "").strip()
    if not pid:
        return
    row = dict(sample)
    row["point_id"] = pid
    ts = _parse_ts(row.get("timestamp"))
    if ts is None:
        ts = _now()
        row["timestamp"] = ts.isoformat()
    else:
        row["timestamp"] = ts.isoformat() if not isinstance(row.get("timestamp"), str) else row["timestamp"]
    seconds, maxlen = buffer_limits()
    cutoff = _now().timestamp() - float(seconds)
    with _LOCK:
        buf = _BUFFERS.get(pid)
        if buf is None or buf.maxlen != maxlen:
            existing = list(buf) if buf is not None else []
            buf = deque(existing, maxlen=maxlen)
            _BUFFERS[pid] = buf
        buf.append(row)
        while buf:
            oldest = _parse_ts(buf[0].get("timestamp"))
            if oldest is None or oldest.timestamp() >= cutoff:
                break
            buf.popleft()


def _in_range(sample: Dict[str, Any], t0: Optional[datetime], t1: Optional[datetime]) -> bool:
    ts = _parse_ts(sample.get("timestamp"))
    if ts is None:
        return False
    if t0 is not None and ts < t0:
        return False
    if t1 is not None and ts > t1:
        return False
    return True


def window(
    point_id: str,
    t0: Optional[Union[datetime, str, float]] = None,
    t1: Optional[Union[datetime, str, float]] = None,
) -> List[Dict[str, Any]]:
    pid = (point_id or "").strip()
    if not pid:
        return []
    start = _parse_ts(t0)
    end = _parse_ts(t1)
    with _LOCK:
        buf = _BUFFERS.get(pid)
        if not buf:
            return []
        rows = [dict(s) for s in buf if _in_range(s, start, end)]
    rows.sort(key=lambda r: _parse_ts(r.get("timestamp")) or datetime.min)
    return rows


def window_many(
    point_ids: Iterable[str],
    t0: Optional[Union[datetime, str, float]] = None,
    t1: Optional[Union[datetime, str, float]] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    return {pid: window(pid, t0, t1) for pid in point_ids if (pid or "").strip()}


def covers(
    point_ids: Iterable[str],
    t0: Optional[Union[datetime, str, float]] = None,
    t1: Optional[Union[datetime, str, float]] = None,
) -> bool:
    """True when buffer spans [t0, t1] for every requested point (oldest<=t0, newest~=t1)."""
    start = _parse_ts(t0)
    end = _parse_ts(t1) or _now()
    pids = [p for p in point_ids if (p or "").strip()]
    if not pids:
        return False
    with _LOCK:
        for pid in pids:
            buf = _BUFFERS.get(pid)
            if not buf:
                return False
            times = [t for t in (_parse_ts(s.get("timestamp")) for s in buf) if t is not None]
            if not times:
                return False
            oldest, newest = min(times), max(times)
            if start is not None and oldest > start:
                return False
            if (end - newest).total_seconds() > 120:
                return False
    return True


def parse_time(value: Any) -> Optional[datetime]:
    return _parse_ts(value)
