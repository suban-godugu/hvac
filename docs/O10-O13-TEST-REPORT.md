# O10–O13 test report

Date: 2026-08-19

## Commands

```
python -m unittest backend.tests.test_ventilation_dashboard
python -m unittest backend.tests.test_official_opportunities tests.test_ventilation_airflow_integration
npx tsc --noEmit   # frontend/
```

## Results

| Suite | Result |
| --- | --- |
| backend.tests.test_ventilation_dashboard | 13 passed |
| test_official_opportunities + ventilation integration | 19 passed |
| TypeScript `tsc --noEmit` | pass |

## Coverage in test_ventilation_dashboard

1. Dashboard payload shape and summary totals  
2. O10–O13 normalized contract  
3. Null/missing telemetry on engines (`evaluate_o10({})`, `evaluate_o12({})`)  
4. Stale telemetry → `telemetry.state=STALE`  
5. Unknown opportunity raises ValueError (API maps to 404)  
6. Percent 0.685 → 68.5%, 68.5 → 68.5%, 6850 rejected  
7. CFM 8200 → 8,200 CFM; 6850 → 6,850 CFM  
8. 3.31 kW; 46.3 kWh/day; enthalpy null → —  
9. Enthalpy advantage when OA/RA present  
10. CO₂ compliance PASS at 560 ppm  
11. CO safety FAIL at 62 ppm  
12. Energy aggregation equals sum of opportunity kW  
13. O10 candidates generated; SELECTED matches optimized damper  

## Not run here

`next build` / `next lint` (tsc passed). Restart FastAPI so Alembic 0006 is loaded if the server was started before this change.
