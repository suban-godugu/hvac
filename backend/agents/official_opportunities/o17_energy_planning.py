"""O17 energy management planning from provided energy snapshot (no invented meters)."""
from __future__ import annotations

from typing import Any, Dict, List

from backend.agents.official_opportunities._common import agent_envelope, num, text


def evaluate_energy_planning(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    power = num(snapshot, "power_kw", "actual_hvac_kw")
    baseline = num(snapshot, "baseline_kw", "baseline_hvac_kw")
    forecast = num(snapshot, "forecast_kw")
    peak = num(snapshot, "peak_demand_kw")
    cost = num(snapshot, "expected_cost_usd")
    tariff = num(snapshot, "tou_tariff")
    daily = num(snapshot, "daily_target_kwh")
    monthly = num(snapshot, "monthly_target_kwh")
    carbon = num(snapshot, "carbon_kg")
    recs: List[Any] = snapshot.get("recommendations") or []
    if power is None and baseline is None:
        return agent_envelope(
            "O17",
            False,
            recommendation="BLOCKED",
            reason="No energy meter or baseline telemetry.",
        )
    reduction = None
    if power is not None and baseline is not None:
        reduction = round(baseline - power, 1)
    reason = text(snapshot, "reason") or "Energy plan derived from current meter and baseline."
    return agent_envelope(
        "O17",
        True,
        current_state={
            "current_energy_kw": power,
            "baseline_energy_kw": baseline,
            "forecast_consumption_kw": forecast,
            "peak_demand_kw": peak,
            "expected_energy_cost": cost,
            "tou_tariff": tariff,
            "daily_target_kwh": daily,
            "monthly_target_kwh": monthly,
            "energy_reduction_kw": reduction,
            "carbon_impact_kg": carbon,
            "planning_status": "ACTIVE",
        },
        optimized_state={"target_kw": daily or (power - 8 if power else None)},
        recommendation="PLAN_REVIEW",
        reason=reason,
        confidence=0.78 if power is not None else 0.5,
        energy_impact=reduction,
        extra={"recommendations": recs, "current_value": power, "optimized_value": forecast or baseline},
    )
