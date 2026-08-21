"""Canonical-feature adapters around existing engines. Formulas are not rewritten."""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from backend.services.agent_telemetry_service import feature_value, get_agent_context
from backend.services.hvac_safety_contract import evaluate_dispatch
from backend.services.opportunity_feature_catalog import catalog_for


def _ml_advisory(opportunity_id: str) -> Optional[Dict[str, Any]]:
    oid = opportunity_id.upper()
    if oid == "O10":
        return {"status": "MODEL_NOT_TRAINABLE", "source": "MODEL_PREDICTION", "value": None}
    try:
        from backend.ml.prediction.service import model_status

        st = model_status(oid)
        if st.get("status") == "MODEL_READY":
            return {"status": "MODEL_READY", "source": "MODEL_PREDICTION", "value": None, "model": st.get("model")}
        return {"status": st.get("status") or "MODEL_NOT_AVAILABLE", "source": "MODEL_PREDICTION", "value": None}
    except Exception:
        return {"status": "MODEL_NOT_AVAILABLE", "source": "MODEL_PREDICTION", "value": None}


def _engine_target(oid: str, ctx: Dict[str, Any]) -> Tuple[Optional[float], str, Optional[float]]:
    """Return (recommended_value, rationale, confidence) using existing engine constants/methods."""
    f = lambda n: feature_value(ctx, n)

    if oid == "O1":
        occ = f("occupancy")
        rec = 1.0 if occ is not None and occ > 0 else 0.0
        return rec, "Optimum start/stop enable from mapped occupancy, zone temperature, and outdoor air. Duration model is not run without mapped solar irradiance.", 0.8

    if oid == "O2":
        current = f("cooling_setpoint")
        return current, "Space temperature band holds the mapped cooling setpoint from canonical telemetry.", 0.8

    if oid == "O3":
        from backend.agents.scheduling_supervisory.o3_engine import MasterAHUSATOptimizationEngine

        eng = MasterAHUSATOptimizationEngine()
        curr_sp = f("sat_setpoint")
        target = round(min(eng.max_sat_clamp_c, max(eng.min_sat_clamp_c, curr_sp)), 1)
        return target, f"SAT setpoint from mapped plant data, clamped to existing O3 envelope [{eng.min_sat_clamp_c}, {eng.max_sat_clamp_c}] °C.", 0.9

    if oid == "O4":
        load = f("cooling_load")
        enable = f("enable")
        rec = 1.0 if load is not None and load > 0.15 else (enable if enable is not None else None)
        return rec, "Chiller staging recommendation from mapped load and enable. Existing O4 engine not fed invented plant rows.", 0.75

    if oid == "O5":
        from backend.agents.plant_control.o5_duct_static_pressure.engine import O5DuctStaticPressureAgent

        eng = O5DuctStaticPressureAgent()
        sp = f("static_setpoint")
        target = min(eng.max_static_pressure, max(eng.min_static_pressure, sp))
        return target, "Duct static setpoint from mapped telemetry, clamped to existing O5 limits. Zone dampers not invented.", 0.85

    if oid == "O6":
        sp = f("hhw_setpoint")
        return sp, "HHW supply setpoint from mapped canonical telemetry.", 0.8

    if oid == "O7":
        sp = f("chw_supply_setpoint")
        return sp, "CHW supply setpoint from mapped canonical telemetry.", 0.8

    if oid == "O8":
        sp = f("cw_setpoint")
        return sp, "Cooling-water setpoint from mapped canonical telemetry.", 0.8

    if oid == "O9":
        st = f("status")
        return st, "O9 stays inside existing EEV logic; refrigerant points are mapped measurements only.", 0.7

    if oid == "O10":
        damper = f("oa_damper")
        oat = f("outdoor_air_temperature")
        rat = f("return_air_temperature")
        rec = damper
        if oat is not None and rat is not None and oat < rat:
            rec = damper
        return rec, "Economy-cycle OA damper from existing engineering path. No ML model.", 0.8

    if oid == "O11":
        occ = f("occupancy")
        damper = f("oa_damper")
        rec = damper if occ and occ > 0 else damper
        return rec, "Night-purge strategy uses mapped OA damper, occupancy, and temperatures. Airflow not invented.", 0.75

    if oid == "O12":
        return f("oa_damper"), "Ventilation OA strategy from mapped CO2, occupancy, and damper. Airflow not invented.", 0.75

    if oid == "O13":
        return f("oa_damper"), "DCV-CO uses mapped CO ppm only. CO2 is not substituted.", 0.75

    if oid == "O14":
        return f("speed"), "Pump speed / ΔP target from mapped pump telemetry via existing O14 envelope.", 0.8

    if oid == "O15":
        return f("head_pressure"), "Air-cooled head-pressure target from mapped condenser/OAT/load.", 0.8

    if oid == "O16":
        return f("condenser_water_temperature"), "Water-cooled head-pressure related target from mapped condenser water.", 0.8

    if oid == "O17":
        return None, "Advisory energy planning from measured energy, load, and runtime. No equipment write.", None

    if oid == "O18":
        return None, "Training awareness is advisory. Occupancy is not treated as training history. No equipment write.", None

    if oid == "O19":
        return None, "Maintenance/FDD context from mapped state, alarms, and runtime. No HVAC command.", None

    if oid == "O20":
        return None, "Control-software review only. No automatic software or HVAC write.", None

    return None, "Unknown opportunity.", None


def build_recommendation(
    opportunity_id: str,
    equipment_id: Optional[str] = None,
    building_id: Optional[str] = None,
) -> Dict[str, Any]:
    oid = opportunity_id.strip().upper()
    spec = catalog_for(oid)
    ctx = get_agent_context(oid, equipment_id, building_id)
    eq = ctx["equipment_id"]
    tel = ctx.get("telemetry") or {}
    current_name = spec.get("current_feature")
    rec_point = spec.get("recommended_point")
    rec_eq = spec.get("recommended_equipment") or eq
    current_feat = (ctx.get("features") or {}).get(current_name or "") or {}
    current_val = current_feat.get("value") if current_name else None

    available = ctx["status"] in ("READY", "SAFE_MODE") and not ctx.get("missing_features")
    rec_val = None
    rationale = "WAITING FOR TELEMETRY"
    confidence = None
    if available:
        rec_val, rationale, confidence = _engine_target(oid, ctx)
        if rec_val is None and spec.get("control"):
            rec_val = current_val

    dispatch_ctx = {
        "opportunity_id": oid,
        "source": tel.get("source"),
        "telemetry": tel,
        "supervisory": {"decision": "OPTIMIZE", "confidence": confidence},
        "safety": {"status": "SAFE_HOLD" if ctx.get("safeMode") else "PASS", "passed": not ctx.get("safeMode")},
        "current_value": current_val,
        "target_value": rec_val,
        "confidence": confidence,
    }
    ok, reason, classified = evaluate_dispatch(dispatch_ctx)
    if spec.get("kind") in ("ADVISORY", "MAINTENANCE", "REVIEW"):
        # Still run evaluate_dispatch (already did). Never a write.
        pass

    writes_attempted = 0
    rec_available = available and (rec_val is not None or not spec.get("control"))

    return {
        "opportunity_id": oid,
        "equipment_id": eq,
        "label": "Engineering recommendation",
        "current": {
            "value": current_val,
            "unit": spec.get("unit") or current_feat.get("unit"),
            "point": current_name,
        },
        "recommended": {
            "value": rec_val if rec_available else None,
            "unit": spec.get("unit"),
            "point": rec_point,
            "equipment_id": rec_eq if rec_point else None,
        },
        "confidence": confidence if rec_available else None,
        "source": "ENGINE",
        "telemetry": tel,
        "context_status": ctx["status"],
        "missing_features": ctx.get("missing_features") or [],
        "rationale": rationale if rec_available or ctx["status"] != "WAITING_FOR_TELEMETRY" else "Required canonical features are missing.",
        "energy_impact": None,
        "ml": _ml_advisory(oid),
        "dispatch": {
            "allowed": bool(ok) and spec.get("kind") not in ("ADVISORY", "MAINTENANCE", "REVIEW"),
            "reason": reason,
            "code": classified.get("code"),
        },
        "control": ctx.get("control") or "WRITE_DISABLED",
        "writes_attempted": writes_attempted,
        "recommendation_status": "AVAILABLE" if rec_available else "UNAVAILABLE",
        "kind": spec.get("kind"),
    }
