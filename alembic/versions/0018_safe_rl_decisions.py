"""Stage E Safe-RL decision persistence table."""
from alembic import op
import sqlalchemy as sa

revision = "0018_safe_rl_decisions"
down_revision = "0017_rls_online_learning"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "safe_rl_decisions" in tables:
        return
    op.create_table(
        "safe_rl_decisions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("building_id", sa.String(), nullable=True),
        sa.Column("zone_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("chosen_action_json", sa.JSON(), nullable=True),
        sa.Column("rejected_actions_json", sa.JSON(), nullable=True),
        sa.Column("constraints_json", sa.JSON(), nullable=True),
        sa.Column("state_snapshot_json", sa.JSON(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("mapped_command_ids_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_safe_rl_decisions_building_id", "safe_rl_decisions", ["building_id"])
    op.create_index("ix_safe_rl_decisions_zone_id", "safe_rl_decisions", ["zone_id"])
    op.create_index("ix_safe_rl_decisions_status", "safe_rl_decisions", ["status"])
    op.create_index("ix_safe_rl_decisions_created_at", "safe_rl_decisions", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_safe_rl_decisions_created_at", table_name="safe_rl_decisions")
    op.drop_index("ix_safe_rl_decisions_status", table_name="safe_rl_decisions")
    op.drop_index("ix_safe_rl_decisions_zone_id", table_name="safe_rl_decisions")
    op.drop_index("ix_safe_rl_decisions_building_id", table_name="safe_rl_decisions")
    op.drop_table("safe_rl_decisions")
