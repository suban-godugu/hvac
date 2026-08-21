import json
import os
import sys
from datetime import datetime, timedelta

# Add root directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from database.session import init_db, SessionLocal
from database.models import Building, Equipment, Point, SupervisoryActionRecord, HistoricalThermalResponse

def seed_database():
    init_db()
    db = SessionLocal()

    # Check if building already seeded
    existing = db.query(Building).filter_by(id="bldg-corp-hq-01").first()
    if existing:
        if existing.name != "Senatria Corporation":
            existing.name = "Senatria Corporation"
            db.commit()
        print("Database already seeded.")
        db.close()
        from backend.services.opportunity_persist_service import ensure_catalog
        ensure_catalog()
        return

    # Seed Building
    bldg = Building(
        id="bldg-corp-hq-01",
        name="Senatria Corporation",
        area_sqft=75000.0,
        floors=3,
        design_cooling_tonnage=240.0,
        location="Bengaluru, Karnataka, India"
    )
    db.add(bldg)

    # Seed Equipment
    equipments = [
        Equipment(id="CH-1", building_id=bldg.id, name="Centrifugal Chiller 1", type="CHILLER", specs={"capacity_tons": 120, "kw_per_ton_design": 0.58, "min_plr": 0.2}),
        Equipment(id="CH-2", building_id=bldg.id, name="Centrifugal Chiller 2", type="CHILLER", specs={"capacity_tons": 120, "kw_per_ton_design": 0.58, "min_plr": 0.2}),
        Equipment(id="CHW-SYSTEM", building_id=bldg.id, name="Chilled Water Primary Header", type="PUMP", specs={"design_flow_lps": 32.5, "delta_t_design": 5.5}),
        Equipment(id="AHU-1", building_id=bldg.id, name="Floor 1-2 Air Handling Unit", type="AHU", specs={"cfm_max": 24000, "fan_hp": 30, "design_sat": 12.8}),
        Equipment(id="AHU-2", building_id=bldg.id, name="Floor 3 Air Handling Unit", type="AHU", specs={"cfm_max": 16000, "fan_hp": 20, "design_sat": 12.8}),
    ]
    for eq in equipments:
        db.add(eq)

    # Load points from catalog
    catalog_path = os.path.join(os.path.dirname(__file__), "../../dataset/scheduling_supervisory/point_catalog.json")
    if os.path.exists(catalog_path):
        with open(catalog_path, "r") as f:
            catalog = json.load(f)
            for pt in catalog.get("points", []):
                p = Point(
                    id=pt["id"],
                    equipment_id=pt.get("equipment"),
                    name=pt["name"],
                    category=pt["category"],
                    point_type=pt["type"],
                    unit=pt.get("unit"),
                    current_value=0.0
                )
                db.add(p)

    # Seed Historical Thermal Response records for O1 self-adaptive learning
    historical_samples = [
        HistoricalThermalResponse(
            date="2026-08-11",
            outdoor_temperature=21.5,
            initial_zone_temperature=24.2,
            target_temperature=22.5,
            hvac_start="07:22",
            target_reached_time="07:57",
            warmup_duration_minutes=35.0,
            overshoot_c=0.1,
            comfort_result="SUCCESS",
            energy_consumed_kwh=28.5
        ),
        HistoricalThermalResponse(
            date="2026-08-12",
            outdoor_temperature=26.0,
            initial_zone_temperature=25.0,
            target_temperature=22.5,
            hvac_start="07:05",
            target_reached_time="07:55",
            warmup_duration_minutes=50.0,
            overshoot_c=0.0,
            comfort_result="SUCCESS",
            energy_consumed_kwh=41.2
        ),
        HistoricalThermalResponse(
            date="2026-08-13",
            outdoor_temperature=28.5,
            initial_zone_temperature=25.8,
            target_temperature=22.5,
            hvac_start="06:48",
            target_reached_time="07:56",
            warmup_duration_minutes=68.0,
            overshoot_c=0.2,
            comfort_result="SUCCESS",
            energy_consumed_kwh=58.4
        ),
        HistoricalThermalResponse(
            date="2026-08-14",
            outdoor_temperature=23.0,
            initial_zone_temperature=24.5,
            target_temperature=22.5,
            hvac_start="07:18",
            target_reached_time="07:58",
            warmup_duration_minutes=40.0,
            overshoot_c=0.0,
            comfort_result="SUCCESS",
            energy_consumed_kwh=32.0
        ),
        HistoricalThermalResponse(
            date="2026-08-15",
            outdoor_temperature=19.5,
            initial_zone_temperature=23.6,
            target_temperature=22.5,
            hvac_start="07:35",
            target_reached_time="07:58",
            warmup_duration_minutes=23.0,
            overshoot_c=0.1,
            comfort_result="SUCCESS",
            energy_consumed_kwh=19.4
        ),
    ]
    for h in historical_samples:
        db.add(h)

    db.commit()
    db.close()
    from backend.services.opportunity_persist_service import ensure_catalog
    ensure_catalog()
    print("Database seeded successfully with historical thermal response records.")

if __name__ == "__main__":
    seed_database()
