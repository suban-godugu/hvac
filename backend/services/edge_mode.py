"""Stage H4 — edge posture / cloud-down detection."""
from __future__ import annotations

import os
import urllib.request
from typing import Any, Dict, Optional


def edge_mode_enabled() -> bool:
    return os.getenv("HVAC_EDGE_MODE", "0").strip() in ("1", "true", "TRUE", "yes")


def cloud_url() -> Optional[str]:
    url = (os.getenv("HVAC_CLOUD_URL") or "").strip()
    return url or None


def cloud_reachable(timeout: float = 2.0) -> bool:
    """True if cloud optional URL responds; empty URL => cloud not configured (local-only)."""
    url = cloud_url()
    if not url:
        return False
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return int(getattr(resp, "status", 200) or 200) < 500
    except Exception:
        return False


def edge_status() -> Dict[str, Any]:
    edge = edge_mode_enabled()
    url = cloud_url()
    reachable = cloud_reachable() if url else False
    return {
        "edge_mode": edge,
        "cloud_url": url,
        "cloud_reachable": reachable,
        "cloud_down": bool(url) and not reachable,
        "local_loop_ok": True,  # infer + rules + control run in-process
        "hint": (
            "Cloud unreachable — local Sense→Optimize→Control continues"
            if (edge and url and not reachable)
            else ("Edge local package" if edge else "Central / full stack")
        ),
    }
