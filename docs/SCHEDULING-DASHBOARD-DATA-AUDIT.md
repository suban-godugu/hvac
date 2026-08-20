# Scheduling Dashboard Data Audit

Screen: `/agents/scheduling` (Scheduling & Supervisory Agent).

## Why cards show ACTIVE + NO LIVE DATA

The dashboard does **not** call O1–O4 dedicated APIs (`/api/agents/scheduling/o1/state`, `/o2/state`, …).

| Layer | What it does | Effect |
| --- | --- | --- |
| Page | `useSupervisoryCycle()` → `GET /api/agents/scheduling/status` → `sim_service.step(0)` | Cycle payload exists |
| Cards | `OpportunityCardGrid` matches `detected_opportunities` with `o.code \|\| o.id \|\| o.opportunity_id` | **Misses `opportunity_code`** |
| Fields | Renders `confidence` and `energy_impact \|\| impact` | Detector emits **`estimated_power_kw_impact`**, not `energy_impact` |
| Empty UI | `fields.filter(non-empty).length === 0` → **NO LIVE DATA** + “Telemetry is not currently available” | Triggered even when sim/DB has data |
| Status | `(live)?.status \|\| (opportunities ? 'ACTIVE' : …)` | Array is truthy → **ACTIVE** with empty fields |

This is a **response-mapping / field-name** failure, not missing telemetry, auth, or NestJS (this stack is FastAPI + SQLite only).

## Data that already exists

| Opportunity | Live sources | Dashboard used them? |
| --- | --- | --- |
| O1 | `o1_service` pipeline, `o1_telemetry_sample`, `o1_decisions`, `o1_engine.evaluate(sim)` | No |
| O2 | `o2_engine.evaluate(sim)`, sim `ahus[].vav_zones`, `o2_service` | No |
| O3 | `o3_engine.evaluate(sim)`, AHU `sat_actual` / `sat_setpoint` | No |
| O4 | `o4_engine.evaluate(sim)`, `plant.total_tons`, chiller run flags | No |

`GET /agents/scheduling/kpis` still hardcodes `verified_power_kw: 17.8`, `telemetry_age_seconds: 2`, `rollbacks_today: 0` — not used by the card grid, but would be dishonest if wired as-is.

Header `TopKPIs` uses cycle `detected_opportunities.length / 4` (triggered flags, not ACTIVE engines), `candidate_actions.length` as “dispatched”, and `telemetryAgeSec` from Zustand default **2**, not measured age.

`LiveControlLog` and `AgentDecisionPanel` ignore live data and fall back to hardcoded 07:18 / 76.0 Tons rows.

## Classification

| Hypothesis | Result |
| --- | --- |
| Missing API call | Partial: cycle is called; O1–O4 studio APIs are not |
| Incorrect endpoint | Cards never hit `/o1/state` … `/o4/state` |
| Incorrect opportunity ID | Match uses `code` vs detector `opportunity_code` |
| Response mapping | **Primary** |
| Missing telemetry | Usually false while the worker/sim is running |
| Frontend empty fallback | **Primary amplifier** |
| Backend returning null | Cycle returns four detections; mapping drops them |
| Auth | Not used |
| NestJS | Not in this repo |

## Repair order

1. Aggregated `GET /api/scheduling/dashboard` (alias `/api/agents/scheduling/dashboard`) from engines + SQLite.
2. Canonical opportunity contract; nulls stay null; verified savings only if VERIFIED.
3. Wire dashboard page + cards + header KPIs; distinguish BACKEND OFFLINE / AWAITING TELEMETRY / STALE TELEMETRY / LIVE.
4. Remove mock activity/decision fallbacks on this screen.
5. Tests + `docs/SCHEDULING-DASHBOARD-DATA-FLOW.md`.
