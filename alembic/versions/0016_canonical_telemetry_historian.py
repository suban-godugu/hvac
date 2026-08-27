"""Canonical telemetry historian index + optional Timescale hypertable."""
from alembic import op
import sqlalchemy as sa

revision = "0016_canonical_telemetry_historian"
down_revision = "0015_bms_integration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "canonical_telemetry" not in tables:
        return

    existing = {ix["name"] for ix in inspector.get_indexes("canonical_telemetry")}
    if "ix_ctel_building_point_ts" not in existing:
        op.create_index(
            "ix_ctel_building_point_ts",
            "canonical_telemetry",
            ["building_id", "point_id", "timestamp"],
        )

    # Timescale hypertable only when running on PostgreSQL with the extension available.
    if bind.dialect.name != "postgresql":
        return
    try:
        op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE")
        op.execute(
            """
            SELECT create_hypertable(
                'canonical_telemetry',
                'timestamp',
                if_not_exists => TRUE,
                migrate_data => TRUE
            )
            """
        )
    except Exception:
        # Plain Postgres or missing privileges: index-only is enough for Stage B.
        pass


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "canonical_telemetry" not in set(inspector.get_table_names()):
        return
    existing = {ix["name"] for ix in inspector.get_indexes("canonical_telemetry")}
    if "ix_ctel_building_point_ts" in existing:
        op.drop_index("ix_ctel_building_point_ts", table_name="canonical_telemetry")
