# Telemetry retention

Canonical samples live in `canonical_telemetry` (SQLite locally, PostgreSQL/Timescale in Docker).

## Policy

- Live KPI queries must only return appropriate sources for plant mode (Live BMS never consumes `SIMULATION` / `DEMO` rows).
- Quality states: `GOOD`, `BAD`, `UNCERTAIN`, `STALE`, `MISSING`. Missing values are never coerced to `0`.
- Retention age: `HVAC_TELEMETRY_RETAIN_DAYS` (default **90**).
- Physical delete: only when `HVAC_TELEMETRY_PURGE=1`. Otherwise the job worker **counts** eligible rows and leaves them in place.
- Docker Compose `job-worker` sets `HVAC_TELEMETRY_PURGE=1` so Timescale/Postgres installs prune after 90 days.
- Local SQLite: keep purge off (`0`) unless you intentionally want deletes.

## Historian

- Alembic `0016_canonical_telemetry_historian` adds index `(building_id, point_id, timestamp)`.
- On TimescaleDB images, the same migration attempts `create_hypertable('canonical_telemetry', 'timestamp')` when the extension is available.
- Hot path: in-process ring buffer (`HVAC_TS_BUFFER_SECONDS`, `HVAC_TS_BUFFER_MAX`) fed by `record_point`; durable history remains the table.

## APIs

- `GET /api/platform/timeseries/window?point_id=...&t0=...&t1=...`
- `GET /api/platform/ai/normalized?zone_id=ZONE-01&t0=...&t1=...&step_seconds=60`
