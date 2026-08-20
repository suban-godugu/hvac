import math
from typing import Dict, Any

class ThermalResponsePredictor:
    """Predicts pull-down / warm-up duration and coast-down drift using multi-parameter thermal models."""

    def __init__(self):
        # Thermal model parameters (calibrated to Skyline Corporate Center)
        self.alpha_cooling = 14.5  # Minutes per degree delta (Indoor vs Target)
        self.beta_weather = 1.8    # Weather compensation factor (Minutes per degree OAT deviation from 20°C)
        self.solar_factor = 0.015  # Minutes reduction/increase per W/m² solar radiation
        self.decay_tau_hours = 6.8 # Thermal decay time constant during coasting

    def predict_precool_minutes(self, zone_temp: float, target_temp: float, oat: float, solar_w_m2: float = 300.0) -> float:
        temp_delta = max(0.0, zone_temp - target_temp)
        if temp_delta <= 0.2:
            return 0.0

        weather_penalty = max(0.0, (oat - 22.0) * self.beta_weather)
        solar_penalty = (solar_w_m2 / 100.0) * self.solar_factor * 10.0

        # Base pull down time
        predicted_minutes = (temp_delta * self.alpha_cooling) + weather_penalty + solar_penalty
        # Clamp within practical bounds (10 mins to 150 mins)
        return min(150.0, max(10.0, round(predicted_minutes, 1)))

    def predict_coastdown_drift(self, current_zone_temp: float, oat: float, coast_minutes: int = 45) -> float:
        """Predicts temperature rise if HVAC is stopped prior to occupancy end."""
        delta_to_ambient = oat - current_zone_temp
        if delta_to_ambient <= 0:
            return 0.1 # Negligible drift if outside is cooler than inside
        
        # Newton's cooling law drift: T(t) = T_env + (T0 - T_env) * exp(-t / tau)
        hours = coast_minutes / 60.0
        drift = delta_to_ambient * (1.0 - math.exp(-hours / self.decay_tau_hours))
        return round(drift, 2)
