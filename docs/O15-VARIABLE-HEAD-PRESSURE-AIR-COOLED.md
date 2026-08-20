# O15 — Variable Head Pressure Control (Air-Cooled Condensers)

## 1. Purpose

O15 is a supervisory optimization vertical slice for **variable head-pressure control on air-cooled condensers**. Condenser-fan VSDs (or EC motors) modulate heat rejection so condensing pressure/temperature can follow outdoor conditions instead of a peak-design constant head-pressure setpoint.

Canonical UI: `/agents/variable-speed/air-cooled-head-pressure`  
Canonical API: `/api/agents/variable-speed/o15`

No application login is used.

## 2. HVAC guide reference

NSW OEH / AIRAH *I am your optimisation guide: HVAC systems* (OEH 2015/0317), Opportunity 15 (printed pp. 71–73).

## 3. Engineering concept

### SOURCE-GUIDE REQUIREMENTS

- VSDs (or EC motors) on **condenser fans** control head/condensing pressure more efficiently than on/off or staged fans.
- At lower ambient, condenser capacity rises and load typically falls; condensing pressure can be reduced (constant **or floating** setpoint).
- **Over-condensing is harmful** (TXV operation, liquid-line flashing, oil return).
- **Typical air-cooled condensing temperature is 8–12°C above ambient dry-bulb.**
- Maintain that condition by modulating fan speed (heat rejection).
- Minimum information: HP setpoint, heat-rejection control strategy, outdoor air temperature (desirable), refrigerant type.
- Typical potential: **up to 30% condenser-fan energy** — treated as guide typical potential, **not verified savings**.
- Manufacturer advice is required. Complements O9 (EEVs).

### IMPLEMENTATION DETAILS

- Supervisory write point: `ACC.FanSpeed` (fan speed % to the BMS heat-rejection loop).
- Floating condensing-temperature target = **OAT + approach**, with approach clamped to the guide 8–12°C range.
- Numeric **head-pressure** target is issued **only** when a site `saturation_curve_json` is configured. The guide does not provide a refrigerant P–T table.

### CONFIGURABLE PARAMETERS

Stored in `o15_config`. API `labels` mark origin:

| Parameter | Default | Label |
|---|---|---|
| `approach_c` | 10 | SOURCE-GUIDE range 8–12°C; CONFIGURABLE within range |
| `approach_min_c` / `approach_max_c` | 8 / 12 | SOURCE-GUIDE |
| `fan_trim_pct` | 2.0 | CONFIGURABLE_DEFAULT |
| `tcond_deadband_c` | 0.5 | CONFIGURABLE_DEFAULT |
| `max_fan_step_pct` | 25 | CONFIGURABLE_DEFAULT |
| min/max HP, Tcond, fan speed | null | CONFIGURABLE (no invented envelope) |
| `saturation_curve_json` | null | CONFIGURABLE |
| `refrigerant` | null | CONFIGURABLE |
| `control_mode` | ADVISORY | IMPLEMENTATION |

### ASSUMPTIONS / MISSING DATA

The guide does **not** specify: numeric psig min/max, an OAT→psig formula, fan trim step, deadband, or a refrigerant saturation table. Those are never presented as guide requirements.

## 4. System inputs

Canonical aliases (LIVE_BMS + GOOD required for `live`):

- `ACC.OAT` / `O15.OAT` / `WEATHER.OutdoorDryBulb`
- `ACC.HeadPressure`, `ACC.HeadPressureSetpoint`
- `ACC.CondTemp`
- `ACC.FanSpeed`, `ACC.FanState`, `ACC.FanPower`, `ACC.FansRunning`
- `ACC.CompressorState`, `ACC.CompressorPower`
- `ACC.Load`, `ACC.Power`, `ACC.RH`, `ACC.Alarm`

Missing values remain `null` / Unavailable. Zeros are not substituted for missing telemetry.

## 5. System outputs

Recommended condensing temperature, optional recommended HP (curve only), recommended fan speed, recommendation state, safety gates, predicted (not verified) fan power delta via affinity if fan kW and speed exist.

## 6. Control strategy

If OAT is present: target Tcond = OAT + approach (8–12°C). If measured Tcond is above target + deadband, increase fan speed by `fan_trim_pct`. If below, decrease fan speed to avoid over-condensing. HOLD inside deadband. REJECT on configured envelopes or rate-of-change.

## 7. Optimization logic

`backend/agents/official_opportunities/o15_air_cooled_hp.py` (`ENGINE_VERSION = o15-float-hp-1.0`).

## 8. Safety limits

Authoritative: engine gates + `evaluate_dispatch`. SAFE_MODE, SIMULATION, STALE, BAD, BMS offline, advisory mode, and engineering limits block writes. Frontend does not compute safety independently.

## 9. BMS points

Write: `ACC.FanSpeed`. Production gateway must be connected. Simulator writes fail honestly.

## 10. Telemetry requirements

Canonical contract: building/equipment/point, timestamp, value, unit, quality (GOOD/BAD/STALE/UNKNOWN), source (LIVE / SIMULATION / OTHER). Simulation is never labeled LIVE.

## 11. Agent workflow

Telemetry → O15 state builder (`sample_o15`) → optimization engine → SafetyEngine → recommendation → ADVISORY / APPROVAL_REQUIRED / AUTO → BMS apply → verify → rollback → audit → historian snapshots.

Shared runtime: `evaluate_o15` in `official_opportunity_runtime` delegates to `o15_service`.

## 12. API endpoints

Prefix `/api/agents/variable-speed/o15`:

- GET `dashboard`, `state`, `telemetry`, `kpis`, `condensers`, `fans`, `recommendation`, `safety`, `history`, `commands`, `runs`, `audit`, `config`
- POST `telemetry`, `optimize`, `commands`, `commands/{id}/apply|verify|rollback`, `config`, `safe-mode`

History CSV: `GET /history?hours=&format=csv`

Errors: `{ code, message, request_id }`.

Legacy `/api/variable-speed/o15/*` remains as a thin caller of `evaluate_o15` (same engine). The domain controller above is canonical.

## 13. Database schema

Alembic `0012_o15_air_cooled_hp`:

- `o15_config`
- `o15_system_snapshots` (indexes on equipment/building + timestamp)
- `o15_recommendations`

Shared: `canonical_telemetry`, `control_commands` (`UNIQUE(opportunity, command_id)`), `agent_runs`, `opportunity_audit_events`.

## 14. Command lifecycle

Statuses: PROPOSED, APPROVAL_REQUIRED, APPROVED, APPLYING, APPLIED, VERIFYING, VERIFIED, ROLLBACK_REQUIRED, ROLLED_BACK, REJECTED, FAILED.

Idempotent on `command_id`. Double Apply does not issue two BMS writes.

Default control mode is **ADVISORY** (recommendation only).

## 15. Verification

After apply, re-read telemetry (`verify_command`). Failure triggers rollback. Before/after/verification persist on the command record.

## 16. Rollback

`POST /commands/{id}/rollback` via shared rollback runtime.

## 17. UI workflow

Open O15 → KPIs / system path / condenser & fan tables from registry → recommendation + why (engine text) → safety panel → optimize → confirm apply → verify / rollback → audit timeline → historian windows 1h / 6h / 24h / 7d / 30d.

States: LOADING, LIVE, DEGRADED, NO_DATA, STALE, SIMULATION, ERROR, SAFE_MODE, BMS_OFFLINE.

## 18. Configuration

See table in §3. UI shows labels so CONFIGURABLE values are not presented as guide mandates.

## 19. Simulation behavior

`source=SIMULATION` → UI SIMULATION, `live=false`, dispatch rejects writes.

## 20. Production requirements

- HVAC deployment / BMS connected / real gateway
- Fresh GOOD LIVE telemetry (not SIMULATION)
- SAFE_MODE off
- Engineering + rate-of-change gates
- No conflicting command
- Command idempotency

## 21. Testing

Backend: `backend/tests/test_o15.py`, `test_official_opportunities.py` O15 cases.

E2E: catalog route + `frontend/e2e/o15-air-cooled.spec.ts`.
