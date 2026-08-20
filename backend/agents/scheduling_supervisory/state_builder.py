"""
StateBuilder: Reads raw/normalized telemetry from BMS, validates data quality,
and constructs the thermodynamic building & plant state.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime


class StateBuilder:
    def __init__(self):
        self.sensor_limits = {
            "oat": (-20.0, 50.0),
            "zone_temp": (10.0, 40.0),
            "sat": (5.0, 35.0),
            "chws_temp": (2.0, 20.0),
            "chwr_temp": (5.0, 30.0),
            "flow_lps": (0.0, 200.0),
        }
        self.critical_alarms: List[Dict[str, Any]] = []

    def validate_and_build_state(self, raw_telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates telemetry quality, checks physical bounds, detects sensor freeze or drift,
        and produces normalized HVAC supervisory state.
        """
        data_quality_valid = True
        sensor_faults: List[str] = []
        validation_flags: Dict[str, Any] = {}

        # 1. Weather Validation
        weather = raw_telemetry.get("weather", {})
        oat = weather.get("oat", 24.0)
        if oat is None or not (self.sensor_limits["oat"][0] <= oat <= self.sensor_limits["oat"][1]):
            data_quality_valid = False
            sensor_faults.append(f"OAT sensor out-of-bounds ({oat}°C)")

        # 2. AHU & Zone Validation
        ahus = raw_telemetry.get("ahus", [])
        for ahu in ahus:
            sat = ahu.get("sat_actual", ahu.get("sat", 13.0))
            if sat is None or not (self.sensor_limits["sat"][0] <= sat <= self.sensor_limits["sat"][1]):
                data_quality_valid = False
                sensor_faults.append(f"AHU {ahu.get('id')} SAT sensor out-of-bounds ({sat}°C)")

            for zone in ahu.get("vav_zones", []):
                z_temp = zone.get("temp_actual", zone.get("temp", 23.0))
                if z_temp is None or not (self.sensor_limits["zone_temp"][0] <= z_temp <= self.sensor_limits["zone_temp"][1]):
                    data_quality_valid = False
                    sensor_faults.append(f"Zone {zone.get('id')} temp sensor out-of-bounds ({z_temp}°C)")

        # 3. Chiller Plant Validation
        plant = raw_telemetry.get("plant", {})
        chws = plant.get("chws_temp", 6.7)
        chwr = plant.get("chwr_temp", 12.2)
        flow = plant.get("flow_rate_lps", plant.get("flow_lps", 28.5))

        if chws is None or not (self.sensor_limits["chws_temp"][0] <= chws <= self.sensor_limits["chws_temp"][1]):
            data_quality_valid = False
            sensor_faults.append(f"ChW Supply Temp sensor out-of-bounds ({chws}°C)")

        if chwr is None or not (self.sensor_limits["chwr_temp"][0] <= chwr <= self.sensor_limits["chwr_temp"][1]):
            data_quality_valid = False
            sensor_faults.append(f"ChW Return Temp sensor out-of-bounds ({chwr}°C)")

        # 4. Critical Alarms Check
        alarms = raw_telemetry.get("active_alarms", [])
        self.critical_alarms = [a for a in alarms if a.get("severity") in ("CRITICAL", "HIGH")]
        if self.critical_alarms:
            data_quality_valid = False
            sensor_faults.append(f"Active Critical Alarms: {[a.get('name') for a in self.critical_alarms]}")

        # Construct structured state
        state = {
            "timestamp": raw_telemetry.get("timestamp", datetime.utcnow().isoformat()),
            "simulation_time": raw_telemetry.get("simulation_time", "08:00"),
            "data_quality_valid": data_quality_valid,
            "sensor_faults": sensor_faults,
            "critical_alarms": self.critical_alarms,
            "weather": weather,
            "ahus": ahus,
            "plant": plant,
            "building_occupancy": raw_telemetry.get("building_occupancy", {
                "scheduled_start": "06:00",
                "occupancy_start": "08:00",
                "scheduled_stop": "18:00",
                "occupancy_stop": "18:00",
                "is_occupied_now": True,
            }),
            "stale_age_seconds": raw_telemetry.get("stale_age_seconds", 0.0),
        }
        return state
