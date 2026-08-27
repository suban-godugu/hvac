---
title: HVAC Agents API
emoji: "🌡️"
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
startup_duration_timeout: 1h
pinned: false
short_description: FastAPI O1-O20 HVAC agents (simulation, writes off)
---

# HVAC agents API (Hugging Face)

Phase 2 demo backend: **API + control worker**. The Next.js Control Center is on **Netlify**; the live FastAPI demo is on **Render**.

| Setting | Value |
| --- | --- |
| `HVAC_BMS_MODE` | `simulation` |
| `HVAC_USE_SIMULATION` | `1` (Dataset feeder) |
| `HVAC_BMS_WRITE_ENABLED` | `0` |
| `HVAC_ALLOW_SIM_WRITES` | `0` |

- OpenAPI: `/docs`
- Health: `/healthz`
- Status: `/api/platform/status` (`plantMode=DATASET`, telemetry `SIMULATED`, never `LIVE`)

Netlify / Render env:

```
HVAC_API_ORIGIN=https://<hvac-api>.onrender.com
NEXT_PUBLIC_API_URL=https://<hvac-api>.onrender.com/api
```
