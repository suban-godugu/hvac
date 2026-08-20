"""Versioned platform APIs: buildings, telemetry, points."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from backend.knowledge.hvac_guide_catalog import catalog_all, catalog_record
from backend.services.canonical_telemetry_service import latest_points
from database.models import Building, Equipment, Point
from database.session import SessionLocal

router = APIRouter(prefix="/api/v1", tags=["v1"])


@router.get("/guide-catalog")
@router.get("/opportunities/catalog")
async def guide_catalog():
    return {
        "opportunities": catalog_all(),
        "source_document": "150317hvacguide.pdf",
        "energy_impact_note": "guide_savings_potential is GUIDE_POTENTIAL, not measured savings",
    }


@router.get("/guide-catalog/{oid}")
@router.get("/opportunities/catalog/{oid}")
async def guide_catalog_one(oid: str):
    item = catalog_record(oid)
    if not item:
        raise HTTPException(status_code=404, detail={"code": "UNKNOWN_OPPORTUNITY", "message": "Official catalog IDs are O1–O20."})
    return item


@router.get("/buildings")
async def buildings():
    db = SessionLocal()
    try:
        rows = db.query(Building).all()
        return {
            "buildings": [
                {
                    "id": b.id,
                    "name": b.name,
                    "location": b.location,
                    "area_sqft": b.area_sqft,
                    "floors": b.floors,
                    "design_cooling_tonnage": b.design_cooling_tonnage,
                }
                for b in rows
            ]
        }
    finally:
        db.close()


@router.get("/buildings/{building_id}")
async def building_one(building_id: str):
    db = SessionLocal()
    try:
        b = db.query(Building).filter_by(id=building_id).first()
        if not b:
            raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Building not found."})
        eq = db.query(Equipment).filter_by(building_id=building_id).all()
        return {
            "id": b.id,
            "name": b.name,
            "location": b.location,
            "area_sqft": b.area_sqft,
            "equipment": [{"id": e.id, "name": e.name, "type": e.type} for e in eq],
        }
    finally:
        db.close()


@router.get("/equipment")
async def equipment(building_id: Optional[str] = None):
    db = SessionLocal()
    try:
        q = db.query(Equipment)
        if building_id:
            q = q.filter_by(building_id=building_id)
        rows = q.all()
        return {"equipment": [{"id": e.id, "building_id": e.building_id, "name": e.name, "type": e.type} for e in rows]}
    finally:
        db.close()


@router.get("/telemetry")
async def telemetry(building_id: Optional[str] = None):
    return {"points": latest_points(building_id)}


@router.get("/points")
async def points(equipment_id: Optional[str] = None):
    db = SessionLocal()
    try:
        q = db.query(Point)
        if equipment_id:
            q = q.filter_by(equipment_id=equipment_id)
        rows = q.limit(500).all()
        return {
            "points": [
                {"id": p.id, "name": p.name, "equipment_id": p.equipment_id, "unit": p.unit, "category": p.category}
                for p in rows
            ]
        }
    finally:
        db.close()
