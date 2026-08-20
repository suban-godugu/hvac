"""Shared shape for the five HVAC agent index files. Not an engine."""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

OpportunityRow = Dict[str, str]


def row(
    oid: str,
    title: str,
    route: str,
    engine: str,
    description: str,
) -> OpportunityRow:
    return {
        "opportunity_id": oid,
        "title": title,
        "route": route,
        "engine": engine,
        "description": description,
    }


def stamp(oid: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(payload or {})
    out["opportunity_id"] = oid
    out.setdefault("live", False)
    try:
        from backend.ml.client import attach_ml_prediction

        return attach_ml_prediction(oid, out)
    except Exception:
        out.setdefault("ml", {"status": "DATA SOURCE ERROR", "provenance": "NO DATA", "prediction": None})
        return out


def require_oid(oid: str, allowed: Tuple[str, ...]) -> str:
    key = (oid or "").strip().upper()
    if key not in allowed:
        raise ValueError(f"This agent owns {', '.join(allowed)}; not {oid!r}")
    return key
