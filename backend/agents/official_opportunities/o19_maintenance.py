"""O19 equipment maintenance / anomaly detection from findings and performance rows."""
from __future__ import annotations

from typing import Any, Dict, List

from backend.agents.official_opportunities._common import agent_envelope, num


def evaluate_maintenance(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    orders: List[Dict[str, Any]] = snapshot.get("findings") or snapshot.get("work_orders") or []
    perf = snapshot.get("performance") or {}
    if not orders and not perf:
        return agent_envelope(
            "O19",
            False,
            recommendation=None,
            reason="No maintenance findings or equipment-performance records.",
        )
    open_orders = [o for o in orders if (o.get("status") or "").upper() not in ("COMPLETED", "CLOSED", "NORMAL")]
    primary = open_orders[0] if open_orders else (orders[0] if orders else {})
    eff = num(primary, "efficiency") if primary else num(perf, "efficiency")
    deg = num(primary, "degradation") if primary else num(perf, "degradation")
    runtime = num(primary, "runtime_hours") if primary else num(perf, "runtime_hours")
    rec = primary.get("recommendation") or primary.get("finding") or "Inspect coil and filters on degraded equipment."
    priority = primary.get("priority") or "MEDIUM"
    return agent_envelope(
        "O19",
        True,
        current_state={
            "equipment_id": primary.get("equipment_id") or perf.get("equipment_id"),
            "maintenance_status": primary.get("status") or "UNKNOWN",
            "efficiency": eff,
            "degradation": deg,
            "runtime_hours": runtime,
            "due_date": primary.get("due_date"),
            "priority": priority,
            "open_findings": len(open_orders),
        },
        optimized_state={"recommended_maintenance": rec, "potential_energy_impact": num(primary, "energy_impact")},
        recommendation="MAINTENANCE_REQUIRED" if open_orders else "MONITOR",
        reason=rec,
        confidence=0.74,
        energy_impact=num(primary, "energy_impact"),
        extra={"findings": orders, "current_value": eff, "optimized_value": 0.85 if eff else None},
    )
