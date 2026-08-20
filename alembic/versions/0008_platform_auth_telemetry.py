"""Platform auth, telemetry, alerts, historian, health."""
from alembic import op
import sqlalchemy as sa

revision = "0008_platform_auth_telemetry"
down_revision = "0007_operations_maintenance"
branch_labels = None
depends_on = None


def _tables():
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    existing = _tables()
    if "hvac_users" not in existing:
        op.create_table(
            "hvac_users",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("username", sa.String(), nullable=False),
            sa.Column("password_hash", sa.String(), nullable=False),
            sa.Column("role", sa.String(), nullable=False),
            sa.Column("building_id", sa.String(), nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_hvac_users_username", "hvac_users", ["username"], unique=True)
        op.create_index("ix_hvac_users_building_id", "hvac_users", ["building_id"])
    if "control_audit_logs" not in existing:
        op.create_table(
            "control_audit_logs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("request_id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=True),
            sa.Column("role", sa.String(), nullable=True),
            sa.Column("timestamp", sa.DateTime(), nullable=False),
            sa.Column("building_id", sa.String(), nullable=True),
            sa.Column("opportunity_id", sa.String(), nullable=True),
            sa.Column("action", sa.String(), nullable=False),
            sa.Column("previous_value", sa.Text(), nullable=True),
            sa.Column("requested_value", sa.Text(), nullable=True),
            sa.Column("decision", sa.String(), nullable=True),
            sa.Column("safety_status", sa.String(), nullable=True),
            sa.Column("telemetry_status", sa.String(), nullable=True),
            sa.Column("approval_status", sa.String(), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("payload_json", sa.JSON(), nullable=True),
        )
        op.create_index("ix_audit_bldg_ts", "control_audit_logs", ["building_id", "timestamp"])
    if "canonical_telemetry" not in existing:
        op.create_table(
            "canonical_telemetry",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("point_id", sa.String(), nullable=False),
            sa.Column("building_id", sa.String(), nullable=True),
            sa.Column("asset_id", sa.String(), nullable=True),
            sa.Column("timestamp", sa.DateTime(), nullable=False),
            sa.Column("value", sa.Float(), nullable=True),
            sa.Column("unit", sa.String(), nullable=True),
            sa.Column("source", sa.String(), nullable=False),
            sa.Column("quality", sa.String(), nullable=False),
            sa.Column("age_seconds", sa.Float(), nullable=True),
        )
        op.create_index("ix_ctel_point_ts", "canonical_telemetry", ["point_id", "timestamp"])
    if "hvac_alerts" not in existing:
        op.create_table(
            "hvac_alerts",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("building_id", sa.String(), nullable=True),
            sa.Column("opportunity_id", sa.String(), nullable=True),
            sa.Column("alert_type", sa.String(), nullable=False),
            sa.Column("severity", sa.String(), nullable=True),
            sa.Column("message", sa.Text(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("timestamp", sa.DateTime(), nullable=True),
            sa.Column("details_json", sa.JSON(), nullable=True),
        )
    if "hvac_approvals" not in existing:
        op.create_table(
            "hvac_approvals",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("request_id", sa.String(), nullable=False),
            sa.Column("building_id", sa.String(), nullable=True),
            sa.Column("opportunity_id", sa.String(), nullable=True),
            sa.Column("requested_by", sa.String(), nullable=True),
            sa.Column("approved_by", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("action", sa.String(), nullable=True),
            sa.Column("timestamp", sa.DateTime(), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
        )
    if "platform_settings" not in existing:
        op.create_table(
            "platform_settings",
            sa.Column("key", sa.String(), primary_key=True),
            sa.Column("value", sa.String(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    pass
