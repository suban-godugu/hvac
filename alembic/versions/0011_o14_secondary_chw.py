"""O14 secondary chilled-water pumping snapshots and config."""
from alembic import op
import sqlalchemy as sa

revision = "0011_o14_secondary_chw"
down_revision = "0010_remove_product_modules"
branch_labels = None
depends_on = None


def _tables():
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    existing = _tables()
    if "o14_config" not in existing:
        op.create_table(
            "o14_config",
            sa.Column("building_id", sa.String(), primary_key=True),
            sa.Column("most_open_valve_target_pct", sa.Float(), nullable=False),
            sa.Column("dp_setpoint_trim", sa.Float(), nullable=True),
            sa.Column("dp_setpoint_trim_unit", sa.String(), nullable=True),
            sa.Column("speed_trim_pct", sa.Float(), nullable=True),
            sa.Column("min_pump_speed_pct", sa.Float(), nullable=True),
            sa.Column("max_pump_speed_pct", sa.Float(), nullable=True),
            sa.Column("min_dp", sa.Float(), nullable=True),
            sa.Column("max_dp", sa.Float(), nullable=True),
            sa.Column("min_flow", sa.Float(), nullable=True),
            sa.Column("max_flow", sa.Float(), nullable=True),
            sa.Column("max_speed_step_pct", sa.Float(), nullable=True),
            sa.Column("verify_tolerance", sa.Float(), nullable=True),
            sa.Column("control_mode", sa.String(), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=True),
            sa.Column("config_version", sa.String(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
    if "o14_system_snapshots" not in existing:
        op.create_table(
            "o14_system_snapshots",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("timestamp", sa.DateTime(), nullable=False),
            sa.Column("building_id", sa.String(), nullable=True),
            sa.Column("equipment_id", sa.String(), nullable=True),
            sa.Column("flow", sa.Float(), nullable=True),
            sa.Column("dp", sa.Float(), nullable=True),
            sa.Column("dp_setpoint", sa.Float(), nullable=True),
            sa.Column("speed", sa.Float(), nullable=True),
            sa.Column("power", sa.Float(), nullable=True),
            sa.Column("valve_position", sa.Float(), nullable=True),
            sa.Column("most_open_valve_pct", sa.Float(), nullable=True),
            sa.Column("supply_temperature", sa.Float(), nullable=True),
            sa.Column("return_temperature", sa.Float(), nullable=True),
            sa.Column("load", sa.Float(), nullable=True),
            sa.Column("pumps_running", sa.Integer(), nullable=True),
            sa.Column("cooling_call", sa.Float(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("quality", sa.String(), nullable=True),
            sa.Column("source", sa.String(), nullable=True),
            sa.Column("payload_json", sa.JSON(), nullable=True),
        )
        op.create_index("ix_o14_snap_eq_ts", "o14_system_snapshots", ["equipment_id", "timestamp"])
        op.create_index("ix_o14_snap_bldg_ts", "o14_system_snapshots", ["building_id", "timestamp"])
        op.create_index("ix_o14_system_snapshots_timestamp", "o14_system_snapshots", ["timestamp"])
    if "o14_recommendations" not in existing:
        op.create_table(
            "o14_recommendations",
            sa.Column("recommendation_id", sa.String(), primary_key=True),
            sa.Column("run_id", sa.String(), nullable=True),
            sa.Column("building_id", sa.String(), nullable=True),
            sa.Column("point_id", sa.String(), nullable=True),
            sa.Column("current_value", sa.Float(), nullable=True),
            sa.Column("recommended_value", sa.Float(), nullable=True),
            sa.Column("unit", sa.String(), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("safety_result", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("payload_json", sa.JSON(), nullable=True),
        )
        op.create_index("ix_o14_rec_created", "o14_recommendations", ["created_at"])
        op.create_index("ix_o14_recommendations_run_id", "o14_recommendations", ["run_id"])


def downgrade() -> None:
    existing = _tables()
    if "o14_recommendations" in existing:
        op.drop_table("o14_recommendations")
    if "o14_system_snapshots" in existing:
        op.drop_table("o14_system_snapshots")
    if "o14_config" in existing:
        op.drop_table("o14_config")
