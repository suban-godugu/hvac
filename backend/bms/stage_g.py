"""Stage G — controlled one-point writes (prerequisites + allowlist)."""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

DEFAULT_WRITABLE = "ZONE-01.cooling_setpoint"


def _truthy(name: str, default: str = "1") -> bool:
    return os.getenv(name, default).strip() in ("1", "true", "TRUE")


def stage_g_enforce() -> bool:
    return _truthy("HVAC_STAGE_G_ENFORCE", "1")


def auto_rollback_enabled() -> bool:
    return _truthy("HVAC_STAGE_G_AUTO_ROLLBACK", "1")


def writable_allowlist() -> List[str]:
    raw = os.getenv("HVAC_STAGE_G_WRITABLE_POINTS", DEFAULT_WRITABLE).strip()
    if not raw:
        return [DEFAULT_WRITABLE]
    return [p.strip() for p in raw.split(",") if p.strip()]


def point_allowed(point_id: str) -> bool:
    pid = (point_id or "").strip()
    return pid in writable_allowlist()


def _stale_limit_s() -> float:
    try:
        return float(os.getenv("HVAC_TELEMETRY_STALE_SECONDS", "90") or 90)
    except (TypeError, ValueError):
        return 90.0


def _check(name: str, ok: bool, detail: str) -> Dict[str, Any]:
    return {"name": name, "ok": bool(ok), "detail": detail}


def prerequisites_ok(point_id: Optional[str] = None) -> Dict[str, Any]:
    """G1 gate before supervised apply/write-enable for a Stage G point."""
    from backend.bms.command_writer import (
        connection_writes_armed,
        resolve_write_target,
        write_enabled_flag,
    )
    from backend.services.hvac_safety_contract import is_safe_mode
    from backend.services.platform_ops_service import PLANT_LIVE, get_plant_mode

    pid = (point_id or "").strip() or DEFAULT_WRITABLE
    checks: List[Dict[str, Any]] = []

    plant = get_plant_mode()
    live = plant == PLANT_LIVE
    checks.append(_check("PLANT_LIVE_BMS", live, f"plantMode={plant}"))

    safe = is_safe_mode()
    checks.append(_check("NOT_SAFE_MODE", not safe, "SAFE_MODE" if safe else "SAFE_MODE off"))

    # Target point LIVE + GOOD + FRESH
    point_ok = False
    point_detail = "no telemetry"
    try:
        from backend.services.canonical_telemetry_service import latest_points

        rows = latest_points(limit=200)
        row = next((r for r in rows if r.get("point_id") == pid), None)
        if row is None:
            point_detail = f"{pid} MISSING"
        else:
            src = str(row.get("source") or "").upper()
            qual = str(row.get("quality") or "").upper()
            age = row.get("age_seconds")
            try:
                age_f = float(age) if age is not None else None
            except (TypeError, ValueError):
                age_f = None
            fresh = age_f is not None and age_f <= _stale_limit_s()
            point_ok = src == "LIVE_BMS" and qual == "GOOD" and fresh
            point_detail = f"source={src} quality={qual} age_s={age_f}"
    except Exception as exc:
        point_detail = f"{type(exc).__name__}: {exc}"
    checks.append(_check("POINT_LIVE_GOOD_FRESH", point_ok, point_detail))

    # Mapping writable
    mapping_ok = False
    mapping_detail = "unresolved"
    try:
        ident, err, direction = resolve_write_target(pid)
        if err is not None:
            mapping_detail = f"{err.code}: {err.message}"
        else:
            mapping_ok = True
            mapping_detail = f"ident={ident} direction={direction or 'WRITE'}"
    except Exception as exc:
        mapping_detail = f"{type(exc).__name__}: {exc}"
    checks.append(_check("MAPPING_WRITABLE", mapping_ok, mapping_detail))

    env_ok = write_enabled_flag()
    checks.append(
        _check("HVAC_BMS_WRITE_ENABLED", env_ok, "HVAC_BMS_WRITE_ENABLED=" + ("1" if env_ok else "0"))
    )

    armed = connection_writes_armed()
    checks.append(_check("CONNECTION_WRITE_ARMED", armed, "write_enabled on connection" if armed else "not armed"))

    allow = point_allowed(pid)
    checks.append(
        _check(
            "STAGE_G_ALLOWLIST",
            allow,
            f"{pid} in [{', '.join(writable_allowlist())}]" if allow else f"{pid} not allowlisted",
        )
    )

    # Apply requires armed connection; write-enable is what arms it (ok_to_enable skips armed).
    apply_names = {c["name"] for c in checks}
    ok = all(c["ok"] for c in checks)
    ok_to_enable = all(c["ok"] for c in checks if c["name"] != "CONNECTION_WRITE_ARMED")
    return {
        "ok": ok,
        "ok_to_enable": ok_to_enable,
        "point_id": pid,
        "checks": checks,
        "allowlist": writable_allowlist(),
        "enforce": stage_g_enforce(),
        "auto_rollback": auto_rollback_enabled(),
        "required_for_apply": sorted(apply_names),
    }


def verify_stats() -> Dict[str, Any]:
    """Recent VERIFIED vs VERIFICATION_FAILED rate for G3 expand gate (docs/ops)."""
    from database.models_platform import ControlCommandDB
    from database.session import SessionLocal

    try:
        window = max(1, int(os.getenv("HVAC_STAGE_G_VERIFY_WINDOW", "10") or 10))
    except (TypeError, ValueError):
        window = 10
    try:
        min_rate = float(os.getenv("HVAC_STAGE_G_VERIFY_SUCCESS_MIN", "0.9") or 0.9)
    except (TypeError, ValueError):
        min_rate = 0.9

    db = SessionLocal()
    try:
        rows = (
            db.query(ControlCommandDB)
            .filter(ControlCommandDB.status.in_(("VERIFIED", "VERIFICATION_FAILED")))
            .order_by(ControlCommandDB.created_at.desc())
            .limit(window)
            .all()
        )
        total = len(rows)
        verified = sum(1 for r in rows if r.status == "VERIFIED")
        rate = (verified / total) if total else 0.0
        ready = total >= window and rate >= min_rate
        return {
            "window": window,
            "min_success_rate": min_rate,
            "sample_size": total,
            "verified": verified,
            "failed": total - verified,
            "success_rate": round(rate, 4),
            "expand_ready": ready,
            "next_candidate": "AHU-01.sat_setpoint",
            "hint": (
                "Append AHU-01.sat_setpoint to HVAC_STAGE_G_WRITABLE_POINTS after expand_ready"
                if ready
                else "Keep one-point allowlist until verify window × min success rate is met"
            ),
        }
    except Exception as exc:
        return {
            "window": window,
            "min_success_rate": min_rate,
            "sample_size": 0,
            "verified": 0,
            "failed": 0,
            "success_rate": 0.0,
            "expand_ready": False,
            "error": str(exc),
        }
    finally:
        db.close()


def recent_allowlisted_commands(limit: int = 5) -> List[Dict[str, Any]]:
    """Last PROPOSED/APPROVED/APPLIED commands on the Stage G allowlist (for UI)."""
    from backend.agents.runtime.command import list_commands

    allowed = set(writable_allowlist())
    statuses = {"PROPOSED", "APPROVED", "APPLYING", "APPLIED", "VERIFYING", "VERIFIED", "VERIFICATION_FAILED"}
    out: List[Dict[str, Any]] = []
    for cmd in list_commands(limit=max(50, limit * 10)):
        if cmd.get("point_id") in allowed and (cmd.get("status") or "") in statuses:
            out.append(cmd)
            if len(out) >= limit:
                break
    return out


def stage_g_status(point_id: Optional[str] = None) -> Dict[str, Any]:
    pid = (point_id or "").strip() or DEFAULT_WRITABLE
    prereq = prerequisites_ok(pid)
    return {
        **prereq,
        "verify_stats": verify_stats(),
        "commands": recent_allowlisted_commands(5),
    }
