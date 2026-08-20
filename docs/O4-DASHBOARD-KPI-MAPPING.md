# O4 dashboard KPI mapping

`GET /api/scheduling/dashboard` → `_build_o4()` → `ChillerCompressorStagingEngine.evaluate(sim)`.

| UI KPI | API field | Source |
| --- | --- | --- |
| Current Stage | `primaryMetric` | Running entries in `current_state.compressor_stages` (`stage_id@load_pct`) |
| Optimized Stage | secondary | Active chiller count ±1 from recommended action id (`stage-up` / `stage-down`) |
| Plant Load | secondary / `plantLoadTons` | `current_state.total_tons` |
| Active Chillers | secondary / `activeChillers` | `current_state.active_chillers_count` |
| Energy Impact | secondary / `impact.energy` | `expected_impact.estimated_power_kw_impact` labeled **predicted** |
| Runtime Impact | secondary / `impact.runtime` | **Not published by O4 engine** → `null` + unavailable reason |
| Confidence | `confidence` | Engine `confidence` |
| Safety | `safetyStatus` | `capacity_sufficiency` (`SUFFICIENT` shown as PASS) |
| Telemetry | `telemetry` | Sim cycle age |

Do not treat engine-internal constants (e.g. `+= 18.5` kW in `o4_engine.py`) as verified plant savings. The dashboard only surfaces `expected_impact` as predicted.
