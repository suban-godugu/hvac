"""Publish SIMULATION-sourced canonical points when HVAC_BMS_MODE=simulation.

Never stamps LIVE_BMS. Header TEL stays SIMULATED by design.
"""
from __future__ import annotations

import math
import threading
import time
from typing import Dict, List, Optional, Tuple

from backend.bms.connection_manager import is_simulation_mode
from backend.services.canonical_telemetry_service import record_point
from backend.services.opportunity_feature_catalog import CATALOG

_STOP = threading.Event()
_THREAD: Optional[threading.Thread] = None

_UNITS: Dict[str, Optional[str]] = {
    "zone_temperature": "°C",
    "outdoor_air_temperature": "°C",
    "supply_air_temperature": "°C",
    "return_air_temperature": "°C",
    "sat_setpoint": "°C",
    "cooling_setpoint": "°C",
    "heating_setpoint": "°C",
    "chw_supply_temperature": "°C",
    "chw_return_temperature": "°C",
    "chw_supply_setpoint": "°C",
    "hhw_supply_temperature": "°C",
    "hhw_return_temperature": "°C",
    "hhw_setpoint": "°C",
    "cw_supply_temperature": "°C",
    "cw_return_temperature": "°C",
    "cw_setpoint": "°C",
    "suction_temperature": "°C",
    "condenser_water_temperature": "°C",
    "fan_speed": "%",
    "oa_damper": "%",
    "speed": "%",
    "heating_demand": "%",
    "occupancy": None,
    "enable": None,
    "status": None,
    "load": "tons",
    "cooling_load": "tons",
    "duct_static_pressure": "in.w.c.",
    "static_setpoint": "in.w.c.",
    "differential_pressure": "kPa",
    "flow": "L/s",
    "co2": "ppm",
    "co_ppm": "ppm",
    "head_pressure": "kPa",
    "discharge_pressure": "kPa",
    "energy": "kWh",
    "runtime": "h",
    "alarms": None,
}

_BASE: Dict[str, float] = {
    "zone_temperature": 24.2,
    "outdoor_air_temperature": 26.1,
    "supply_air_temperature": 13.8,
    "return_air_temperature": 24.0,
    "sat_setpoint": 13.0,
    "cooling_setpoint": 24.0,
    "heating_setpoint": 21.0,
    "chw_supply_temperature": 7.2,
    "chw_return_temperature": 12.4,
    "chw_supply_setpoint": 7.0,
    "hhw_supply_temperature": 52.0,
    "hhw_return_temperature": 42.0,
    "hhw_setpoint": 50.0,
    "cw_supply_temperature": 29.0,
    "cw_return_temperature": 34.0,
    "cw_setpoint": 29.5,
    "suction_temperature": 4.5,
    "condenser_water_temperature": 31.0,
    "fan_speed": 68.0,
    "oa_damper": 42.0,
    "speed": 62.0,
    "heating_demand": 18.0,
    "occupancy": 1.0,
    "enable": 1.0,
    "status": 1.0,
    "load": 183.0,
    "cooling_load": 183.0,
    "duct_static_pressure": 1.35,
    "static_setpoint": 1.40,
    "differential_pressure": 85.0,
    "flow": 28.0,
    "co2": 780.0,
    "co_ppm": 4.0,
    "head_pressure": 1180.0,
    "discharge_pressure": 1450.0,
    "energy": 412.0,
    "runtime": 6.4,
    "alarms": 0.0,
}


def _catalog_points() -> List[Tuple[str, str, str]]:
    seen = set()
    rows: List[Tuple[str, str, str]] = []
    for spec in CATALOG.values():
        for req in spec.get("required") or []:
            eq = req["equipment_id"]
            canon = req["canonical_point"]
            key = (eq, canon)
            if key in seen:
                continue
            seen.add(key)
            rows.append((eq, canon, f"{eq}.{canon}"))
    return rows


def publish_once() -> int:
    from backend.services.weather_service import weather_service

    weather = weather_service.snapshot()
    oat = weather.get("oat")
    n = 0
    drift = math.sin(time.time() / 40.0) * 0.04
    for eq, canon, pid in _catalog_points():
        base = _BASE.get(canon, 1.0)
        if canon == "outdoor_air_temperature" and oat is not None:
            value = float(oat)
        elif canon in ("enable", "status", "occupancy", "alarms"):
            value = base
        else:
            value = round(base * (1.0 + drift), 3)
        record_point(
            point_id=pid,
            value=value,
            unit=_UNITS.get(canon),
            source="SIMULATION",
            quality="GOOD",
            equipment_id=eq,
        )
        n += 1
    return n


def _loop(interval: float) -> None:
    while not _STOP.is_set():
        try:
            if is_simulation_mode():
                publish_once()
        except Exception:
            pass
        _STOP.wait(interval)


def start_simulation_telemetry(interval: float = 8.0) -> None:
    global _THREAD
    if not is_simulation_mode():
        return
    if _THREAD and _THREAD.is_alive():
        return
    _STOP.clear()
    try:
        publish_once()
    except Exception:
        pass
    _THREAD = threading.Thread(target=_loop, args=(max(5.0, interval),), name="sim-telemetry", daemon=True)
    _THREAD.start()


def stop_simulation_telemetry() -> None:
    _STOP.set()
