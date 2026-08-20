from typing import Dict, Any, List
from ..state import ChillerPlantState
from .load import ChillerPlantLoadCalculator

class ChillerStagingOptimizer:
    """Optimizes chiller sequencing, staging transitions, and Chilled Water Supply Temperature (CHW-ST) reset."""

    def __init__(self):
        self.load_calc = ChillerPlantLoadCalculator()

    def optimize_staging(self, plant: ChillerPlantState, oat: float) -> Dict[str, Any]:
        load_info = self.load_calc.calculate_plant_load(plant.chws_temp, plant.chwr_temp, plant.flow_rate_lps)
        total_tons = load_info["load_tons"]

        # Capacity per chiller = 120 Tons
        # Optimum operation curve for Centrifugal Chiller:
        # Single chiller peak efficiency is between 60% and 85% load (72 to 102 Tons)
        # Staging up to 2 chillers is optimal when load > 105 Tons for > 15 mins
        # Staging down to 1 chiller is optimal when load < 85 Tons for > 15 mins

        active_chillers = [c for c in plant.chillers if c.status]
        num_active = len(active_chillers)

        recommended_active_count = 1
        staging_action = "MAINTAIN_CURRENT"
        staging_reason = "Load within single chiller high-efficiency window."

        if total_tons > 105.0:
            recommended_active_count = 2
            if num_active < 2:
                staging_action = "STAGE_UP_CH2"
                staging_reason = f"Load at {total_tons} Tons exceeds single chiller max threshold (105T). Enabling CH-2."
            else:
                staging_action = "MAINTAIN_DUAL"
                staging_reason = f"Dual chillers active sharing {total_tons} Tons ({total_tons/2:.1f}T each)."
        elif total_tons < 85.0:
            recommended_active_count = 1
            if num_active > 1:
                staging_action = "STAGE_DOWN_CH2"
                staging_reason = f"Load decreased to {total_tons} Tons. De-staging CH-2 to eliminate low-PLR penalty."
            else:
                staging_action = "MAINTAIN_SINGLE"
                staging_reason = f"Single chiller operating efficiently at {total_tons/120*100:.1f}% load."

        # Chilled Water Supply Temp (CHWS) Reset Calculation
        # Baseline CHWS = 6.7°C (44°F)
        # When OAT is mild and plant load is moderate, reset CHWS up to 8.5°C to save ~2% compressor energy per °C lift reduction
        base_chws = 6.7
        chws_reset_sp = base_chws
        if total_tons < 80.0 and oat < 26.0:
            chws_reset_sp = 8.0 # +1.3°C warmer
        elif total_tons < 110.0 and oat < 30.0:
            chws_reset_sp = 7.5 # +0.8°C warmer
        else:
            chws_reset_sp = 6.7 # Full design cooling lift

        chws_delta = round(chws_reset_sp - plant.chws_setpoint, 2)
        power_saved_est_kw = round(max(0.0, (chws_reset_sp - 6.7) * 2.8), 2)

        return {
            "load_tons": total_tons,
            "load_kw_thermal": load_info["load_kw_thermal"],
            "delta_t": load_info["delta_t_deg_c"],
            "current_active_chillers": num_active,
            "recommended_active_count": recommended_active_count,
            "staging_action": staging_action,
            "staging_reason": staging_reason,
            "current_chws_sp": plant.chws_setpoint,
            "target_chws_sp": chws_reset_sp,
            "chws_delta": chws_delta,
            "power_saved_est_kw": power_saved_est_kw,
            "plant_cop_est": 6.4 if recommended_active_count == 1 else 5.8
        }
