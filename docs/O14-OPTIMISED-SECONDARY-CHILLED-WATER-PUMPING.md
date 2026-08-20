# O14 — Optimised Secondary Chilled Water Pumping (differential pressure reset)

## 1. Purpose

O14 minimises secondary chilled-water (SCHW) pumping energy by resetting the chilled-water differential-pressure setpoint from valve demand, then applying that recommendation through the shared HVAC command / safety / BMS / verification pipeline.

Canonical UI route: `/agents/variable-speed/chilled-water-pump`  
(The path `/agents/variable-speed/secondary-chilled-water-pumping` redirects here. No duplicate route tree.)

## 2. Engineering concept

### SOURCE-GUIDE REQUIREMENTS

NSW OEH / AIRAH *I am your optimisation guide: HVAC systems* (OEH 2015/0317), Opportunity 14:

- Applies to **secondary CHW systems with 2-port modulating valves** (variable flow).
- SCHW distributes CHW from the plant room to AHUs/FCUs. **Primary pumps** circulate CHW through chillers.
- Typical waste: a **constant DP setpoint** chosen for peak design flow, so the pump holds too much pressure at part load.
- Reset rule: **when all CHW valves are less than 95% open**, reduce SCHW pump speed incrementally (**CHW pressure setpoint reset**) to **hold the most-open valve at 95%**.
- Deliver CHW at the **lowest pressure that still satisfies all users**.
- Guide-stated typical potential: **up to 30% energy reduction on SCHW pumps**. This is **not** treated as verified savings.
- Minimum information: cooling call (enable pumps), index-run CHW differential pressure, CHW valve positions (percentile / most-open), software to adjust speed and number of pumps at intervals.
- Minimum equipment: index-run DP sensor, DDC, SCHW software, SCHW pumps, VSDs.
- Constant-flow 3-port systems must be converted to 2-port before this strategy applies (site change; not auto-invented in software).

### IMPLEMENTATION DETAILS

- Supervisory output is **`SCHW.DPSetpoint`**. Speed trim is reported as a configurable companion, not a substitute for the BMS DP loop.
- Pump staging is **not auto-executed** (guide mentions speed and number of pumps; no staging formula is given).
- Affinity-law predicted power (Appendix D of the guide: power varies approximately with speed cubed) is labeled **PREDICTED** only.

### CONFIGURABLE PARAMETERS

Stored in `o14_config` (defaults labeled in API `labels`):

| Parameter | Default | Label |
|---|---|---|
| `most_open_valve_target_pct` | 95 | SOURCE-GUIDE |
| `dp_setpoint_trim` | 0.5 | CONFIGURABLE_DEFAULT |
| `speed_trim_pct` | 2.0 | CONFIGURABLE_DEFAULT |
| min/max DP, flow, speed | null | CONFIGURABLE (no write if null) |
| `max_speed_step_pct` | 25 | CONFIGURABLE_DEFAULT |
| `control_mode` | ADVISORY | IMPLEMENTATION |

## 3. Inputs

Canonical telemetry point aliases (LIVE_BMS + GOOD only counts as live):

- `SCHW.IndexDP` / `O14.INDEX_DP`
- `SCHW.DPSetpoint` / `O14.DP_SETPOINT`
- `SCHW.MostOpenValve` / `O14.MOST_OPEN_VALVE_PCT`
- `SCHW.Flow`, `SCHW.Speed`, `SCHW.Power`, `SCHW.SupplyTemp`, `SCHW.ReturnTemp`, `SCHW.Load`, `SCHW.CoolingCall`, `SCHW.PumpsRunning`

## 4. Outputs

Recommended DP setpoint, optional recommended speed, recommendation state, safety gates, predicted (not verified) power delta.

## 5. Control strategy

DP reset toward most-open valve = 95%. HOLD at target. HOLD at 100% open with a balancing note (no invented boost formula). HOLD when cooling call is off.

## 6. Optimization logic

See `backend/agents/official_opportunities/o14_secondary_chw.py`.

## 7. Safety gates

Authoritative backend: `evaluate_dispatch` + O14 engineering/write gates. SAFE_MODE, SIMULATION, STALE, BAD, BMS offline block writes.

## 8. Telemetry requirements

Canonical contract: building/equipment/point, timestamp, value, unit, quality (GOOD/BAD/STALE/UNKNOWN), source (LIVE_BMS / SIMULATION / OTHER). Simulation is never LIVE.

## 9. BMS points

Write target: `SCHW.DPSetpoint`. Production gateway must be connected. Simulator writes fail.

## 10. Database entities

- Shared: `canonical_telemetry`, `control_commands`, `agent_runs`, `opportunity_audit_events`, `variable_speed_equipment`
- O14: `o14_config`, `o14_system_snapshots`, `o14_recommendations` (Alembic `0011_o14_secondary_chw`)

## 11. API endpoints

Prefix: `/api/agents/variable-speed/o14`

GET dashboard, telemetry, state, recommendation, kpis, pumps, history, safety, commands, runs, audit, config  
POST telemetry, optimize, commands, commands/{id}/apply|verify|rollback, config, safe-mode

Errors: `{ code, message, request_id }`.

## 12. Command lifecycle

PROPOSED → APPROVAL_REQUIRED (if mode) → APPLYING → APPLIED → VERIFYING → VERIFIED | ROLLBACK_REQUIRED → ROLLED_BACK. Idempotent `command_id`. Default mode ADVISORY does not write.

## 13. Verification

Re-read BMS point vs `new_value` within configurable tolerance. Failure triggers rollback.

## 14. Rollback

Writes previous DP setpoint through the shared runtime rollback helper.

## 15. UI workflow

Header (BMS / telemetry / mode / safety / optimization / timestamps / SAFE MODE) → KPIs → system state → recommendation → history (1h–30d) → pumps → safety → confirm apply → command history.

## 16. Testing

`python -m unittest backend.tests.test_o14 -q`

## 17. Configuration

GET/POST `/config`.

## 18. Simulation behavior

Explicit SIMULATION source is labeled SIMULATION and cannot dispatch.

## 19. Production requirements

Physical BMS + index DP sensor + valve positions + SCHW VSDs + 2-port valves. Until BMS is connected, the interface is complete and writes are rejected honestly (BMS OFFLINE / not LIVE).
