"""O17–O20 persistence using energy-ops tables plus training/maintenance/controller models."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from database.session import SessionLocal
from database.models_energy_ops import (
    EnergyTelemetryDB,
    EnergyBaselineDB,
    EnergyConsumptionDB,
    EnergySavingsMVDB,
    EnergyRecommendationDB,
    EquipmentPerformanceDB,
)
from database.models_opportunities import (
    TrainingProgramDB,
    TrainingCompletionDB,
    MaintenanceWorkOrderDB,
    ControllerSoftwareStatusDB,
    OpportunityOptimizationResultDB,
)
from backend.services.opportunity_persist_service import (
    LIVE_QUALITY,
    _is_live_row,
    _latest_opt,
    ensure_catalog,
    persist_optimization,
    audit,
)

SIM_SOURCE = "SIMULATION"


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def persist_energy_reading(payload: Dict[str, Any]) -> int:
    ensure_catalog()
    db = SessionLocal()
    try:
        row = EnergyTelemetryDB(
            timestamp=payload.get("timestamp") or _now(),
            building_id=payload.get("building_id", "BLD-01"),
            meter_id=payload["meter_id"],
            category=payload.get("category", "TOTAL_HVAC"),
            power_kw=float(payload["power_kw"]),
            quality=payload.get("quality", LIVE_QUALITY),
            source=payload.get("source", "BACnet_IP_PowerMeter"),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        rid = int(row.id)
        quality = payload.get("quality", LIVE_QUALITY)
        source = payload.get("source", "BACnet_IP_PowerMeter")
    finally:
        db.close()
    if _is_live_row(quality, source):
        persist_optimization(
            "O17",
            {
                "current_value": float(payload["power_kw"]),
                "energy_impact": payload.get("energy_impact"),
                "status": "PROPOSED",
                "reason": payload.get("meter_id"),
            },
        )
    return rid


def persist_training_program(payload: Dict[str, Any]) -> str:
    ensure_catalog()
    pid = payload.get("id") or str(uuid.uuid4())
    db = SessionLocal()
    try:
        existing = db.query(TrainingProgramDB).filter_by(id=pid).first()
        if existing:
            existing.topic = payload["topic"]
            existing.program_name = payload["program_name"]
            existing.required = bool(payload.get("required", existing.required))
            existing.status = payload.get("status", existing.status)
        else:
            db.add(
                TrainingProgramDB(
                    id=pid,
                    topic=payload["topic"],
                    program_name=payload["program_name"],
                    required=bool(payload.get("required", False)),
                    status=payload.get("status", "ACTIVE"),
                )
            )
        db.commit()
        persist_optimization(
            "O18",
            {
                "current_value": payload.get("completion_pct"),
                "optimized_value": 100.0,
                "reason": payload.get("topic"),
                "status": "PROPOSED",
            },
        )
        return pid
    finally:
        db.close()


def persist_training_completion(payload: Dict[str, Any]) -> int:
    db = SessionLocal()
    try:
        row = TrainingCompletionDB(
            program_id=payload["program_id"],
            role_label=payload.get("role_label", "OPERATOR"),
            completion_pct=float(payload.get("completion_pct", 0)),
            status=payload.get("status", "IN_PROGRESS"),
            completed_at=payload.get("completed_at"),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return int(row.id)
    finally:
        db.close()


def persist_work_order(payload: Dict[str, Any]) -> str:
    ensure_catalog()
    oid = payload.get("id") or str(uuid.uuid4())
    db = SessionLocal()
    try:
        db.add(
            MaintenanceWorkOrderDB(
                id=oid,
                equipment_id=payload["equipment_id"],
                maintenance_type=payload["maintenance_type"],
                status=payload.get("status", "OPEN"),
                due_date=payload.get("due_date"),
                runtime_hours=payload.get("runtime_hours"),
                efficiency=payload.get("efficiency"),
                degradation=payload.get("degradation"),
                priority=payload.get("priority", "MEDIUM"),
                recommendation=payload.get("recommendation"),
                completed_at=payload.get("completed_at"),
            )
        )
        db.commit()
        persist_optimization(
            "O19",
            {
                "current_value": payload.get("efficiency"),
                "reason": payload.get("recommendation"),
                "status": payload.get("status", "OPEN"),
            },
        )
        return oid
    finally:
        db.close()


def persist_controller(payload: Dict[str, Any]) -> int:
    ensure_catalog()
    db = SessionLocal()
    try:
        row = ControllerSoftwareStatusDB(
            controller_id=payload["controller_id"],
            software_version=payload.get("software_version"),
            firmware_version=payload.get("firmware_version"),
            comm_status=payload.get("comm_status", "UNKNOWN"),
            point_quality=payload.get("point_quality", "UNKNOWN"),
            override_state=payload.get("override_state"),
            alarm_state=payload.get("alarm_state"),
            control_loop_state=payload.get("control_loop_state"),
            last_communication=payload.get("last_communication") or _now(),
            health_status=payload.get("health_status", "UNKNOWN"),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        persist_optimization(
            "O20",
            {
                "reason": payload.get("health_status"),
                "status": payload.get("comm_status"),
            },
        )
        return int(row.id)
    finally:
        db.close()


def get_o17_state() -> Dict[str, Any]:
    db = SessionLocal()
    try:
        tel = (
            db.query(EnergyTelemetryDB)
            .order_by(EnergyTelemetryDB.timestamp.desc())
            .limit(50)
            .all()
        )
        live_tel = next(
            (
                r
                for r in tel
                if _is_live_row(r.quality, r.source) and (r.meter_id or "") != "MAIN-ELEC-METER"
            ),
            None,
        )
        baseline = db.query(EnergyBaselineDB).order_by(EnergyBaselineDB.timestamp.desc()).first()
        cons = db.query(EnergyConsumptionDB).order_by(EnergyConsumptionDB.timestamp.desc()).first()
        mv = db.query(EnergySavingsMVDB).order_by(EnergySavingsMVDB.timestamp.desc()).first()
        rec = db.query(EnergyRecommendationDB).order_by(EnergyRecommendationDB.timestamp.desc()).first()
        opt = _latest_opt(db, "O17")
        return {
            "opportunity_id": "O17",
            "live": live_tel is not None or opt is not None,
            "power_kw": live_tel.power_kw if live_tel else None,
            "meter_id": live_tel.meter_id if live_tel else None,
            "baseline_kw": baseline.baseline_hvac_power_kw if baseline else None,
            "tariff": cons.tou_tariff_rate_usd_kwh if cons else None,
            "carbon": cons.carbon_avoided_kg_co2 if cons else None,
            "savings_kw": mv.verified_savings_kw if mv else None,
            "forecast": None,
            "recommendation": rec.recommended_action if rec else None,
            "optimization": opt,
            "current_value": live_tel.power_kw if live_tel else (opt["current_value"] if opt else None),
            "optimized_value": opt["optimized_value"] if opt else None,
            "energy_impact": opt["energy_impact"] if opt else (mv.verified_savings_kw if mv else None),
            "confidence": opt["confidence"] if opt else None,
            "status": opt["status"] if opt else None,
        }
    finally:
        db.close()


def get_o18_state() -> Dict[str, Any]:
    db = SessionLocal()
    try:
        programs = db.query(TrainingProgramDB).all()
        completions = db.query(TrainingCompletionDB).order_by(TrainingCompletionDB.id.desc()).limit(20).all()
        opt = _latest_opt(db, "O18")
        latest = completions[0] if completions else None
        return {
            "opportunity_id": "O18",
            "live": bool(programs) or bool(completions),
            "programs": [
                {"id": p.id, "topic": p.topic, "program_name": p.program_name, "required": p.required, "status": p.status}
                for p in programs
            ],
            "latest_completion": None
            if latest is None
            else {
                "program_id": latest.program_id,
                "role_label": latest.role_label,
                "completion_pct": latest.completion_pct,
                "status": latest.status,
                "completed_at": latest.completed_at.isoformat() if latest.completed_at else None,
            },
            "optimization": opt,
            "current_value": latest.completion_pct if latest else None,
            "optimized_value": 100.0 if latest else None,
            "status": latest.status if latest else (opt["status"] if opt else None),
        }
    finally:
        db.close()


def get_o19_state() -> Dict[str, Any]:
    db = SessionLocal()
    try:
        orders = db.query(MaintenanceWorkOrderDB).order_by(MaintenanceWorkOrderDB.id.desc()).limit(50).all()
        perf = db.query(EquipmentPerformanceDB).order_by(EquipmentPerformanceDB.timestamp.desc()).first()
        opt = _latest_opt(db, "O19")
        open_order = next((o for o in orders if o.status != "COMPLETED"), orders[0] if orders else None)
        return {
            "opportunity_id": "O19",
            "live": bool(orders),
            "findings": [
                {
                    "id": o.id,
                    "equipment_id": o.equipment_id,
                    "maintenance_type": o.maintenance_type,
                    "status": o.status,
                    "due_date": o.due_date.isoformat() if o.due_date else None,
                    "runtime_hours": o.runtime_hours,
                    "efficiency": o.efficiency,
                    "degradation": o.degradation,
                    "priority": o.priority,
                    "recommendation": o.recommendation,
                    "completed_at": o.completed_at.isoformat() if o.completed_at else None,
                }
                for o in orders
            ],
            "performance": None
            if perf is None
            else {"equipment_id": perf.equipment_id, "efficiency": perf.current_efficiency, "health": perf.health_status},
            "optimization": opt,
            "current_value": open_order.efficiency if open_order else None,
            "status": open_order.status if open_order else None,
        }
    finally:
        db.close()


def get_o20_state() -> Dict[str, Any]:
    db = SessionLocal()
    try:
        row = db.query(ControllerSoftwareStatusDB).order_by(ControllerSoftwareStatusDB.updated_at.desc()).first()
        opt = _latest_opt(db, "O20")
        return {
            "opportunity_id": "O20",
            "live": row is not None,
            "controller": None
            if row is None
            else {
                "controller_id": row.controller_id,
                "software_version": row.software_version,
                "firmware_version": row.firmware_version,
                "comm_status": row.comm_status,
                "point_quality": row.point_quality,
                "override_state": row.override_state,
                "alarm_state": row.alarm_state,
                "control_loop_state": row.control_loop_state,
                "last_communication": row.last_communication.isoformat() if row.last_communication else None,
                "health_status": row.health_status,
            },
            "optimization": opt,
            "status": row.health_status if row else None,
            "current_value": None,
        }
    finally:
        db.close()
