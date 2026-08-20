from typing import Dict, Any, List

class SpaceTempVerifier:
    """Verifies that zone setpoint resets remain strictly within safety bounds and ASHRAE 55 envelopes."""

    def verify(self, recommendations: Dict[str, Any], min_comfort_cool_sp: float = 21.5, max_comfort_cool_sp: float = 26.0) -> Dict[str, Any]:
        violations = []
        is_safe = True

        for adj in recommendations.get("zone_adjustments", []):
            t_cool = adj.get("target_cooling_sp", 23.0)
            if t_cool > max_comfort_cool_sp:
                violations.append(f"Zone {adj['zone_id']} target cooling SP {t_cool}°C exceeds max limit {max_comfort_cool_sp}°C.")
                is_safe = False
            elif t_cool < min_comfort_cool_sp:
                violations.append(f"Zone {adj['zone_id']} target cooling SP {t_cool}°C below min limit {min_comfort_cool_sp}°C.")
                is_safe = False

            # Check deadband integrity (must be at least 1.0°C to prevent hunting)
            db = adj.get("deadband", 2.0)
            if db < 1.0:
                violations.append(f"Zone {adj['zone_id']} deadband {db}°C is narrower than safety minimum 1.0°C.")
                is_safe = False

        return {
            "is_valid": is_safe,
            "status": "PASS" if is_safe else "FAIL",
            "violations": violations,
            "checked_zones_count": len(recommendations.get("zone_adjustments", []))
        }
