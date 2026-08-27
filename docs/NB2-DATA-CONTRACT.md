# NB2 Data Contract — AI record ↔ DB ↔ UI

Stage H5 contract for the NB2 closed loop. **Missing ≠ 0.** Simulation never masquerades as LIVE.

## Canonical AI record (normalized)

Built by `backend/services/ai_normalized_telemetry.py` → `build_ai_records` / `GET /api/platform/ai/normalized`.

| Field | Meaning | Source points (examples) | Quality |
|---|---|---|---|
| `Outdoor_Temp` | Outside air °C | `SITE.outdoor_air_temperature` | GOOD / STALE / BAD / MISSING |
| `Indoor_Temp` | Zone air °C | `ZONE-01.zone_temperature` | same |
| `Setpoint` | Zone cooling SP °C | `ZONE-01.cooling_setpoint` | same |
| `Fan_Speed` | Fan % | `AHU-01.fan_speed` | same |
| `Occupancy` | 0–1 fraction | `ZONE-01.occupancy` | same |
| `HVAC_Power` | Plant power kW | `CH-01.power` | same |
| `Equipment_Status` | Enable/status | `AHU-01.enable`, `CH-01.status` | same |
| `source` | Provenance | `LIVE_BMS` \| `SIMULATION` \| `DEMO` \| `HISTORIAN` | — |
| `quality` | Sample quality | From `canonical_telemetry.quality` | — |
| `timestamp` | Sample time (UTC) | Historian / poll | — |

**Rules**

1. Never invent numeric zeros for MISSING points — use `null` / omit.
2. LIVE and SIMULATION RLS rows never mix (`source_mode` split).
3. LSTM / Safe RL / UI treat `MODEL PREDICTION` as advisory — not LIVE BMS.
4. Stage G writable allowlist default: `ZONE-01.cooling_setpoint` only.

## DB mapping

| Layer | Table / store | Notes |
|---|---|---|
| Raw historian | `canonical_telemetry` | `(building_id, point_id, timestamp)`; retention see `database/RETENTION.md` |
| Ring buffer | in-memory `timeseries_buffer` | Stage B window API |
| RLS θ | `rls_model_state` | LIVE_BMS vs SIMULATION |
| LSTM artifacts | `ml_model_registry` + files under `ARTIFACT_DIR/lstm/{model_key}/{version}.pkl` | Status: MODEL_READY / SUPERSEDED / MODEL_NOT_READY |
| Safe RL | `safe_rl_decisions` | Recommend + Stage H `realized_reward*` after VERIFIED |
| Commands | `control_commands` | PROPOSED → APPROVED → APPLIED → VERIFIED |
| Audit | `control_audit_logs` | Rule Engine + `RLS_POST_VERIFY` |

## UI surfaces

| Surface | Consumes |
|---|---|
| `/ml` | RLS status, LSTM forecast/status (`model_version`), Safe RL recommend, Rule Engine |
| `/platform/bms` | Stage G checklist, supervised write lifecycle |
| `/readyz` | DB, control watchdog, `ai_watchdogs`, `edge` |

## Closed loop (Stage H)

```
Sense (canonical) → Learn (RLS tick / post-verify)
  → Predict (LSTM) → Optimize (Safe RL recommend)
  → Validate (Rule Engine) → Control (Stage G apply)
  → Measure (verify + reward) → Learn
```

Recommend alone never calls `command_writer` / `execute_write` (`wrote_setpoints: false`).

## Ops checklist (manual — not code gaps)

1. Lab: `HVAC_BMS_LAB=1` + Live BMS → `python scripts/stage_a_commission.py` (or pytest Stage A).
2. LSTM: `pip install -r backend/requirements-lstm.txt` then `POST /ai/lstm/train`.
3. Stage G: enable writes only after G1 checklist; expand `HVAC_STAGE_G_WRITABLE_POINTS` after `verify_stats.expand_ready`.
4. Optional: `HVAC_SAFE_RL_TICK_SECONDS>0` for job_worker recommend tick; `HVAC_LSTM_REQUIRE_TORCH=1` to hard-require torch.
