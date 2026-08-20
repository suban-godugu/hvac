from alembic import op

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing tables were created by SQLAlchemy create_all(). Stamp only.
    pass


def downgrade() -> None:
    pass
