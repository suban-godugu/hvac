from typing import Dict, Any

class ChillerPlantLoadCalculator:
    """Calculates instantaneous building cooling load (Tonnage / kW) and individual chiller Part Load Ratios (PLR)."""

    def calculate_plant_load(self, chws_temp: float, chwr_temp: float, flow_lps: float) -> Dict[str, Any]:
        delta_t = max(0.1, chwr_temp - chws_temp)
        # Thermal power Q (kW) = flow_lps * 4.184 * delta_t
        load_kw_thermal = flow_lps * 4.184 * delta_t
        # 1 Ton of refrigeration = 3.51685 kW
        load_tons = load_kw_thermal / 3.51685

        return {
            "delta_t_deg_c": round(delta_t, 2),
            "flow_rate_lps": flow_lps,
            "load_kw_thermal": round(load_kw_thermal, 1),
            "load_tons": round(load_tons, 1)
        }

    def calculate_chiller_efficiency(self, tons: float, power_kw: float) -> Dict[str, Any]:
        if tons <= 1.0 or power_kw <= 0.1:
            return {"kw_per_ton": 0.0, "cop": 0.0}
        
        kw_per_ton = round(power_kw / tons, 3)
        # COP = 3.51685 / kw_per_ton
        cop = round(3.51685 / kw_per_ton, 2)
        return {"kw_per_ton": kw_per_ton, "cop": cop}
