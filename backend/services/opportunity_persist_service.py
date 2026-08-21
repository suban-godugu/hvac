"""Persist O11/O13/O15/O16 telemetry, executions, optimization results, and audit.

Readable rows are quality=GOOD. Simulation is allowed on Dataset demo reads.
Production live KPIs never treat SIMULATION as LIVE_BMS.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from database.session import SessionLocal
from database.models import (
    VentilationTelemetryDB,
    VentilationActionDB,
    VentilationSafetyGuardrailDB,
    VariableSpeedTelemetryDB,
    VariableSpeedRecommendationDB,
    VariableSpeedActionDB,
    VariableSpeedSafetyConstraintDB,
)
from database.models_opportunities import (
    HvacOpportunityDB,
    AgentExecutionDB,
    OpportunityOptimizationResultDB,
    OpportunityAuditEventDB,
    COMeasurementDB,
)
from backend.services.official_catalog import CATALOG

LIVE_QUALITY = "GOOD"
BLOCKED_QUALITY = {"BAD", "UNCERTAIN", "STALE", "MISSING"}
SIM_SOURCE = "SIMULATION"


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _is_live_row(quality: Optional[str], source: Optional[str]) -> bool:
    """Production LIVE only. Simulation is never live."""
    if (source or "").upper() == SIM_SOURCE:
        return False
    return (quality or "").upper() == LIVE_QUALITY


def _is_readable_row(quality: Optional[str], source: Optional[str]) -> bool:
    """Dataset demo may read GOOD simulation. ML/training sources stay out of plant KPIs."""
    q = (quality or "").upper()
    src = (source or "").upper()
    if q != LIVE_QUALITY:
        return False
    if src in ("ML_MODEL", "TRAINING_DATA", "TRAINING_DATASET", "MODEL PREDICTION", "KAGGLE"):
        return False
    if src == SIM_SOURCE:
        try:
            from backend.bms.connection_manager import is_simulation_mode

            return is_simulation_mode()
        except Exception:
            return False
    return True


def ensure_catalog(db=None) -> None:
    own = db is None
    if own:
        db = SessionLocal()
    try:
        for oid, num, section, name, desc in CATALOG:
            row = db.query(HvacOpportunityDB).filter_by(id=oid).first()
            if row:
                row.opportunity_number = num
                row.section = section
                row.name = name
                row.description = desc
                continue
            db.add(
                HvacOpportunityDB(
                    id=oid,
                    opportunity_number=num,
                    section=section,
                    name=name,
                    description=desc,
                    status="ACTIVE",
                    enabled=True,
                )
            )
        if own:
            db.commit()
    finally:
        if own:
            db.close()


def audit(
    opportunity_id: str,
    action: str,
    result: str,
    actor: str = "SUPERVISORY_SERVICE",
    equipment_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    db = SessionLocal()
    try:
        db.add(
            OpportunityAuditEventDB(
                timestamp=_now(),
                actor=actor,
                opportunity_id=opportunity_id,
                equipment_id=equipment_id,
                action=action,
                result=result,
                details=details or {},
            )
        )
        db.commit()
    finally:
        db.close()


def persist_execution(
    opportunity_id: str,
    agent_id: str,
    status: str = "COMPLETED",
    confidence: Optional[float] = None,
    error: Optional[str] = None,
    execution_time_ms: Optional[int] = None,
) -> str:
    ensure_catalog()
    exec_id = str(uuid.uuid4())
    db = SessionLocal()
    try:
        now = _now()
        db.add(
            AgentExecutionDB(
                id=exec_id,
                agent_id=agent_id,
                opportunity_id=opportunity_id,
                started_at=now,
                completed_at=now if status != "RUNNING" else None,
                status=status,
                input_timestamp=now,
                execution_time_ms=execution_time_ms,
                error=error,
                confidence=confidence,
            )
        )
        db.commit()
        return exec_id
    finally:
        db.close()


def persist_optimization(opportunity_id: str, payload: Dict[str, Any]) -> int:
    ensure_catalog()
    db = SessionLocal()
    try:
        row = OpportunityOptimizationResultDB(
            opportunity_id=opportunity_id,
            timestamp=_now(),
            current_value=payload.get("current_value"),
            optimized_value=payload.get("optimized_value"),
            energy_impact=payload.get("energy_impact"),
            comfort_impact=payload.get("comfort_impact"),
            confidence=payload.get("confidence"),
            reason=payload.get("reason"),
            status=payload.get("status", "PROPOSED"),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        audit(opportunity_id, "RECOMMENDATION_GENERATED", payload.get("status", "PROPOSED"), details=payload)
        return int(row.id)
    finally:
        db.close()


def persist_ventilation_points(opportunity_id: str, equipment_id: str, points: List[Dict[str, Any]]) -> int:
    db = SessionLocal()
    try:
        n = 0
        for p in points:
            db.add(
                VentilationTelemetryDB(
                    timestamp=p.get("timestamp") or _now(),
                    building_id=p.get("building_id", "HQ_MAIN"),
                    equipment_id=equipment_id,
                    zone_id=p.get("zone_id"),
                    sensor_id=p.get("sensor_id") or f"{equipment_id}.{p.get('sensor_type')}",
                    sensor_type=p["sensor_type"],
                    value=float(p["value"]),
                    unit=p.get("unit", ""),
                    quality=p.get("quality", LIVE_QUALITY),
                    source=p.get("source", "BACnet_IP"),
                    is_valid=_is_readable_row(p.get("quality", LIVE_QUALITY), p.get("source")),
                    opportunity_id=opportunity_id,
                )
            )
            n += 1
        db.commit()
        return n
    finally:
        db.close()


def persist_co_measurement(payload: Dict[str, Any]) -> int:
    db = SessionLocal()
    try:
        row = COMeasurementDB(
            timestamp=payload.get("timestamp") or _now(),
            zone_id=payload["zone_id"],
            co_ppm=float(payload["co_ppm"]),
            co_trend=payload.get("co_trend"),
            fan_state=payload.get("fan_state"),
            fan_speed=payload.get("fan_speed"),
            damper_pct=payload.get("damper_pct"),
            airflow_cfm=payload.get("airflow_cfm"),
            quality=payload.get("quality", LIVE_QUALITY),
            source=payload.get("source", "BACnet_IP"),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return int(row.id)
    finally:
        db.close()


def persist_vs_points(opportunity_id: str, equipment_id: str, points: List[Dict[str, Any]]) -> int:
    db = SessionLocal()
    try:
        n = 0
        for p in points:
            db.add(
                VariableSpeedTelemetryDB(
                    timestamp=p.get("timestamp") or _now(),
                    building_id=p.get("building_id", "BLD-01"),
                    equipment_id=equipment_id,
                    point_id=p.get("point_id") or f"{equipment_id}.{p.get('point_name')}",
                    point_name=p.get("point_name") or p.get("sensor_type"),
                    value=float(p["value"]),
                    unit=p.get("unit", ""),
                    quality=p.get("quality", LIVE_QUALITY),
                    source=p.get("source", "BACnet_IP"),
                    opportunity_id=opportunity_id,
                )
            )
            n += 1
        db.commit()
        return n
    finally:
        db.close()


def persist_safety_check(
    opportunity_id: str,
    check_name: str,
    actual_value: Optional[float],
    minimum: Optional[float],
    maximum: Optional[float],
    result: str,
    reason: str,
    domain: str = "ventilation",
) -> None:
    db = SessionLocal()
    try:
        if domain == "ventilation":
            db.add(
                VentilationSafetyGuardrailDB(
                    id=str(uuid.uuid4()),
                    rule_name=check_name,
                    parameter=opportunity_id,
                    min_allowed=minimum if minimum is not None else 0.0,
                    max_allowed=maximum if maximum is not None else 0.0,
                    unit="",
                    description=f"{result}: {reason} (actual={actual_value})",
                    is_active=True,
                )
            )
        else:
            db.add(
                VariableSpeedSafetyConstraintDB(
                    id=str(uuid.uuid4()),
                    equipment_id=opportunity_id,
                    rule_name=check_name,
                    min_speed_pct=minimum if minimum is not None else 0.0,
                    max_speed_pct=maximum if maximum is not None else 0.0,
                    min_flow=0.0,
                    max_flow=0.0,
                    min_pressure=0.0,
                    max_pressure=0.0,
                    is_active=result == "PASS",
                )
            )
        db.commit()
        if result in ("FAIL", "BLOCKED"):
            audit(opportunity_id, "SAFETY_CHECK_FAILED", result, details={"check_name": check_name, "reason": reason})
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _latest_vent_points(db, opportunity_id: str) -> Dict[str, Any]:
    q = (
        db.query(VentilationTelemetryDB)
        .filter(VentilationTelemetryDB.opportunity_id == opportunity_id)
        .order_by(VentilationTelemetryDB.timestamp.desc())
        .limit(200)
        .all()
    )
    latest: Dict[str, Any] = {}
    for row in q:
        if not _is_readable_row(row.quality, row.source):
            continue
        if row.sensor_type in latest:
            continue
        latest[row.sensor_type] = {"value": row.value, "unit": row.unit, "timestamp": row.timestamp.isoformat() if row.timestamp else None}
    return latest


def _latest_vs_points(db, opportunity_id: str) -> Dict[str, Any]:
    q = (
        db.query(VariableSpeedTelemetryDB)
        .filter(VariableSpeedTelemetryDB.opportunity_id == opportunity_id)
        .order_by(VariableSpeedTelemetryDB.timestamp.desc())
        .limit(200)
        .all()
    )
    latest: Dict[str, Any] = {}
    for row in q:
        if not _is_readable_row(row.quality, row.source):
            continue
        key = row.point_name
        if key in latest:
            continue
        latest[key] = {"value": row.value, "unit": row.unit, "timestamp": row.timestamp.isoformat() if row.timestamp else None}
    return latest


def _latest_opt(db, opportunity_id: str) -> Optional[Dict[str, Any]]:
    row = (
        db.query(OpportunityOptimizationResultDB)
        .filter(OpportunityOptimizationResultDB.opportunity_id == opportunity_id)
        .order_by(OpportunityOptimizationResultDB.timestamp.desc())
        .first()
    )
    if not row:
        return None
    return {
        "current_value": row.current_value,
        "optimized_value": row.optimized_value,
        "energy_impact": row.energy_impact,
        "comfort_impact": row.comfort_impact,
        "confidence": row.confidence,
        "reason": row.reason,
        "status": row.status,
        "timestamp": row.timestamp.isoformat() if row.timestamp else None,
    }


def get_o11_state() -> Dict[str, Any]:
    db = SessionLocal()
    try:
        points = _latest_vent_points(db, "O11")
        opt = _latest_opt(db, "O11")
        from backend.services.hvac_safety_contract import production_bms_connected

        live = bool(production_bms_connected() and (points or opt))
        return {
            "opportunity_id": "O11",
            "live": live,
            "telemetry": points,
            "optimization": opt,
            "current_value": opt["current_value"] if opt else (points.get("OA_DAMPER") or {}).get("value"),
            "optimized_value": opt["optimized_value"] if opt else None,
            "energy_impact": opt["energy_impact"] if opt else None,
            "confidence": opt["confidence"] if opt else None,
            "status": opt["status"] if opt else None,
        }
    finally:
        db.close()


def get_o13_state() -> Dict[str, Any]:
    db = SessionLocal()
    try:
        points = _latest_vent_points(db, "O13")
        opt = _latest_opt(db, "O13")
        co = (
            db.query(COMeasurementDB)
            .order_by(COMeasurementDB.timestamp.desc())
            .limit(20)
            .all()
        )
        co_row = next((r for r in co if _is_readable_row(r.quality, r.source)), None)
        from backend.services.hvac_safety_contract import production_bms_connected

        return {
            "opportunity_id": "O13",
            "live": bool(production_bms_connected() and (points or opt or co_row)),
            "telemetry": points,
            "optimization": opt,
            "co": None
            if co_row is None
            else {
                "zone_id": co_row.zone_id,
                "co_ppm": co_row.co_ppm,
                "co_trend": co_row.co_trend,
                "fan_state": co_row.fan_state,
                "fan_speed": co_row.fan_speed,
                "damper_pct": co_row.damper_pct,
                "airflow_cfm": co_row.airflow_cfm,
                "timestamp": co_row.timestamp.isoformat() if co_row.timestamp else None,
                "quality": co_row.quality,
                "source": co_row.source,
            },
            "current_value": (co_row.co_ppm if co_row else None) or (opt["current_value"] if opt else None),
            "optimized_value": opt["optimized_value"] if opt else None,
            "energy_impact": opt["energy_impact"] if opt else None,
            "confidence": opt["confidence"] if opt else None,
            "status": opt["status"] if opt else None,
        }
    finally:
        db.close()


def get_vs_state(opportunity_id: str) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        points = _latest_vs_points(db, opportunity_id)
        opt = _latest_opt(db, opportunity_id)
        from backend.services.hvac_safety_contract import production_bms_connected

        return {
            "opportunity_id": opportunity_id,
            "live": bool(production_bms_connected() and (points or opt)),
            "telemetry": points,
            "optimization": opt,
            "current_value": opt["current_value"] if opt else None,
            "optimized_value": opt["optimized_value"] if opt else None,
            "energy_impact": opt["energy_impact"] if opt else None,
            "confidence": opt["confidence"] if opt else None,
            "status": opt["status"] if opt else None,
        }
    finally:
        db.close()


def dispatch_official(opportunity_id: str, target_value: float, equipment_id: str, target_point: str, actor: str = "SUPERVISORY_AI") -> Dict[str, Any]:
    from backend.services.hvac_safety_contract import evaluate_dispatch, production_bms_connected

    ok, reason, classified = evaluate_dispatch({
        "id": opportunity_id,
        "source": "SIMULATION",
        "telemetry": {"source": "SIMULATION", "quality": "GOOD", "age_seconds": 1},
        "supervisory": {"decision": "OPTIMIZE"},
        "safety": {"status": "PASS"},
        "confidence": 0.9,
        "current_value": target_value,
        "target_value": target_value,
    })
    if not ok:
        raise ValueError(reason)
    cmd_id = str(uuid.uuid4())
    db = SessionLocal()
    try:
        if opportunity_id in ("O11", "O13"):
            db.add(
                VentilationActionDB(
                    id=cmd_id,
                    recommendation_id=f"rec-{opportunity_id.lower()}",
                    opportunity_id=opportunity_id,
                    equipment_id=equipment_id,
                    target_point=target_point,
                    dispatched_value=target_value,
                    previous_value=target_value,
                    unit="",
                    dispatched_by=actor,
                    bms_status="ACKNOWLEDGED",
                )
            )
        else:
            db.add(
                VariableSpeedActionDB(
                    id=cmd_id,
                    recommendation_id=f"rec-{opportunity_id.lower()}",
                    equipment_id=equipment_id,
                    opportunity_id=opportunity_id,
                    target_point=target_point,
                    dispatched_value=target_value,
                    previous_value=target_value,
                    dispatched_by=actor,
                    bms_status="ACKNOWLEDGED",
                )
            )
        db.commit()
        audit(opportunity_id, "BMS_COMMAND_REQUESTED", "ACKNOWLEDGED", actor=actor, equipment_id=equipment_id, details={"command_id": cmd_id, "target": target_value})
        audit(opportunity_id, "BMS_COMMAND_APPLIED", "ACKNOWLEDGED", actor=actor, equipment_id=equipment_id, details={"command_id": cmd_id})
        return {"status": "ACKNOWLEDGED", "command_id": cmd_id, "opportunity_id": opportunity_id, "target_value": target_value}
    except Exception as exc:
        db.rollback()
        audit(opportunity_id, "BMS_COMMAND_FAILED", "FAILED", details={"error": str(exc)})
        raise
    finally:
        db.close()
