from typing import Dict, Any, List

class SATVerifier:
    """Verifies SAT setpoints against low-limit freeze-stat, high-limit de-stratification, and humidity thresholds."""

    def verify(self, decision: Dict[str, Any], min_clamp: float = 12.0, max_clamp: float = 18.0, oah_pct: float = 55.0) -> Dict[str, Any]:
        violations = []
        is_safe = True

        target_sat = decision.get("target_sat_sp", 13.0)

        if target_sat < min_clamp:
            violations.append(f"Target SAT {target_sat}°C violates minimum freeze protection limit of {min_clamp}°C.")
            is_safe = False

        if target_sat > max_clamp:
            violations.append(f"Target SAT {target_sat}°C exceeds maximum de-humidification ceiling of {max_clamp}°C.")
            is_safe = False

        # High ambient humidity lockout check
        if oah_pct > 75.0 and target_sat > 15.0:
            violations.append(f"High outdoor humidity ({oah_pct}%) lock prevents SAT reset above 15.0°C.")
            is_safe = False

        return {
            "is_valid": is_safe,
            "status": "PASS" if is_safe else "FAIL",
            "violations": violations,
            "freeze_stat_safe": target_sat >= 4.0,
            "humidity_lockout_active": oah_pct > 75.0
        }
