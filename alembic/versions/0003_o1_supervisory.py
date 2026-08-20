"""Additive O1 supervisory tables and column extensions (idempotent)."""
from alembic import op
import sqlalchemy as sa

revision = "0003_o1_supervisory"
down_revision = "0002_o11_o20_persistence"
branch_labels = None
depends_on = None


def _tables():
    return sa.inspect(op.get_bind()).get_table_names()


def _cols(table: str):
    insp = sa.inspect(op.get_bind())
    if table not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(table)}


def _indexes(table: str):
    insp = sa.inspect(op.get_bind())
    if table not in insp.get_table_names():
        return set()
    return {i["name"] for i in insp.get_indexes(table)}


def _ensure_index(name, table, cols):
    if table in _tables() and name not in _indexes(table):
        op.create_index(name, table, cols)


def upgrade() -> None:
    existing = _tables()
    if "o1_actions" in existing:
        cols = _cols("o1_actions")
        with op.batch_alter_table("o1_actions") as batch:
            if "run_id" not in cols:
                batch.add_column(sa.Column("run_id", sa.String(), nullable=True))
            if "command_status" not in cols:
                batch.add_column(sa.Column("command_status", sa.String(), nullable=True))
            if "verified_state" not in cols:
                batch.add_column(sa.Column("verified_state", sa.String(), nullable=True))
            if "verification_timestamp" not in cols:
                batch.add_column(sa.Column("verification_timestamp", sa.DateTime(), nullable=True))
            if "safety_validation_id" not in cols:
                batch.add_column(sa.Column("safety_validation_id", sa.String(), nullable=True))
    if "o1_activity_log" in existing:
        cols = _cols("o1_activity_log")
        with op.batch_alter_table("o1_activity_log") as batch:
            if "run_id" not in cols:
                batch.add_column(sa.Column("run_id", sa.String(), nullable=True))
            if "event_type" not in cols:
                batch.add_column(sa.Column("event_type", sa.String(), nullable=True))
            if "severity" not in cols:
                batch.add_column(sa.Column("severity", sa.String(), nullable=True))

    defs = {
        "o1_point_map": [
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("building_id", sa.String(), nullable=True),
            sa.Column("signal", sa.String(), nullable=False),
            sa.Column("point_id", sa.String(), nullable=True),
            sa.Column("unit", sa.String(), nullable=True),
            sa.Column("data_type", sa.String(), nullable=True),
            sa.Column("required", sa.Boolean(), nullable=True),
            sa.Column("quality_requirement", sa.String(), nullable=True),
            sa.Column("freshness_seconds", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        ],
        "o1_configuration": [
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("building_id", sa.String(), nullable=True),
            sa.Column("equipment_id", sa.String(), nullable=True),
            sa.Column("scheduled_start", sa.String(), nullable=True),
            sa.Column("scheduled_stop", sa.String(), nullable=True),
            sa.Column("occupancy_start", sa.String(), nullable=True),
            sa.Column("occupancy_end", sa.String(), nullable=True),
            sa.Column("comfort_target_c", sa.Float(), nullable=True),
            sa.Column("comfort_lower_c", sa.Float(), nullable=True),
            sa.Column("comfort_upper_c", sa.Float(), nullable=True),
            sa.Column("max_start_delay_min", sa.Integer(), nullable=True),
            sa.Column("candidate_interval_min", sa.Integer(), nullable=True),
            sa.Column("stale_telemetry_seconds", sa.Integer(), nullable=True),
            sa.Column("min_runtime_min", sa.Integer(), nullable=True),
            sa.Column("min_off_time_min", sa.Integer(), nullable=True),
            sa.Column("safety_margin_min", sa.Float(), nullable=True),
            sa.Column("ahu_kw", sa.Float(), nullable=True),
            sa.Column("energy_cost_usd_kwh", sa.Float(), nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        ],
        "o1_telemetry_sample": [
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("point_id", sa.String(), nullable=False),
            sa.Column("signal", sa.String(), nullable=False),
            sa.Column("timestamp", sa.DateTime(), nullable=False),
            sa.Column("value", sa.Float(), nullable=True),
            sa.Column("unit", sa.String(), nullable=True),
            sa.Column("quality", sa.String(), nullable=True),
            sa.Column("source", sa.String(), nullable=True),
            sa.Column("raw_value", sa.String(), nullable=True),
            sa.Column("ingested_at", sa.DateTime(), nullable=True),
            sa.Column("building_id", sa.String(), nullable=True),
            sa.Column("equipment_id", sa.String(), nullable=True),
            sa.Column("zone_id", sa.String(), nullable=True),
        ],
        "weather_observation": [
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("timestamp", sa.DateTime(), nullable=False),
            sa.Column("building_id", sa.String(), nullable=True),
            sa.Column("oat_c", sa.Float(), nullable=True),
            sa.Column("rh_pct", sa.Float(), nullable=True),
            sa.Column("solar_w_m2", sa.Float(), nullable=True),
            sa.Column("wind_speed_ms", sa.Float(), nullable=True),
            sa.Column("condition", sa.String(), nullable=True),
            sa.Column("quality", sa.String(), nullable=True),
            sa.Column("source", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        ],
        "occupancy_schedule": [
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("building_id", sa.String(), nullable=True),
            sa.Column("zone_id", sa.String(), nullable=True),
            sa.Column("weekday", sa.Integer(), nullable=True),
            sa.Column("occupancy_start", sa.String(), nullable=False),
            sa.Column("occupancy_end", sa.String(), nullable=False),
            sa.Column("is_holiday", sa.Boolean(), nullable=True),
            sa.Column("is_weekend", sa.Boolean(), nullable=True),
            sa.Column("source", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        ],
        "o1_model": [
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("version", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("artifact_path", sa.String(), nullable=True),
            sa.Column("parameters", sa.JSON(), nullable=True),
            sa.Column("mae_minutes", sa.Float(), nullable=True),
            sa.Column("rmse_minutes", sa.Float(), nullable=True),
            sa.Column("r2_score", sa.Float(), nullable=True),
            sa.Column("sample_count", sa.Integer(), nullable=True),
            sa.Column("dataset_version", sa.String(), nullable=True),
            sa.Column("activated_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        ],
        "o1_model_training_run": [
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("model_id", sa.String(), nullable=True),
            sa.Column("dataset_version", sa.String(), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("feature_count", sa.Integer(), nullable=True),
            sa.Column("sample_count", sa.Integer(), nullable=True),
            sa.Column("mae_minutes", sa.Float(), nullable=True),
            sa.Column("rmse_minutes", sa.Float(), nullable=True),
            sa.Column("r2_score", sa.Float(), nullable=True),
            sa.Column("mape", sa.Float(), nullable=True),
            sa.Column("validation_score", sa.Float(), nullable=True),
            sa.Column("test_score", sa.Float(), nullable=True),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        ],
        "o1_prediction": [
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("run_id", sa.String(), nullable=True),
            sa.Column("model_version", sa.String(), nullable=True),
            sa.Column("timestamp", sa.DateTime(), nullable=True),
            sa.Column("time_to_target_minutes", sa.Float(), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("input_quality", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("features", sa.JSON(), nullable=True),
        ],
        "o1_daily_run": [
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("building_id", sa.String(), nullable=True),
            sa.Column("equipment_id", sa.String(), nullable=True),
            sa.Column("zone_id", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("failure_reason", sa.Text(), nullable=True),
            sa.Column("model_version", sa.String(), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("source", sa.String(), nullable=True),
            sa.Column("environment", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        ],
        "o1_start_candidate": [
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("run_id", sa.String(), nullable=True),
            sa.Column("candidate_start", sa.String(), nullable=False),
            sa.Column("predicted_target_reached", sa.String(), nullable=True),
            sa.Column("pull_down_minutes", sa.Float(), nullable=True),
            sa.Column("energy_kwh", sa.Float(), nullable=True),
            sa.Column("comfort_margin_c", sa.Float(), nullable=True),
            sa.Column("safety_risk", sa.String(), nullable=True),
            sa.Column("occupancy_breach_risk", sa.String(), nullable=True),
            sa.Column("decision", sa.String(), nullable=False),
            sa.Column("rejection_reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        ],
        "o1_stop_candidate": [
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("run_id", sa.String(), nullable=True),
            sa.Column("candidate_stop", sa.String(), nullable=False),
            sa.Column("predicted_temp_at_occ_end", sa.Float(), nullable=True),
            sa.Column("runtime_saved_min", sa.Float(), nullable=True),
            sa.Column("energy_saved_kwh", sa.Float(), nullable=True),
            sa.Column("comfort_margin_c", sa.Float(), nullable=True),
            sa.Column("safety_status", sa.String(), nullable=True),
            sa.Column("decision", sa.String(), nullable=False),
            sa.Column("rejection_reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        ],
        "o1_safety_validation": [
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("run_id", sa.String(), nullable=True),
            sa.Column("check_id", sa.String(), nullable=False),
            sa.Column("check_name", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("current_value", sa.String(), nullable=True),
            sa.Column("limit_value", sa.String(), nullable=True),
            sa.Column("unit", sa.String(), nullable=True),
            sa.Column("severity", sa.String(), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("timestamp", sa.DateTime(), nullable=True),
        ],
        "o1_comfort_validation": [
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("run_id", sa.String(), nullable=True),
            sa.Column("check_id", sa.String(), nullable=False),
            sa.Column("check_name", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("current_value", sa.String(), nullable=True),
            sa.Column("limit_value", sa.String(), nullable=True),
            sa.Column("unit", sa.String(), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("timestamp", sa.DateTime(), nullable=True),
        ],
        "o1_energy_baseline": [
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("run_id", sa.String(), nullable=True),
            sa.Column("methodology", sa.String(), nullable=True),
            sa.Column("baseline_runtime_min", sa.Float(), nullable=True),
            sa.Column("baseline_energy_kwh", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        ],
        "o1_savings_verification": [
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("run_id", sa.String(), nullable=True),
            sa.Column("calculation_timestamp", sa.DateTime(), nullable=True),
            sa.Column("baseline_reference", sa.String(), nullable=True),
            sa.Column("optimized_reference", sa.String(), nullable=True),
            sa.Column("energy_baseline", sa.Float(), nullable=True),
            sa.Column("energy_optimized", sa.Float(), nullable=True),
            sa.Column("energy_saved", sa.Float(), nullable=True),
            sa.Column("runtime_baseline", sa.Float(), nullable=True),
            sa.Column("runtime_optimized", sa.Float(), nullable=True),
            sa.Column("runtime_saved", sa.Float(), nullable=True),
            sa.Column("verification_status", sa.String(), nullable=True),
            sa.Column("cost_saved_usd", sa.Float(), nullable=True),
            sa.Column("source", sa.String(), nullable=True),
        ],
    }
    existing = _tables()
    for name, cols in defs.items():
        if name not in existing:
            op.create_table(name, *cols)

    _ensure_index("ix_o1_tel_point_ts", "o1_telemetry_sample", ["point_id", "timestamp"])
    _ensure_index("ix_o1_tel_signal_ts", "o1_telemetry_sample", ["signal", "timestamp"])
    _ensure_index("ix_o1_tel_zone_ts", "o1_telemetry_sample", ["zone_id", "timestamp"])
    _ensure_index("ix_weather_bldg_ts", "weather_observation", ["building_id", "timestamp"])
    _ensure_index("ix_o1_pred_run", "o1_prediction", ["run_id"])
    _ensure_index("ix_o1_run_status", "o1_daily_run", ["status"])
    _ensure_index("ix_o1_start_run", "o1_start_candidate", ["run_id"])
    _ensure_index("ix_o1_stop_run", "o1_stop_candidate", ["run_id"])
    _ensure_index("ix_o1_safety_run", "o1_safety_validation", ["run_id"])


def downgrade() -> None:
    for name in [
        "ix_o1_safety_run",
        "ix_o1_stop_run",
        "ix_o1_start_run",
        "ix_o1_run_status",
        "ix_o1_pred_run",
        "ix_weather_bldg_ts",
        "ix_o1_tel_zone_ts",
        "ix_o1_tel_signal_ts",
        "ix_o1_tel_point_ts",
    ]:
        try:
            op.drop_index(name)
        except Exception:
            pass
    for t in [
        "o1_savings_verification",
        "o1_energy_baseline",
        "o1_comfort_validation",
        "o1_safety_validation",
        "o1_stop_candidate",
        "o1_start_candidate",
        "o1_prediction",
        "o1_model_training_run",
        "o1_daily_run",
        "o1_model",
        "occupancy_schedule",
        "weather_observation",
        "o1_telemetry_sample",
        "o1_configuration",
        "o1_point_map",
    ]:
        if t in _tables():
            op.drop_table(t)
