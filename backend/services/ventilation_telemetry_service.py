"""
VentilationTelemetryService: Ingestion, validation, and real-time normalization
for all Ventilation & Air Flow sensor points across AHUs, VAVs, fans, dampers, and IAQ CO2 meters.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import random

class VentilationTelemetryService:
    def __init__(self):
        self.points: Dict[str, Dict[str, Any]] = {
            "AHU-01.SupplyAirflow": {"value": 7800.0, "unit": "CFM", "quality": "GOOD", "source": "SIMULATION", "type": "AIRFLOW"},
            "AHU-01.ReturnAirflow": {"value": 7350.0, "unit": "CFM", "quality": "GOOD", "source": "SIMULATION", "type": "AIRFLOW"},
            "AHU-01.OutdoorAirflow": {"value": 2400.0, "unit": "CFM", "quality": "GOOD", "source": "SIMULATION", "type": "AIRFLOW"},
            "AHU-01.ExhaustAirflow": {"value": 850.0, "unit": "CFM", "quality": "GOOD", "source": "SIMULATION", "type": "AIRFLOW"},
            "AHU-01.SupplyFanSpeed": {"value": 1450.0, "unit": "RPM", "quality": "GOOD", "source": "SIMULATION", "type": "SPEED"},
            "AHU-01.SupplyFanVFD": {"value": 54.0, "unit": "Hz", "quality": "GOOD", "source": "SIMULATION", "type": "FREQUENCY"},
            "AHU-01.SupplyFanPower": {"value": 8.4, "unit": "kW", "quality": "GOOD", "source": "SIMULATION", "type": "POWER"},
            "AHU-01.ReturnFanPower": {"value": 4.2, "unit": "kW", "quality": "GOOD", "source": "SIMULATION", "type": "POWER"},
            "AHU-01.DuctStaticPressure": {"value": 1.45, "unit": "in.w.c.", "quality": "GOOD", "source": "SIMULATION", "type": "PRESSURE"},
            "AHU-01.BuildingDiffPressure": {"value": 0.012, "unit": "in.w.c.", "quality": "GOOD", "source": "SIMULATION", "type": "PRESSURE"},
            "AHU-01.OutdoorAirDamper": {"value": 20.0, "unit": "%", "quality": "GOOD", "source": "SIMULATION", "type": "DAMPER"},
            "AHU-01.ReturnAirDamper": {"value": 80.0, "unit": "%", "quality": "GOOD", "source": "SIMULATION", "type": "DAMPER"},
            "AHU-01.SupplyAirTemp": {"value": 13.8, "unit": "°C", "quality": "GOOD", "source": "SIMULATION", "type": "TEMPERATURE"},
            "AHU-01.ReturnAirTemp": {"value": 24.0, "unit": "°C", "quality": "GOOD", "source": "SIMULATION", "type": "TEMPERATURE"},
            "AHU-01.MixedAirTemp": {"value": 22.7, "unit": "°C", "quality": "GOOD", "source": "SIMULATION", "type": "TEMPERATURE"},
            "WEATHER.OutdoorDryBulb": {"value": 17.5, "unit": "°C", "quality": "GOOD", "source": "SIMULATION", "type": "TEMPERATURE"},
            "WEATHER.OutdoorRH": {"value": 52.0, "unit": "%", "quality": "GOOD", "source": "SIMULATION", "type": "HUMIDITY"},
            "ZONE.AvgCO2": {"value": 560.0, "unit": "ppm", "quality": "GOOD", "source": "SIMULATION", "type": "CO2"},
            "ZONE.MaxCO2": {"value": 640.0, "unit": "ppm", "quality": "GOOD", "source": "SIMULATION", "type": "CO2"},
            "ZONE.OutdoorCO2": {"value": 415.0, "unit": "ppm", "quality": "GOOD", "source": "SIMULATION", "type": "CO2"},
            "ZONE.OccupantCount": {"value": 68.0, "unit": "Persons", "quality": "GOOD", "source": "SIMULATION", "type": "COUNT"},
            "ZONE.AvgTemp": {"value": 25.8, "unit": "°C", "quality": "GOOD", "source": "SIMULATION", "type": "TEMPERATURE"},
            "AHU-01.SupplyFanState": {"value": 1.0, "unit": "bool", "quality": "GOOD", "source": "SIMULATION", "type": "STATE"},
            "AHU-01.EconomizerEnable": {"value": 1.0, "unit": "bool", "quality": "GOOD", "source": "SIMULATION", "type": "STATE"},
            "AHU-01.PurgeState": {"value": 0.0, "unit": "bool", "quality": "GOOD", "source": "SIMULATION", "type": "STATE"},
            "PARK.CO": {"value": 12.5, "unit": "ppm", "quality": "GOOD", "source": "SIMULATION", "type": "CO"},
            "PARK.FanState": {"value": 1.0, "unit": "bool", "quality": "GOOD", "source": "SIMULATION", "type": "STATE"},
            "PARK.FanSpeed": {"value": 35.0, "unit": "%", "quality": "GOOD", "source": "SIMULATION", "type": "SPEED"},
            "PARK.Damper": {"value": 30.0, "unit": "%", "quality": "GOOD", "source": "SIMULATION", "type": "DAMPER"},
            "PARK.Airflow": {"value": 4200.0, "unit": "CFM", "quality": "GOOD", "source": "SIMULATION", "type": "AIRFLOW"},
        }

    def get_all_points(self) -> Dict[str, Any]:
        """Returns in-memory SIMULATION points. Dataset mode may read them; they are never LIVE_BMS."""
        now = datetime.now(timezone.utc)
        hour = now.hour
        try:
            from zoneinfo import ZoneInfo
            hour = datetime.now(ZoneInfo("Asia/Kolkata")).hour
        except Exception:
            pass
        night = hour >= 21 or hour < 6
        now_iso = now.isoformat()
        res = {}
        for k, v in self.points.items():
            value = v["value"]
            if k == "ZONE.OccupantCount":
                value = 2.0 if night else v["value"]
            elif k == "WEATHER.OutdoorDryBulb" and night:
                value = min(v["value"], 22.1)
            elif k == "AHU-01.OutdoorAirDamper" and night:
                value = max(v["value"], 42.0)
            jitter = random.uniform(-0.02, 0.02) * (value if value else 1.0)
            res[k] = {
                "point_id": k,
                "value": round(value + jitter, 2),
                "unit": v["unit"],
                "quality": v["quality"],
                "source": v["source"],
                "type": v["type"],
                "timestamp": now_iso,
                "freshness_seconds": 1.2
            }
        return res

    def get_opportunity_telemetry(self, opp_code: str) -> Dict[str, Any]:
        """Returns filtered telemetry relevant to a specific opportunity."""
        all_pts = self.get_all_points()
        if opp_code == "O10":
            keys = ["WEATHER.OutdoorDryBulb", "WEATHER.OutdoorRH", "AHU-01.ReturnAirTemp", "AHU-01.MixedAirTemp", "AHU-01.OutdoorAirDamper", "AHU-01.EconomizerEnable"]
        elif opp_code == "O11":
            keys = ["WEATHER.OutdoorDryBulb", "WEATHER.OutdoorRH", "ZONE.AvgTemp", "AHU-01.ReturnAirTemp", "AHU-01.SupplyAirTemp", "AHU-01.OutdoorAirDamper", "AHU-01.SupplyFanState", "ZONE.OccupantCount", "AHU-01.PurgeState"]
        elif opp_code == "O12":
            keys = ["AHU-01.OutdoorAirflow", "ZONE.AvgCO2", "ZONE.MaxCO2", "ZONE.OutdoorCO2", "ZONE.OccupantCount"]
        elif opp_code == "O13":
            keys = ["PARK.CO", "PARK.FanState", "PARK.FanSpeed", "PARK.Damper", "PARK.Airflow"]
        else:
            keys = list(all_pts.keys())
        return {k: all_pts[k] for k in keys if k in all_pts}

ventilation_telemetry_service = VentilationTelemetryService()
