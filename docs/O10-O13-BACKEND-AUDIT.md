# O10–O13 backend audit (read-only)

Module: Ventilation & Air Flow Optimizations  
Opportunities: O10 Economy Cycle, O11 Night Purge, O12 DCV CO₂, O13 DCV CO

## 1. Current architecture

Two overlapping stacks:

1. **Leftover in-memory engines** (`backend/agents/ventilation_airflow/o12_outdoor_air/engine.py`, `o11_demand_ventilation/engine.py`) used as **O10** and **O12** after ID remap (`official_catalog.py`). They default missing sensors to hardcoded weather/airflow (17.5°C, 2400 CFM, etc.).
2. **Official persist agents** (`o11_night_purge.py`, `o13_dcv_co.py`) used for O11/O13. `official_opportunity_runtime.sample_o11/o13` **drops `source=SIMULATION` points**, so live evaluation is usually empty.

Orchestration: `ventilation_airflow_service.py` → FastAPI `ventilation_airflow_controller.py` (`prefix=/api/ventilation-airflow`). Frontend Next rewrites `/api/*` to FastAPI.

Dashboard UI: `frontend/app/agents/ventilation-airflow/page.tsx` via `SectionDashboard` + `OpportunityCard`.  
Detail: O10 `outdoor-air/page.tsx`, O12 `demand-ventilation/page.tsx` (custom studios). O11/O13 `OfficialOpportunityStudio` against `/opportunities/{id}/state`.

## 2. Current database schema

| Table | Role |
| --- | --- |
| `hvac_opportunities` | Catalog (0002). Missing `agent`, `priority`. |
| `ventilation_telemetry` | Narrow sensor rows (equipment/sensor_type). |
| `opportunity_optimization_results` | Generic current/optimized/energy. |
| `co_measurements` | O13 CO samples. |
| `ventilation_opportunities` | Snapshot columns defaulting to 0.0 / 0.95 confidence. |

Missing (requested): wide `hvac_telemetry` snapshot, `hvac_optimization_results` + `hvac_optimization_candidates` with FKs.

## 3. Current API endpoints

| Method | Path | Issue |
| --- | --- | --- |
| GET | `/api/ventilation-airflow/dashboard` | Cards nulled unless `live`; KPIs `iaq_*`, heartbeat, totals are `None`. |
| GET | `/api/ventilation-airflow/opportunities/{id}` | O10/O12 engines with defaults; O11/O13 official evaluate. |
| GET | `/api/ventilation-airflow/opportunities/{id}/state` | **404 unless id is O11 or O13**. |
| GET | `/api/agents/ventilation-airflow/dashboard` | **Does not exist**. |
| GET | `/health` | Hardcoded `OPTIMAL`, `10_OF_10_ACTIVE`. |
| GET | `/history` | Synthetic 8200/6850 CFM series. |

## 4. Current frontend data flow

Dashboard: `fetch('/api/ventilation-airflow/dashboard')` every 5s, no loading flag → `KPIGrid` / empty cards show **NO LIVE DATA** immediately.  
O10/O12: `localhost:8000` absolute URLs; format numbers in JSX (`% Open`, `.toLocaleString()`).  
O11/O13: `/state` 404 shown as `API 404` in `OfficialOpportunityStudio`.

## 5. Missing backend data

No single `HVACOpportunityResult`. Dashboard and detail payloads differ. No aggregated summary (active/optimal/ready/energy/IAQ). O10 candidates are static literals, not derived from live damper/OAT.

## 6. Missing telemetry

In-memory `VentilationTelemetryService` is `source=SIMULATION` with random jitter. Official runtime ignores it. No Bengaluru / Skyline site snapshot in SQLite labeled DEMO.

## 7. Mock/fallback data

- Engine defaults when `telemetry is None`.
- `get_zones` / `get_equipment` hardcoded 6850 CFM.
- `get_history` 8200/6850.
- `get_activity_log` fake row if DB empty.
- O10 UI fallbacks: `'97%'`, `'Comparative enthalpy indicates optimal free cooling.'`
- O12 UI: `'95%'`, `'56.6% Active Loading'`.
- `card_from_engine(..., live_fields=False)` **always nulls KPIs**.

## 8. Unit/formatting problems

- O10 appends `% Open` to `optimized_value`. If CFM (6850) leaks in, UI shows **6850%**.
- `enthalpy_advantage_kj_kg` interpolated even when undefined → **undefined kJ/kg**.
- O12 `data.optimized_airflow_cfm.toLocaleString()` throws when undefined.
- Confidence `* 100` if value already 0–100 → thousands of percent.
- No shared `formatPercent` (0.685 vs 68.5).

## 9. API failures

O11 `/state` 404 for any non-O11/O13 id; missing telemetry incorrectly looks like missing route. Dashboard rewrite 404 if FastAPI down → silent empty `data`.

## 10. Runtime errors

`Cannot read properties of undefined (reading 'toLocaleString')` on O12. String `"undefined kJ/kg"` on O10. Unsafe `.toFixed` on confidence.

## 11. KPI calculation gaps

Dashboard `total_power_shed_kw`, `total_daily_kwh_savings`, `iaq_comfort_compliance_pct`, `telemetry_heartbeat` always null. Cards hide engine kW because `live_fields=False`. O11/O13 energy not rolled into fleet totals.

## 12. Required implementation changes

1. Wide `hvac_telemetry` + optimization/candidate tables; seed DEMO snapshot (labeled).
2. One evaluator: DB telemetry → engines (no silent defaults) → persist → normalized API.
3. `GET /api/agents/ventilation-airflow/dashboard` and `.../opportunities/O10–O13`; `/state` 200 with UNAVAILABLE.
4. Frontend formatters; loading vs UNAVAILABLE; cards Current/Optimized/Energy/Daily/Confidence/Telemetry.
5. Tests for percent/CFM/enthalpy/null/stale/aggregation.
