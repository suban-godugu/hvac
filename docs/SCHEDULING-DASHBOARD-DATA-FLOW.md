# Scheduling Dashboard Data Flow (O1–O4)

Screen: `/agents/scheduling`  
API: `GET /api/scheduling/dashboard` (alias `GET /api/agents/scheduling/dashboard`)  
Service: `backend/services/scheduling_dashboard_service.py`  
UI: `frontend/app/agents/scheduling/page.tsx` → `OpportunityKPICard` / `TopKPIs`

KPI field maps: `docs/O1-DASHBOARD-KPI-MAPPING.md`, `O2-DASHBOARD-KPI-MAPPING.md`, `O3-DASHBOARD-KPI-MAPPING.md`, `O4-DASHBOARD-KPI-MAPPING.md`.

Each opportunity includes `primaryMetric`, `secondaryMetrics`, `impact`, `confidence`, `telemetry`, `dataState` (`LIVE` | `STALE` | `LAST_KNOWN` | `AWAITING_TELEMETRY` | `ENGINE_OFFLINE` | `ERROR`). `ACTIVE` is only used when `dataState` is `LIVE`.

## Shared path

```
Dashboard UI
  → fetchSchedulingDashboard()
  → GET /api/scheduling/dashboard
  → get_scheduling_dashboard()
  → sim_service.step(0) once
  → SQLite (actions, savings VERIFIED, safety, activity)
  → per-opportunity engines / O1 pipeline
```

Null values stay null. Predicted energy is labeled `predicted`. The Verified Savings KPI uses only `o1_savings_verification.verification_status = VERIFIED`.

Freshness (configurable LIVE threshold from `o1_configuration.stale_telemetry_seconds`, defaults 30 / 120 / 300 s):

LIVE · STALE · DEGRADED · OFFLINE → card `displayState` LIVE / STALE TELEMETRY / DEGRADED TELEMETRY / AWAITING TELEMETRY / BACKEND OFFLINE / ENGINE NOT CONFIGURED / EVALUATION ERROR.

## O1 — Optimum Start/Stop

| Step | Source |
| --- | --- |
| UI Current / Optimized / Energy / Confidence | `opportunities[0]` |
| Service | `o1_service.get_state`, `get_energy_impact`, `get_decision`, `get_safety_checks` |
| DB | `o1_telemetry_sample`, `o1_daily_run`, `o1_decisions`, `o1_start_candidate`, `o1_savings_verification`, `o1_safety_validation` |
| Origin | Ingested ZONE_TEMP/OAT (SIMULATED or BMS) + thermal model / PHYSICS_FALLBACK |

Route on Open: `/agents/scheduling/optimum-start-stop`

## O2 — Space temperature & bands

| Step | Source |
| --- | --- |
| UI Current / Optimized / Control band / Comfort | `opportunities[1]` |
| Service | `SpaceTemperatureOptimizationEngine.evaluate(sim_state)` |
| Origin | Sim `ahus[].vav_zones` actual temperatures and setpoints |

Route: `/agents/scheduling/space-temperature`

## O3 — Master AHU SAT

| Step | Source |
| --- | --- |
| UI Current SAT / Optimized SAT / Reset | `opportunities[2]` |
| Service | `MasterAHUSATOptimizationEngine.evaluate(sim_state)` |
| Origin | Sim `ahus[0].sat_actual` / `sat_setpoint` + Guideline 36 trim/respond |

Route: `/agents/scheduling/master-ahu-sat`

## O4 — Chiller staging

| Step | Source |
| --- | --- |
| UI Current/Optimized stage / Load | `opportunities[3]` |
| Service | `ChillerCompressorStagingEngine.evaluate(sim_state)` |
| Origin | Sim `plant` chiller run flags and `total_tons` |

Route: `/agents/scheduling/chiller-staging`

## Header KPIs

| KPI | Query |
| --- | --- |
| Agent Health | telemetry freshness + DB + engine + BMS connectivity + O1 model presence |
| Active Opportunities | count of LIVE / ACTIVE / READY cards (not hardcoded 4/4) |
| Actions Dispatched | `COUNT` `o1_actions`+`o2_actions`+`o3_actions`+`o4_actions`+`supervisory_actions` |
| Verified Savings | sum `o1_savings_verification.energy_saved` where VERIFIED |
| Comfort Compliance | fraction of sim zones in 20.0–24.5°C |
| Safety Guardrails | latest `o1_safety_validation` PASS/WARNING/BLOCKED |
| Telemetry Heartbeat | min telemetry age across cards |
| Safety Rollbacks | rollback flags on O1–O4 action tables |
