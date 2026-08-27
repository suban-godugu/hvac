"""Debounced Safe RL recommend tick. Never writes setpoints."""
from __future__ import annotations

import os
import threading
import time
from typing import Any, Dict, Optional

_LOCK = threading.Lock()
_LAST_TICK = 0.0


def tick(
    zone_id: str = "ZONE-01",
    *,
    building_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Run one recommend pass. Advisory only — does not call command_writer."""
    from backend.ai.safe_rl.service import recommend
    from backend.workers.watchdog import beat

    result = recommend(zone_id=zone_id or "ZONE-01", building_id=building_id)
    try:
        beat(note="tick", service="safe_rl")
    except Exception:
        pass
    return {
        **result,
        "wrote_setpoints": False,
    }


def tick_debounced(
    zone_id: str = "ZONE-01",
    *,
    building_id: Optional[str] = None,
    force: bool = False,
) -> Optional[Dict[str, Any]]:
    """If HVAC_SAFE_RL_TICK_SECONDS <= 0, no-op (API-only Stage E default)."""
    global _LAST_TICK
    try:
        interval = float(os.getenv("HVAC_SAFE_RL_TICK_SECONDS", "0") or "0")
    except (TypeError, ValueError):
        interval = 0.0
    if interval <= 0 and not force:
        return None
    interval = max(5.0, interval) if interval > 0 else 0.0
    now = time.monotonic()
    with _LOCK:
        if not force and interval > 0 and (now - _LAST_TICK) < interval:
            return None
        if force or interval > 0:
            _LAST_TICK = now
        else:
            return None
    try:
        return tick(zone_id=zone_id, building_id=building_id)
    except Exception as exc:
        return {"updated": False, "error": type(exc).__name__, "wrote_setpoints": False}


def reset_debounce() -> None:
    global _LAST_TICK
    with _LOCK:
        _LAST_TICK = 0.0
