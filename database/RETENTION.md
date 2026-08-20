# Telemetry retention

This project uses SQLite (`database/hvac_supervisory.db`) with no TimescaleDB and **no automatic delete job**.

- Live KPI queries must only return `quality=GOOD` and must exclude `source=SIMULATION`.
- Do not silently purge rows. Grow the file with WAL backups or a future scheduled archive if needed.
- Quality states: `GOOD`, `BAD`, `UNCERTAIN`, `STALE`, `MISSING`.
