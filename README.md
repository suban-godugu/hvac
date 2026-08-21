# HVAC Optimization Platform

Supervisory control for commercial HVAC, covering **O1–O20** from the NSW Office of Environment and Heritage / AIRAH guide *[Optimising your heating, ventilation and air conditioning systems](https://www.environment.nsw.gov.au/)*. The app evaluates live (or simulated) plant telemetry, proposes setpoints and schedules, and — only when every safety gate passes — can write to a BMS.

Simulation and live BMS writes are strictly separated. Missing telemetry is shown as **NO LIVE DATA** / **AWAITING TELEMETRY**. Guide “potential savings” are teaching figures, never treated as measured building savings.

| Layer | Stack |
| --- | --- |
| UI | Next.js 14, React 18, Tailwind, TanStack Query, Recharts |
| API | FastAPI 1.0 (`HVAC Optimization & Scheduling Supervisory Engine`) |
| Runtime | Safety → approval → apply → verify → rollback → audit |
| BMS | Simulator, BACnet, MQTT, REST, Modbus |
| Data | SQLite (local) or PostgreSQL / TimescaleDB (Docker & production) |
| ML | scikit-learn pipelines for thermal response, plant, and VFD models |

There is **no application login**. Opening `/` redirects to `/overview`. Production access is network and infrastructure, not JWT or sessions.

**Demo:** API snapshot on Hugging Face ([subhan07/hvac-agents](https://huggingface.co/subhan07/hvac-agents)). A **Docker Space** needs Hugging Face PRO (`python scripts/sync_hf_space.py --space`). Until then the live API is [hvac-two-kappa.vercel.app](https://hvac-two-kappa.vercel.app) (simulation, writes off). UI: [frontend-omega-five-11.vercel.app](https://frontend-omega-five-11.vercel.app).

---

## Architecture

```
Next.js (:3000)
    │  NEXT_PUBLIC_API_URL → http://localhost:8000/api
    ▼
FastAPI (:8000)     health: GET /healthz  ready: GET /readyz
    │
    ├─ Five agents (O1–O20)
    ├─ Control worker     python -m backend.workers.control_entrypoint
    ├─ Job worker         python -m backend.workers.job_worker   (retention / weather)
    └─ BMS gateway
           simulation  ──► in-process simulator (never reports production-connected)
           production  ──► BACnet | MQTT | REST | Modbus  (handshake required; no sim fallback)
                    ▼
         SQLite  or  TimescaleDB (+ Redis in compose)
```

Control path for a write:

**safety envelope → operational approval → apply → telemetry verify → rollback on failure → audit log**

`HVAC_SAFE_MODE=1` blocks all automatic writes. Approval is an operations workflow, not a login.

---

## Opportunity catalog (O1–O20)

Encoded from the OEH/AIRAH guide (catalog lives in `backend/services/official_catalog.py`; teaching copy in `backend/knowledge/hvac_guide_catalog.py`). The PDF is **not** read at runtime.

### Scheduling

| ID | Opportunity | UI |
| --- | --- | --- |
| O1 | Optimum start / stop | `/agents/scheduling/optimum-start-stop` |
| O2 | Space temperature setpoints & control bands | `/agents/scheduling/space-temperature` |
| O3 | Master AHU supply-air temperature | `/agents/scheduling/master-ahu-sat` |
| O4 | Chiller & compressor staging | `/agents/scheduling/chiller-staging` |

### Plant control

| ID | Opportunity | UI |
| --- | --- | --- |
| O5 | Duct static pressure reset | `/agents/plant-control/duct-static-pressure` |
| O6 | Heating hot water temperature reset | `/agents/plant-control/temperature-reset?mode=HHW` |
| O7 | Chilled water temperature reset | `/agents/plant-control/temperature-reset?mode=CHW` |
| O8 | Condenser water temperature reset | `/agents/plant-control/temperature-reset?mode=CW` |
| O9 | Electronic expansion valve (advisory retrofit) | `/agents/plant-control/electronic-expansion-valve` |

### Ventilation & airflow

| ID | Opportunity | UI |
| --- | --- | --- |
| O10 | Economy cycle | `/agents/ventilation-airflow/economy-cycle` |
| O11 | Night purge | `/agents/ventilation-airflow/night-purge` |
| O12 | Demand control ventilation — CO₂ | `/agents/ventilation-airflow/demand-ventilation` |
| O13 | Demand control ventilation — CO (carparks) | `/agents/ventilation-airflow/dcv-co` |

### Variable speed

| ID | Opportunity | UI |
| --- | --- | --- |
| O14 | Secondary chilled-water pumping | `/agents/variable-speed/chilled-water-pump` |
| O15 | Variable head pressure — air-cooled | `/agents/variable-speed/air-cooled-head-pressure` |
| O16 | Variable head pressure — water-cooled | `/agents/variable-speed/water-cooled-head-pressure` |

### Operations & maintenance

| ID | Opportunity | Kind | UI |
| --- | --- | --- | --- |
| O17 | Energy management planning | Advisory | `/agents/operations-maintenance/energy-management-planning` |
| O18 | Training & awareness | Advisory only | `/agents/operations-maintenance/training-awareness` |
| O19 | Energy-efficiency maintenance | Work-order only | `/agents/operations-maintenance/equipment-maintenance` |
| O20 | Control-software change control | Change-request only — never auto-deploys firmware or logic | `/agents/operations-maintenance/control-software` |

Platform pages: `/overview`, `/agents`, `/platform/bms`, `/platform/telemetry`, `/ml`.

---

## Safety and BMS modes

| Setting | Behaviour |
| --- | --- |
| `HVAC_BMS_MODE=simulation` | Simulator only. `is_production_connected()` is always false. |
| `HVAC_BMS_MODE=production` | Requires `HVAC_BMS_PROTOCOL=bacnet\|mqtt\|rest\|modbus`. Handshake required. **Never** falls back to the simulator. `HVAC_BMS_CONNECTED` is ignored. |
| `HVAC_BMS_WRITE_ENABLED=0` | Default. All writes return `WRITE_DISABLED` (Phase 1). |
| `HVAC_SAFE_MODE=1` | Blocks every automatic write. |

A live write additionally requires: **LIVE + GOOD + FRESH** telemetry, BMS connected, engineering limits, safety contract, operating mode, and operational approval.

---

## Quick start (local, SQLite)

Requires **Python 3.12**, **Node 20**, and a clone of this repo.

```bash
cp .env.example .env
```

API (from the **repository root** so `backend.main` and imports resolve):

```bash
pip install -r backend/requirements.txt
set PYTHONPATH=.
uvicorn backend.main:app --reload --port 8000
```

On PowerShell:

```powershell
Copy-Item .env.example .env
pip install -r backend/requirements.txt
$env:PYTHONPATH = "."
uvicorn backend.main:app --reload --port 8000
```

UI:

```bash
cd frontend
npm install
npm run dev
```

| Service | URL |
| --- | --- |
| Dashboard | http://localhost:3000 → `/overview` |
| OpenAPI | http://localhost:8000/docs |
| Health | http://localhost:8000/healthz |

SQLite file: `database/hvac_supervisory.db`. Backup/restore notes are in [`docs/operations.md`](docs/operations.md).

Optional workers (same `PYTHONPATH`):

```bash
python -m backend.workers.control_entrypoint
python -m backend.workers.job_worker
```

Set `HVAC_START_CONTROL_WORKER=0` on the API process if you run the control loop as a separate process (as Docker Compose does).

---

## Demo deploy (Phase 2)

Hugging Face Docker Spaces require PRO. The API image is published as a model repo:

```bash
python scripts/sync_hf_space.py
# after PRO:
python scripts/sync_hf_space.py --space
```

Until a Docker Space is available, the live FastAPI demo is on Vercel (`https://hvac-two-kappa.vercel.app`) with `HVAC_BMS_MODE=simulation` and **simulator-only** control (`SIM WRITE ENABLED`). Production BMS writes stay off.

Frontend:

```bash
cd frontend
npx vercel --prod --yes --project frontend
```

Set `HVAC_API_ORIGIN` and `NEXT_PUBLIC_API_URL` to the API host. Smoke:

```bash
python scripts/smoke_demo.py https://hvac-two-kappa.vercel.app
```

---

```bash
docker compose up
```

Starts TimescaleDB, Redis, API, control worker, job worker, and the Next.js app.

| Service | Port |
| --- | --- |
| Frontend | 3000 |
| API | 8000 |
| PostgreSQL | 5432 |
| Redis | 6379 |

Compose defaults: `HVAC_BMS_MODE=simulation`, `HVAC_BMS_WRITE_ENABLED=0`, `HVAC_DEPLOYMENT_MODE=local`.

---

## Configuration

Copy [`.env.example`](.env.example). Important variables:

| Variable | Default | Role |
| --- | --- | --- |
| `HVAC_ENV` | `development` | `production` tightens CORS and DB create-all |
| `HVAC_DEPLOYMENT_MODE` | `local` | Marks local / demo vs production deployment |
| `HVAC_CORS_ORIGINS` | `http://localhost:3000,...` | Allowed UI origins |
| `HVAC_BMS_MODE` | `simulation` | `simulation` or `production` |
| `HVAC_BMS_PROTOCOL` | `bacnet` | `bacnet` / `mqtt` / `rest` / `modbus` |
| `HVAC_BMS_WRITE_ENABLED` | `0` | Master write switch |
| `HVAC_SAFE_MODE` | `0` | Blocks automatic writes when `1` |
| `HVAC_ALLOW_CREATE_ALL` | `0` | SQLAlchemy `create_all`; keep off in production |
| `HVAC_ALLOW_DB_RESET` | `0` | Required (with `HVAC_ENV=development`) for `init_all_dbs.py` |
| `HVAC_TELEMETRY_STALE_SECONDS` | `90` | Stale telemetry window |
| `HVAC_TELEMETRY_RETAIN_DAYS` | `90` | Retention candidate age |
| `HVAC_TELEMETRY_PURGE` | `0` | Physical purge; counts only unless `1` |
| `HVAC_DISPATCH_CONFIDENCE_MIN` | `0.65` | Minimum confidence to dispatch |
| `HVAC_START_CONTROL_WORKER` | `1` | Embed control loop in the API process |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api` | Browser → API |
| `OPENWEATHER_API_KEY` | empty | Optional outdoor weather |
| `FACILITY_*` | Bengaluru defaults | Display / weather location |

Production BMS hosts (`HVAC_BACNET_HOST`, `HVAC_MQTT_URL`, `HVAC_OPCUA_URL`) stay unset until a real gateway is bound.

### Database

- **Alembic is the schema authority:** `alembic upgrade head`
- Do not enable `HVAC_ALLOW_CREATE_ALL` in production
- Production target: Timescale hypertables on `canonical_telemetry` keyed by `(building_id, point_id, timestamp)`
- Retention: `backend/workers/retention_worker.py` via the job worker. Physical deletes need `HVAC_TELEMETRY_PURGE=1`

---

## Tests and CI

Backend (from repo root):

```bash
pip install -r backend/requirements.txt pytest
python -m pytest backend/tests -q
```

CI currently runs a focused subset: `test_p0_security`, `test_runtime_contracts`, `test_oeh_guide`.

Frontend:

```bash
cd frontend
npm ci
npx tsc --noEmit
npm run lint
npm run build
npx playwright test
```

GitHub Actions: [`.github/workflows/ci.yml`](.github/workflows/ci.yml) (Python 3.12, Node 20).

---

## Repository map

```
backend/           FastAPI app, agents, BMS gateways, ML, workers
  agents/          Five agents + official O1–O20 engines + runtime (safety/apply/rollback)
  api/             HTTP controllers
  bms/             Simulator and protocol gateways
  knowledge/       OEH/AIRAH catalog (pages, control kind, risks)
  ml/              Feature maps, training, prediction services
  workers/         Control loop, jobs, watchdog
frontend/          Next.js App Router dashboards
database/          Local SQLite, retention notes
docs/              Data contracts, KPI maps, opportunity audits
alembic.ini        Schema migrations
docker-compose.yml Timescale + Redis + API + workers + UI
```

---

## Documentation

| Doc | Topic |
| --- | --- |
| [`docs/operations.md`](docs/operations.md) | Local SQLite backup, Alembic, production Timescale |
| [`docs/O1-DATA-CONTRACT.md`](docs/O1-DATA-CONTRACT.md) | O1 UI ↔ API ↔ tables |
| [`docs/O1-DASHBOARD-KPI-MAPPING.md`](docs/O1-DASHBOARD-KPI-MAPPING.md) | O1 KPI mapping |
| [`docs/O10-O13-DATA-CONTRACT.md`](docs/O10-O13-DATA-CONTRACT.md) | Ventilation O10–O13 |
| [`docs/O14-OPTIMISED-SECONDARY-CHILLED-WATER-PUMPING.md`](docs/O14-OPTIMISED-SECONDARY-CHILLED-WATER-PUMPING.md) | O14 |
| [`docs/O15-VARIABLE-HEAD-PRESSURE-AIR-COOLED.md`](docs/O15-VARIABLE-HEAD-PRESSURE-AIR-COOLED.md) | O15 |
| [`docs/O16-WATER-COOLED-HEAD-PRESSURE.md`](docs/O16-WATER-COOLED-HEAD-PRESSURE.md) | O16 |
| [`docs/SCHEDULING-DASHBOARD-DATA-FLOW.md`](docs/SCHEDULING-DASHBOARD-DATA-FLOW.md) | Scheduling dashboard flow |
| [`database/RETENTION.md`](database/RETENTION.md) | Telemetry quality and retention |

---

## Design rules worth knowing

- **No invented numbers.** Charts and KPIs stay empty or labelled unavailable when the model or telemetry is not ready.
- **Simulation labels stay visible.** Demo/sim rows are not presented as live BMS.
- **O9, O17–O20 are not automatic plant control.** O18 is advisory, O19 raises work orders, O20 is change-request only.
- **API errors** include a `request_id` (`X-Request-ID`) for tracing.

---

## License and source guide

Application code is private unless a license file is added at the repo root.

Opportunity definitions and teaching copy follow **NSW Office of Environment and Heritage / AIRAH**, *Optimising your heating, ventilation and air conditioning systems* (`150317hvacguide.pdf`). Guide percentages and case-study dollars are **GUIDE_POTENTIAL** only.
