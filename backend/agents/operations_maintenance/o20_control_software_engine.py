"""O20 Control software management — no automatic firmware/logic deploy."""
from __future__ import annotations
from typing import Any, Dict, Optional


def _n(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    if x != x or x in (float("inf"), float("-inf")):
        return None
    return x


def _i(v: Any) -> Optional[int]:
    n = _n(v)
    return int(n) if n is not None else None


def evaluate_o20(tel: Dict[str, Any]) -> Dict[str, Any]:
    ctrl = tel.get("controller") or tel
    if not ctrl or not (ctrl.get("controller_id") or ctrl.get("software_version") or ctrl.get("comm_status")):
        return {"available": False, "missing": "controller software/status records"}

    comm = (ctrl.get("comm_status") or "").upper()
    health = (ctrl.get("health_status") or "").upper() or None
    version = ctrl.get("software_version")
    firmware = ctrl.get("firmware_version")
    drift = _n(ctrl.get("config_drift_pct") or ctrl.get("drift_pct") or tel.get("config_drift_pct"))
    exceptions = _i(ctrl.get("exception_count") if ctrl.get("exception_count") is not None else tel.get("exception_count"))
    backup = ctrl.get("backup_status") or tel.get("backup_status")
    alarms = ctrl.get("alarm_state") or ctrl.get("alarm_status")
    point_count = _i(ctrl.get("point_count") or tel.get("point_count"))
    healthy_points = _i(ctrl.get("healthy_points") or tel.get("healthy_points"))
    degraded_points = _i(ctrl.get("degraded_points") or tel.get("degraded_points"))
    override_count = _i(ctrl.get("override_count") or tel.get("override_count"))
    drift_count = _i(ctrl.get("drift_count") or tel.get("drift_count"))
    critical_issues = _i(ctrl.get("critical_issues") or tel.get("critical_issues"))
    stale_points = _i(ctrl.get("stale_points") or tel.get("stale_points"))
    failed_points = _i(ctrl.get("failed_points") or tel.get("failed_points"))
    if override_count is None and (ctrl.get("override_state") or "").upper() not in ("", "NONE", "OFF", "AUTO"):
        override_count = 1
    control_health_pct = None
    if point_count not in (None, 0) and healthy_points is not None:
        control_health_pct = round(100.0 * healthy_points / point_count, 1)

    if comm and comm not in ("ONLINE", "CONNECTED", "OK", "HEALTHY"):
        rec, decision, status, risk, safety = "RESTORE_COMMUNICATION", "BLOCK", "BLOCKED", "HIGH", "FAIL"
        rationale = f"Controller communication is {comm}; software changes are blocked."
        controller_health = "UNHEALTHY"
    elif critical_issues is not None and critical_issues > 0:
        rec, decision, status, risk, safety = "OPEN_CHANGE_REQUEST", "REVIEW_REQUIRED", "REVIEW", "HIGH", "FAIL"
        rationale = f"{critical_issues} critical control-software issues require governed change control."
        controller_health = health or "CRITICAL"
    elif stale_points is not None and stale_points > 0:
        rec, decision, status, risk, safety = "INVESTIGATE_STALE_POINTS", "REVIEW_REQUIRED", "REVIEW", "MEDIUM", "WARNING"
        rationale = f"{stale_points} stale control points require investigation. Automatic logic deploy is prohibited."
        controller_health = health or "STALE_POINTS"
    elif override_count is not None and override_count >= 1:
        rec, decision, status, risk, safety = "REVIEW_MANUAL_OVERRIDES", "REVIEW_REQUIRED", "REVIEW", "MEDIUM", "WARNING"
        rationale = f"{override_count} manual control overrides are active. Automatic software deploy is prohibited."
        controller_health = health or "OVERRIDES"
    elif drift is not None and drift >= 5:
        rec, decision, status, risk, safety = "OPEN_CHANGE_REQUEST", "REVIEW_REQUIRED", "REVIEW", "MEDIUM", "WARNING"
        rationale = f"Configuration drift {drift:.1f}% requires approved change control, backup, and rollback plan."
        controller_health = health or "DRIFT"
    elif exceptions is not None and exceptions >= 3:
        rec, decision, status, risk, safety = "INVESTIGATE_EXCEPTIONS", "REVIEW_REQUIRED", "REVIEW", "MEDIUM", "WARNING"
        rationale = f"{exceptions} control-system exceptions require review. Automatic logic deploy is prohibited."
        controller_health = health or "EXCEPTIONS"
    elif failed_points is not None and failed_points > 0:
        rec, decision, status, risk, safety = "RESTORE_FAILED_POINTS", "REVIEW_REQUIRED", "REVIEW", "MEDIUM", "WARNING"
        rationale = f"{failed_points} failed control points require restoration before software changes."
        controller_health = health or "FAILED_POINTS"
    else:
        rec, decision, status, risk, safety = "MAINTAIN_BASELINE", "MONITOR", "OPTIMAL", "LOW", "PASS"
        rationale = "Controller software/configuration health is within the governance envelope. No automatic deploy."
        controller_health = health or "HEALTHY"

    present = sum(1 for v in (version, comm, drift, exceptions, backup, point_count) if v is not None and v != "")
    confidence = round(min(0.94, 0.48 + 0.1 * present), 2)
    return {
        "available": True,
        "status": status,
        "controller_health": controller_health,
        "software_version": version,
        "firmware_version": firmware,
        "config_drift_pct": drift,
        "exception_count": exceptions,
        "change_risk": risk,
        "backup_status": backup,
        "alarm_status": alarms,
        "controller_id": ctrl.get("controller_id"),
        "point_count": point_count,
        "healthy_points": healthy_points,
        "degraded_points": degraded_points,
        "override_count": override_count,
        "drift_count": drift_count,
        "critical_issues": critical_issues,
        "stale_points": stale_points,
        "failed_points": failed_points,
        "control_health_pct": control_health_pct,
        "confidence": confidence,
        "guardrail_pass": rec != "RESTORE_COMMUNICATION",
        "safety_status": safety,
        "recommendation": rec,
        "rationale": rationale,
        "supervisory_decision": decision,
        "dispatch_eligible": False,
        "requires_change_ticket": True,
        "evidence": ["Controller record", "Version", "Drift" if drift is not None else None, "Backup" if backup else None],
    }
