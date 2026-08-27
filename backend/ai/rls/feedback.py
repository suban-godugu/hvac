"""Stage H1 — post-VERIFIED RLS feedback. Never writes setpoints."""
from __future__ import annotations

import os
import threading
from typing import Any, Dict, Optional

from backend.services.logging_service import log_event


def _zone_from_point(point_id: Optional[str]) -> str:
    pid = (point_id or "").strip()
    if "." in pid:
        return pid.split(".", 1)[0] or "ZONE-01"
    return "ZONE-01"


def _lookback_min() -> int:
    try:
        return max(5, int(os.getenv("HVAC_RLS_POST_WRITE_LOOKBACK", "30") or "30"))
    except (TypeError, ValueError):
        return 30


def _lag_seconds() -> float:
    try:
        return max(0.0, float(os.getenv("HVAC_RLS_POST_WRITE_LAG_SECONDS", "300") or "300"))
    except (TypeError, ValueError):
        return 300.0


def _audit(command_id: str, summary: Dict[str, Any]) -> None:
    try:
        from backend.services.platform_ops_service import record_control_audit

        record_control_audit(
            user={},
            action="RLS_POST_VERIFY",
            opportunity_id=summary.get("opportunity"),
            previous_value=None,
            requested_value=None,
            decision="LEARN",
            safety_status="PASS",
            telemetry_status=None,
            approval_status=None,
            reason=f"RLS feedback after VERIFIED {command_id}",
            building_id=summary.get("building_id"),
            payload_json={"command_id": command_id, **summary},
        )
    except Exception:
        pass


def run_feedback(command_id: str, *, zone_id: str, building_id: Optional[str] = None) -> Dict[str, Any]:
    """Immediate RLS tick for a verified command (lookback window)."""
    from backend.ai.rls.runner import tick
    from backend.workers.watchdog import beat

    lookback = _lookback_min()
    try:
        result = tick(zone_id=zone_id, building_id=building_id, lookback_minutes=lookback)
        beat(note="post_verify", service="rls")
        summary = {
            "zone_id": zone_id,
            "building_id": building_id,
            "lookback_minutes": lookback,
            "updated": result.get("updated"),
            "records_used": result.get("records_used"),
            "wrote_setpoints": False,
        }
        _audit(command_id, summary)
        log_event("INFO", "rls", "RLS_POST_VERIFY", command_id=command_id, extra=summary)
        return {"ok": True, **summary, "result": result}
    except Exception as exc:
        err = {"ok": False, "error": type(exc).__name__, "zone_id": zone_id, "wrote_setpoints": False}
        log_event("WARN", "rls", "RLS_POST_VERIFY_FAIL", command_id=command_id, extra=err)
        return err


def on_command_verified(command_id: str) -> None:
    """Best-effort: schedule lagged RLS update after VERIFIED. Never raises to caller."""
    try:
        from backend.agents.runtime.command import get_command

        cmd = get_command(command_id)
        if not cmd:
            return
        zone_id = _zone_from_point(cmd.get("point_id"))
        building_id = cmd.get("building_id")
        lag = _lag_seconds()

        def _run() -> None:
            try:
                run_feedback(command_id, zone_id=zone_id, building_id=building_id)
            except Exception:
                pass

        if lag <= 0:
            _run()
        else:
            t = threading.Timer(lag, _run)
            t.daemon = True
            t.start()
    except Exception:
        pass
