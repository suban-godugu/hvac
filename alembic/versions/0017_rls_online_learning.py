"""Online RLS model state table for Stage C."""
from alembic import op
import sqlalchemy as sa

revision = "0017_rls_online_learning"
down_revision = "0016_canonical_telemetry_historian"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "rls_model_state" in tables:
        return
    op.create_table(
        "rls_model_state",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("building_id", sa.String(), nullable=False),
        sa.Column("zone_id", sa.String(), nullable=False),
        sa.Column("model_key", sa.String(), nullable=False),
        sa.Column("source_mode", sa.String(), nullable=False),
        sa.Column("theta_json", sa.JSON(), nullable=True),
        sa.Column("p_json", sa.JSON(), nullable=True),
        sa.Column("lambda", sa.Float(), nullable=True),
        sa.Column("n_updates", sa.Integer(), nullable=True),
        sa.Column("last_error", sa.Float(), nullable=True),
        sa.Column("rmse_ewma", sa.Float(), nullable=True),
        sa.Column("last_predicted", sa.Float(), nullable=True),
        sa.Column("last_actual", sa.Float(), nullable=True),
        sa.Column("last_sample_ts", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=True),
    )
    op.create_index("ix_rls_model_state_building_id", "rls_model_state", ["building_id"])
    op.create_index("ix_rls_model_state_zone_id", "rls_model_state", ["zone_id"])
    op.create_index("ix_rls_model_state_model_key", "rls_model_state", ["model_key"])
    op.create_index("ix_rls_model_state_source_mode", "rls_model_state", ["source_mode"])
    op.create_index("ix_rls_model_state_updated_at", "rls_model_state", ["updated_at"])
    op.create_index(
        "uq_rls_zone_model_source",
        "rls_model_state",
        ["building_id", "zone_id", "model_key", "source_mode"],
        unique=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "rls_model_state" not in tables:
        return
    op.drop_index("uq_rls_zone_model_source", table_name="rls_model_state")
    op.drop_index("ix_rls_model_state_updated_at", table_name="rls_model_state")
    op.drop_index("ix_rls_model_state_source_mode", table_name="rls_model_state")
    op.drop_index("ix_rls_model_state_model_key", table_name="rls_model_state")
    op.drop_index("ix_rls_model_state_zone_id", table_name="rls_model_state")
    op.drop_index("ix_rls_model_state_building_id", table_name="rls_model_state")
    op.drop_table("rls_model_state")
