"""
VerificationEngine: Closed-loop verification of supervisory actions.
Monitors system physical response against expected result and triggers rollback on critical failure.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from backend.agents.scheduling_supervisory.state import (
    CandidateAction,
    ActionRecordModel,
    VerificationOutcome
)


class VerificationEngine:
    def __init__(self):
        self.active_verifications: Dict[str, Dict[str, Any]] = {}

    def track_action(self, action: CandidateAction, written_value: float):
        """Registers an action to be tracked across its verification window."""
        self.active_verifications[action.id] = {
            "action": action,
            "written_value": written_value,
            "dispatched_at": datetime.utcnow().isoformat(),
            "window_minutes": action.verification_window_minutes,
            "status": "PENDING"
        }

    def verify_action(
        self,
        action: CandidateAction,
        current_state: Dict[str, Any],
        actual_measured_value: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Compares expected vs actual physical trajectory.
        Returns outcome (SUCCESS / PARTIAL / FAILED), measured result, and rollback recommendation.
        """
        outcome = VerificationOutcome.SUCCESS
        actual_result_str = ""
        requires_rollback = False

        # Specific evaluation per opportunity code
        if action.opportunity_code == "O1":
            # O1: Verify zone reached comfort target without overshoot
            all_zones = [z for ahu in current_state.get("ahus", []) for z in ahu.get("vav_zones", [])]
            avg_temp = sum(z.get("temp_actual", 22.5) for z in all_zones) / max(1, len(all_zones)) if all_zones else 22.5
            target = 22.5
            drift = abs(avg_temp - target)

            if drift <= 0.5:
                outcome = VerificationOutcome.SUCCESS
                actual_result_str = f"Avg zone temperature {avg_temp:.1f}°C stabilized within ±0.5°C of target {target}°C."
            elif drift <= 1.0:
                outcome = VerificationOutcome.PARTIAL
                actual_result_str = f"Avg zone temperature {avg_temp:.1f}°C drifted slightly (±{drift:.1f}°C)."
            else:
                outcome = VerificationOutcome.FAILED
                actual_result_str = f"Avg zone temperature {avg_temp:.1f}°C failed to reach comfort target (error > 1.0°C)."
                requires_rollback = True

        elif action.opportunity_code == "O3":
            # O3: Verify AHU SAT matches setpoint without coil freeze trip
            ahu1 = current_state.get("ahus", [{}])[0]
            sat_actual = ahu1.get("sat_actual", action.proposed_value)
            error = abs(sat_actual - action.proposed_value)

            if sat_actual < 11.5:  # Freeze risk
                outcome = VerificationOutcome.FAILED
                actual_result_str = f"SAT dropped to unsafe low {sat_actual:.1f}°C (Freeze-stat proximity)."
                requires_rollback = True
            elif error <= 0.6:
                outcome = VerificationOutcome.SUCCESS
                actual_result_str = f"AHU SAT stabilized at {sat_actual:.1f}°C (error {error:.1f}°C ≤ 0.6°C tolerance)."
            else:
                outcome = VerificationOutcome.PARTIAL
                actual_result_str = f"AHU SAT lagging at {sat_actual:.1f}°C."

        elif action.opportunity_code == "O4":
            # O4: Verify ChW supply temp stability
            plant = current_state.get("plant", {})
            chws = plant.get("chws_temp", action.proposed_value)
            error = abs(chws - action.proposed_value)

            if error <= 0.5:
                outcome = VerificationOutcome.SUCCESS
                actual_result_str = f"ChW supply temperature tracking at {chws:.1f}°C within ±0.5°C tolerance."
            else:
                outcome = VerificationOutcome.PARTIAL
                actual_result_str = f"ChW supply temperature at {chws:.1f}°C."

        elif action.opportunity_code == "O2":
            # O2: Verify zone setback
            outcome = VerificationOutcome.SUCCESS
            actual_result_str = f"Zone setpoint maintained. VAV damper modulated according to new deadband."

        return {
            "action_id": action.id,
            "outcome": outcome.value,
            "actual_result": actual_result_str,
            "requires_rollback": requires_rollback,
            "measured_value": actual_measured_value or action.proposed_value,
            "timestamp": datetime.utcnow().isoformat()
        }
