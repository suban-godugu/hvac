"""
Variable Speed Simulator: Realistic physics-informed simulator generating correlated
variable-speed telemetry (affinity laws, thermal loads, hydraulic curves).
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import random
import math

class VariableSpeedSimulator:
    def __init__(self):
        self.operating_scenario = "NORMAL" # "NORMAL", "HIGH_LOAD", "LOW_LOAD", "MORNING_START", "OCCUPANCY_SPIKE", "HOT_DAY", "MILD_DAY", "EQUIPMENT_FAULT", "SENSOR_FAULT", "BMS_DISCONNECTED"
        self.bms_connected = True

    def set_scenario(self, scenario: str):
        self.operating_scenario = scenario.upper()
        if self.operating_scenario == "BMS_DISCONNECTED":
            self.bms_connected = False
        else:
            self.bms_connected = True

    def generate_telemetry(self) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        if not self.bms_connected:
            return {"status": "BMS_DISCONNECTED", "timestamp": now, "telemetry": {}}

        # Base load factor
        if self.operating_scenario == "HIGH_LOAD" or self.operating_scenario == "HOT_DAY":
            load_factor = 0.88
            oat_c = 34.5
            wb_c = 26.0
        elif self.operating_scenario == "LOW_LOAD" or self.operating_scenario == "MILD_DAY":
            load_factor = 0.42
            oat_c = 19.5
            wb_c = 14.0
        elif self.operating_scenario == "MORNING_START":
            load_factor = 0.75
            oat_c = 22.0
            wb_c = 17.5
        else:
            load_factor = 0.65
            oat_c = 28.5
            wb_c = 21.0

        jitter = lambda base, pct=0.015: base * (1.0 + random.uniform(-pct, pct))

        # 1. AHU Supply Fan
        fan_speed_pct = jitter(72.0 * load_factor / 0.65)
        fan_speed_pct = max(35.0, min(100.0, fan_speed_pct))
        fan_hz = fan_speed_pct * 0.60 # 60 Hz max
        fan_flow_cfm = 10000.0 * (fan_speed_pct / 100.0)
        fan_dp_inwc = 1.80 * math.pow(fan_speed_pct / 100.0, 2)
        fan_kw = 18.4 * math.pow(fan_speed_pct / 100.0, 2.85)

        # 2. General HVAC Pump
        pump_speed_pct = jitter(75.0 * load_factor / 0.65)
        pump_hz = pump_speed_pct * 0.60
        pump_flow_gpm = 650.0 * (pump_speed_pct / 100.0)
        pump_dp_psi = 28.0 * math.pow(pump_speed_pct / 100.0, 2)
        pump_kw = 15.2 * math.pow(pump_speed_pct / 100.0, 2.9)

        # 3. CHW Pump
        chw_pump_speed_pct = jitter(70.0 * load_factor / 0.65)
        chw_hz = chw_pump_speed_pct * 0.60
        chw_flow_gpm = 800.0 * (chw_pump_speed_pct / 100.0)
        chw_dp_psi = 24.0 * math.pow(chw_pump_speed_pct / 100.0, 2)
        chw_pump_kw = 22.0 * math.pow(chw_pump_speed_pct / 100.0, 2.85)
        chws_temp = 6.7
        chwr_temp = chws_temp + (5.5 * load_factor / max(0.2, chw_pump_speed_pct / 100.0))

        # 4. Condenser Water Pump
        cw_pump_speed_pct = jitter(80.0 * load_factor / 0.65)
        cw_hz = cw_pump_speed_pct * 0.60
        cw_flow_gpm = 1100.0 * (cw_pump_speed_pct / 100.0)
        cw_dp_psi = 20.0 * math.pow(cw_pump_speed_pct / 100.0, 2)
        cw_pump_kw = 18.5 * math.pow(cw_pump_speed_pct / 100.0, 2.85)
        cws_temp = wb_c + 3.8 # Approach
        cwr_temp = cws_temp + (5.0 * load_factor / max(0.2, cw_pump_speed_pct / 100.0))

        # 5. Cooling Tower Fan
        ct_fan_speed_pct = jitter(68.0 * load_factor / 0.65)
        ct_hz = ct_fan_speed_pct * 0.60
        ct_fan_kw = 11.0 * math.pow(ct_fan_speed_pct / 100.0, 2.9)
        approach_c = 3.5 + (4.0 * (1.0 - ct_fan_speed_pct / 100.0))

        # Fault injection if scenario
        quality = "BAD" if self.operating_scenario == "SENSOR_FAULT" else "GOOD"

        return {
            "status": "ONLINE",
            "source": "SIMULATION",
            "scenario": self.operating_scenario,
            "timestamp": now,
            "weather": {"oat_c": round(oat_c, 1), "wet_bulb_c": round(wb_c, 1)},
            "fan": {
                "equipment_id": "AHU-FAN-01",
                "speed_pct": round(fan_speed_pct, 1),
                "frequency_hz": round(fan_hz, 1),
                "flow_cfm": round(fan_flow_cfm, 0),
                "static_pressure_inwc": round(fan_dp_inwc, 2),
                "power_kw": round(fan_kw, 2),
                "avg_vav_damper_pct": round(min(98.0, 62.0 / (fan_speed_pct / 72.0)), 1),
                "max_vav_damper_pct": 82.5,
                "critical_zones": 1,
                "quality": quality
            },
            "pump": {
                "equipment_id": "PUMP-GEN-01",
                "speed_pct": round(pump_speed_pct, 1),
                "frequency_hz": round(pump_hz, 1),
                "flow_gpm": round(pump_flow_gpm, 0),
                "differential_pressure_psi": round(pump_dp_psi, 1),
                "power_kw": round(pump_kw, 2),
                "valve_open_count": 18,
                "quality": quality
            },
            "chw_pump": {
                "equipment_id": "CHW-PUMP-01",
                "speed_pct": round(chw_pump_speed_pct, 1),
                "frequency_hz": round(chw_hz, 1),
                "flow_gpm": round(chw_flow_gpm, 0),
                "differential_pressure_psi": round(chw_dp_psi, 1),
                "power_kw": round(chw_pump_kw, 2),
                "chws_temp_c": round(chws_temp, 1),
                "chwr_temp_c": round(chwr_temp, 1),
                "delta_t_c": round(chwr_temp - chws_temp, 2),
                "chiller_load_pct": round(load_factor * 100.0, 1),
                "quality": quality
            },
            "condenser_pump": {
                "equipment_id": "CW-PUMP-01",
                "speed_pct": round(cw_pump_speed_pct, 1),
                "frequency_hz": round(cw_hz, 1),
                "flow_gpm": round(cw_flow_gpm, 0),
                "differential_pressure_psi": round(cw_dp_psi, 1),
                "power_kw": round(cw_pump_kw, 2),
                "cws_temp_c": round(cws_temp, 1),
                "cwr_temp_c": round(cwr_temp, 1),
                "delta_t_c": round(cwr_temp - cws_temp, 2),
                "quality": quality
            },
            "cooling_tower": {
                "equipment_id": "CT-FAN-01",
                "speed_pct": round(ct_fan_speed_pct, 1),
                "frequency_hz": round(ct_hz, 1),
                "power_kw": round(ct_fan_kw, 2),
                "approach_temp_c": round(approach_c, 1),
                "cws_target_temp_c": round(wb_c + approach_c, 1),
                "quality": quality
            },
            "air_cooled": {
                "equipment_id": "ACC-01",
                "oat_c": round(oat_c, 1),
                "rh_pct": round(min(90.0, 45.0 + wb_c), 1),
                "cond_temp_c": round(oat_c + 12.0, 1),
                "head_pressure_psig": round(155.0 + max(0.0, oat_c - 15.0) * 3.4, 1),
                "compressor_state": 1.0,
                "fan_state": 1.0,
                "fan_speed_pct": round(min(100.0, 40.0 + load_factor * 50.0), 1),
                "load_pct": round(load_factor * 100.0, 1),
                "power_kw": round(85.0 * load_factor, 2),
                "quality": quality,
            },
            "water_cooled": {
                "equipment_id": "CH-1",
                "cewt_c": round(cws_temp, 1),
                "clwt_c": round(cwr_temp, 1),
                "cw_flow_gpm": round(cw_flow_gpm, 0),
                "cond_temp_c": round(cwr_temp + 2.0, 1),
                "head_pressure_psig": round(140.0 + (cwr_temp - 24.0) * 4.0, 1),
                "tower_state": 1.0,
                "pump_state": 1.0,
                "load_pct": round(load_factor * 100.0, 1),
                "power_kw": round(120.0 * load_factor, 2),
                "quality": quality,
            },
        }

vs_simulator = VariableSpeedSimulator()
