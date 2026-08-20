"""Additive: tenants, zones, commands, work orders, telemetry equipment_id."""
from alembic import op
import sqlalchemy as sa

revision = "0009_commands_work_orders"
down_revision = "0008_platform_auth_telemetry"
branch_labels = None
depends_on = None


def _tables():
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table: str):
    bind = op.get_bind()
    if table not in set(sa.inspect(bind).get_table_names()):
        return set()
    return {c["name"] for c in sa.inspect(bind).get_columns(table)}


def upgrade() -> None:
    existing = _tables()
    if "tenants" not in existing:
        op.create_table(
            "tenants",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
    if "zones" not in existing:
        op.create_table(
            "zones",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("building_id", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("floor", sa.String(), nullable=True),
        )
        op.create_index("ix_zones_building_id", "zones", ["building_id"])
    if "control_commands" not in existing:
        op.create_table(
            "control_commands",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("command_id", sa.String(), nullable=False),
            sa.Column("opportunity", sa.String(), nullable=False),
            sa.Column("building_id", sa.String(), nullable=True),
            sa.Column("equipment_id", sa.String(), nullable=True),
            sa.Column("point_id", sa.String(), nullable=True),
            sa.Column("old_value", sa.Float(), nullable=True),
            sa.Column("new_value", sa.Float(), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("engine_version", sa.String(), nullable=True),
            sa.Column("config_version", sa.String(), nullable=True),
            sa.Column("safety_gates", sa.JSON(), nullable=True),
            sa.Column("requested_by", sa.String(), nullable=True),
            sa.Column("approval_id", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("applied_at", sa.DateTime(), nullable=True),
            sa.Column("verified_at", sa.DateTime(), nullable=True),
            sa.Column("rollback_at", sa.DateTime(), nullable=True),
            sa.Column("payload_json", sa.JSON(), nullable=True),
        )
        op.create_index("ix_control_commands_command_id", "control_commands", ["command_id"], unique=True)
        op.create_index("uq_cmd_opp_id", "control_commands", ["opportunity", "command_id"], unique=True)
    if "work_orders" not in existing:
        op.create_table(
            "work_orders",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("opportunity_id", sa.String(), nullable=True),
            sa.Column("building_id", sa.String(), nullable=True),
            sa.Column("equipment_id", sa.String(), nullable=True),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("finding", sa.Text(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("assignee", sa.String(), nullable=True),
            sa.Column("requested_by", sa.String(), nullable=True),
            sa.Column("verified_by", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
    if "agent_runs" not in existing:
        op.create_table(
            "agent_runs",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("opportunity", sa.String(), nullable=False),
            sa.Column("building_id", sa.String(), nullable=True),
            sa.Column("engine_version", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            sa.Column("input_json", sa.JSON(), nullable=True),
            sa.Column("output_json", sa.JSON(), nullable=True),
        )
    cols = _columns("canonical_telemetry")
    if "canonical_telemetry" in existing and "equipment_id" not in cols:
        op.add_column("canonical_telemetry", sa.Column("equipment_id", sa.String(), nullable=True))
        op.create_index("ix_canonical_telemetry_equipment_id", "canonical_telemetry", ["equipment_id"])


def downgrade() -> None:
    pass
