"""Indexes used by the scheduling dashboard aggregations."""
from alembic import op
import sqlalchemy as sa

revision = "0005_scheduling_dashboard_indexes"
down_revision = "0004_o1_decisions_columns"
branch_labels = None
depends_on = None


def _indexes(table: str):
    insp = sa.inspect(op.get_bind())
    if table not in insp.get_table_names():
        return set()
    return {i["name"] for i in insp.get_indexes(table)}


def _ensure(name, table, cols):
    if name not in _indexes(table):
        op.create_index(name, table, cols)


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    tables = set(insp.get_table_names())
    if "o1_actions" in tables:
        _ensure("ix_o1_actions_ts", "o1_actions", ["timestamp"])
        _ensure("ix_o1_actions_run", "o1_actions", ["run_id"])
    if "o2_actions" in tables:
        _ensure("ix_o2_actions_ts", "o2_actions", ["timestamp"])
        _ensure("ix_o2_actions_zone", "o2_actions", ["zone_id"])
    if "o3_actions" in tables:
        _ensure("ix_o3_actions_ts", "o3_actions", ["timestamp"])
        _ensure("ix_o3_actions_ahu", "o3_actions", ["ahu_id"])
    if "o4_actions" in tables:
        _ensure("ix_o4_actions_ts", "o4_actions", ["timestamp"])
    if "o1_savings_verification" in tables:
        _ensure("ix_o1_sav_status", "o1_savings_verification", ["verification_status"])
    if "supervisory_actions" in tables:
        cols = {c["name"] for c in insp.get_columns("supervisory_actions")}
        if "timestamp" in cols:
            _ensure("ix_sup_actions_ts", "supervisory_actions", ["timestamp"])
        if "opportunity_code" in cols:
            _ensure("ix_sup_actions_opp", "supervisory_actions", ["opportunity_code"])


def downgrade() -> None:
    pass
