"""Process isolation + heartbeat. Control loop must not continue writes if worker dies."""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any, Dict

_HEARTBEAT_PATH = os.getenv("HVAC_WATCHDOG_FILE", os.path.join(os.path.dirname(__file__), "..", "..", "database", "worker_heartbeat.txt"))
STALE_S = float(os.getenv("HVAC_WATCHDOG_STALE_SECONDS", "30"))
_last = {"ts": None, "alive": False, "note": "not-started"}


def beat(note: str = "ok") -> None:
    _last["ts"] = datetime.now(timezone.utc).isoformat()
    _last["alive"] = True
    _last["note"] = note
    try:
        with open(_HEARTBEAT_PATH, "w", encoding="utf-8") as f:
            f.write(_last["ts"] + "\n" + note)
    except Exception:
        pass


def watchdog_status() -> Dict[str, Any]:
    ts = _last.get("ts")
    age = None
    if ts:
        try:
            then = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if then.tzinfo:
                then = then.replace(tzinfo=None)
            age = (datetime.now(timezone.utc).replace(tzinfo=None) - then).total_seconds()
        except Exception:
            age = None
    alive = bool(age is not None and age <= STALE_S)
    return {"alive": alive, "ageSeconds": age, "note": _last.get("note"), "lastBeat": ts, "holdWrites": not alive}


def allow_autonomous_writes() -> bool:
    st = watchdog_status()
    return bool(st.get("alive")) and os.getenv("HVAC_SAFE_MODE", "0") not in ("1", "true", "TRUE")
