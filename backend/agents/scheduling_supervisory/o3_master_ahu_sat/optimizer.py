from typing import Dict, Any
from ..state import AHUState
from .demand import AHUDemandAnalyzer

class SATOptimizer:
    """ASHRAE Guideline 36 Trim & Respond Supply Air Temperature Optimizer."""

    def __init__(self):
        self.analyzer = AHUDemandAnalyzer()
        self.min_sat = 12.2   # °C (Design cooling minimum)
        self.max_sat = 17.5   # °C (Design maximum before air circulation issues)
        self.trim_step = +0.25  # °C increase when requests = 0
        self.respond_step = -0.40 # °C decrease per critical request
        self.ignore_req_threshold = 1 # Ignore single rogue zone request

    def optimize_sat(self, ahu: AHUState) -> Dict[str, Any]:
        demand = self.analyzer.calculate_cooling_requests(ahu.vav_zones)
        requests = demand["cooling_requests_count"]
        effective_requests = max(0, requests - self.ignore_req_threshold)

        current_sp = ahu.sat_setpoint
        delta_t = 0.0

        if effective_requests == 0:
            # Trim: System is satisfied or only 1 minor outlier -> Reset SAT warmer to save chiller lift
            delta_t = self.trim_step
            action = "TRIM_WARMER"
            reason = f"0 effective zone requests (avg damper {demand['avg_damper_pos']}%), raising SAT by +{self.trim_step}°C."
        else:
            # Respond: Zones are calling for more cooling -> Drop SAT cooler
            delta_t = self.respond_step * effective_requests
            action = "RESPOND_COOLER"
            reason = f"{requests} zones requesting cooling ({effective_requests} effective), lowering SAT by {abs(delta_t):.2f}°C."

        target_sat = round(min(self.max_sat, max(self.min_sat, current_sp + delta_t)), 1)
        actual_delta = round(target_sat - current_sp, 2)

        # Estimate savings: 1°C increase in SAT reduces chiller power by ~3.2%
        fan_penalty_kw = max(0.0, (target_sat - 12.8) * 0.4) # Slightly higher fan CFM
        chiller_savings_kw = max(0.0, (target_sat - 12.8) * 1.8) # Significant chiller lift reduction
        net_savings_kw = round(max(0.0, chiller_savings_kw - fan_penalty_kw), 2)

        return {
            "ahu_id": ahu.id,
            "ahu_name": ahu.name,
            "current_sat": ahu.sat_actual,
            "current_sat_sp": current_sp,
            "target_sat_sp": target_sat,
            "delta_sat": actual_delta,
            "action": action,
            "reasoning": reason,
            "cooling_requests": requests,
            "critical_zones": demand["critical_zones"],
            "avg_damper_pct": demand["avg_damper_pos"],
            "net_savings_kw_est": net_savings_kw
        }
