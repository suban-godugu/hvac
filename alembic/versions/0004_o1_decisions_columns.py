"""Add missing columns on existing o1_decisions to match ORM."""
from alembic import op
import sqlalchemy as sa

revision = "0004_o1_decisions_columns"
down_revision = "0003_o1_supervisory"
branch_labels = None
depends_on = None


def _cols(table: str):
    insp = sa.inspect(op.get_bind())
    if table not in insp.get_table_names():
        return set()
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    cols = _cols("o1_decisions")
    if not cols:
        return
    with op.batch_alter_table("o1_decisions") as batch:
        if "building_id" not in cols:
            batch.add_column(sa.Column("building_id", sa.String(), nullable=True))
        if "start_confidence" not in cols:
            batch.add_column(sa.Column("start_confidence", sa.Float(), nullable=True))
        if "stop_confidence" not in cols:
            batch.add_column(sa.Column("stop_confidence", sa.Float(), nullable=True))
        if "stop_decision" not in cols:
            batch.add_column(sa.Column("stop_decision", sa.String(), nullable=True))
        if "coast_advance_min" not in cols:
            batch.add_column(sa.Column("coast_advance_min", sa.Float(), nullable=True))
        if "thermal_rate_used" not in cols:
            batch.add_column(sa.Column("thermal_rate_used", sa.Float(), nullable=True))
        if "predicted_savings_kwh" not in cols:
            batch.add_column(sa.Column("predicted_savings_kwh", sa.Float(), nullable=True))
        if "safety_check" not in cols:
            batch.add_column(sa.Column("safety_check", sa.String(), nullable=True))


def downgrade() -> None:
    pass
