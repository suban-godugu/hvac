"""O16 water-cooled condenser variable head-pressure tables."""
from alembic import op
import sqlalchemy as sa

revision = "0013_o16_water_cooled_hp"
down_revision = "0012_o15_air_cooled_hp"
branch_labels = None
depends_on = None


def _tables():
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    existing = _tables()
    if "o16_config" not in existing:
        op.create_table(
            "o16_config",
            sa.Column("building_id", sa.String(), primary_key=True),
            sa.Column("enabled", sa.Boolean(), nullable=True),
            sa.Column("control_mode", sa.String(), nullable=False),
            sa.Column("control_strategy", sa.String(), nullable=False),
            sa.Column("shared_pump", sa.Boolean(), nullable=True),
            sa.Column("target_head_pressure", sa.Float(), nullable=True),
            sa.Column("target_condensing_temp_c", sa.Float(), nullable=True),
            sa.Column("min_head_pressure", sa.Float(), nullable=True),
            sa.Column("max_head_pressure", sa.Float(), nullable=True),
            sa.Column("min_condensing_temp_c", sa.Float(), nullable=True),
            sa.Column("max_condensing_temp_c", sa.Float(), nullable=True),
            sa.Column("min_pump_speed_pct", sa.Float(), nullable=True),
            sa.Column("max_pump_speed_pct", sa.Float(), nullable=True),
            sa.Column("min_cw_flow", sa.Float(), nullable=True),
            sa.Column("max_cw_flow", sa.Float(), nullable=True),
            sa.Column("min_valve_pct", sa.Float(), nullable=True),
            sa.Column("max_valve_pct", sa.Float(), nullable=True),
            sa.Column("pump_trim_pct", sa.Float(), nullable=True),
            sa.Column("valve_trim_pct", sa.Float(), nullable=True),
            sa.Column("hp_deadband", sa.Float(), nullable=True),
            sa.Column("max_pump_step_pct", sa.Float(), nullable=True),
            sa.Column("high_load_pct", sa.Float(), nullable=True),
            sa.Column("isolate_valve_pct", sa.Float(), nullable=True),
            sa.Column("verify_tolerance", sa.Float(), nullable=True),
            sa.Column("refrigerant", sa.String(), nullable=True),
            sa.Column("config_version", sa.String(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
    if "o16_telemetry" not in existing:
        op.create_table(
            "o16_telemetry",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("building_id", sa.String(), nullable=True),
            sa.Column("equipment_id", sa.String(), nullable=True),
            sa.Column("point_id", sa.String(), nullable=True),
            sa.Column("timestamp", sa.DateTime(), nullable=False),
            sa.Column("value", sa.Float(), nullable=True),
            sa.Column("unit", sa.String(), nullable=True),
            sa.Column("quality", sa.String(), nullable=True),
            sa.Column("source", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_o16_tel_eq_ts", "o16_telemetry", ["equipment_id", "timestamp"])
        op.create_index("ix_o16_tel_pt_ts", "o16_telemetry", ["point_id", "timestamp"])
        op.create_index("ix_o16_tel_bldg_ts", "o16_telemetry", ["building_id", "timestamp"])
        op.create_index("ix_o16_telemetry_timestamp", "o16_telemetry", ["timestamp"])
    if "o16_state" not in existing:
        op.create_table(
            "o16_state",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("building_id", sa.String(), nullable=True),
            sa.Column("equipment_id", sa.String(), nullable=True),
            sa.Column("timestamp", sa.DateTime(), nullable=False),
            sa.Column("load_ratio", sa.Float(), nullable=True),
            sa.Column("condensing_pressure", sa.Float(), nullable=True),
            sa.Column("condensing_temperature", sa.Float(), nullable=True),
            sa.Column("cw_supply_temperature", sa.Float(), nullable=True),
            sa.Column("cw_return_temperature", sa.Float(), nullable=True),
            sa.Column("cw_flow", sa.Float(), nullable=True),
            sa.Column("pump_speed", sa.Float(), nullable=True),
            sa.Column("pump_power", sa.Float(), nullable=True),
            sa.Column("valve_position", sa.Float(), nullable=True),
            sa.Column("head_pressure_margin", sa.Float(), nullable=True),
            sa.Column("quality", sa.String(), nullable=True),
            sa.Column("source", sa.String(), nullable=True),
            sa.Column("state_json", sa.JSON(), nullable=True),
        )
        op.create_index("ix_o16_state_eq_ts", "o16_state", ["equipment_id", "timestamp"])
        op.create_index("ix_o16_state_bldg_ts", "o16_state", ["building_id", "timestamp"])
        op.create_index("ix_o16_state_timestamp", "o16_state", ["timestamp"])
    if "o16_recommendations" not in existing:
        op.create_table(
            "o16_recommendations",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("building_id", sa.String(), nullable=True),
            sa.Column("equipment_id", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("run_id", sa.String(), nullable=True),
            sa.Column("target_condensing_pressure", sa.Float(), nullable=True),
            sa.Column("target_condensing_temperature", sa.Float(), nullable=True),
            sa.Column("recommended_pump_speed", sa.Float(), nullable=True),
            sa.Column("recommended_valve_position", sa.Float(), nullable=True),
            sa.Column("predicted_power", sa.Float(), nullable=True),
            sa.Column("predicted_savings", sa.Float(), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("engine_version", sa.String(), nullable=True),
            sa.Column("config_version", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("payload_json", sa.JSON(), nullable=True),
        )
        op.create_index("ix_o16_rec_created", "o16_recommendations", ["created_at"])
        op.create_index("ix_o16_recommendations_run_id", "o16_recommendations", ["run_id"])
    if "o16_verification" not in existing:
        op.create_table(
            "o16_verification",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("command_id", sa.String(), nullable=False),
            sa.Column("timestamp", sa.DateTime(), nullable=True),
            sa.Column("expected_value", sa.Float(), nullable=True),
            sa.Column("actual_value", sa.Float(), nullable=True),
            sa.Column("tolerance", sa.Float(), nullable=True),
            sa.Column("verification_status", sa.String(), nullable=True),
            sa.Column("response_time_ms", sa.Integer(), nullable=True),
            sa.Column("details_json", sa.JSON(), nullable=True),
        )
        op.create_index("ix_o16_verification_command_id", "o16_verification", ["command_id"])
    if "o16_savings" not in existing:
        op.create_table(
            "o16_savings",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("building_id", sa.String(), nullable=True),
            sa.Column("equipment_id", sa.String(), nullable=True),
            sa.Column("period_start", sa.DateTime(), nullable=True),
            sa.Column("period_end", sa.DateTime(), nullable=True),
            sa.Column("baseline_kw", sa.Float(), nullable=True),
            sa.Column("predicted_kw", sa.Float(), nullable=True),
            sa.Column("applied_kw", sa.Float(), nullable=True),
            sa.Column("verified_kw", sa.Float(), nullable=True),
            sa.Column("baseline_kwh", sa.Float(), nullable=True),
            sa.Column("predicted_kwh", sa.Float(), nullable=True),
            sa.Column("applied_kwh", sa.Float(), nullable=True),
            sa.Column("verified_kwh", sa.Float(), nullable=True),
            sa.Column("methodology", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_o16_savings_building_id", "o16_savings", ["building_id"])


def downgrade() -> None:
    existing = _tables()
    for name in ("o16_savings", "o16_verification", "o16_recommendations", "o16_state", "o16_telemetry", "o16_config"):
        if name in existing:
            op.drop_table(name)
