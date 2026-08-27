"""Safe-RL status and decision listing."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.ai.safe_rl.persist import get_decision_by_id, latest_decision, list_recent
from backend.ai.safe_rl.state import build_decision_state
from backend.services.hvac_safety_contract import is_safe_mode


def readiness_status(zone_id: str = "ZONE-01", *, building_id: Optional[str] = None) -> Dict[str, Any]:
    state = build_decision_state(zone_id, building_id=building_id)
    rls_ready = bool((state.get("rls") or {}).get("ready"))
    lstm_st = (state.get("lstm") or {}).get("status") or {}
    lstm_ready = any(v.get("status") == "MODEL_READY" for v in lstm_st.values() if isinstance(v, dict))
    telemetry_ok = bool(state.get("telemetry_ok"))
    inputs_ok = telemetry_ok and not is_safe_mode()

    overall = "INPUTS_MISSING"
    if is_safe_mode():
        overall = "BLOCKED"
    elif inputs_ok:
        overall = "READY"

    last = latest_decision(zone_id)
    return {
        "opportunity_id": "SAFE_RL",
        "zone_id": zone_id,
        "building_id": state.get("building_id"),
        "readiness": overall,
        "telemetry_ok": telemetry_ok,
        "rls_ready": rls_ready,
        "lstm_ready": lstm_ready,
        "safe_mode": is_safe_mode(),
        "last_decision": last,
        "tariff_usd_kwh": state.get("tariff_usd_kwh"),
        "comfort_band": state.get("comfort_band"),
        "wrote_setpoints": False,
    }


def list_decisions(limit: int = 20) -> Dict[str, Any]:
    rows = list_recent(limit)
    return {"decisions": rows, "count": len(rows), "wrote_setpoints": False}


def get_decision(decision_id: str) -> Optional[Dict[str, Any]]:
    return get_decision_by_id(decision_id)
