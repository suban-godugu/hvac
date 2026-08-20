from typing import List, Dict, Any
from ..state import ZoneState, AHUState

class AHUDemandAnalyzer:
    """Analyzes zone cooling requests and critical zones for Guideline 36 Trim & Respond SAT reset."""

    def calculate_cooling_requests(self, zones: List[ZoneState], critical_damper_threshold: float = 85.0) -> Dict[str, Any]:
        cooling_requests = 0
        critical_zones = []

        for z in zones:
            # Check if zone is struggling (damper open > 85% and actual temp > setpoint + 0.5)
            if z.damper_pos >= critical_damper_threshold and z.temp_actual > z.cooling_sp + 0.3:
                cooling_requests += 1
                critical_zones.append({
                    "id": z.id,
                    "name": z.name,
                    "damper_pos": z.damper_pos,
                    "temp_error": round(z.temp_actual - z.cooling_sp, 2)
                })

        return {
            "total_zones": len(zones),
            "cooling_requests_count": cooling_requests,
            "critical_zones": critical_zones,
            "max_damper_pos": max([z.damper_pos for z in zones]) if zones else 0.0,
            "avg_damper_pos": round(sum(z.damper_pos for z in zones) / max(1, len(zones)), 1)
        }
