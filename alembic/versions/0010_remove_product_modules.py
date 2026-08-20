"""Remove product-module tables: alerts and work orders.

Keep control_commands, hvac_approvals, canonical_telemetry, and O19
maintenance_work_orders (internal findings store).
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_remove_product_modules"
down_revision = "0009_commands_work_orders"
branch_labels = None
depends_on = None


def _tables():
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    existing = _tables()
    if "hvac_alerts" in existing:
        op.drop_table("hvac_alerts")
    if "work_orders" in existing:
        op.drop_table("work_orders")


def downgrade() -> None:
    existing = _tables()
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
