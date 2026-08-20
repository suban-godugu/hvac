"""Explicit dataset → opportunity maps. No silent column inference. No O10 model."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

AGENT_FOR = {
    "O1": "scheduling",
    "O2": "scheduling",
    "O3": "scheduling",
    "O4": "scheduling",
    "O5": "plant-control",
    "O6": "plant-control",
    "O7": "plant-control",
    "O8": "plant-control",
    "O9": "plant-control",
    "O11": "ventilation",
    "O12": "ventilation",
    "O13": "ventilation",
    "O14": "variable-speed",
    "O15": "variable-speed",
    "O16": "variable-speed",
    "O17": "operations",
    "O18": "operations",
    "O19": "operations",
    "O20": "operations",
}


def _map(
    dataset_id: str,
    opportunity_id: str,
    file_name: str | None,
    feature_map: Dict[str, str],
    target_column: str | None,
    task_type: str,
    training_allowed: bool,
    status: str,
    notes: str,
    join_files: Optional[List[str]] = None,
    loader: str = "csv",
    missing_dataset: Optional[str] = None,
) -> Dict[str, Any]:
    stored_file = file_name
    if join_files:
        stored_file = "+".join(join_files)
    return {
        "dataset_id": dataset_id,
        "opportunity_id": opportunity_id,
        "agent_id": AGENT_FOR[opportunity_id],
        "file_name": stored_file,
        "join_files": join_files,
        "loader": loader,
        "feature_map": feature_map,
        "target_column": target_column,
        "task_type": task_type,
        "training_allowed": training_allowed,
        "status": status,
        "notes": notes,
        "missing_dataset": missing_dataset,
    }


# Measured plant-response / classification targets only. No invented optimal setpoints.
OPPORTUNITY_MAPS: List[Dict[str, Any]] = [
    _map(
        "ds_archive_6",
        "O1",
        "RTU.csv",
        {
            "occupancy": "Occupancy Mode Indicator",
            "sat": "RTU: Supply Air Temperature",
            "rat": "RTU: Return Air Temperature",
        },
        "HVAC System: Electricity",
        "regression",
        True,
        "TRAINABLE",
        "Measured HVAC electricity vs occupancy/SAT/RAT. Not a labelled optimum-start schedule.",
    ),
    _map(
        "ds_archive",
        "O2",
        None,
        {
            "cooling_setpoint": "zone_016_cooling_sp",
            "outdoor_temperature": "air_temp_set_1",
            "hw_valve": "zone_016_hw_valve",
        },
        "zone_016_temp",
        "regression",
        True,
        "TRAINABLE",
        "Building 59 measured zone temperature vs cooling setpoint, outdoor air, and HW valve. Not a labelled optimal deadband.",
        join_files=["zone_temp_exterior.csv", "zone_temp_sp_c.csv", "site_weather.csv", "uft_hw_valve.csv"],
    ),
    _map(
        "ds_archive_6",
        "O3",
        "MZVAV-1.csv",
        {
            "oat": "AHU: Outdoor Air Temperature",
            "rat": "AHU: Return Air Temperature",
            "mat": "AHU: Mixed Air Temperature",
            "occupancy": "Occupancy Mode Indicator",
            "cooling_valve": "AHU: Cooling Coil Valve Control Signal",
            "heating_valve": "AHU: Heating Coil Valve Control Signal",
            "fan_speed": "AHU: Supply Air Fan Speed Control Signal",
        },
        "AHU: Supply Air Temperature",
        "regression",
        True,
        "TRAINABLE",
        "Plant-response SAT given OAT/valves/occupancy. Not a labelled optimal SAT reset.",
    ),
    _map(
        "ds_archive_4",
        "O4",
        "HVAC Energy Data.csv",
        {
            "chw_flow": "Chilled Water Rate (L/sec)",
            "cw_temperature": "Cooling Water Temperature (C)",
            "cooling_load": "Building Load (RT)",
            "outdoor_temperature": "Outside Temperature (F)",
            "humidity": "Humidity (%)",
            "dew_point": "Dew Point (F)",
        },
        "Chiller Energy Consumption (kWh)",
        "regression",
        True,
        "TRAINABLE",
        "Measured chiller kWh vs load/weather/flow. Predicts expected_kw, not stage count.",
    ),
    _map(
        "ds_archive_6",
        "O5",
        "MZVAV-1.csv",
        {
            "fan_speed": "AHU: Supply Air Fan Speed Control Signal",
            "occupancy": "Occupancy Mode Indicator",
            "oat": "AHU: Outdoor Air Temperature",
            "static_pressure_setpoint": "AHU: Supply Air Duct Static Pressure Set Point",
        },
        "AHU: Supply Air Duct Static Pressure",
        "regression",
        True,
        "TRAINABLE",
        "Measured duct static vs fan/occupancy/setpoint. Not an optimal floating-static label.",
    ),
    _map(
        "ds_archive",
        "O6",
        "ashp_hw.csv",
        {
            "hhw_return": "aru_001_hwr_temp",
            "hhw_flow": "aru_001_hws_fr_gpm",
        },
        "aru_001_hws_temp",
        "regression",
        True,
        "TRAINABLE",
        "Building 59 ASHP heating-water supply temperature vs return/flow. Not a labelled HHW reset schedule.",
    ),
    _map(
        "ds_archive",
        "O7",
        "ashp_cw.csv",
        {
            "chw_return": "aru_001_cwr_temp",
            "chw_flow": "aru_001_cws_fr_gpm",
        },
        "aru_001_cws_temp",
        "regression",
        True,
        "TRAINABLE",
        "Building 59 ASHP chilled-water supply temperature vs return/flow. Not a labelled CHWS reset schedule.",
    ),
    _map(
        "ds_archive_4",
        "O8",
        "HVAC Energy Data.csv",
        {
            "cooling_load": "Building Load (RT)",
            "outdoor_temperature": "Outside Temperature (F)",
            "humidity": "Humidity (%)",
        },
        "Cooling Water Temperature (C)",
        "regression",
        True,
        "TRAINABLE",
        "Measured condenser-water temperature vs load/weather. Not a labelled tower setpoint.",
    ),
    _map(
        "ds_archive_6",
        "O9",
        "RTU.csv",
        {
            "discharge_pressure": "RTU: Circuit 1 Discharge Pressure",
            "condenser_outlet_t": "RTU: Circuit 1 Condenser Outlet Temperature",
            "occupancy": "Occupancy Mode Indicator",
        },
        "RTU: Circuit 1 Suction Temperature",
        "regression",
        True,
        "TRAINABLE",
        "Measured suction temperature vs head/condenser. No EXV position column — circuit response only.",
    ),
    _map(
        "ds_archive_6",
        "O11",
        "MZVAV-1.csv",
        {
            "oat": "AHU: Outdoor Air Temperature",
            "occupancy": "Occupancy Mode Indicator",
            "sat": "AHU: Supply Air Temperature",
        },
        "AHU: Outdoor Air Damper Control Signal  ",
        "regression",
        True,
        "TRAINABLE",
        "Measured OA damper signal vs OAT/occupancy/SAT. Not a labelled night-purge window.",
    ),
    _map(
        "ds_archive_8",
        "O12",
        "room_occupancy_detection_data.csv",
        {
            "co2": "indoor_co2_concentration",
            "zone_temperature": "indoor_operative_temperature",
            "humidity": "indoor_relative_humidity",
            "hour": "hour_of_the_day",
            "day_of_week": "day_number_of_the_week",
        },
        "occupancy_ground_truth",
        "classification",
        True,
        "TRAINABLE",
        "Occupancy classification from CO2/T/RH. Not a legal OA-flow setpoint.",
    ),
    _map(
        "ds_archive_7",
        "O13",
        "2024-12-01_2024-12-09.json",
        {"co_ppm": "MQ7_CO_ppm", "co2_ppm": "CO2_ppm"},
        None,
        "none",
        False,
        "MODEL_NOT_TRAINABLE",
        "Archive 7 JSON is one sensor per row; CO, people, and airflow are not aligned on the same record.",
        missing_dataset="Need a flattened CO-DCV table: timestamp, CO_ppm, exhaust_or_OA_flow, occupancy. Archive 7 has MQ7_CO_ppm / no_people / CO2_ppm but not on the same JSON row and has no airflow target.",
    ),
    _map(
        "ds_archive_4",
        "O14",
        "HVAC Energy Data.csv",
        {
            "cooling_load": "Building Load (RT)",
            "outdoor_temperature": "Outside Temperature (F)",
            "cw_temperature": "Cooling Water Temperature (C)",
        },
        "Chilled Water Rate (L/sec)",
        "regression",
        True,
        "TRAINABLE",
        "Measured CHW flow vs load/weather. No pump speed or 95% valve-position columns.",
    ),
    _map(
        "ds_archive_6",
        "O15",
        "RTU.csv",
        {
            "condenser_outlet_t": "RTU: Circuit 1 Condenser Outlet Temperature",
            "occupancy": "Occupancy Mode Indicator",
            "sat": "RTU: Supply Air Temperature",
        },
        "RTU: Circuit 1 Discharge Pressure",
        "regression",
        True,
        "TRAINABLE",
        "Measured air-cooled circuit discharge pressure vs condenser outlet/SAT. Not a labelled floating head-pressure setpoint.",
    ),
    _map(
        "ds_archive",
        "O16",
        None,
        {
            "chw_return": "aru_001_cwr_temp",
            "chw_flow": "aru_001_cws_fr_gpm",
            "chw_supply": "aru_001_cws_temp",
        },
        "aru_001_power_mbtuph",
        "regression",
        True,
        "TRAINABLE",
        "Building 59 ASHP thermal power vs water temperatures/flow. Closest water-side plant response; not condenser-fan VFD head pressure.",
        join_files=["ashp_cw.csv", "ashp_meter.csv"],
    ),
    _map(
        "ds_archive_4",
        "O17",
        "HVAC Energy Data.csv",
        {
            "cooling_load": "Building Load (RT)",
            "outdoor_temperature": "Outside Temperature (F)",
            "humidity": "Humidity (%)",
        },
        "Chiller Energy Consumption (kWh)",
        "regression",
        True,
        "TRAINABLE",
        "Energy baseline: chiller kWh vs load and weather.",
    ),
    _map(
        "ds_archive_8",
        "O18",
        "room_occupancy_detection_data.csv",
        {"occupancy": "occupancy_ground_truth"},
        None,
        "none",
        False,
        "MODEL_NOT_TRAINABLE",
        "Occupancy labels exist, but there are no operator-training completion / awareness-action columns.",
        missing_dataset="Need a training-records dataset: session_id, staff_id, course_completed, timestamp, HVAC-action taken. Not present in Kaggle archives.",
    ),
    _map(
        "ds_archive_6",
        "O19",
        "MZVAV-1.csv",
        {
            "sat": "AHU: Supply Air Temperature",
            "sat_sp": "AHU: Supply Air Temperature Set Point",
            "oat": "AHU: Outdoor Air Temperature",
            "fan_speed": "AHU: Supply Air Fan Speed Control Signal",
            "static_pressure": "AHU: Supply Air Duct Static Pressure",
            "occupancy": "Occupancy Mode Indicator",
        },
        "Fault Detection Ground Truth",
        "classification",
        True,
        "TRAINABLE",
        "FDD ground-truth labels on AHU operation. Maintenance classification only — no HVAC write.",
    ),
    _map(
        "ds_archive",
        "O20",
        None,
        {},
        None,
        "none",
        False,
        "MODEL_NOT_TRAINABLE",
        "No BMS firmware, change-request, or override-log columns in these archives.",
        missing_dataset="Need a controls-change dataset: firmware_version, change_request_id, override_point, operator, timestamp, rollback. Not present in Kaggle archives.",
    ),
]


# O10 is intentionally unmapped (no Economy Cycle ML model).
O10_MISSING_DATASET = (
    "O10 has no ML model by product rule. Unused Building 59 files that are NOT trained: "
    "rtu_econ_sp.csv, rtu_oa_damper.csv, rtu_ma_t.csv, rtu_ra_t.csv, rtu_oa_t.csv."
)


def maps_for_opportunity(oid: str) -> List[Dict[str, Any]]:
    return [m for m in OPPORTUNITY_MAPS if m["opportunity_id"] == oid]


def trainable_maps() -> List[Dict[str, Any]]:
    return [m for m in OPPORTUNITY_MAPS if m["training_allowed"] and m["target_column"]]


def missing_dataset_for(oid: str) -> Optional[str]:
    if oid == "O10":
        return O10_MISSING_DATASET
    maps = maps_for_opportunity(oid)
    if not maps:
        return "No dataset mapped."
    return maps[0].get("missing_dataset")
