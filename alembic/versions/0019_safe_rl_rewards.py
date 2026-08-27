"""Stage H3 — add realized reward columns to safe_rl_decisions."""
from alembic import op
import sqlalchemy as sa

revision = "0019_safe_rl_rewards"
down_revision = "0018_safe_rl_decisions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "safe_rl_decisions" not in tables:
        return
    cols = {c["name"] for c in sa.inspect(bind).get_columns("safe_rl_decisions")}
    if "realized_reward" not in cols:
        op.add_column("safe_rl_decisions", sa.Column("realized_reward", sa.Float(), nullable=True))
    if "reward_energy" not in cols:
        op.add_column("safe_rl_decisions", sa.Column("reward_energy", sa.Float(), nullable=True))
    if "reward_comfort" not in cols:
        op.add_column("safe_rl_decisions", sa.Column("reward_comfort", sa.Float(), nullable=True))
    if "reward_equipment" not in cols:
        op.add_column("safe_rl_decisions", sa.Column("reward_equipment", sa.Float(), nullable=True))
    if "measured_at" not in cols:
        op.add_column("safe_rl_decisions", sa.Column("measured_at", sa.DateTime(), nullable=True))
    if "command_id" not in cols:
        op.add_column("safe_rl_decisions", sa.Column("command_id", sa.String(), nullable=True))
        op.create_index("ix_safe_rl_decisions_command_id", "safe_rl_decisions", ["command_id"])


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "safe_rl_decisions" not in tables:
        return
    cols = {c["name"] for c in sa.inspect(bind).get_columns("safe_rl_decisions")}
    if "command_id" in cols:
        op.drop_index("ix_safe_rl_decisions_command_id", table_name="safe_rl_decisions")
        op.drop_column("safe_rl_decisions", "command_id")
    for name in ("measured_at", "reward_equipment", "reward_comfort", "reward_energy", "realized_reward"):
        if name in cols:
            op.drop_column("safe_rl_decisions", name)
