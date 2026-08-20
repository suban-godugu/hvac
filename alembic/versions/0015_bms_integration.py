"""BMS connections, devices, points, and equipment mappings. No seed data."""
from alembic import op
import sqlalchemy as sa

revision = "0015_bms_integration"
down_revision = "0014_ml_layer"
branch_labels = None
depends_on = None


def _tables():
    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    existing = _tables()
    if "bms_connections" not in existing:
        op.create_table(
            "bms_connections",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("building_id", sa.String(), nullable=True),
            sa.Column("protocol", sa.String(), nullable=False),
            sa.Column("host", sa.String(), nullable=True),
            sa.Column("port", sa.Integer(), nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=True),
            sa.Column("connected", sa.Boolean(), nullable=True),
            sa.Column("last_connected_at", sa.DateTime(), nullable=True),
            sa.Column("last_error", sa.String(), nullable=True),
            sa.Column("write_enabled", sa.Boolean(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_bms_connections_building_id", "bms_connections", ["building_id"])
        op.create_index("ix_bms_conn_bldg", "bms_connections", ["building_id", "protocol"])
    if "bms_devices" not in existing:
        op.create_table(
            "bms_devices",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("connection_id", sa.String(), nullable=False),
            sa.Column("device_identifier", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=True),
            sa.Column("device_type", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["connection_id"], ["bms_connections.id"]),
            sa.UniqueConstraint("connection_id", "device_identifier", name="uq_bms_device_ident"),
        )
        op.create_index("ix_bms_devices_connection_id", "bms_devices", ["connection_id"])
    if "bms_points" not in existing:
        op.create_table(
            "bms_points",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("device_id", sa.String(), nullable=False),
            sa.Column("point_identifier", sa.String(), nullable=False),
            sa.Column("name", sa.String(), nullable=True),
            sa.Column("object_type", sa.String(), nullable=True),
            sa.Column("object_instance", sa.String(), nullable=True),
            sa.Column("register", sa.String(), nullable=True),
            sa.Column("unit", sa.String(), nullable=True),
            sa.Column("data_type", sa.String(), nullable=True),
            sa.Column("readable", sa.Boolean(), nullable=True),
            sa.Column("writable", sa.Boolean(), nullable=True),
            sa.Column("min_value", sa.Float(), nullable=True),
            sa.Column("max_value", sa.Float(), nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["device_id"], ["bms_devices.id"]),
            sa.UniqueConstraint("device_id", "point_identifier", name="uq_bms_point_ident"),
        )
        op.create_index("ix_bms_points_device_id", "bms_points", ["device_id"])
    if "equipment_point_mappings" not in existing:
        op.create_table(
            "equipment_point_mappings",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("equipment_id", sa.String(), nullable=False),
            sa.Column("canonical_point", sa.String(), nullable=False),
            sa.Column("bms_point_id", sa.String(), nullable=False),
            sa.Column("direction", sa.String(), nullable=False),
            sa.Column("safety_enabled", sa.Boolean(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["bms_point_id"], ["bms_points.id"]),
            sa.UniqueConstraint("equipment_id", "canonical_point", name="uq_eq_canonical"),
        )
        op.create_index("ix_equipment_point_mappings_equipment_id", "equipment_point_mappings", ["equipment_id"])
        op.create_index("ix_equipment_point_mappings_bms_point_id", "equipment_point_mappings", ["bms_point_id"])


def downgrade() -> None:
    existing = _tables()
    for name in ("equipment_point_mappings", "bms_points", "bms_devices", "bms_connections"):
        if name in existing:
            op.drop_table(name)
