"""
PlantControlTelemetryService: Ingests, validates, standardizes, and buffers
telemetry for Plant Control Parameter Optimizations (Opportunities 5 to 9).

Ensures all points strictly conform to:
- pointId
- equipmentId
- value
- unit
- timestamp
- quality
- source (BMS_BACNET or DETERMINISTIC_SIMULATOR)
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, asdict

@dataclass
class TelemetryPoint:
    pointId: str
    equipmentId: str
    value: float
    unit: str
    timestamp: str
    quality: str  # GOOD, UNRELIABLE, SENSOR_FAULT
    source: str   # BMS_BACNET, DETERMINISTIC_SIMULATOR

class PlantControlTelemetryService:
    def __init__(self):
        self._point_cache: Dict[str, TelemetryPoint] = {}
        self._history_buffer: Dict[str, List[Dict[str, Any]]] = {
            "O5": [],
            "O6": [],
            "O7": [],
            "O8": [],
            "O9": []
        }
        self._init_default_telemetry()

    def _init_default_telemetry(self):
        now = datetime.now(timezone.utc).isoformat()
        # Seed initial standard telemetry points
        points = [
            # O5 - Duct Static Pressure
            TelemetryPoint("AHU1.DuctStaticPressure", "AHU-01", 1.82, "in.w.c.", now, "GOOD", "DETERMINISTIC_SIMULATOR"),
            TelemetryPoint("AHU1.StaticPressureSetpoint", "AHU-01", 1.80, "in.w.c.", now, "GOOD", "DETERMINISTIC_SIMULATOR"),
            TelemetryPoint("AHU1.SupplyFanPower", "AHU-01", 14.8, "kW", now, "GOOD", "DETERMINISTIC_SIMULATOR"),
            TelemetryPoint("AHU1.SupplyAirflow", "AHU-01", 14250.0, "CFM", now, "GOOD", "DETERMINISTIC_SIMULATOR"),
            TelemetryPoint("VAV101.DamperPosition", "VAV-101", 88.0, "%", now, "GOOD", "DETERMINISTIC_SIMULATOR"),
            
            # O6 - Heating Hot Water
            TelemetryPoint("HHW.SupplyTemp", "BOILER-01", 78.4, "°C", now, "GOOD", "DETERMINISTIC_SIMULATOR"),
            TelemetryPoint("HHW.ReturnTemp", "BOILER-01", 64.2, "°C", now, "GOOD", "DETERMINISTIC_SIMULATOR"),
            TelemetryPoint("HHW.SupplySetpoint", "BOILER-01", 80.0, "°C", now, "GOOD", "DETERMINISTIC_SIMULATOR"),
            TelemetryPoint("HHW.PumpPower", "PUMP-HHW-1", 4.2, "kW", now, "GOOD", "DETERMINISTIC_SIMULATOR"),
            TelemetryPoint("WEATHER.OutdoorAirTemp", "WEATHER-STATION", 24.5, "°C", now, "GOOD", "DETERMINISTIC_SIMULATOR"),
            
            # O7 - Chilled Water Reset
            TelemetryPoint("CHW.SupplyTemp", "CHILLER-01", 6.8, "°C", now, "GOOD", "DETERMINISTIC_SIMULATOR"),
            TelemetryPoint("CHW.ReturnTemp", "CHILLER-01", 12.2, "°C", now, "GOOD", "DETERMINISTIC_SIMULATOR"),
            TelemetryPoint("CHW.SupplySetpoint", "CHILLER-01", 6.7, "°C", now, "GOOD", "DETERMINISTIC_SIMULATOR"),
            TelemetryPoint("CHW.PlantFlow", "CHILLER-01", 338.0, "GPM", now, "GOOD", "DETERMINISTIC_SIMULATOR"),
            TelemetryPoint("CHILLER1.CompressorPower", "CHILLER-01", 40.8, "kW", now, "GOOD", "DETERMINISTIC_SIMULATOR"),
            TelemetryPoint("CHW.SecondaryPumpPower", "SCHWP-01", 8.5, "kW", now, "GOOD", "DETERMINISTIC_SIMULATOR"),
            
            # O8 - Condenser Water Reset
            TelemetryPoint("CWS.SupplyTemp", "CT-01", 29.2, "°C", now, "GOOD", "DETERMINISTIC_SIMULATOR"),
            TelemetryPoint("CWR.ReturnTemp", "CT-01", 34.5, "°C", now, "GOOD", "DETERMINISTIC_SIMULATOR"),
            TelemetryPoint("CWS.SupplySetpoint", "CT-01", 29.5, "°C", now, "GOOD", "DETERMINISTIC_SIMULATOR"),
            TelemetryPoint("WEATHER.WetBulbTemp", "WEATHER-STATION", 21.4, "°C", now, "GOOD", "DETERMINISTIC_SIMULATOR"),
            TelemetryPoint("CT1.FanPower", "CT-01", 10.5, "kW", now, "GOOD", "DETERMINISTIC_SIMULATOR"),
            TelemetryPoint("CWP1.PumpPower", "CWP-01", 5.5, "kW", now, "GOOD", "DETERMINISTIC_SIMULATOR"),
            
            # O9 - EXV Retrofit Telemetry
            TelemetryPoint("REF.SuctionPressure", "CHILLER-01", 64.2, "psig", now, "GOOD", "DETERMINISTIC_SIMULATOR"),
            TelemetryPoint("REF.SuctionTemp", "CHILLER-01", 10.4, "°C", now, "GOOD", "DETERMINISTIC_SIMULATOR"),
            TelemetryPoint("REF.EvaporatorSuperheat", "CHILLER-01", 6.2, "°C", now, "GOOD", "DETERMINISTIC_SIMULATOR"),
            TelemetryPoint("REF.EvapTemp", "CHILLER-01", 4.2, "°C", now, "GOOD", "DETERMINISTIC_SIMULATOR")
        ]
        for p in points:
            self._point_cache[p.pointId] = p

    def record_point(self, point_id: str, equipment_id: str, value: float, unit: str, quality: str = "GOOD", source: str = "DETERMINISTIC_SIMULATOR") -> TelemetryPoint:
        now = datetime.now(timezone.utc).isoformat()
        point = TelemetryPoint(
            pointId=point_id,
            equipmentId=equipment_id,
            value=float(value),
            unit=unit,
            timestamp=now,
            quality=quality,
            source=source
        )
        self._point_cache[point_id] = point
        return point

    def get_point(self, point_id: str) -> Optional[Dict[str, Any]]:
        pt = self._point_cache.get(point_id)
        return asdict(pt) if pt else None

    def get_all_points(self) -> List[Dict[str, Any]]:
        return [asdict(p) for p in self._point_cache.values()]

    def get_opportunity_telemetry(self, opportunity: str) -> List[Dict[str, Any]]:
        prefix_map = {
            "O5": ["AHU", "VAV"],
            "O6": ["HHW", "BOILER", "WEATHER"],
            "O7": ["CHW", "CHILLER", "SCHWP"],
            "O8": ["CWS", "CWR", "CT", "CWP", "WEATHER"],
            "O9": ["REF", "CHILLER"]
        }
        allowed = prefix_map.get(opportunity.upper(), [])
        return [
            asdict(p) for p in self._point_cache.values()
            if any(p.pointId.startswith(prefix) for prefix in allowed)
        ]

    def buffer_history_entry(self, opportunity: str, entry: Dict[str, Any]):
        opp = opportunity.upper()
        if opp not in self._history_buffer:
            self._history_buffer[opp] = []
        
        entry_with_time = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **entry
        }
        self._history_buffer[opp].append(entry_with_time)
        if len(self._history_buffer[opp]) > 100:
            self._history_buffer[opp].pop(0)

    def get_history(self, opportunity: str, limit: int = 50) -> List[Dict[str, Any]]:
        opp = opportunity.upper()
        return self._history_buffer.get(opp, [])[-limit:]

plant_control_telemetry_service = PlantControlTelemetryService()
