# O1 Dataset Specification

Target: `time_to_target_minutes` — minutes of HVAC runtime predicted to bring zone temperature to the occupied comfort target.

## Source policy

All generated files under `data/o1/` are `source=SIMULATED` and `environment=development`. Existing `data/training/o1_training.jsonl` is treated as SIMULATED/dev unless a record is explicitly labeled otherwise. Do not relabel it as live BMS.

## Columns

| Column | Unit | Required | Range / notes |
| --- | --- | --- | --- |
| timestamp | ISO-8601 | yes | Sample time; reject future >5 min |
| zone_temperature | °C | yes for labeled rows | -5 to 45; missing → `null`, never 0 |
| outdoor_air_temperature | °C | yes | -30 to 55 |
| comfort_target | °C | yes | typically 21–25 |
| solar_w_m2 | W/m² | no | 0–1400 |
| time_to_target_minutes | min | target | ≥ 0; omit when sensors missing |
| quality | enum | yes | GOOD / STALE / BAD / MISSING |
| scenario | string | yes (sim) | see generator |
| source | string | yes | SIMULATED |
| building_id / zone_id | string | yes | catalog keys |
| occupancy_start / occupancy_end | HH:MM | yes | leakage: occupancy must not be used as a feature that encodes the target |
| equip_avail | 0/1 | no | HVAC unavailable scenarios |

## Sampling

Morning pre-cool window 05:00–08:00. One labeled pull-down event per simulated day per scenario. Generator default 40 rows × 11 scenarios.

## Missing / outlier policy

- Missing optional signals: `null`, never coerced to 0.
- Out-of-range values: quality `BAD`, excluded from training labels.
- Stale sensors: quality `STALE`, excluded from live inference inputs.

## Splits

70% train / 15% validation / 15% test, shuffled with a fixed seed. Split by `sample_id` after generation so days are mixed; do not train on test files.

## Leakage rules

- Do not use `optimized_start`, `energy_saved`, or post-occupancy temperatures as features for `time_to_target_minutes`.
- Do not use the same timestamp as both a training feature and a verification actual without a held-out split.
- Occupancy clock is a constraint for candidate windows, not a regression feature.

## Scenarios (generator)

hot_morning, mild_morning, cool_morning, high_mass, low_mass, occupied_early, stale_sensor, missing_sensor, weekend, holiday, hvac_unavailable.

Command: `python scripts/o1/generate_dataset.py --seed 42`
