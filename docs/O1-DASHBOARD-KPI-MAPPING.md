# O1 dashboard KPI mapping

Source of truth: `GET /api/scheduling/dashboard` → `backend/services/scheduling_dashboard_service.py` `_build_o1()` → `backend/services/o1_service.py` → SQLite (`database/models_o1.py`).

Dashboard does not invent 07:18, 42.5 kWh, or 94.2%. Those were UI mock examples only.

| UI KPI | API field | Service / table | Source |
| --- | --- | --- | --- |
| Opportunity ID | `opportunityId` | constant `"O1"` | Opportunity catalog |
| Name | `name` | constant | Opportunity catalog |
| Status | `status` | derived from `dataState` (`LIVE`→ACTIVE, `STALE`/`LAST_KNOWN`→MONITORING, fail→BLOCKED) | Freshness + `o1_daily_runs` status if FAILED/BLOCKED |
| Optimized Start (primary) | `primaryMetric` / `kpis.optimized_start` | `o1_optimization_decisions.optimized_start` via `o1_service.get_state()` | O1 optimization engine / last decision row |
| Current Temp | `secondaryMetrics["Current Temp"]` / `currentValue` | `o1_telemetry_sample` signal `ZONE_TEMP` via `live_value("ZONE_TEMP")` | Telemetry ingest |
| Optimized Stop | `secondaryMetrics["Optimized Stop"]` | `o1_optimization_decisions.optimized_stop` | O1 optimization engine |
| Runtime Saved | `secondaryMetrics["Runtime Saved"]` / `impact.runtime` | `o1_savings_verification.runtime_saved` | Verification record; labeled VERIFIED vs status |
| Energy Saved | `secondaryMetrics["Energy Saved"]` / `impact.energy` | `o1_service.get_energy_impact()` → verified `tiers.verified_savings_kwh` or predicted `daily_energy_savings_kwh` | Never shown as VERIFIED unless `verification_status==VERIFIED` |
| Confidence | `confidence` | Active model `prediction_confidence_pct` or `o1_optimization_decisions.start_confidence` | `MODEL NOT READY` omitted (not faked) |
| Comfort | `comfortStatus` | `o1_comfort_validation.status` | PASS/FAIL from comfort validation row |
| Safety | `safetyStatus` | `o1_service.get_safety_checks()` | BLOCKED if any check failed |
| Telemetry age | `telemetry.ageSeconds` | `telemetry_health().telemetry_age_seconds` | Latest `o1_telemetry_sample` timestamp vs now |
| `dataState` | `dataState` | `_data_state()` | LIVE / STALE / LAST_KNOWN / AWAITING_TELEMETRY / ENGINE_OFFLINE / ERROR |
| Last evaluation | `lastEvaluationAt` | `o1_service.get_state().timestamp` | Pipeline clock |

If a field is missing, the metric value is `null` with `unavailableReason` (UI: DATA NOT AVAILABLE).
