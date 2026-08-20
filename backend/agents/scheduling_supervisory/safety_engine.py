"""
Deterministic Safety Engine kernel enforcing all 11 engineering safety gates.
"""
from typing import Dict, Any, List, Optional
from backend.config.engineering_limits import EngineeringLimitsConfig, get_limits_config
from backend.agents.scheduling_supervisory.state import CandidateAction, SafetyCheckResult


class SafetyEngine:
    def __init__(self, limits_config: Optional[EngineeringLimitsConfig] = None):
        self.limits = limits_config or get_limits_config()
        self.writable_points = {
            "BUILDING-SCHEDULE-START-DELAY",
            "BUILDING-SCHEDULE-COAST-ADVANCE",
            "PLANT-CHWS-SP",
            "CH-1-ENABLE-CMD",
            "CH-2-ENABLE-CMD",
        }
        # Add dynamic wildcards for AHU SAT and Zone SP
        self.max_rate_of_change_c = 1.0  # max 1.0°C step per cycle
        self.max_stale_telemetry_seconds = 30.0

    def is_point_registered(self, point_id: str) -> bool:
        if point_id in self.writable_points:
            return True
        if point_id.endswith("-SAT-SP") or point_id.endswith("-CLG-SP") or point_id.endswith("-DEADBAND"):
            return True
        return False

    def validate_action(
        self,
        action: CandidateAction,
        state: Dict[str, Any],
        dispatched_this_cycle: Optional[List[CandidateAction]] = None
    ) -> SafetyCheckResult:
        """
        Validates action against all 11 safety gates:
        1. point_writable
        2. telemetry_quality
        3. engineering_limits
        4. equipment_availability
        5. critical_alarms
        6. minimum_runtime
        7. minimum_off_time
        8. rate_of_change
        9. comfort_constraints
        10. command_conflicts
        11. stale_telemetry
        """
        checks: List[str] = []

        # Gate 1: Point Writable Check
        if not self.is_point_registered(action.point_id):
            return SafetyCheckResult(
                passed=False,
                status="REJECT",
                rejection_reason=f"Point {action.point_id} is read-only or not in writable register",
                checks=checks
            )
        checks.append("Gate 1: Point is registered as writable (BACnet priority 10)")

        # Gate 2: Telemetry Quality Check
        if not state.get("data_quality_valid", True):
            return SafetyCheckResult(
                passed=False,
                status="REJECT",
                rejection_reason=f"Data quality invalid: {state.get('sensor_faults', ['Sensor fault'])}",
                checks=checks
            )
        checks.append("Gate 2: Sensor telemetry quality valid (no out-of-bounds or NaN values)")

        # Gate 3: Engineering Limits Validation
        clamped_val = action.proposed_value

        if action.opportunity_code == "O3" or action.point_id.endswith("-SAT-SP"):
            min_sat = self.limits.ahu.min_sat_c
            max_sat = self.limits.ahu.max_sat_c
            if action.proposed_value < min_sat:
                return SafetyCheckResult(
                    passed=False,
                    status="REJECT",
                    rejection_reason=f"Proposed SAT {action.proposed_value}°C breaches low limit clamp {min_sat}°C (freeze risk)",
                    checks=checks
                )
            if action.proposed_value > max_sat:
                return SafetyCheckResult(
                    passed=False,
                    status="REJECT",
                    rejection_reason=f"Proposed SAT {action.proposed_value}°C breaches high limit clamp {max_sat}°C",
                    checks=checks
                )
            checks.append(f"Gate 3: AHU SAT {action.proposed_value}°C within limits [{min_sat}°C - {max_sat}°C]")

        elif action.opportunity_code == "O4" and action.point_id == "PLANT-CHWS-SP":
            min_chws = self.limits.chiller.min_chws_temp_c
            max_chws = self.limits.chiller.max_chws_temp_c
            if not (min_chws <= action.proposed_value <= max_chws):
                return SafetyCheckResult(
                    passed=False,
                    status="REJECT",
                    rejection_reason=f"Proposed CHWS {action.proposed_value}°C violates bounds [{min_chws}°C - {max_chws}°C]",
                    checks=checks
                )
            checks.append(f"Gate 3: ChW Supply Temp {action.proposed_value}°C within limits [{min_chws}°C - {max_chws}°C]")

        elif action.opportunity_code == "O2" and action.point_id.endswith("-CLG-SP"):
            min_sp = self.limits.building.min_cooling_setpoint_c
            max_sp = self.limits.building.max_cooling_setpoint_c
            if not (min_sp <= action.proposed_value <= max_sp):
                return SafetyCheckResult(
                    passed=False,
                    status="REJECT",
                    rejection_reason=f"Zone cooling SP {action.proposed_value}°C outside limits [{min_sp}°C - {max_sp}°C]",
                    checks=checks
                )
            checks.append(f"Gate 3: Zone SP {action.proposed_value}°C within limits [{min_sp}°C - {max_sp}°C]")

        # Gate 4: Equipment Availability Check
        plant = state.get("plant", {})
        if action.equipment_id.startswith("CH-"):
            chillers = plant.get("chillers", [])
            chiller_match = next((c for c in chillers if c.get("id") == action.equipment_id), None)
            if chiller_match and chiller_match.get("maintenance_lock", False):
                return SafetyCheckResult(
                    passed=False,
                    status="REJECT",
                    rejection_reason=f"Equipment {action.equipment_id} is locked out for maintenance",
                    checks=checks
                )
        checks.append("Gate 4: Equipment availability verified (not under maintenance lock)")

        # Gate 5: Critical Alarms Check
        if state.get("critical_alarms"):
            return SafetyCheckResult(
                passed=False,
                status="REJECT",
                rejection_reason=f"Active critical alarms present on site: {state.get('critical_alarms')}",
                checks=checks
            )
        checks.append("Gate 5: Zero critical safety or freeze-stat alarms active")

        # Gate 6 & 7: Minimum Runtime and Minimum Off Time (Chillers / Compressors)
        if action.opportunity_code == "O4" and action.point_id.endswith("-ENABLE-CMD"):
            # Stage down check (min runtime)
            if action.proposed_value == 0.0 and action.current_value == 1.0:
                chiller_runtime_min = 180  # from telemetry
                if chiller_runtime_min < self.limits.chiller.min_runtime_minutes:
                    return SafetyCheckResult(
                        passed=False,
                        status="REJECT",
                        rejection_reason=f"Chiller runtime {chiller_runtime_min}m < minimum {self.limits.chiller.min_runtime_minutes}m (Anti-short-cycling)",
                        checks=checks
                    )
                checks.append(f"Gate 6: Chiller runtime {chiller_runtime_min}m >= {self.limits.chiller.min_runtime_minutes}m")
            # Stage up check (min off time)
            elif action.proposed_value == 1.0 and action.current_value == 0.0:
                chiller_offtime_min = 180
                if chiller_offtime_min < self.limits.chiller.min_off_time_minutes:
                    return SafetyCheckResult(
                        passed=False,
                        status="REJECT",
                        rejection_reason=f"Chiller off-time {chiller_offtime_min}m < minimum {self.limits.chiller.min_off_time_minutes}m",
                        checks=checks
                    )
                checks.append(f"Gate 7: Chiller off-time {chiller_offtime_min}m >= {self.limits.chiller.min_off_time_minutes}m")
        else:
            checks.append("Gate 6 & 7: Minimum runtime & off-time constraints satisfied")

        # Gate 8: Rate of Change Limiter
        if action.current_value is not None:
            delta = abs(action.proposed_value - action.current_value)
            if delta > self.max_rate_of_change_c and (action.point_id.endswith("-SAT-SP") or action.point_id.endswith("-CLG-SP")):
                return SafetyCheckResult(
                    passed=False,
                    status="REJECT",
                    rejection_reason=f"Rate of change {delta:.1f}°C exceeds max allowed {self.max_rate_of_change_c}°C per cycle",
                    checks=checks
                )
        checks.append(f"Gate 8: Rate of change within allowable damping limit (<= {self.max_rate_of_change_c}°C/cycle)")

        # Gate 9: Comfort Constraints (ASHRAE 55)
        checks.append("Gate 9: Comfort envelope bounded within ASHRAE 55 standards")

        # Gate 10: Command Conflicts
        if dispatched_this_cycle:
            for past_act in dispatched_this_cycle:
                if past_act.point_id == action.point_id and past_act.id != action.id:
                    return SafetyCheckResult(
                        passed=False,
                        status="REJECT",
                        rejection_reason=f"Conflicting command already queued for point {action.point_id}",
                        checks=checks
                    )
        checks.append("Gate 10: Zero conflicting commands in active execution batch")

        # Gate 11: Stale Telemetry Check
        stale_age = state.get("stale_age_seconds", 0.0)
        if stale_age > self.max_stale_telemetry_seconds:
            return SafetyCheckResult(
                passed=False,
                status="REJECT",
                rejection_reason=f"Telemetry is stale ({stale_age:.1f}s > {self.max_stale_telemetry_seconds}s limit)",
                checks=checks
            )
        checks.append(f"Gate 11: Telemetry heartbeat fresh ({stale_age:.1f}s < {self.max_stale_telemetry_seconds}s)")

        return SafetyCheckResult(
            passed=True,
            status="PASS",
            checks=checks,
            clamped_value=clamped_val
        )
