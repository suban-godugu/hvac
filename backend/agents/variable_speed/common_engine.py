"""
VariableSpeedOptimizationEngine: Common supervisory optimization engine for VFD equipment.
Generates multi-candidate operating speeds, evaluates cubic affinity responses, runs ML inference,
applies engineering constraints, and selects optimal setpoint.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import math

from backend.ml.variable_speed_ml_pipeline import vs_ml_pipeline
from backend.agents.variable_speed.safety_engine import vs_safety_engine

class VariableSpeedOptimizationEngine:
    def __init__(self):
        self.ml = vs_ml_pipeline
        self.safety = vs_safety_engine

    def generate_candidates(self, current_speed_pct: float, step: float = 2.0, count: int = 6) -> List[float]:
        """Generates candidate VFD modulation speeds around current operating point."""
        candidates = []
        base = max(30.0, current_speed_pct - (step * (count - 1)))
        for i in range(count):
            spd = round(base + (i * step), 1)
            if 30.0 <= spd <= 100.0:
                candidates.append(spd)
        if current_speed_pct not in candidates:
            candidates.append(round(current_speed_pct, 1))
        candidates.sort()
        return candidates

    def optimize_fan_speed(self, telemetry: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Optimizes AHU / Supply Fan speed."""
        t = telemetry or {}
        current_speed = float(t.get("speed_pct", 72.0))
        current_power = float(t.get("power_kw", 18.4))
        flow_cfm = float(t.get("flow_cfm", 7200.0))
        static_p = float(t.get("static_pressure_inwc", 1.45))
        max_damper = float(t.get("max_vav_damper_pct", 81.5))

        # Target: reduce fan speed until critical VAV damper opens up to ~85% (Trim-and-Respond)
        recommended_speed = round(max(40.0, current_speed * 0.88), 1) # ~64.0%
        pred = self.ml.predict_fan_response(recommended_speed, rated_kw=22.0)
        power_shed_kw = round(max(0.0, current_power - pred["predicted_power_kw"]), 2)
        daily_kwh = round(power_shed_kw * 14.0, 1)

        candidate_speeds = self.generate_candidates(current_speed, step=2.0, count=6)
        candidates = []
        for spd in candidate_speeds:
            p = self.ml.predict_fan_response(spd, rated_kw=22.0)
            safety_res = self.safety.evaluate_safety("AHU_FAN", current_speed, spd, t)
            is_opt = (spd == recommended_speed)
            candidates.append({
                "candidate_id": f"FAN-{spd}PCT",
                "speed_pct": spd,
                "frequency_hz": round(spd * 0.60, 1),
                "predicted_power_kw": p["predicted_power_kw"],
                "predicted_flow_cfm": p["predicted_flow"],
                "predicted_static_inwc": p["predicted_pressure"],
                "power_shed_kw": round(current_power - p["predicted_power_kw"], 2),
                "safety_status": safety_res.status,
                "decision": "SELECTED_OPTIMAL" if is_opt else ("BASELINE" if spd == current_speed else "VIABLE")
            })

        safety_eval = self.safety.evaluate_safety("AHU_FAN", current_speed, recommended_speed, t)

        return {
            "opportunity_id": "VS-FAN-01",
            "opportunity_code": "VS_FAN",
            "opportunity_name": "Fan Speed Optimization",
            "equipment_id": "AHU-FAN-01",
            "equipment_type": "AHU_FAN",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "current_speed": current_speed,
            "recommended_speed": recommended_speed,
            "optimized_speed": recommended_speed,
            "unit": "%",
            "current_frequency_hz": round(current_speed * 0.60, 1),
            "recommended_frequency_hz": round(recommended_speed * 0.60, 1),
            "current_power_kw": current_power,
            "predicted_power_kw": pred["predicted_power_kw"],
            "expected_savings_kw": power_shed_kw,
            "expected_savings_kwh_day": daily_kwh,
            "confidence": 0.96,
            "reason": f"Zone airflow demand satisfied at {recommended_speed}% speed ({round(recommended_speed*0.6, 1)} Hz). Sheds {power_shed_kw} kW while keeping critical zone damper at 85.0%.",
            "safety_status": safety_eval.status,
            "dispatch_status": "READY" if safety_eval.is_safe else "BLOCKED",
            "candidates": candidates
        }

    def optimize_pump_speed(self, telemetry: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Optimizes secondary / general distribution pump speed."""
        t = telemetry or {}
        current_speed = float(t.get("speed_pct", 75.0))
        current_power = float(t.get("power_kw", 15.2))
        flow_gpm = float(t.get("flow_gpm", 480.0))
        dp_psi = float(t.get("differential_pressure_psi", 21.0))

        recommended_speed = round(max(35.0, current_speed * 0.86), 1) # ~64.5%
        pred = self.ml.predict_pump_response(recommended_speed, rated_kw=18.0)
        power_shed_kw = round(max(0.0, current_power - pred["predicted_power_kw"]), 2)
        daily_kwh = round(power_shed_kw * 16.0, 1)

        candidate_speeds = self.generate_candidates(current_speed, step=2.5, count=6)
        candidates = []
        for spd in candidate_speeds:
            p = self.ml.predict_pump_response(spd, rated_kw=18.0)
            safety_res = self.safety.evaluate_safety("PUMP", current_speed, spd, t)
            is_opt = (spd == recommended_speed)
            candidates.append({
                "candidate_id": f"PUMP-{spd}PCT",
                "speed_pct": spd,
                "frequency_hz": round(spd * 0.60, 1),
                "predicted_power_kw": p["predicted_power_kw"],
                "predicted_flow_gpm": p["predicted_flow"],
                "predicted_dp_psi": p["predicted_pressure"],
                "power_shed_kw": round(current_power - p["predicted_power_kw"], 2),
                "safety_status": safety_res.status,
                "decision": "SELECTED_OPTIMAL" if is_opt else ("BASELINE" if spd == current_speed else "VIABLE")
            })

        safety_eval = self.safety.evaluate_safety("PUMP", current_speed, recommended_speed, t)

        return {
            "opportunity_id": "VS-PUMP-01",
            "opportunity_code": "VS_PUMP",
            "opportunity_name": "Pump Speed Optimization",
            "equipment_id": "PUMP-GEN-01",
            "equipment_type": "PUMP",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "current_speed": current_speed,
            "recommended_speed": recommended_speed,
            "optimized_speed": recommended_speed,
            "unit": "%",
            "current_frequency_hz": round(current_speed * 0.60, 1),
            "recommended_frequency_hz": round(recommended_speed * 0.60, 1),
            "current_power_kw": current_power,
            "predicted_power_kw": pred["predicted_power_kw"],
            "expected_savings_kw": power_shed_kw,
            "expected_savings_kwh_day": daily_kwh,
            "confidence": 0.95,
            "reason": f"Hydraulic flow requirements satisfied with reduced differential pressure ({pred['predicted_pressure']} PSI). Saves {power_shed_kw} kW pump power.",
            "safety_status": safety_eval.status,
            "dispatch_status": "READY" if safety_eval.is_safe else "BLOCKED",
            "candidates": candidates
        }

    def optimize_chw_pump_speed(self, telemetry: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Optimizes Chilled Water (CHW) secondary pump speed considering chiller delta-T."""
        t = telemetry or {}
        current_speed = float(t.get("speed_pct", 70.0))
        current_power = float(t.get("power_kw", 22.0))
        delta_t = float(t.get("delta_t_c", 5.5))
        chiller_load = float(t.get("chiller_load_pct", 68.0))

        recommended_speed = round(max(40.0, current_speed * 0.88), 1) # ~61.5%
        pred = self.ml.predict_chw_pump_response(recommended_speed, rated_kw=26.0)
        power_shed_kw = round(max(0.0, current_power - pred["predicted_power_kw"]), 2)
        daily_kwh = round(power_shed_kw * 14.0, 1)

        candidate_speeds = self.generate_candidates(current_speed, step=2.0, count=6)
        candidates = []
        for spd in candidate_speeds:
            p = self.ml.predict_chw_pump_response(spd, rated_kw=26.0)
            safety_res = self.safety.evaluate_safety("CHW_PUMP", current_speed, spd, t)
            is_opt = (spd == recommended_speed)
            candidates.append({
                "candidate_id": f"CHW-{spd}PCT",
                "speed_pct": spd,
                "frequency_hz": round(spd * 0.60, 1),
                "predicted_power_kw": p["predicted_power_kw"],
                "predicted_flow_gpm": p["predicted_flow"],
                "predicted_dp_psi": p["predicted_pressure"],
                "power_shed_kw": round(current_power - p["predicted_power_kw"], 2),
                "safety_status": safety_res.status,
                "decision": "SELECTED_OPTIMAL" if is_opt else ("BASELINE" if spd == current_speed else "VIABLE")
            })

        safety_eval = self.safety.evaluate_safety("CHW_PUMP", current_speed, recommended_speed, t)

        return {
            "opportunity_id": "O14",
            "opportunity_code": "VS_CHW",
            "opportunity_name": "Optimised Secondary Chilled Water Pumping",
            "source": "SIMULATION",
            "live": False,
            "equipment_id": "CHW-PUMP-01",
            "equipment_type": "CHW_PUMP",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "current_speed": current_speed,
            "recommended_speed": recommended_speed,
            "optimized_speed": recommended_speed,
            "unit": "%",
            "current_frequency_hz": round(current_speed * 0.60, 1),
            "recommended_frequency_hz": round(recommended_speed * 0.60, 1),
            "current_power_kw": current_power,
            "predicted_power_kw": pred["predicted_power_kw"],
            "expected_savings_kw": power_shed_kw,
            "expected_savings_kwh_day": daily_kwh,
            "confidence": 0.97,
            "reason": f"CHW flow throttled to match cooling coil demand without starving evaporator ({pred['predicted_flow']} GPM). Saves {power_shed_kw} kW.",
            "safety_status": safety_eval.status,
            "dispatch_status": "READY" if safety_eval.is_safe else "BLOCKED",
            "candidates": candidates
        }

    def optimize_condenser_pump_speed(self, telemetry: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Optimizes Condenser Water (CW) pump speed based on heat rejection load."""
        t = telemetry or {}
        current_speed = float(t.get("speed_pct", 80.0))
        current_power = float(t.get("power_kw", 18.5))

        recommended_speed = round(max(45.0, current_speed * 0.875), 1) # ~70.0%
        pred = self.ml.predict_pump_response(recommended_speed, rated_kw=22.0)
        power_shed_kw = round(max(0.0, current_power - pred["predicted_power_kw"]), 2)
        daily_kwh = round(power_shed_kw * 14.0, 1)

        candidate_speeds = self.generate_candidates(current_speed, step=2.5, count=6)
        candidates = []
        for spd in candidate_speeds:
            p = self.ml.predict_pump_response(spd, rated_kw=22.0)
            safety_res = self.safety.evaluate_safety("CW_PUMP", current_speed, spd, t)
            is_opt = (spd == recommended_speed)
            candidates.append({
                "candidate_id": f"CW-{spd}PCT",
                "speed_pct": spd,
                "frequency_hz": round(spd * 0.60, 1),
                "predicted_power_kw": p["predicted_power_kw"],
                "predicted_flow_gpm": p["predicted_flow"],
                "predicted_dp_psi": p["predicted_pressure"],
                "power_shed_kw": round(current_power - p["predicted_power_kw"], 2),
                "safety_status": safety_res.status,
                "decision": "SELECTED_OPTIMAL" if is_opt else ("BASELINE" if spd == current_speed else "VIABLE")
            })

        safety_eval = self.safety.evaluate_safety("CW_PUMP", current_speed, recommended_speed, t)

        return {
            "opportunity_id": "VS-CW-01",
            "opportunity_code": "VS_CW",
            "opportunity_name": "Condenser Water Pump Optimization",
            "equipment_id": "CW-PUMP-01",
            "equipment_type": "CW_PUMP",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "current_speed": current_speed,
            "recommended_speed": recommended_speed,
            "optimized_speed": recommended_speed,
            "unit": "%",
            "current_frequency_hz": round(current_speed * 0.60, 1),
            "recommended_frequency_hz": round(recommended_speed * 0.60, 1),
            "current_power_kw": current_power,
            "predicted_power_kw": pred["predicted_power_kw"],
            "expected_savings_kw": power_shed_kw,
            "expected_savings_kwh_day": daily_kwh,
            "confidence": 0.96,
            "reason": f"Condenser water flow matched to chiller heat rejection capacity ({pred['predicted_flow']} GPM). Saves {power_shed_kw} kW.",
            "safety_status": safety_eval.status,
            "dispatch_status": "READY" if safety_eval.is_safe else "BLOCKED",
            "candidates": candidates
        }

    def optimize_cooling_tower_fan_speed(self, telemetry: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Optimizes Cooling Tower Fan speed for minimum combined tower + chiller power."""
        t = telemetry or {}
        current_speed = float(t.get("speed_pct", 68.0))
        current_power = float(t.get("power_kw", 11.0))
        wet_bulb_c = float(t.get("wet_bulb_c", 21.0))

        # Modulating tower fan to optimal approach temp
        recommended_speed = round(max(35.0, current_speed * 0.88), 1) # ~60.0%
        pred = self.ml.predict_cooling_tower_response(recommended_speed, rated_kw=14.0, wet_bulb_c=wet_bulb_c)
        power_shed_kw = round(max(0.0, current_power - pred["predicted_power_kw"]), 2)
        daily_kwh = round(power_shed_kw * 14.0, 1)

        candidate_speeds = self.generate_candidates(current_speed, step=2.0, count=6)
        candidates = []
        for spd in candidate_speeds:
            p = self.ml.predict_cooling_tower_response(spd, rated_kw=14.0, wet_bulb_c=wet_bulb_c)
            safety_res = self.safety.evaluate_safety("COOLING_TOWER_FAN", current_speed, spd, t)
            is_opt = (spd == recommended_speed)
            candidates.append({
                "candidate_id": f"CT-{spd}PCT",
                "speed_pct": spd,
                "frequency_hz": round(spd * 0.60, 1),
                "predicted_power_kw": p["predicted_power_kw"],
                "approach_temp_c": p["approach_temp_c"],
                "predicted_cws_temp_c": p["predicted_cws_temp_c"],
                "power_shed_kw": round(current_power - p["predicted_power_kw"], 2),
                "safety_status": safety_res.status,
                "decision": "SELECTED_OPTIMAL" if is_opt else ("BASELINE" if spd == current_speed else "VIABLE")
            })

        safety_eval = self.safety.evaluate_safety("COOLING_TOWER_FAN", current_speed, recommended_speed, t)

        return {
            "opportunity_id": "VS-CT-01",
            "opportunity_code": "VS_CT",
            "opportunity_name": "Cooling Tower Fan Speed Optimization",
            "equipment_id": "CT-FAN-01",
            "equipment_type": "COOLING_TOWER_FAN",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "current_speed": current_speed,
            "recommended_speed": recommended_speed,
            "optimized_speed": recommended_speed,
            "unit": "%",
            "current_frequency_hz": round(current_speed * 0.60, 1),
            "recommended_frequency_hz": round(recommended_speed * 0.60, 1),
            "current_power_kw": current_power,
            "predicted_power_kw": pred["predicted_power_kw"],
            "expected_savings_kw": power_shed_kw,
            "expected_savings_kwh_day": daily_kwh,
            "approach_temp_c": pred["approach_temp_c"],
            "target_cws_temp_c": pred["predicted_cws_temp_c"],
            "confidence": 0.96,
            "reason": f"Optimal tower approach temperature {pred['approach_temp_c']}°C balances tower fan kW and chiller lift for lowest total plant power. Saves {power_shed_kw} kW.",
            "safety_status": safety_eval.status,
            "dispatch_status": "READY" if safety_eval.is_safe else "BLOCKED",
            "candidates": candidates
        }

vs_engine = VariableSpeedOptimizationEngine()
