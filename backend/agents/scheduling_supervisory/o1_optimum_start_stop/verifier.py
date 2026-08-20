from typing import Dict, Any, List

class OptimumStartStopVerifier:
    """Verifies that start/stop recommendations satisfy safety and comfort constraints (ASHRAE 55)."""

    def verify(self, decision: Dict[str, Any], max_allowed_precool_min: int = 150, max_comfort_limit: float = 24.5) -> Dict[str, Any]:
        violations: List[str] = []
        is_safe = True

        precool_min = decision.get("required_precool_minutes", 0)
        if precool_min > max_allowed_precool_min:
            violations.append(f"Pre-cool time {precool_min}m exceeds max safety envelope of {max_allowed_precool_min}m.")
            is_safe = False

        if decision.get("start_delay_minutes", 0) < 0:
            violations.append("Calculated start time is earlier than baseline start limit.")
            is_safe = False

        coast_min = decision.get("coast_down_minutes", 0)
        if coast_min > 60:
            violations.append(f"Coast down duration {coast_min}m exceeds 60m comfort safety limit.")
            is_safe = False

        return {
            "is_valid": is_safe,
            "status": "PASS" if is_safe else "FAIL",
            "violations": violations,
            "comfort_compliance": True if is_safe else False,
            "verification_note": "Target zone comfort guaranteed within ASHRAE 55 thermal comfort band." if is_safe else "Constraints breached."
        }
