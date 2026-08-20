"""O15 air-cooled condenser variable head-pressure tables."""
from alembic import op
import sqlalchemy as sa

revision = "0012_o15_air_cooled_hp"
down_revision = "0011_o14_secondary_chw"
branch_labels = None
depends_on = None


def _tables():
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    existing = _tables()
    if "o15_config" not in existing:
        op.create_table(
            "o15_config",
            sa.Column("building_id", sa.String(), primary_key=True),
            sa.Column("approach_c", sa.Float(), nullable=False),
            sa.Column("approach_min_c", sa.Float(), nullable=False),
            sa.Column("approach_max_c", sa.Float(), nullable=False),
            sa.Column("min_head_pressure", sa.Float(), nullable=True),
            sa.Column("max_head_pressure", sa.Float(), nullable=True),
            sa.Column("min_condensing_temp_c", sa.Float(), nullable=True),
            sa.Column("max_condensing_temp_c", sa.Float(), nullable=True),
            sa.Column("min_fan_speed_pct", sa.Float(), nullable=True),
            sa.Column("max_fan_speed_pct", sa.Float(), nullable=True),
            sa.Column("fan_trim_pct", sa.Float(), nullable=True),
            sa.Column("tcond_deadband_c", sa.Float(), nullable=True),
            sa.Column("max_fan_step_pct", sa.Float(), nullable=True),
            sa.Column("verify_tolerance", sa.Float(), nullable=True),
            sa.Column("refrigerant", sa.String(), nullable=True),
            sa.Column("saturation_curve_json", sa.JSON(), nullable=True),
            sa.Column("control_mode", sa.String(), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=True),
            sa.Column("config_version", sa.String(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
    if "o15_system_snapshots" not in existing:
        op.create_table(
            "o15_system_snapshots",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("timestamp", sa.DateTime(), nullable=False),
            sa.Column("building_id", sa.String(), nullable=True),
            sa.Column("equipment_id", sa.String(), nullable=True),
            sa.Column("outdoor_air_temperature", sa.Float(), nullable=True),
            sa.Column("head_pressure", sa.Float(), nullable=True),
            sa.Column("head_pressure_setpoint", sa.Float(), nullable=True),
            sa.Column("condensing_temperature", sa.Float(), nullable=True),
            sa.Column("fan_speed", sa.Float(), nullable=True),
            sa.Column("fan_power", sa.Float(), nullable=True),
            sa.Column("compressor_load", sa.Float(), nullable=True),
            sa.Column("compressor_power", sa.Float(), nullable=True),
            sa.Column("cooling_load", sa.Float(), nullable=True),
            sa.Column("fans_running", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("quality", sa.String(), nullable=True),
            sa.Column("source", sa.String(), nullable=True),
            sa.Column("payload_json", sa.JSON(), nullable=True),
        )
        op.create_index("ix_o15_snap_eq_ts", "o15_system_snapshots", ["equipment_id", "timestamp"])
        op.create_index("ix_o15_snap_bldg_ts", "o15_system_snapshots", ["building_id", "timestamp"])
        op.create_index("ix_o15_system_snapshots_timestamp", "o15_system_snapshots", ["timestamp"])
    if "o15_recommendations" not in existing:
        op.create_table(
            "o15_recommendations",
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
        op.create_index("ix_o15_rec_created", "o15_recommendations", ["created_at"])
        op.create_index("ix_o15_recommendations_run_id", "o15_recommendations", ["run_id"])


def downgrade() -> None:
    existing = _tables()
    if "o15_recommendations" in existing:
        op.drop_table("o15_recommendations")
    if "o15_system_snapshots" in existing:
        op.drop_table("o15_system_snapshots")
    if "o15_config" in existing:
        op.drop_table("o15_config")
