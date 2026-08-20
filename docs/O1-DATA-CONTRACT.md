# O1 Data Contract

Every visible O1 KPI, chart, and table maps to an existing `/api/agents/scheduling/o1/*` endpoint, a service method, and a SQLite field. Missing data renders `NO LIVE DATA` / `MODEL NOT READY` / `TELEMETRY STALE` — never a hardcoded 07:18, 0.924, or $5.21.

| UI element | Endpoint | Service | Table / field | Unit | Fallback |
| --- | --- | --- | --- | --- | --- |
| Start delay KPI | GET `.../o1/state` | `O1Service.get_state` | `o1_decisions.start_delay_min` | min | NO LIVE DATA |
| Coast stop KPI | GET `.../o1/state` | same | `o1_decisions.coast_advance_min` | min | NO LIVE DATA |
| Runtime saved KPI | GET `.../o1/state` | same | `o1_savings_verification.runtime_saved` | min | NO LIVE DATA; verified figure only if `verification_status=VERIFIED` |
| Model confidence | GET `.../o1/state` | `get_active_model` | `o1_model.mae_minutes` → derived % | % | MODEL NOT READY |
| Zone / target | GET `.../o1/state` | `live_value(ZONE_TEMP)` / `o1_configuration.comfort_target_c` | °C | NO LIVE DATA |
| Predicted target reached | GET `.../o1/state` | selected `o1_start_candidate.predicted_target_reached` | HH:MM | NO LIVE DATA |
| Occupancy window | GET `.../o1/state` | `o1_configuration.occupancy_start/end` | HH:MM | NO LIVE DATA |
| Telemetry KPI | GET `.../o1/state` + `.../o1/telemetry` | `telemetry_health` | `o1_telemetry_sample.timestamp/quality` | s | TELEMETRY STALE / NO LIVE DATA |
| Thermal R²/MAE/RMSE | GET `.../o1/thermal-model` | `O1Service.get_thermal_model` | `o1_model.r2_score/mae_minutes/rmse_minutes` | — | MODEL NOT READY (null metrics) |
| Trajectory chart | GET `.../o1/trajectory` | predicted pull-down from selected start | °C | empty chart |
| Start candidates | GET `.../o1/start-candidates` | `o1_start_candidate` | HH:MM, min, kWh | empty table |
| Coast candidates | GET `.../o1/coast-candidates` | `o1_stop_candidate` | HH:MM, °C, min | empty table |
| Decision card | GET `.../o1/decision` | `o1_decisions` + selected candidates | — | NO LIVE DATA |
| Timeline | GET `.../o1/timeline` | derived from decision | — | empty |
| Safety table | GET `.../o1/safety` | `o1_safety_validation` | PASS/FAIL/BLOCKED | empty; badge `{passed}/{total}` |
| BMS action | GET `.../o1/bms-action` | `o1_actions` | status | NO_COMMAND / PENDING |
| History | GET `.../o1/history?limit&offset` | `o1_calibration_records` | mixed | empty; `verification` is PREDICTED unless verified |
| Energy panel | GET `.../o1/energy` | `o1_savings_verification` + `o1_energy_baseline` | h, kWh, USD | UNAVAILABLE; **Verified Savings** only if VERIFIED |
| Activity | GET `.../o1/activity` | `o1_activity_log.event_type/message` | — | empty |
| Optimize | POST `.../o1/optimize` | persist `o1_actions` DISPATCHED/PENDING | — | BLOCKED if safety fails |
| Verify | POST `.../o1/verify` | read-back telemetry + update action | — | FAILED if stale/missing; never static 07:54 |
| Rollback | POST `.../o1/rollback` | new action ROLLED_BACK | — | — |

Signal map: `backend/config/o1_point_map.json` → `o1_point_map`. Ingestion never writes 0 for a missing value.
