"""Official O1–O20 catalog and API ID remaps.

Internal leftover engines keep their original physics modules. Public APIs use
these official numbers only:

  O10 Economy Cycle          <- enthalpy economizer (was leftover O12 engine)
  O11 Night Purge            <- official_opportunities.o11_night_purge
  O12 DCV CO₂ occupied       <- leftover DCV engine (was O11)
  O13 DCV CO carparks        <- official_opportunities.o13_dcv_co
  O14 Secondary CHW pumping  <- chw_pump_agent
  O15–O20                    <- official_opportunities
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

CATALOG: List[Tuple[str, int, str, str, str]] = [
    ("O1", 1, "scheduling", "Optimum Start/Stop Programming", "Thermodynamic pull-down trajectory and coasting stop."),
    ("O2", 2, "scheduling", "Space Temperature Set Points & Control Bands", "Occupancy-driven setpoint floating and deadband expansion."),
    ("O3", 3, "scheduling", "Master Air Handling Unit Supply Air Temperature Signal", "Guideline 36 trim and respond with rogue-zone isolation."),
    ("O4", 4, "scheduling", "Staging of Chillers & Compressors", "Thermal tonnage matching and CHWS reset."),
    ("O5", 5, "plant-control", "Duct Static Pressure Reset", "Trim-and-respond duct static pressure for fan kW reduction."),
    ("O6", 6, "plant-control", "Heating Hot Water Temperature Reset", "HHW loop temperature reset."),
    ("O7", 7, "plant-control", "Chilled Water Temperature Reset", "CHW loop temperature reset."),
    ("O8", 8, "plant-control", "Condenser Water Temperature Reset", "CW loop temperature reset."),
    ("O9", 9, "plant-control", "Retrofit of Electronic Expansion Valve", "TXV to EXV retrofit engineering assessment."),
    ("O10", 10, "ventilation", "Economy Cycle", "Enthalpy economizer outdoor-air free cooling."),
    ("O11", 11, "ventilation", "Night Purge", "Night-time outdoor-air purge of stored heat."),
    ("O12", 12, "ventilation", "Demand Control Ventilation — CO₂", "ASHRAE 62.1 CO₂-based outdoor air reset."),
    ("O13", 13, "ventilation", "Demand Control Ventilation — CO", "CO-based ventilation for carparks and loading docks."),
    ("O14", 14, "variable-speed", "Optimised Secondary Chilled Water Pumping", "Secondary CHW pump speed vs differential pressure."),
    ("O15", 15, "variable-speed", "Variable Head Pressure — Air-Cooled", "Air-cooled condenser head-pressure control."),
    ("O16", 16, "variable-speed", "Variable Head Pressure — Water-Cooled", "Water-cooled condenser head-pressure control."),
    ("O17", 17, "operations", "Energy Management Planning", "Energy management planning and governance."),
    ("O18", 18, "operations", "Energy Management Training & Awareness", "Operator training and energy awareness."),
    ("O19", 19, "operations", "Energy Efficiency Maintenance", "Efficiency-focused maintenance practices."),
    ("O20", 20, "operations", "Management of System Control Software", "Control-software versioning and change control."),
]

OFFICIAL_VENT_IDS = ("O10", "O11", "O12", "O13")
DEPRECATED_VENT_IDS: tuple[str, ...] = ()
OFFICIAL_VS_IDS = ("O14", "O15", "O16")
OFFICIAL_OM_IDS = ("O17", "O18", "O19", "O20")

SIM_SOURCE = "SIMULATION"


def stamp_official(result: Dict[str, Any], oid: str, name: str) -> Dict[str, Any]:
    out = dict(result)
    out["opportunity_id"] = oid
    out["opportunity_code"] = oid
    out["opportunity_name"] = name
    out["source"] = out.get("source") or SIM_SOURCE
    if "live" not in out:
        out["live"] = False
    return out


def card_from_engine(result: Dict[str, Any], route: str, live_fields: bool = False) -> Dict[str, Any]:
    live = bool(result.get("live")) and live_fields
    return {
        "opportunity_id": result.get("opportunity_id"),
        "opportunity_name": result.get("opportunity_name"),
        "route": route,
        "current_value": result.get("current_value") if live else None,
        "optimized_value": result.get("optimized_value") if live else None,
        "current_airflow": None,
        "optimized_airflow": None,
        "fan_power": None,
        "energy_impact": result.get("energy_impact") if live else None,
        "comfort_iaq_impact": None,
        "confidence": result.get("confidence") if live else None,
        "status": "OPTIMAL" if live else "AWAITING_TELEMETRY",
        "live": live,
        "source": result.get("source") or SIM_SOURCE,
        "potential_kw_savings": result.get("expected_power_saving_kw") if live else None,
        "potential_kwh_day_savings": result.get("expected_energy_saving_kwh_day") if live else None,
    }


def card_from_official(state: Dict[str, Any], oid: str, name: str, route: str) -> Dict[str, Any]:
    live = bool(state.get("live"))
    current = state.get("current_value")
    if current is None and isinstance(state.get("current_state"), dict):
        cs = state["current_state"]
        current = cs.get("current_value") or cs.get("oa_damper_pct") or cs.get("co_ppm") or cs.get("head_pressure") or cs.get("current_energy_kw")
    optimized = state.get("optimized_value")
    if optimized is None and isinstance(state.get("optimized_state"), dict):
        os_ = state["optimized_state"]
        optimized = os_.get("optimized_value") or os_.get("target_kw")
    return {
        "opportunity_id": oid,
        "opportunity_name": name,
        "route": route,
        "current_value": current if live else None,
        "optimized_value": optimized if live else None,
        "energy_impact": state.get("energy_impact") if live else None,
        "confidence": state.get("confidence") if live else None,
        "status": state.get("status") or ("OPTIMAL" if live else "AWAITING_TELEMETRY"),
        "live": live,
        "source": None if live else SIM_SOURCE,
        "potential_kw_savings": state.get("energy_impact") if live else None,
        "potential_kwh_day_savings": None,
    }


def catalog_entry(oid: str) -> Optional[Tuple[str, int, str, str, str]]:
    for row in CATALOG:
        if row[0] == oid:
            return row
    return None
