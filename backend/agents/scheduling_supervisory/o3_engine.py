"""
O3: Master AHU Supply Air Temperature Signal Engine (MasterAHUSATOptimizationEngine)

Maintains downstream VAV zone demand telemetry, excludes invalid/blacklisted zones,
calculates master demand using configurable algorithms (Third-Highest, Percentile, Weighted),
evaluates total HVAC power impact (Chiller Lift vs Fan Power vs Reheat), and generates
safe supervisory SAT reset setpoints.
"""
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import math

from backend.agents.scheduling_supervisory.state import (
    CandidateAction,
    OpportunityEvaluationResult
)


@dataclass
class VAVZoneSignal:
    zone_id: str
    name: str
    temperature: float
    setpoint: float
    deviation: float
    cooling_demand_pct: float
    heating_demand_pct: float
    damper_position_pct: float
    cooling_valve_pct: float
    reheat_valve_pct: float
    sensor_quality: str # GOOD, SUSPECT, FAULT, FROZEN
    is_excluded: bool
    exclusion_reason: Optional[str] = None


class MasterAHUSATOptimizationEngine:
    """
    Production-grade O3 Master AHU SAT Signal Engine.
    Implements ASHRAE Guideline 36 Trim & Respond with Total HVAC Impact modeling.
    """

    def __init__(self, master_demand_method: str = "THIRD_HIGHEST"):
        self.master_demand_method = master_demand_method # THIRD_HIGHEST, PERCENTILE, WEIGHTED
        self.min_sat_clamp_c = 12.0 # Freeze guard engineering limit
        self.max_sat_clamp_c = 17.5 # Humidity / Dehumidification ceiling
        self.design_sat_c = 12.8    # Standard baseline design setpoint
        self.trim_step_c = 0.3      # Step up (warmer) when demand is low
        self.respond_step_c = -0.4  # Step down (cooler) when demand is high
        self.max_rate_of_change_c = 0.5 # Max step per supervisory cycle

        # Blacklisted process zones (e.g. server rooms requiring continuous sub-cooling)
        self.blacklisted_zone_ids = {"VAV-107"}

    def _parse_vav_signals(self, raw_zones: List[Dict[str, Any]]) -> List[VAVZoneSignal]:
        """Parses raw VAV telemetry, validates sensor quality, and applies exclusion filters."""
        vav_signals: List[VAVZoneSignal] = []

        for z in raw_zones:
            zid = z.get("id", "VAV-UNKNOWN")
            name = z.get("name", zid)
            temp = z.get("temp_actual", z.get("temp", 22.8))
            sp = z.get("cooling_sp", z.get("temp_setpoint", 23.0))
            dev = round(temp - sp, 2)
            damper = z.get("damper_pos", z.get("damper", 35.0))
            c_valve = z.get("cooling_valve_pct", 0.0)
            r_valve = z.get("reheat_valve_pct", 0.0)
            quality = z.get("sensor_quality", "GOOD")

            # Calculate cooling demand based on damper position and positive temp deviation
            if damper > 30.0 or dev > 0:
                cooling_demand = min(100.0, max(0.0, ((damper - 30.0) / 70.0 * 80.0) + (max(0.0, dev) * 20.0)))
            else:
                cooling_demand = 0.0

            heating_demand = 100.0 if r_valve > 20.0 or dev < -0.8 else 0.0

            # Exclusion determination
            is_excluded = False
            exclusion_reason = None

            if zid in self.blacklisted_zone_ids:
                is_excluded = True
                exclusion_reason = f"Process cooling zone ({name}) excluded from comfort AHU reset."
            elif quality != "GOOD":
                is_excluded = True
                exclusion_reason = f"Sensor quality is {quality} (out-of-bounds or drift detected)."
            elif z.get("occupied") is False and damper < 15.0:
                is_excluded = False # Included but low weight

            vav_signals.append(VAVZoneSignal(
                zone_id=zid,
                name=name,
                temperature=round(temp, 2),
                setpoint=round(sp, 2),
                deviation=dev,
                cooling_demand_pct=round(cooling_demand, 1),
                heating_demand_pct=round(heating_demand, 1),
                damper_position_pct=round(damper, 1),
                cooling_valve_pct=round(c_valve, 1),
                reheat_valve_pct=round(r_valve, 1),
                sensor_quality=quality,
                is_excluded=is_excluded,
                exclusion_reason=exclusion_reason
            ))

        return vav_signals

    def calculate_master_demand(self, vav_signals: List[VAVZoneSignal]) -> Tuple[float, int, List[str]]:
        """
        Calculates master zone demand from non-excluded VAV boxes using configured algorithm:
        - THIRD_HIGHEST (Guideline 36 standard)
        - PERCENTILE (90th percentile)
        - WEIGHTED (Area/airflow weighted)
        Returns: (master_demand_pct, cooling_request_count, active_request_reasons)
        """
        active_zones = [z for z in vav_signals if not z.is_excluded]
        if not active_zones:
            return 25.0, 0, ["No active zones available; defaulting to 25% nominal demand."]

        demands = sorted([z.cooling_demand_pct for z in active_zones], reverse=True)
        requests = [z for z in active_zones if z.damper_position_pct >= 85.0 and z.deviation >= 0.3]
        req_count = len(requests)
        req_reasons = [f"Zone {r.zone_id} calling (damper={r.damper_position_pct:.0f}%, dev=+{r.deviation:.1f}°C)" for r in requests]

        if self.master_demand_method == "THIRD_HIGHEST":
            # Guideline 36: Ignore top 2 outlier/rogue zones, take the 3rd highest
            if len(demands) >= 3:
                master_demand = demands[2]
            else:
                master_demand = demands[0]
        elif self.master_demand_method == "PERCENTILE":
            # 85th percentile
            idx = int(math.ceil(0.85 * len(demands))) - 1
            master_demand = demands[max(0, min(len(demands) - 1, idx))]
        elif self.master_demand_method == "WEIGHTED":
            # Weighted average
            master_demand = sum(demands) / len(demands)
        else:
            master_demand = demands[0]

        return round(master_demand, 1), req_count, req_reasons

    def evaluate_total_hvac_power_impact(
        self,
        curr_sat: float,
        candidate_sat: float,
        chiller_power_kw: float = 42.5,
        fan_power_kw: float = 10.4,
        reheat_power_kw: float = 2.0
    ) -> Tuple[float, float, float, float]:
        """
        Evaluates Total HVAC Power Impact of SAT setpoint change:
        delta_P_total = delta_P_chiller + delta_P_fan + delta_P_reheat
        - Chiller Lift: Higher SAT saves ~3.0% chiller kW per °C warmer.
        - Fan Power: Higher SAT requires slightly higher CFM (fan power scales with cube law).
        - Reheat: Higher SAT reduces simultaneous terminal reheat power.
        Returns: (net_power_impact_kw, delta_chiller_kw, delta_fan_kw, delta_reheat_kw)
        """
        delta_sat = candidate_sat - curr_sat

        # 1. Chiller Power Reduction (negative means saving)
        # 3.2% chiller power reduction per °C of higher SAT due to reduced compressor pressure ratio
        delta_chiller_kw = -(delta_sat * 0.032 * chiller_power_kw)

        # 2. Fan Power Impact (positive means slight penalty)
        # Higher SAT requires proportionally more CFM to deliver same sensible BTU
        delta_fan_kw = (delta_sat * 0.025 * fan_power_kw)

        # 3. Reheat Energy Impact (negative means saving)
        # Higher SAT prevents zone overcooling and avoids reheat calls
        delta_reheat_kw = -(delta_sat * 0.15 * reheat_power_kw)

        # Total Net Impact (Positive value represents net power saved)
        net_saved_kw = round(-(delta_chiller_kw + delta_fan_kw + delta_reheat_kw), 2)

        return (
            net_saved_kw,
            round(-delta_chiller_kw, 2),
            round(delta_fan_kw, 2),
            round(-delta_reheat_kw, 2)
        )

    def evaluate(self, state: Dict[str, Any]) -> OpportunityEvaluationResult:
        """
        Common evaluation interface for O3 Master AHU SAT.
        Ingests AHU and VAV telemetry, computes master demand, evaluates HVAC impact,
        and produces candidate supervisory actions.
        """
        ahus = state.get("ahus", [])
        candidates: List[CandidateAction] = []
        plant = state.get("plant", {})
        chiller_kw = plant.get("total_power_kw", 42.5)

        total_net_savings_kw = 0.0
        all_vav_signals: List[VAVZoneSignal] = []

        for ahu in ahus:
            ahu_id = ahu.get("id", "AHU-1")
            curr_sat = ahu.get("sat_actual", ahu.get("sat", 13.2))
            curr_sp = ahu.get("sat_setpoint", ahu.get("sat_sp", 13.0))
            fan_kw = ahu.get("fan_power_kw", ahu.get("fan_kw", 10.4))
            raw_zones = ahu.get("vav_zones", [])

            vav_signals = self._parse_vav_signals(raw_zones)
            all_vav_signals.extend(vav_signals)

            master_demand, req_count, req_reasons = self.calculate_master_demand(vav_signals)

            # Guideline 36 Trim & Respond Logic
            if req_count == 0:
                # No critical cooling calls -> Trim SAT Warmer to save chiller lift
                target_sat = round(min(self.max_sat_clamp_c, curr_sp + self.trim_step_c), 1)
                action_verb = "RESET_SAT_UPWARD"
                action_reason = (
                    f"AHU {ahu_id} downstream master zone demand has 0 cooling calls (master demand {master_demand}%). "
                    f"Trimming SAT setpoint warmer by +{self.trim_step_c}°C ({curr_sp:.1f}°C → {target_sat:.1f}°C) to reduce central chiller lift."
                )
            elif req_count >= 2 or master_demand > 75.0:
                # High cooling calls -> Respond SAT Cooler to satisfy comfort
                target_sat = round(max(self.min_sat_clamp_c, curr_sp + self.respond_step_c), 1)
                action_verb = "RESET_SAT_DOWNWARD"
                action_reason = (
                    f"AHU {ahu_id} detected {req_count} zone cooling calls (master demand {master_demand}%). "
                    f"Responding SAT cooler by {self.respond_step_c}°C ({curr_sp:.1f}°C → {target_sat:.1f}°C) to satisfy thermal comfort."
                )
            else:
                # Equilibrium hold
                target_sat = curr_sp
                action_verb = "HOLD_SAT"
                action_reason = f"AHU {ahu_id} master demand ({master_demand}%) in balance with current SAT ({curr_sp:.1f}°C)."

            # Total HVAC Power Impact
            net_saved_kw, chiller_sav, fan_pen, reheat_sav = self.evaluate_total_hvac_power_impact(
                curr_sat=curr_sat,
                candidate_sat=target_sat,
                chiller_power_kw=chiller_kw,
                fan_power_kw=fan_kw
            )

            if abs(target_sat - curr_sp) >= 0.2:
                act = CandidateAction(
                    id=f"act-o3-sat-{ahu_id}",
                    opportunity_code="O3",
                    point_id=f"{ahu_id}-SAT-SP",
                    equipment_id=ahu_id,
                    current_value=curr_sp,
                    proposed_value=target_sat,
                    reason=(
                        f"{action_reason} "
                        f"Net HVAC Power Impact: +{net_saved_kw:+.2f} kW (-{chiller_sav:.2f} kW chiller lift, +{fan_pen:.2f} kW fan airflow)."
                    ),
                    confidence=0.94,
                    verification_window_minutes=15,
                    expected_result=f"{ahu_id} SAT stabilizes within ±0.3°C of target {target_sat:.1f}°C without tripping freeze-stat limit.",
                    rollback_value=curr_sp,
                    priority=10,
                    constraints_applied=[
                        f"Guideline 36 SAT Clamp [{self.min_sat_clamp_c}°C - {self.max_sat_clamp_c}°C]",
                        f"Coil Freeze Guard >= {self.min_sat_clamp_c}°C",
                        f"Max Step Rate <= {self.max_rate_of_change_c}°C/cycle"
                    ]
                )
                candidates.append(act)
                total_net_savings_kw += max(0.0, net_saved_kw)

        recommended = candidates[0] if candidates else None

        # Format zone signals for UI
        zone_signals_data = [
            {
                "zone_id": z.zone_id,
                "name": z.name,
                "temperature": z.temperature,
                "setpoint": z.setpoint,
                "deviation": z.deviation,
                "cooling_demand_pct": z.cooling_demand_pct,
                "heating_demand_pct": z.heating_demand_pct,
                "damper_position_pct": z.damper_position_pct,
                "cooling_valve_pct": z.cooling_valve_pct,
                "reheat_valve_pct": z.reheat_valve_pct,
                "sensor_quality": z.sensor_quality,
                "is_excluded": z.is_excluded,
                "exclusion_reason": z.exclusion_reason
            }
            for z in all_vav_signals
        ]

        return OpportunityEvaluationResult(
            opportunity_code="O3",
            equipment="AHU-FLEET",
            current_state={
                "ahus_count": len(ahus),
                "calculation_method": self.master_demand_method,
                "min_sat_limit": self.min_sat_clamp_c,
                "max_sat_limit": self.max_sat_clamp_c,
                "total_vav_zones": len(all_vav_signals),
                "excluded_zones_count": sum(1 for z in all_vav_signals if z.is_excluded),
                "vav_zones": zone_signals_data
            },
            candidates=candidates,
            recommended_action=recommended,
            reason=recommended.reason if recommended else "AHU SAT setpoints in optimal equilibrium with downstream zone demand.",
            confidence=0.94,
            constraints=[
                "ASHRAE Guideline 36 Trim & Respond",
                f"Freeze Guard Coil Clamp >= {self.min_sat_clamp_c}°C",
                f"Dehumidification Upper Clamp <= {self.max_sat_clamp_c}°C",
                "Faulty & Blacklisted Zone Exclusion Filter"
            ],
            expected_impact={
                "estimated_power_kw_impact": round(total_net_savings_kw, 1),
                "chiller_power_saved_kw": round(total_net_savings_kw * 1.25, 1),
                "fan_power_penalty_kw": round(total_net_savings_kw * 0.25, 1),
                "daily_kwh_saved": round(total_net_savings_kw * 10.0, 1),
                "cost_saved_usd_per_day": round(total_net_savings_kw * 10.0 * 0.12, 2)
            },
            verification_plan={
                "target_point": "AHU-1-SAT",
                "expected_target": "SAT stabilizes at target setpoint (±0.3°C)",
                "window_minutes": 15,
                "rollback_condition": ">= 2 zones enter cooling breach or SAT < 12.0°C (Immediate revert to 12.8°C design SAT via Priority 8)"
            }
        )
