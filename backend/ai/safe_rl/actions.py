"""Discrete Safe-RL action catalog with O1–O16 mapping."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

DEFAULT_POINT_MAP: Dict[str, str] = {
    "zone_cooling_setpoint": "ZONE-01.cooling_setpoint",
    "ahu_sat": "AHU-01-SAT-SP",
    "duct_static": "AHU-01.DuctStaticPressureSetpoint",
    "chws": "PLANT-CHWS-SP",
    "schw_dp": "SCHW.DPSetpoint",
    "cw_pump": "CW.PumpSpeed",
}


@dataclass(frozen=True)
class SafeRlAction:
    action_id: str
    opportunity: Optional[str]
    point_key: Optional[str]
    delta: Optional[float]
    equipment_id: Optional[str]
    label: str

    @property
    def is_hold(self) -> bool:
        return self.action_id == "hold"


def point_map() -> Dict[str, str]:
    raw = os.getenv("HVAC_SAFE_RL_POINT_MAP_JSON")
    if raw:
        try:
            override = json.loads(raw)
            if isinstance(override, dict):
                merged = dict(DEFAULT_POINT_MAP)
                merged.update({str(k): str(v) for k, v in override.items()})
                return merged
        except Exception:
            pass
    return dict(DEFAULT_POINT_MAP)


def action_catalog() -> List[SafeRlAction]:
    return [
        SafeRlAction("hold", None, None, None, None, "Hold — no change"),
        SafeRlAction("zone_sp_down_0.5", "O2", "zone_cooling_setpoint", -0.5, "ZONE-01", "Zone cooling SP −0.5 °C"),
        SafeRlAction("zone_sp_up_0.5", "O2", "zone_cooling_setpoint", 0.5, "ZONE-01", "Zone cooling SP +0.5 °C"),
        SafeRlAction("sat_warmer_0.5", "O3", "ahu_sat", 0.5, "AHU-01", "SAT warmer +0.5 °C"),
        SafeRlAction("sat_cooler_0.5", "O3", "ahu_sat", -0.5, "AHU-01", "SAT cooler −0.5 °C"),
        SafeRlAction("static_down_0.1", "O5", "duct_static", -0.1, "AHU-01", "Duct static −0.1 in.wc"),
        SafeRlAction("chws_up_0.3", "O7", "chws", 0.3, "PLANT", "CHWS reset +0.3 °C"),
        SafeRlAction("schw_pump_down_5", "O14", "schw_dp", -5.0, "SCHW", "Secondary CHW pump −5 %"),
        SafeRlAction("cw_pump_down_5", "O16", "cw_pump", -5.0, "CH-01", "Condenser pump −5 %"),
    ]


def resolve_point_id(action: SafeRlAction, zone_id: str = "ZONE-01") -> Optional[str]:
    if action.is_hold or not action.point_key:
        return None
    pmap = point_map()
    pid = pmap.get(action.point_key or "")
    if not pid:
        return None
    if action.point_key == "zone_cooling_setpoint":
        z = (zone_id or "ZONE-01").strip() or "ZONE-01"
        return f"{z}.cooling_setpoint"
    return pid


def materialize_candidate(
    action: SafeRlAction,
    *,
    zone_id: str,
    building_id: Optional[str],
    current_values: Dict[str, Optional[float]],
) -> Dict[str, Any]:
    if action.is_hold:
        return {
            "action_id": action.action_id,
            "label": action.label,
            "mapped_opportunity": None,
            "point_id": None,
            "equipment_id": None,
            "building_id": building_id,
            "old_value": None,
            "new_value": None,
            "delta": None,
        }
    point_id = resolve_point_id(action, zone_id)
    current = current_values.get(point_id or "") if point_id else None
    if current is None and point_id:
        current = current_values.get(action.point_key or "")
    new_value = None
    if current is not None and action.delta is not None:
        new_value = float(current) + float(action.delta)
    return {
        "action_id": action.action_id,
        "label": action.label,
        "mapped_opportunity": action.opportunity,
        "point_id": point_id,
        "equipment_id": action.equipment_id,
        "building_id": building_id,
        "old_value": current,
        "new_value": new_value,
        "delta": action.delta,
    }
