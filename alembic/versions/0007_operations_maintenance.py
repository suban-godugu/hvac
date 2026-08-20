"""O17–O20 operations & maintenance tables."""
from alembic import op
import sqlalchemy as sa

revision = "0007_operations_maintenance"
down_revision = "0006_ventilation_hvac_telemetry"
branch_labels = None
depends_on = None


def _tables():
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    existing = _tables()
    if "om_opportunities" not in existing:
        op.create_table(
            "om_opportunities",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("opportunity_number", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
    if "om_telemetry" not in existing:
        op.create_table(
            "om_telemetry",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("opportunity_id", sa.String(), sa.ForeignKey("om_opportunities.id"), nullable=False),
            sa.Column("timestamp", sa.DateTime(), nullable=False),
            sa.Column("source", sa.String(), nullable=True),
            sa.Column("quality", sa.String(), nullable=True),
            sa.Column("payload_json", sa.Text(), nullable=True),
            sa.Column("electrical_power_kw", sa.Float(), nullable=True),
            sa.Column("hvac_power_kw", sa.Float(), nullable=True),
            sa.Column("daily_energy_kwh", sa.Float(), nullable=True),
            sa.Column("occupancy", sa.Float(), nullable=True),
            sa.Column("outdoor_temp_c", sa.Float(), nullable=True),
        )


def downgrade() -> None:
    pass
