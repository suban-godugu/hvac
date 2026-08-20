# O2 dashboard KPI mapping

`GET /api/scheduling/dashboard` → `_build_o2()` → `SpaceTemperatureOptimizationEngine.evaluate(sim)`.

Sim snapshot: `sim_service.step(0)` (or `get_latest_status` if present). Not O1 telemetry.

| UI KPI | API field | Engine / sim field | Source |
| --- | --- | --- | --- |
| Current Avg Temp | `primaryMetric` | mean `current_state.zones[].actual_temperature` | O2 engine zone parse of sim VAV temps |
| Optimized Setpoint | secondary | `recommended_action.proposed_value`, else mean cooling/setpoint | O2 optimizer |
| Control Band | secondary / `controlBand` | mean setpoint ± mean `deadband`/2 | Zone deadbands from engine |
| Zone Coverage | secondary / `zoneCoverage` | `len(engine zones)/len(sim VAV zones)` | Actual counts, not 48/48 |
| Comfort | secondary / `comfortStatus` | share of zones with `comfort_status` in OPTIMAL/ACCEPTABLE/PASS | Engine zone flags |
| Energy Impact | secondary / `impact.energy` | `expected_impact.estimated_power_kw_impact` labeled **predicted** | Engine estimate, not verified savings |
| Confidence | `confidence` | `evaluation.confidence` as percent | Engine-reported |
| Telemetry | `telemetry` | sim cycle age (0s when `step(0)` succeeds) | Simulator, not BMS live bus |

O2 does not read `o1_telemetry_sample` or O1 decisions.
