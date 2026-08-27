from typing import Dict, Any, List, Optional


class ThermalModelLearner:
    """Holds prior thermal rates. Prefer Stage C RLS zone_thermal when READY."""

    def __init__(self):
        self.pull_down_rate_deg_per_hr = 1.45
        self.drift_rate_deg_per_hr = 0.28
        self.learning_samples_count = 0

    def update_model(self, historic_trajectories: List[Dict[str, Any]]) -> Dict[str, Any]:
        n = len(historic_trajectories or [])
        if n == 0:
            return {
                "status": "INSUFFICIENT_DATA",
                "pull_down_rate": None,
                "drift_rate": None,
                "r_squared": None,
                "total_samples": self.learning_samples_count,
            }
        self.learning_samples_count += n
        return {
            "status": "UPDATED",
            "pull_down_rate": self.pull_down_rate_deg_per_hr,
            "drift_rate": self.drift_rate_deg_per_hr,
            "r_squared": None,
            "note": "Prior rates only; R² is not computed without a fitted model.",
            "total_samples": self.learning_samples_count,
        }

    def rls_zone_thermal_snapshot(self, zone_id: str = "ZONE-01") -> Optional[Dict[str, Any]]:
        """Read-only adapter to Stage C RLS (no setpoint writes)."""
        try:
            from backend.ai.rls.service import params_for

            return params_for("zone_thermal", zone_id=zone_id)
        except Exception:
            return None
