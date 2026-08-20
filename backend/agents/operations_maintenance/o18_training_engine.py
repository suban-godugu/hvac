"""O18 Energy Management Training — advisory only, no equipment dispatch."""
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


def _i(v: Any) -> Optional[int]:
    n = _n(v)
    return int(n) if n is not None else None


def evaluate_o18(tel: Dict[str, Any]) -> Dict[str, Any]:
    programs: List[Dict[str, Any]] = tel.get("programs") or []
    completions: List[Dict[str, Any]] = tel.get("completions") or []
    overrides = _n(tel.get("manual_override_count"))
    if not programs and not completions and overrides is None:
        return {"available": False, "missing": "training program or operator-action records"}

    required = [p for p in programs if p.get("required")]
    latest = completions[0] if completions else None
    coverage = _n(latest.get("completion_pct")) if latest else None
    if coverage is None and required:
        done = sum(1 for p in required if (p.get("status") or "").upper() == "COMPLETED")
        coverage = round(100.0 * done / len(required), 1) if required else None
    gaps = []
    for p in required:
        if (p.get("status") or "").upper() != "COMPLETED":
            gaps.append(p.get("program_name") or p.get("topic") or "Required program")
    if overrides is not None and overrides >= 3:
        gaps.append("Repeated manual override of approved SAT/reset strategy")
    open_actions = len(gaps)
    energy_impact = _n(tel.get("energy_impact_kwh_day") or tel.get("energy_impact"))
    affected = _i(tel.get("affected_users") or tel.get("affected_operators"))
    if affected is None:
        roles = {c.get("role_label") for c in completions if c.get("role_label")}
        affected = len(roles) if roles else None
    if coverage is not None and coverage >= 85 and open_actions == 0:
        readiness, rec, decision, status = "GOOD", "MAINTAIN_AWARENESS", "MONITOR", "OPTIMAL"
        rationale = "Required energy-management training is current; no knowledge-gap actions are open."
        safety, priority = "PASS", "LOW"
    elif coverage is not None or gaps:
        if coverage is None:
            readiness = "UNKNOWN"
        elif coverage < 70:
            readiness = "NEEDS_TRAINING"
        else:
            readiness = "FAIR"
        rec, decision, status, safety = "ASSIGN_TRAINING", "REVIEW_REQUIRED", "REVIEW", "PASS"
        priority = "HIGH" if (overrides is not None and overrides >= 3) or (coverage is not None and coverage < 70) else "MEDIUM"
        rationale = (
            "Operator capability gaps affect HVAC energy performance. "
            + (gaps[0] if gaps else "Complete outstanding required programs.")
        )
    else:
        readiness, rec, decision, status, safety, priority = "UNKNOWN", "HOLD", "WAIT_FOR_TELEMETRY", "NO LIVE DATA", "WARNING", None
        rationale = "Training coverage cannot be scored without completion records."
    present = sum(1 for v in (coverage, len(programs) or None, overrides) if v is not None)
    confidence = round(min(0.95, 0.5 + 0.12 * present), 2)
    return {
        "available": True,
        "status": status,
        "training_coverage_pct": coverage,
        "operator_readiness": readiness,
        "knowledge_gaps": gaps,
        "knowledge_gap_count": len(gaps),
        "training_items": open_actions,
        "affected_users": affected,
        "open_actions": open_actions,
        "required_programs": len(required),
        "manual_override_count": overrides,
        "energy_impact_kwh_day": energy_impact,
        "priority": priority,
        "confidence": confidence,
        "guardrail_pass": True,
        "safety_status": safety,
        "recommendation": rec,
        "rationale": rationale,
        "supervisory_decision": decision,
        "dispatch_eligible": False,
        "evidence": ["Training programs", "Completions", "Manual overrides" if overrides is not None else None],
    }
