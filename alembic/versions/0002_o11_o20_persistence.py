"""Additive O11–O20 persistence tables and telemetry indexes (idempotent)."""
from alembic import op
import sqlalchemy as sa

revision = "0002_o11_o20_persistence"
down_revision = "0001_baseline"
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


def _ensure_index(name: str, table: str, cols: list):
    if name not in _indexes(table):
        op.create_index(name, table, cols)


def upgrade() -> None:
    existing = _tables()

    if "hvac_opportunities" not in existing:
        op.create_table(
            "hvac_opportunities",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("opportunity_number", sa.Integer(), nullable=False),
            sa.Column("section", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
    if "agent_executions" not in existing:
        op.create_table(
            "agent_executions",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("agent_id", sa.String(), nullable=False),
            sa.Column("opportunity_id", sa.String(), sa.ForeignKey("hvac_opportunities.id"), nullable=False),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("input_timestamp", sa.DateTime(), nullable=True),
            sa.Column("execution_time_ms", sa.Integer(), nullable=True),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=True),
        )
    if "opportunity_optimization_results" not in existing:
        op.create_table(
            "opportunity_optimization_results",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("opportunity_id", sa.String(), sa.ForeignKey("hvac_opportunities.id"), nullable=False),
            sa.Column("timestamp", sa.DateTime(), nullable=True),
            sa.Column("current_value", sa.Float(), nullable=True),
            sa.Column("optimized_value", sa.Float(), nullable=True),
            sa.Column("energy_impact", sa.Float(), nullable=True),
            sa.Column("comfort_impact", sa.String(), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
        )
    if "opportunity_audit_events" not in existing:
        op.create_table(
            "opportunity_audit_events",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("timestamp", sa.DateTime(), nullable=True),
            sa.Column("actor", sa.String(), nullable=True),
            sa.Column("opportunity_id", sa.String(), nullable=False),
            sa.Column("equipment_id", sa.String(), nullable=True),
            sa.Column("action", sa.String(), nullable=False),
            sa.Column("result", sa.String(), nullable=False),
            sa.Column("details", sa.JSON(), nullable=True),
        )
    if "co_measurements" not in existing:
        op.create_table(
            "co_measurements",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("timestamp", sa.DateTime(), nullable=True),
            sa.Column("zone_id", sa.String(), nullable=False),
            sa.Column("co_ppm", sa.Float(), nullable=False),
            sa.Column("co_trend", sa.String(), nullable=True),
            sa.Column("fan_state", sa.String(), nullable=True),
            sa.Column("fan_speed", sa.Float(), nullable=True),
            sa.Column("damper_pct", sa.Float(), nullable=True),
            sa.Column("airflow_cfm", sa.Float(), nullable=True),
            sa.Column("quality", sa.String(), nullable=True),
            sa.Column("source", sa.String(), nullable=True),
        )
    if "training_programs" not in existing:
        op.create_table(
            "training_programs",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("topic", sa.String(), nullable=False),
            sa.Column("program_name", sa.String(), nullable=False),
            sa.Column("required", sa.Boolean(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
        )
    if "training_completions" not in existing:
        op.create_table(
            "training_completions",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("program_id", sa.String(), sa.ForeignKey("training_programs.id"), nullable=False),
            sa.Column("role_label", sa.String(), nullable=True),
            sa.Column("completion_pct", sa.Float(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
        )
    if "maintenance_work_orders" not in existing:
        op.create_table(
            "maintenance_work_orders",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("equipment_id", sa.String(), nullable=False),
            sa.Column("maintenance_type", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("due_date", sa.DateTime(), nullable=True),
            sa.Column("runtime_hours", sa.Float(), nullable=True),
            sa.Column("efficiency", sa.Float(), nullable=True),
            sa.Column("degradation", sa.Float(), nullable=True),
            sa.Column("priority", sa.String(), nullable=True),
            sa.Column("recommendation", sa.Text(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
        )
    if "controller_software_status" not in existing:
        op.create_table(
            "controller_software_status",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("controller_id", sa.String(), nullable=False),
            sa.Column("software_version", sa.String(), nullable=True),
            sa.Column("firmware_version", sa.String(), nullable=True),
            sa.Column("comm_status", sa.String(), nullable=True),
            sa.Column("point_quality", sa.String(), nullable=True),
            sa.Column("override_state", sa.String(), nullable=True),
            sa.Column("alarm_state", sa.String(), nullable=True),
            sa.Column("control_loop_state", sa.String(), nullable=True),
            sa.Column("last_communication", sa.DateTime(), nullable=True),
            sa.Column("health_status", sa.String(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )

    if "opportunity_id" not in _cols("ventilation_telemetry"):
        with op.batch_alter_table("ventilation_telemetry") as batch:
            batch.add_column(sa.Column("opportunity_id", sa.String(), nullable=True))
    if "opportunity_id" not in _cols("variable_speed_telemetry"):
        with op.batch_alter_table("variable_speed_telemetry") as batch:
            batch.add_column(sa.Column("opportunity_id", sa.String(), nullable=True))

    _ensure_index("ix_opt_result_opp_ts", "opportunity_optimization_results", ["opportunity_id", "timestamp"])
    _ensure_index("ix_co_zone_ts", "co_measurements", ["zone_id", "timestamp"])
    _ensure_index("ix_vent_tel_eq_ts", "ventilation_telemetry", ["equipment_id", "timestamp"])
    _ensure_index("ix_vent_tel_sensor_ts", "ventilation_telemetry", ["sensor_id", "timestamp"])
    _ensure_index("ix_vs_tel_eq_ts", "variable_speed_telemetry", ["equipment_id", "timestamp"])
    _ensure_index("ix_vs_tel_point_ts", "variable_speed_telemetry", ["point_id", "timestamp"])
    _ensure_index("ix_energy_tel_meter_ts", "energy_telemetry", ["meter_id", "timestamp"])


def downgrade() -> None:
    existing = _tables()
    for name, table in [
        ("ix_energy_tel_meter_ts", "energy_telemetry"),
        ("ix_vs_tel_point_ts", "variable_speed_telemetry"),
        ("ix_vs_tel_eq_ts", "variable_speed_telemetry"),
        ("ix_vent_tel_sensor_ts", "ventilation_telemetry"),
        ("ix_vent_tel_eq_ts", "ventilation_telemetry"),
        ("ix_co_zone_ts", "co_measurements"),
        ("ix_opt_result_opp_ts", "opportunity_optimization_results"),
    ]:
        if table in existing and name in _indexes(table):
            op.drop_index(name, table_name=table)

    if "opportunity_id" in _cols("variable_speed_telemetry"):
        with op.batch_alter_table("variable_speed_telemetry") as batch:
            batch.drop_column("opportunity_id")
    if "opportunity_id" in _cols("ventilation_telemetry"):
        with op.batch_alter_table("ventilation_telemetry") as batch:
            batch.drop_column("opportunity_id")

    for t in [
        "controller_software_status",
        "maintenance_work_orders",
        "training_completions",
        "training_programs",
        "co_measurements",
        "opportunity_audit_events",
        "opportunity_optimization_results",
        "agent_executions",
        "hvac_opportunities",
    ]:
        if t in _tables():
            op.drop_table(t)
