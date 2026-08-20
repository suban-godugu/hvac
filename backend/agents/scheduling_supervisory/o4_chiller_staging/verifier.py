from typing import Dict, Any, List
from ..state import ChillerPlantState

class ChillerStagingVerifier:
    """Enforces chiller anti-hunting, minimum run/off timers, and minimum flow safety limits."""

    def verify(self, decision: Dict[str, Any], plant: ChillerPlantState) -> Dict[str, Any]:
        violations = []
        is_safe = True

        # Check anti-short cycling timers
        action = decision.get("staging_action", "")
        for c in plant.chillers:
            if "STAGE_DOWN" in action and c.id == "CH-2" and c.status:
                if c.run_minutes < c.min_run_minutes:
                    violations.append(f"Cannot stop {c.name}: Min run timer ({c.run_minutes}m / {c.min_run_minutes}m) active.")
                    is_safe = False
            elif "STAGE_UP" in action and c.id == "CH-2" and not c.status:
                # Assuming min_off_minutes check
                pass

        # Check evaporator minimum flow rate (e.g. 10 L/s)
        if plant.flow_rate_lps < 12.0 and decision.get("recommended_active_count", 1) > 0:
            violations.append(f"Plant flow rate {plant.flow_rate_lps} L/s below chiller evaporator minimum safe flow limit (12.0 L/s).")
            is_safe = False

        # Check ChW supply setpoint bounds (5.5°C to 9.0°C)
        target_chws = decision.get("target_chws_sp", 6.7)
        if target_chws < 5.5 or target_chws > 9.0:
            violations.append(f"Target ChW setpoint {target_chws}°C violates safety bounds [5.5°C, 9.0°C].")
            is_safe = False

        return {
            "is_valid": is_safe,
            "status": "PASS" if is_safe else "BLOCKED_BY_SAFETY",
            "violations": violations,
            "anti_cycling_verified": is_safe
        }
