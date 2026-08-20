"""O17 Energy Management Planning — no invented meters."""
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


def evaluate_o17(tel: Dict[str, Any]) -> Dict[str, Any]:
    current = _n(tel.get("hvac_power_kw") if tel.get("hvac_power_kw") is not None else tel.get("electrical_power_kw"))
    baseline = _n(tel.get("baseline_kw"))
    occupancy = _n(tel.get("occupancy"))
    oat = _n(tel.get("outdoor_temp_c"))
    daily = _n(tel.get("daily_energy_kwh"))
    peak = _n(tel.get("peak_demand_kw"))
    target_in = _n(tel.get("target_kw") or tel.get("energy_target_kw"))
    if current is None:
        return {"available": False, "missing": "HVAC or electrical power (kW)"}

    present = sum(1 for v in (current, baseline, occupancy, oat, daily) if v is not None)
    confidence = round(min(0.97, 0.45 + 0.1 * present), 2)
    delta = round(current - baseline, 2) if baseline is not None else None
    target = target_in
    if target is None and occupancy is not None and occupancy <= 8 and baseline is not None:
        target = round(min(current, baseline) * 0.96, 2)
    elif target is None and baseline is not None:
        target = round(baseline * 0.97, 2)
    savings_kw = round(current - target, 2) if target is not None else None
    if savings_kw is not None and savings_kw < 0:
        savings_kw = 0.0
    daily_kwh = None
    monthly_kwh = None
    if savings_kw is not None and current not in (None, 0) and daily is not None:
        daily_kwh = round(daily * (savings_kw / current), 1)
        monthly_kwh = round(daily_kwh * 30.0, 1)
    occupancy_ok = occupancy is None or occupancy >= 0
    deviation_pct = round(100.0 * (current - baseline) / baseline, 1) if baseline not in (None, 0) else None
    if not occupancy_ok:
        decision, rec, status, safety, priority = "BLOCK", "HOLD", "BLOCKED", "FAIL", "HIGH"
        rationale = "Occupancy constraint invalid; energy plan is blocked."
    elif baseline is None:
        decision, rec, status, safety, priority = "WAIT_FOR_TELEMETRY", "HOLD", "NO LIVE DATA", "WARNING", None
        rationale = "Power is present but no energy baseline is available; planning is withheld."
        confidence = min(confidence, 0.4)
    elif deviation_pct is not None and deviation_pct >= 5:
        decision, rec, status, safety = "OPTIMIZE", "TRIM_UNOCCUPIED_LOAD", "OPTIMIZABLE", "PASS"
        priority = "HIGH" if deviation_pct >= 8 else "MEDIUM"
        rationale = (
            f"Energy baseline analysis indicates HVAC load is {deviation_pct:.1f}% above expected "
            f"({current:.1f} kW vs baseline {baseline:.1f} kW)."
        )
    elif savings_kw is not None and savings_kw > 0.5:
        decision, rec, status, safety, priority = "OPTIMIZE", "TRIM_UNOCCUPIED_LOAD", "OPTIMIZABLE", "PASS", "MEDIUM"
        rationale = (
            f"Current HVAC energy {current:.1f} kW versus baseline {baseline:.1f} kW. "
            f"A further reduction opportunity of {savings_kw:.1f} kW is identified without violating occupancy constraints."
        )
    else:
        decision, rec, status, safety, priority = "MONITOR", "MAINTAIN_PLAN", "OPTIMAL", "PASS", "LOW"
        rationale = (
            f"Current HVAC energy {current:.1f} kW is at or below the established baseline"
            + (f" ({baseline:.1f} kW)." if baseline is not None else ".")
        )
    return {
        "available": True,
        "status": status,
        "current_kw": current,
        "baseline_kw": baseline,
        "target_kw": target,
        "delta_kw": delta,
        "savings_kw": savings_kw,
        "daily_kwh": daily_kwh,
        "monthly_kwh": monthly_kwh,
        "peak_demand_kw": peak,
        "occupancy": occupancy,
        "outdoor_temp_c": oat,
        "daily_energy_kwh": daily,
        "priority": priority,
        "deviation_pct": deviation_pct,
        "confidence": confidence,
        "guardrail_pass": safety == "PASS",
        "safety_status": safety,
        "recommendation": rec,
        "rationale": rationale,
        "supervisory_decision": decision,
        "dispatch_eligible": decision == "OPTIMIZE" and safety == "PASS" and confidence >= 0.65,
        "evidence": ["Energy meter snapshot", "Baseline", "Occupancy" if occupancy is not None else None, "Weather" if oat is not None else None],
    }
