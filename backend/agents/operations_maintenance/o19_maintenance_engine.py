"""O19 Energy Efficiency Maintenance — evidence-based findings only."""
from __future__ import annotations
from typing import Any, Dict, List, Optional


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


def evaluate_o19(tel: Dict[str, Any]) -> Dict[str, Any]:
    orders: List[Dict[str, Any]] = tel.get("findings") or tel.get("work_orders") or []
    findings: List[Dict[str, Any]] = tel.get("findings") or []
    health = _n(tel.get("equipment_health_pct"))
    dp_rise = _n(tel.get("filter_dp_rise_pct"))
    fan_kw = _n(tel.get("fan_power_kw"))
    runtime = _n(tel.get("runtime_hours"))
    sensor_drift = _n(tel.get("sensor_drift_pct") or tel.get("sensor_drift"))
    cycles = _n(tel.get("cycle_count") or tel.get("excessive_cycles"))
    if not orders and not findings and health is None and dp_rise is None and fan_kw is None and sensor_drift is None and cycles is None:
        return {"available": False, "missing": "maintenance, equipment health, or runtime evidence"}

    issues: List[Dict[str, Any]] = []
    energy_kw = None
    eq_id = tel.get("equipment_id")
    if dp_rise is not None and dp_rise >= 20:
        impact = round(fan_kw * min(0.35, dp_rise / 100.0), 2) if fan_kw is not None else None
        issues.append(
            {
                "finding": f"Filter differential pressure is {dp_rise:.0f}% above maintenance baseline.",
                "energy_impact_kw": impact,
                "priority": "P1" if dp_rise >= 50 else "P2",
                "equipment_id": eq_id,
                "issue_type": "FILTER",
            }
        )
        energy_kw = impact
    if sensor_drift is not None and abs(sensor_drift) >= 5:
        issues.append(
            {
                "finding": f"Sensor drift of {sensor_drift:.1f}% detected versus calibration baseline.",
                "energy_impact_kw": None,
                "priority": "P2" if abs(sensor_drift) < 12 else "P1",
                "equipment_id": eq_id,
                "issue_type": "SENSOR_DRIFT",
            }
        )
    if cycles is not None and cycles >= 8:
        issues.append(
            {
                "finding": f"Abnormal equipment cycling ({cycles:.0f} cycles in the evaluation window).",
                "energy_impact_kw": None,
                "priority": "P2",
                "equipment_id": eq_id,
                "issue_type": "CYCLING",
            }
        )
    for o in orders:
        if (o.get("status") or "").upper() not in ("COMPLETED", "CLOSED"):
            issues.append(
                {
                    "finding": o.get("recommendation") or o.get("finding") or o.get("maintenance_type") or "Maintenance finding",
                    "energy_impact_kw": _n(o.get("energy_impact")),
                    "priority": o.get("priority") or "P2",
                    "equipment_id": o.get("equipment_id"),
                    "issue_type": o.get("maintenance_type") or o.get("issue_type") or "FINDING",
                }
            )
            if energy_kw is None:
                energy_kw = _n(o.get("energy_impact"))
    for f in findings:
        issues.append(
            {
                "finding": f.get("finding") or f.get("issue"),
                "energy_impact_kw": _n(f.get("energy_impact_kw") or f.get("energy_impact")),
                "priority": f.get("priority") or "P2",
                "equipment_id": f.get("equipment_id") or eq_id,
                "issue_type": f.get("issue_type") or "FINDING",
            }
        )
    count = len(issues)
    assets = sorted({i.get("equipment_id") for i in issues if i.get("equipment_id")})
    urgent = any(i.get("priority") == "P1" for i in issues) or (dp_rise is not None and dp_rise >= 50)
    if count == 0 and (health is None or health >= 90):
        risk, rec, decision, status, priority, safety = "LOW", "MONITOR", "MONITOR", "NORMAL", "LOW", "PASS"
        rationale = "No evidence-based efficiency defects are open."
    elif count == 0:
        risk, rec, decision, status, priority, safety = "MEDIUM", "MONITOR", "MONITOR", "MONITOR", "MEDIUM", "PASS"
        rationale = "Equipment health is below the optimal band; continue monitoring."
    elif urgent:
        risk, rec, decision, status = "HIGH", "MAINTENANCE_RECOMMENDED", "MAINTENANCE_REQUIRED", "URGENT_MAINTENANCE"
        priority, safety = "CRITICAL", "WARNING"
        rationale = issues[0]["finding"]
    else:
        risk, rec, decision, status = "HIGH" if any(i.get("priority") == "P1" for i in issues) else "MEDIUM", "MAINTENANCE_RECOMMENDED", "MAINTENANCE_REQUIRED", "MAINTENANCE_REQUIRED"
        priority = "HIGH" if risk == "HIGH" else "MEDIUM"
        rationale = issues[0]["finding"]
        safety = "WARNING" if risk != "LOW" else "PASS"
    present = sum(1 for v in (health, dp_rise, fan_kw, runtime, count or None, sensor_drift) if v is not None)
    confidence = round(min(0.96, 0.5 + 0.09 * present), 2)
    return {
        "available": True,
        "status": status,
        "equipment_health_pct": round(health, 1) if health is not None else None,
        "maintenance_risk": risk,
        "issues_detected": count,
        "maintenance_alerts": count,
        "assets_at_risk": len(assets) if assets else (0 if count == 0 else None),
        "detected_issues": issues,
        "estimated_energy_impact_kw": energy_kw,
        "priority": priority,
        "runtime_hours": runtime,
        "filter_dp_rise_pct": dp_rise,
        "fan_power_kw": fan_kw,
        "sensor_drift_pct": sensor_drift,
        "confidence": confidence,
        "guardrail_pass": True,
        "safety_status": safety,
        "recommendation": rec,
        "rationale": rationale,
        "supervisory_decision": decision,
        "dispatch_eligible": False,
        "action_type": "MAINTENANCE_ACTION",
        "evidence": ["Maintenance findings", "Filter ΔP" if dp_rise is not None else None, "Fan power" if fan_kw is not None else None, "Sensor drift" if sensor_drift is not None else None],
    }
