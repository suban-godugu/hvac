from typing import List, Dict, Any
from ..state import ZoneState

class SpaceTempDetector:
    """Detects unoccupied zones, comfort band outliers, and thermal imbalance across zones."""

    def analyze_zones(self, zones: List[ZoneState]) -> Dict[str, Any]:
        if not zones:
            return {"unoccupied_count": 0, "hot_spots": [], "cold_spots": [], "avg_temp": 23.0}

        unoccupied_zones = [z for z in zones if not z.occupied]
        hot_zones = [z for z in zones if z.temp_actual > z.cooling_sp + 0.8]
        cold_zones = [z for z in zones if z.temp_actual < z.heating_sp - 0.8]
        avg_temp = sum(z.temp_actual for z in zones) / len(zones)

        return {
            "total_zones": len(zones),
            "unoccupied_count": len(unoccupied_zones),
            "unoccupied_zone_ids": [z.id for z in unoccupied_zones],
            "hot_spots": [{"id": z.id, "temp": z.temp_actual, "cooling_sp": z.cooling_sp} for z in hot_zones],
            "cold_spots": [{"id": z.id, "temp": z.temp_actual, "heating_sp": z.heating_sp} for z in cold_zones],
            "avg_temp": round(avg_temp, 2),
            "high_demand_ratio": len([z for z in zones if z.damper_pos > 85]) / len(zones)
        }
