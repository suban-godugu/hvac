from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from backend.bms.command_writer import resolve_write_target, write_point
from backend.bms.connection_manager import get_connection_manager
from backend.agents.runtime.command import get_command, set_status
from backend.services.hvac_safety_contract import evaluate_dispatch
from backend.services.logging_service import log_event


def _context_for(cmd: Dict[str, Any], action: str) -> Dict[str, Any]:
    from backend.services.platform_bms_service import platform_snapshot

    snap = platform_snapshot()
    tel = snap.get("telemetry") or {}
    payload = cmd.get("payload_json") if isinstance(cmd.get("payload_json"), dict) else {}
    return {
        "action": action,
        "opportunity_id": cmd.get("opportunity") or payload.get("opportunity"),
        "point_id": cmd.get("point_id"),
        "current_value": cmd.get("old_value"),
        "old_value": cmd.get("old_value"),
        "target_value": cmd.get("old_value") if action == "ROLLBACK" else cmd.get("new_value"),
        "new_value": cmd.get("old_value") if action == "ROLLBACK" else cmd.get("new_value"),
        "source": tel.get("source"),
        "telemetry": {
            "source": tel.get("source"),
            "quality": tel.get("quality"),
            "age_seconds": tel.get("ageSeconds"),
            "raw": tel.get("status"),
        },
        "supervisory": {"decision": "OPTIMIZE", "confidence": 0.99},
        "safety": {"status": snap.get("safety"), "passed": snap.get("safety") == "PASS"},
        "approval_status": "APPROVED",
    }


def _persist_verify_readback(command_id: str, readback: Any, bms_ident: Optional[str], ok: bool, reason: str) -> None:
    from database.models_platform import ControlCommandDB
    from database.session import SessionLocal

    db = SessionLocal()
    try:
        row = db.query(ControlCommandDB).filter_by(command_id=command_id).first()
        if row is None:
            return
        payload = dict(row.payload_json or {}) if isinstance(row.payload_json, dict) else {}
        payload["verify"] = {
            "readback": readback,
            "bms_ident": bms_ident,
            "ok": ok,
            "reason": reason,
        }
        row.payload_json = payload
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def verify_command(command_id: str, expected: Optional[float] = None, tolerance: float = 0.5) -> Tuple[bool, str]:
    cmd = get_command(command_id)
    if not cmd:
        return False, "NOT_FOUND"
    ok, reason, classified = evaluate_dispatch(_context_for(cmd, "VERIFY"))
    if not ok:
        set_status(command_id, "VERIFICATION_FAILED")
        return False, classified.get("code") or reason
    set_status(command_id, "VERIFYING")
    mgr = get_connection_manager()
    adapter = mgr.adapter()
    point_id = cmd.get("point_id")
    target = expected if expected is not None else cmd.get("new_value")
    if adapter is None or not mgr.is_production_connected() or not point_id or target is None:
        set_status(command_id, "VERIFICATION_FAILED")
        return False, "MISSING_VALUES"

    ident, err, _dir = resolve_write_target(str(point_id))
    if err is not None:
        set_status(command_id, "VERIFICATION_FAILED")
        _persist_verify_readback(command_id, None, None, False, err.code)
        _maybe_auto_rollback(command_id)
        return False, err.code

    read_id = ident or str(point_id)
    try:
        pt = adapter.read_point(read_id)
        val = getattr(pt, "value", None)
        if val is None:
            set_status(command_id, "VERIFICATION_FAILED")
            _persist_verify_readback(command_id, None, read_id, False, "NO_FEEDBACK")
            log_event("WARN", "control-worker", "COMMAND_VERIFY_FAILED", command_id=command_id, extra={"code": "NO_FEEDBACK"})
            _maybe_auto_rollback(command_id)
            return False, "NO_FEEDBACK"
        if abs(float(val) - float(target)) <= tolerance:
            set_status(command_id, "VERIFIED")
            _persist_verify_readback(command_id, float(val), read_id, True, "VERIFIED")
            log_event("INFO", "control-worker", "COMMAND_VERIFIED", command_id=command_id, extra={"readback": float(val)})
            _on_verified_closed_loop(command_id)
            return True, "VERIFIED"
        set_status(command_id, "VERIFICATION_FAILED")
        _persist_verify_readback(command_id, float(val), read_id, False, "OUT_OF_TOLERANCE")
        log_event(
            "WARN",
            "control-worker",
            "COMMAND_VERIFY_FAILED",
            command_id=command_id,
            extra={"code": "OUT_OF_TOLERANCE", "readback": float(val), "target": float(target)},
        )
        _maybe_auto_rollback(command_id)
        return False, "OUT_OF_TOLERANCE"
    except Exception as exc:
        set_status(command_id, "VERIFICATION_FAILED")
        _persist_verify_readback(command_id, None, read_id, False, type(exc).__name__)
        _maybe_auto_rollback(command_id)
        return False, str(type(exc).__name__)


def _maybe_auto_rollback(command_id: str) -> None:
    from backend.bms.stage_g import auto_rollback_enabled

    if not auto_rollback_enabled():
        return
    try:
        rollback_command(command_id)
    except Exception:
        pass


def _on_verified_closed_loop(command_id: str) -> None:
    """Stage H: Measure → Learn (RLS) + Safe RL reward. Best-effort only."""
    try:
        from backend.ai.rls.feedback import on_command_verified

        on_command_verified(command_id)
    except Exception:
        pass
    try:
        from backend.ai.safe_rl.outcome import measure_after_verify

        measure_after_verify(command_id)
    except Exception:
        pass


def rollback_command(command_id: str) -> Tuple[bool, str]:
    cmd = get_command(command_id)
    if not cmd:
        return False, "NOT_FOUND"
    ok, reason, classified = evaluate_dispatch(_context_for(cmd, "ROLLBACK"))
    if not ok:
        set_status(command_id, "BLOCKED")
        return False, classified.get("code") or reason
    old = cmd.get("old_value")
    point_id = cmd.get("point_id")
    set_status(command_id, "ROLLBACK")
    if old is None or not point_id:
        set_status(command_id, "ROLLED_BACK")
        return True, "NO_PREVIOUS_VALUE"
    outcome = write_point(
        str(point_id),
        float(old),
        context={
            **_context_for(cmd, "ROLLBACK"),
            "approval_status": "APPROVED",
            "opportunity_id": cmd.get("opportunity"),
            "old_value": old,
            "new_value": float(old),
        },
    )
    if not outcome.success:
        set_status(command_id, "BLOCKED")
        return False, outcome.code
    set_status(command_id, "ROLLED_BACK")
    log_event("INFO", "control-worker", "COMMAND_ROLLED_BACK", command_id=command_id)
    return True, "ROLLED_BACK"
