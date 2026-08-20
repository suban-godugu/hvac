# O3 dashboard KPI mapping

`GET /api/scheduling/dashboard` → `_build_o3()` → `MasterAHUSATOptimizationEngine.evaluate(sim)`.

`current_state` does **not** include `master_demand_pct`. Dashboard computes third-highest `vav_zones[].cooling_demand_pct` (same method as the engine).

| UI KPI | API field | Source |
| --- | --- | --- |
| Current SAT | `primaryMetric` | Sim AHU `sat_actual` / `sat` |
| Optimized SAT | secondary | `recommended_action.proposed_value` else AHU `sat_setpoint` |
| SAT Reset | secondary / `satReset` | optimized − current |
| Master Demand | secondary / `masterDemand` | Third-highest VAV cooling demand from `current_state.vav_zones` |
| Chiller Impact | secondary / `chillerImpact` | `expected_impact.chiller_power_saved_kw` (**predicted**) |
| Fan Impact | secondary / `fanImpact` | `expected_impact.fan_power_penalty_kw` (**predicted**) |
| Confidence | `confidence` | Engine `confidence` (currently a constant inside `o3_engine.py`; passed through, not independently modeled) |
| Safety | `safetyStatus` | PASS if current SAT ≥ `current_state.min_sat_limit` (freeze clamp), else BLOCKED |
| Telemetry | `telemetry` | Sim cycle age |

Comfort % is not published by the O3 engine; it is omitted (`null` / DATA NOT AVAILABLE) rather than copied from O1 or hardcoded 100%.
