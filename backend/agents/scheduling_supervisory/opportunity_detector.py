"""
OpportunityDetector: Detects optimization trigger conditions for O1, O2, O3, O4.
Does not invent missing telemetry or hardcoded kW savings.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class OpportunityDetectionResult:
    opportunity_code: str
    title: str
    is_triggered: bool
    trigger_reason: str
    estimated_power_kw_impact: Optional[float]
    confidence: float


def _mean(values: List[float]) -> Optional[float]:
    return sum(values) / len(values) if values else None


class OpportunityDetector:
    def detect_opportunities(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        detections: List[OpportunityDetectionResult] = []
        all_zones = [z for ahu in state.get("ahus", []) for z in ahu.get("vav_zones", [])]
        temps = [z.get("temp_actual", z.get("temp")) for z in all_zones]
        temps = [float(t) for t in temps if t is not None]
        avg_temp = _mean(temps)
        plant = state.get("plant") or {}
        plant_kw = plant.get("total_power_kw") or plant.get("power_kw")
        plant_kw = float(plant_kw) if plant_kw is not None else None

        if avg_temp is None:
            detections.append(OpportunityDetectionResult(
                opportunity_code="O1",
                title="Optimum Start/Stop Scheduling",
                is_triggered=False,
                trigger_reason="ZONE_TEMP missing; cannot evaluate start/stop.",
                estimated_power_kw_impact=None,
                confidence=0.0,
            ))
        else:
            o1_triggered = avg_temp < 24.5
            detections.append(OpportunityDetectionResult(
                opportunity_code="O1",
                title="Optimum Start/Stop Scheduling",
                is_triggered=o1_triggered,
                trigger_reason=f"Mean zone temperature {avg_temp:.1f}°C.",
                estimated_power_kw_impact=round(plant_kw * 0.04, 2) if plant_kw is not None else None,
                confidence=0.6 if plant_kw is not None else 0.4,
            ))

        unoccupied_zones = [z for z in all_zones if z.get("occupied") is False]
        o2_triggered = bool(unoccupied_zones)
        detections.append(OpportunityDetectionResult(
            opportunity_code="O2",
            title="Space Temperature & Control Band Optimization",
            is_triggered=o2_triggered,
            trigger_reason=(
                f"{len(unoccupied_zones)} unoccupied zones eligible for setback."
                if o2_triggered
                else ("No occupancy flags in state." if all_zones else "No zone telemetry.")
            ),
            estimated_power_kw_impact=round(plant_kw * 0.03, 2) if plant_kw is not None and o2_triggered else None,
            confidence=0.55 if all_zones else 0.0,
        ))

        ahus = state.get("ahus", [])
        total_clg_calls = sum(
            1
            for a in ahus
            for z in a.get("vav_zones", [])
            if z.get("damper_pos") is not None
            and z.get("temp_actual") is not None
            and z.get("cooling_sp") is not None
            and z.get("damper_pos") > 85
            and (z.get("temp_actual") - z.get("cooling_sp")) > 0.3
        )
        o3_triggered = bool(ahus) and total_clg_calls == 0
        detections.append(OpportunityDetectionResult(
            opportunity_code="O3",
            title="Master AHU Supply Air Temperature Signal",
            is_triggered=o3_triggered,
            trigger_reason=(
                f"{total_clg_calls} critical cooling calls."
                if ahus
                else "No AHU telemetry."
            ),
            estimated_power_kw_impact=round(plant_kw * 0.025, 2) if plant_kw is not None and o3_triggered else None,
            confidence=0.5 if ahus else 0.0,
        ))

        total_tons = plant.get("total_tons")
        if total_tons is None:
            detections.append(OpportunityDetectionResult(
                opportunity_code="O4",
                title="Chiller and Compressor Staging",
                is_triggered=False,
                trigger_reason="Plant cooling load missing.",
                estimated_power_kw_impact=None,
                confidence=0.0,
            ))
        else:
            o4_triggered = float(total_tons) < 85.0
            detections.append(OpportunityDetectionResult(
                opportunity_code="O4",
                title="Chiller and Compressor Staging",
                is_triggered=o4_triggered,
                trigger_reason=f"Plant cooling load is {float(total_tons):.1f} tons.",
                estimated_power_kw_impact=round(plant_kw * 0.05, 2) if plant_kw is not None else None,
                confidence=0.55 if plant_kw is not None else 0.35,
            ))

        return [d.__dict__ for d in detections]
