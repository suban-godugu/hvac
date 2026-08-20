# O10–O13 integrity audit

Trace for displayed numbers after this rebuild.

## Dashboard KPIs

| UI | API | Source |
| --- | --- | --- |
| Active opportunities | summary.active / total | Count of O10–O13 statuses |
| Optimization status | summary.optimal, ready | Engine status strings |
| Energy / daily | summary.energySavingsKw, dailySavingsKwh | Sum of engine instantaneousKw / dailyKwh |
| IAQ | summary.iaqCompliancePercent | O12+O13 PASS share |
| Telemetry | telemetry.state · ageSeconds | Latest `hvac_telemetry.timestamp` |

## O10 Economy Cycle

| UI | Field | Source |
| --- | --- | --- |
| Current damper | current_value | hvac_telemetry.damper_percent |
| Optimized damper | optimized_value | evaluate_o10 (free-cooling trim, e.g. 82→68.5) |
| Enthalpy | enthalpy_advantage_kj_kg | h_ra − h_oa (Magnus psychrometric) or null |
| Energy / daily | energy.* | Fan+chiller delta vs OA mass flow × Δh |
| Candidates | candidates[] | BASELINE/MODERATE/OPTIMAL/AGGRESSIVE from same eval |
| Rationale | recommendation.rationale | Engine string |

## O11 Night Purge

Airflow current/optimized from supply_airflow_cfm and eligibility (window 21:00–06:00 Asia/Kolkata, occupancy, ΔT). Daytime DEMO snapshot is typically HOLD, not fake OPTIMAL.

## O12 DCV CO₂

optimized_airflow_cfm nullable; ASHRAE 62.1 people+area OA; IAQ PASS if CO₂ ≤ 800 ppm.

## O13 DCV CO

Airflow + CO ppm vs 50 ppm limit. Alarm → MAX_VENTILATION, energy not claimed as savings.

## Not used for dashboard/detail KPIs

- Leftover `O12OutdoorAirAgent` / `O11DemandVentilationAgent` defaults (17.5°C, 2400 CFM)
- `card_from_engine(live_fields=False)` nulling
- Synthetic `get_history` 8200/6850 series (still on /history, not cards)
- In-memory `VentilationTelemetryService` SIMULATION jitter (official O11/O13 sampler still ignores it)

Dashboard and `GET .../opportunities/O10` share `evaluate_opportunity`.
