# O1 Backend Audit — Optimum Start/Stop Programming

**Date:** 2026-08-19  
**Scope:** FastAPI + SQLAlchemy SQLite. No code changes in this document.  
**Live database:** `database/hvac_supervisory.db` (not PostgreSQL). Alembic `0001`/`0002` exist.

## Current architecture

Two O1 stacks run in parallel:

1. **Closed-loop worker** — `SchedulingControlWorker` → `OptimumStartStopEngine` (`backend/agents/scheduling_supervisory/o1_engine.py`) via `GET /api/agents/scheduling/o1`.
2. **Dashboard service** — `backend/services/o1_service.py` serving `/api/agents/scheduling/o1/state` and related GETs. Most dashboard payloads are hardcoded.

```
BMS simulator / sim_service
        → o1_engine (physics, HistoricalThermalResponse adaptation)
        → worker cycle
Dashboard GETs → o1_service (static 07:18 / 16:45 / 2.55 hrs)
        → existing O1 frontend (react-query + extra hardcoded subtitles)
```

No Redis. Model registry is JSON files (`backend/models/registry.py`), not SQL. Canonical models: `database/models.py`. Stale duplicate: `backend/database/models.py`.

## Existing O1 endpoints

Prefix `/api` from `backend/main.py`. Implemented in `backend/api/routes.py`.

| Method | Path | Backend | Honesty |
|--------|------|---------|---------|
| GET | `/agents/scheduling/o1` | `o1_engine.evaluate` | Live sim |
| GET | `/agents/scheduling/o1/state` | `o1_service.get_state` | Hybrid; schedule/target hardcoded; telemetry_age=2 |
| GET | `/agents/scheduling/o1/telemetry` | weather slice of state | Incomplete |
| GET | `/agents/scheduling/o1/schedule` | KPI slice | Hardcoded windows |
| GET | `/agents/scheduling/o1/thermal-model` | `get_thermal_model` | Hardcoded R² 0.924, “4,320 Real Thermal Cycles” |
| GET | `/agents/scheduling/o1/start-candidates` | static list | Hardcoded SELECTED 07:18 |
| GET | `/agents/scheduling/o1/coast-candidates` | static list | Hardcoded SELECTED 16:45 |
| GET | `/agents/scheduling/o1/decision` | static | Hardcoded |
| GET | `/agents/scheduling/o1/timeline` | static | Hardcoded |
| GET | `/agents/scheduling/o1/safety` | 12 PASS rows | Hardcoded |
| GET | `/agents/scheduling/o1/trajectory` | synthetic curve | Fabricated |
| GET | `/agents/scheduling/o1/energy` | static 43.4 kWh | Hardcoded; **UI polls but does not render** |
| GET | `/agents/scheduling/o1/bms-action` | static VERIFIED | Hardcoded |
| GET | `/agents/scheduling/o1/history` | `o1_calibration_records` | DB, but auto-seeded fake VERIFIED days |
| GET | `/agents/scheduling/o1/activity` | in-memory list | Fabricated stream |
| POST | `/agents/scheduling/o1/optimize` | writes `o1_actions` as VERIFIED immediately | False ack |
| POST | `/agents/scheduling/o1/verify` | **literal JSON** `07:54` / PASS | Fake |
| POST | `/agents/scheduling/o1/rollback` | writes rollback row | Partial |

Frontend client: `frontend/lib/api.ts`. Page: `frontend/app/agents/scheduling/optimum-start-stop/page.tsx`. Route unchanged: `/agents/scheduling/optimum-start-stop`.

## Existing DB tables (O1-relevant)

Reuse: `buildings`, `equipment`, `points`, `engineering_limits`, `supervisory_actions`, `historical_thermal_response`.

Thin O1 tables already present:

| Table | Fields (summary) | Gaps |
|-------|------------------|------|
| `o1_thermal_telemetry` | oat, indoor_temp, setpoint, ahu, demands, solar index | No point_id, quality, source, raw_value, ingested_at; missing SAT/RAT/fan/valves |
| `o1_decisions` | start/stop strings, delay, confidence, savings, model_version | No run_id, candidates, safety FK |
| `o1_actions` | previous/requested/applied, bms_status default ACKNOWLEDGED | No run_id, verification timestamp, command lifecycle |
| `o1_calibration_records` | daily calibration | Defaults include VERIFIED / 42.5 kWh |
| `o1_activity_log` | stage, message, detail JSON | No run_id, event_type enum, severity |

Missing tables: point map, config, telemetry samples, weather observations, occupancy schedule, model registry SQL, training runs, predictions, start/stop candidates, daily run, safety/comfort validation rows, energy baseline, savings verification.

## Existing fields vs required engineering signals

Dashboard uses zone temp + OAT + solar from sim when present; defaults `24.2`, `28.5`, `450`. No BMS point mapping. Required optional signals (SAT, RAT, MAT, CHWS, CHWR, fan, valves, occupancy, alarms) are not ingested.

## Data / model flow today

- Predictor: `ThermalResponsePredictor` with hardcoded alpha=14.5, beta=1.8, tau=6.8.
- Engine: same coefficients; adapts alpha from `historical_thermal_response` if ≥3 rows.
- `train_o1.py`: lstsq on JSONL; **clamps r2 with `max(0.92, r2)`** — invented metric floor.
- Worker: 10s loop, simulator BMS gateway. No production BACnet writes.

## Mock / hardcoded locations

| File | Problem |
|------|---------|
| `backend/services/o1_service.py` | `_ensure_initial_records` fake VERIFIED days; candidates; safety 12/12; energy; BMS VERIFIED; activities |
| `backend/api/routes.py` L353–356 | POST verify static |
| `backend/api/routes.py` L215–225 | Scheduling activity hardcoded incl. O1 |
| `backend/models/train_o1.py` | `max(0.92, r2)` |
| `frontend/.../optimum-start-stop/page.tsx` | thermal fallback 0.924; KPI subtitles 07:18/16:45/2.55h; decision badges; 12/12 PASSED; energy $5.21; telemetry “2s HEALTHY” |

## Missing persistence / indexes / relationships / validation

No FKs from O1 tables to `buildings`/`equipment`/`points`. No `(point_id, timestamp)` sample index. No run graph. Safety always PASS. Missing values coerced via `.get(..., 24.2)`. No quality/freshness service. Historical JSONL not loaded as labeled SIMULATED samples.

## Missing pipelines

Telemetry ingestion with quality; honest training without metric floor; candidate persistence; blocking guardrails; savings verification (PREDICTED vs VERIFIED); daily run_id; BMS ack/verify/rollback from state; activity from real events.

## API / frontend mismatches

- UI `comfort_compliance_pct` vs API `comfort_compliance`.
- `/o1/energy` fetched every 3s, energy panel is static HTML.
- Scheduled window KPI hardcoded `06:00 – 18:00` ignoring API.
- Telemetry KPI ignores `kpis.telemetry_freshness`.

## Recommended implementation order

Audit (this doc) → Alembic 0003 additive schema → point map → ingestion/health → dataset spec + SIMULATED generator → model/registry (no invented R²) → start/coast/guardrails/savings → daily run + BMS verify → keep existing routes, strip UI mocks → contract + dev seed + tests + integrity audit.

## Redis / PostgreSQL

Not used. Stay on SQLite + Alembic. Do not add a second catalog.
