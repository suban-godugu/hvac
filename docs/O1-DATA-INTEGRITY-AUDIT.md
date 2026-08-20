# O1 Data Integrity Audit

Date: 2026-08-19. Scope: Optimum Start/Stop dashboard path (`/api/agents/scheduling/o1/*` + `optimum-start-stop/page.tsx` + SQLite O1 tables).

## P0 — resolved on O1 dashboard path

| Finding | Status |
| --- | --- |
| `o1_service` hardcoded 07:18 / 16:45 / 2.55 hrs / R² 0.924 | Replaced by pipeline + SQLite |
| POST `/o1/verify` static `"07:54"` / `"VERIFIED"` | Reads persisted command + live telemetry; FAILED if stale/missing |
| Fake VERIFIED calibration auto-seed (`_ensure_initial_records`) | Removed |
| Frontend thermal fallback 0.924 / 4,320 cycles | Removed; MODEL NOT READY if unevaluated |
| Frontend energy $5.21 / 12/12 PASSED / 2s HEALTHY | Wired to `energyData` / safety counts / telemetry health |
| Verified savings shown without VERIFIED status | KPI and energy panel require `verification_status=VERIFIED` |
| Missing values coerced to 0 | Ingest stores `null` + quality MISSING |

## P1 — remaining (out of O1 page or physics defaults)

| Finding | Severity | Notes |
| --- | --- | --- |
| `ThermalResponsePredictor` default α=14.5 when no ACTIVE model | P1 | Labeled PHYSICS_FALLBACK; not presented as R² |
| `GET /api/agents/scheduling/activity` still static O1–O4 log including 07:18 | P1 | Shared scheduling overview, not O1 studio routes |
| `frontend/components/scheduling/cards/O1OptimumStartStopCard.tsx` hardcoded 07:18 | P2 | Different surface than the O1 page |
| `database/seed/seed_data.py` historical thermal rows include a 07:18 start | P2 | Catalog/history seed; not `o1_calibration_records` VERIFIED savings |
| Physics fallback coefficients in `predict_time_to_target` if registry empty | P1 | Honest status PHYSICS_FALLBACK / MODEL NOT READY on thermal card |

## P2 / P3

- Worker `GET /agents/scheduling/o1` still uses in-memory `OptimumStartStopEngine` (by design; do not delete).
- O2–O20 services unchanged; some still mock on their own pages.
- `datetime.utcnow()` deprecation warnings (P3).

## Readiness scores (O1 studio only)

| Area | Score | Comment |
| --- | --- | --- |
| Schema + Alembic | 0.9 | 0003 O1 tables; 0004 decision-column alignment to legacy SQLite |
| Ingestion / health | 0.85 | Config map; HEALTHY/STALE/MISSING/BAD_QUALITY |
| Model honesty | 0.85 | Held-out MAE/RMSE/R²; MODEL_NOT_READY if &lt;8 samples; no 0.92 floor |
| Optimization persist | 0.85 | Candidates, guardrails, PREDICTED savings |
| BMS verify | 0.75 | Persist PENDING; verify reads telemetry; no BACnet gateway ack in this pass |
| UI wiring | 0.9 | Layout preserved; mocks stripped on the O1 page |
| Tests | 0.8 | `backend/tests/test_o1_pipeline.py` (telemetry, model, 06:00–08:00 occupancy, savings, verify) |

**Overall O1 dashboard integrity: 0.84** — safe to treat the studio page as pipeline-backed. Do not treat SIMULATED seed or PHYSICS_FALLBACK as production M&V.
