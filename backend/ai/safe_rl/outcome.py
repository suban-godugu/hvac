"""Stage H3 — measure realized reward after VERIFIED. Never writes setpoints."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.services.logging_service import log_event


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _num(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _find_decision_for_command(command_id: str):
    from database.session import SessionLocal
    from database.models_platform import SafeRlDecisionDB

    db = SessionLocal()
    try:
        row = db.query(SafeRlDecisionDB).filter_by(command_id=command_id).first()
        if row:
            return row
        # Match via mapped_command_ids_json
        rows = db.query(SafeRlDecisionDB).order_by(SafeRlDecisionDB.created_at.desc()).limit(50).all()
        for r in rows:
            ids = list(r.mapped_command_ids_json or [])
            if command_id in ids:
                return r
        return None
    finally:
        db.close()


def _comfort_component(tin: Optional[float], lo: float, hi: float) -> float:
    """Higher is better: 1 inside band, decays outside."""
    if tin is None:
        return 0.0
    if lo <= tin <= hi:
        return 1.0
    if tin < lo:
        return max(-1.0, 1.0 - (lo - tin))
    return max(-1.0, 1.0 - (tin - hi))


def measure_after_verify(command_id: str) -> Dict[str, Any]:
    """Join Safe RL decision to verified command; persist realized reward."""
    from backend.agents.runtime.command import get_command
    from database.session import SessionLocal
    from database.models_platform import SafeRlDecisionDB

    cmd = get_command(command_id)
    if not cmd:
        return {"ok": False, "code": "NOT_FOUND", "wrote_setpoints": False}

    decision = _find_decision_for_command(command_id)
    # Also allow orphan commands: create soft link via latest decision for zone
    zone_id = "ZONE-01"
    pid = str(cmd.get("point_id") or "")
    if "." in pid:
        zone_id = pid.split(".", 1)[0]

    lo = float(os.getenv("HVAC_COMFORT_MIN_C", "21") or "21")
    hi = float(os.getenv("HVAC_COMFORT_MAX_C", "24") or "24")
    w_e = float(os.getenv("HVAC_SAFE_RL_REWARD_W_ENERGY", "1.0") or "1.0")
    w_c = float(os.getenv("HVAC_SAFE_RL_REWARD_W_COMFORT", "2.0") or "2.0")
    w_eq = float(os.getenv("HVAC_SAFE_RL_REWARD_W_EQUIPMENT", "0.5") or "0.5")

    tin = None
    power = None
    try:
        from backend.services.canonical_telemetry_service import latest_points

        rows = latest_points(limit=200)
        for r in rows:
            if r.get("point_id") == f"{zone_id}.zone_temperature":
                tin = _num(r.get("value"))
            if r.get("point_id") in ("CH-01.power", "AHU-01.power", f"{zone_id}.hvac_power"):
                power = _num(r.get("value"))
    except Exception:
        pass

    snap = (decision.state_snapshot_json if decision else None) or {}
    norm = snap.get("normalized") or {}
    if tin is None:
        tin = _num(norm.get("Indoor_Temp"))
    prior_power = _num(norm.get("HVAC_Power"))

    # Energy: positive if power dropped vs snapshot
    energy = 0.0
    if power is not None and prior_power is not None:
        energy = float(prior_power - power)
    elif cmd.get("old_value") is not None and cmd.get("new_value") is not None:
        # Setpoint raise often saves cooling energy (heuristic)
        delta_sp = float(cmd["new_value"]) - float(cmd["old_value"])
        energy = 0.3 * delta_sp

    comfort = _comfort_component(tin, lo, hi)
    # Equipment: +1 if verified cleanly (no rollback path)
    equipment = 1.0 if (cmd.get("status") or "").upper() == "VERIFIED" else 0.0

    reward = w_e * energy + w_c * comfort + w_eq * equipment

    db = SessionLocal()
    try:
        row = None
        if decision is not None:
            row = db.query(SafeRlDecisionDB).filter_by(id=decision.id).first()
        if row is None:
            # No Safe RL decision — still return measured values for audit
            out = {
                "ok": True,
                "decision_id": None,
                "command_id": command_id,
                "realized_reward": reward,
                "reward_energy": energy,
                "reward_comfort": comfort,
                "reward_equipment": equipment,
                "wrote_setpoints": False,
            }
            log_event("INFO", "safe-rl", "REWARD_MEASURED", command_id=command_id, extra=out)
            return out

        row.realized_reward = float(reward)
        row.reward_energy = float(energy)
        row.reward_comfort = float(comfort)
        row.reward_equipment = float(equipment)
        row.measured_at = _now()
        row.command_id = command_id
        db.commit()
        out = {
            "ok": True,
            "decision_id": row.id,
            "command_id": command_id,
            "realized_reward": float(reward),
            "reward_energy": float(energy),
            "reward_comfort": float(comfort),
            "reward_equipment": float(equipment),
            "wrote_setpoints": False,
        }
        log_event("INFO", "safe-rl", "REWARD_MEASURED", command_id=command_id, extra=out)
        try:
            from backend.workers.watchdog import beat

            beat(note="reward", service="safe_rl")
        except Exception:
            pass
        return out
    except Exception as exc:
        db.rollback()
        return {"ok": False, "error": type(exc).__name__, "wrote_setpoints": False}
    finally:
        db.close()
