"""Additive O10–O13 telemetry snapshot and optimization tables."""
from alembic import op
import sqlalchemy as sa

revision = "0006_ventilation_hvac_telemetry"
down_revision = "0005_scheduling_dashboard_indexes"
branch_labels = None
depends_on = None


def _tables():
    return set(sa.inspect(op.get_bind()).get_table_names())


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
    if name not in _indexes(table):
        op.create_index(name, table, cols)


def _add_col(table, col):
    if col.name not in _cols(table):
        op.add_column(table, col)


def upgrade() -> None:
    existing = _tables()
    if "hvac_opportunities" in existing:
        _add_col("hvac_opportunities", sa.Column("agent", sa.String(), nullable=True))
        _add_col("hvac_opportunities", sa.Column("priority", sa.Integer(), nullable=True))

    if "hvac_telemetry" not in existing:
        op.create_table(
            "hvac_telemetry",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("timestamp", sa.DateTime(), nullable=False),
            sa.Column("site_id", sa.String(), nullable=True),
            sa.Column("ahu_id", sa.String(), nullable=True),
            sa.Column("zone_id", sa.String(), nullable=True),
            sa.Column("outdoor_temp_c", sa.Float(), nullable=True),
            sa.Column("outdoor_rh_percent", sa.Float(), nullable=True),
            sa.Column("outdoor_enthalpy_kjkg", sa.Float(), nullable=True),
            sa.Column("return_temp_c", sa.Float(), nullable=True),
            sa.Column("return_rh_percent", sa.Float(), nullable=True),
            sa.Column("return_enthalpy_kjkg", sa.Float(), nullable=True),
            sa.Column("supply_air_temp_c", sa.Float(), nullable=True),
            sa.Column("supply_airflow_cfm", sa.Float(), nullable=True),
            sa.Column("mixed_air_temp_c", sa.Float(), nullable=True),
            sa.Column("damper_percent", sa.Float(), nullable=True),
            sa.Column("co2_ppm", sa.Float(), nullable=True),
            sa.Column("co_ppm", sa.Float(), nullable=True),
            sa.Column("fan_power_kw", sa.Float(), nullable=True),
            sa.Column("chiller_power_kw", sa.Float(), nullable=True),
            sa.Column("total_hvac_power_kw", sa.Float(), nullable=True),
            sa.Column("occupancy", sa.Float(), nullable=True),
            sa.Column("occupied", sa.Boolean(), nullable=True),
            sa.Column("schedule_state", sa.String(), nullable=True),
            sa.Column("return_airflow_cfm", sa.Float(), nullable=True),
            sa.Column("quality", sa.String(), nullable=True),
            sa.Column("source", sa.String(), nullable=True),
            sa.Column("site_name", sa.String(), nullable=True),
            sa.Column("site_location", sa.String(), nullable=True),
            sa.Column("plant_label", sa.String(), nullable=True),
            sa.Column("building_area_sqft", sa.Float(), nullable=True),
        )
        _ensure_index("ix_hvac_tel_site_ts", "hvac_telemetry", ["site_id", "timestamp"])
        _ensure_index("ix_hvac_tel_ahu_ts", "hvac_telemetry", ["ahu_id", "timestamp"])
        _ensure_index("ix_hvac_tel_zone_ts", "hvac_telemetry", ["zone_id", "timestamp"])
        _ensure_index("ix_hvac_tel_source", "hvac_telemetry", ["source"])
        _ensure_index("ix_hvac_telemetry_timestamp", "hvac_telemetry", ["timestamp"])

    if "hvac_optimization_results" not in existing:
        op.create_table(
            "hvac_optimization_results",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("opportunity_id", sa.String(), nullable=False),
            sa.Column("telemetry_id", sa.Integer(), nullable=True),
            sa.Column("current_value", sa.Float(), nullable=True),
            sa.Column("optimized_value", sa.Float(), nullable=True),
            sa.Column("energy_savings_kw", sa.Float(), nullable=True),
            sa.Column("daily_savings_kwh", sa.Float(), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("guardrail_pass", sa.Boolean(), nullable=True),
            sa.Column("recommendation", sa.String(), nullable=True),
            sa.Column("rationale", sa.Text(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("payload_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        _ensure_index("ix_hvac_opt_opp_ts", "hvac_optimization_results", ["opportunity_id", "created_at"])
        _ensure_index("ix_hvac_optimization_results_opportunity_id", "hvac_optimization_results", ["opportunity_id"])
        _ensure_index("ix_hvac_optimization_results_telemetry_id", "hvac_optimization_results", ["telemetry_id"])
        _ensure_index("ix_hvac_optimization_results_created_at", "hvac_optimization_results", ["created_at"])

    if "hvac_optimization_candidates" not in existing:
        op.create_table(
            "hvac_optimization_candidates",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("optimization_result_id", sa.Integer(), nullable=False),
            sa.Column("candidate_id", sa.String(), nullable=False),
            sa.Column("damper_position_percent", sa.Float(), nullable=True),
            sa.Column("mixed_air_temp_c", sa.Float(), nullable=True),
            sa.Column("chiller_power_kw", sa.Float(), nullable=True),
            sa.Column("free_cooling_kw", sa.Float(), nullable=True),
            sa.Column("economizer_mode", sa.String(), nullable=True),
            sa.Column("outdoor_air_cfm", sa.Float(), nullable=True),
            sa.Column("decision", sa.String(), nullable=True),
            sa.Column("rejection_reason", sa.String(), nullable=True),
        )
        _ensure_index(
            "ix_hvac_optimization_candidates_optimization_result_id",
            "hvac_optimization_candidates",
            ["optimization_result_id"],
        )


def downgrade() -> None:
    pass
