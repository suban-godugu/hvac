# O10–O13 data contract

## Pipeline

```
hvac_telemetry (DEMO or BMS)
  → evaluate_o10 / o11 / o12 / o13
  → hvac_optimization_results + hvac_optimization_candidates
  → GET dashboard / GET opportunities/{id}
  → Ventilation dashboard cards + detail pages
```

Demo snapshots use `source=DEMO` (label **DEMO / TEST TELEMETRY**).  
`HVAC_ALLOW_DEMO_TELEMETRY=0` disables DEMO/SIMULATION rows (telemetry UNAVAILABLE until real ingest).

Live age: `VENTILATION_LIVE_SECONDS` (default 60). States: **LIVE | STALE | UNAVAILABLE | ERROR**.

## HVACOpportunityResult

| Field | Notes |
| --- | --- |
| opportunityId, code, name, description, status, priority | Catalog |
| telemetry.state / lastUpdated / ageSeconds / source | Never fabricate LIVE |
| current.values / optimized.values | Nullable measurements |
| energy.instantaneousKw / dailyKwh | Signed kW (negative = reduction); kWh/day |
| confidence | 0–1 fraction |
| guardrails.passed | Boolean or null |
| recommendation.action / rationale | Backend-generated text |
| candidates | Engine-generated (O10/O12) |

Missing measurements → HTTP **200**, `status=UNAVAILABLE`, numeric fields `null`. Unknown id → **404**. Evaluator crash → **500**.

## Endpoints

- `GET /api/agents/ventilation-airflow/dashboard`
- `GET /api/ventilation-airflow/dashboard` (same payload)
- `GET /api/agents/ventilation-airflow/opportunities/O10` … `O13`
- `GET /api/ventilation-airflow/opportunities/{id}` and `.../state` (same contract)

## KPI formulas (dashboard summary)

- active = count status not UNAVAILABLE/ERROR  
- optimal / ready / warning from status  
- energySavingsKw = sum of instantaneousKw  
- dailySavingsKwh = sum of dailyKwh  
- iaqCompliancePercent = share of O12/O13 `iaq_compliance == PASS`

## Formatters

`frontend/lib/hvac/formatters.ts` and `backend/services/ventilation_formatters.py`:

- percent: `|x|≤1` → ×100; else already percent; `|x|>1000` invalid  
- null/NaN/Infinity → `—`
