"""Add Phase 9–12 model, mart, orchestration, and retention metadata.

Revision ID: 20260720_0004
Revises: 20260719_0003
Create Date: 2026-07-20
"""

from alembic import op
import sqlalchemy as sa

from eduwork_databridge.db import Base, models  # noqa: F401

revision = "20260720_0004"
down_revision = "20260719_0003"
branch_labels = None
depends_on = None

NEW_TABLES = [
    "probabilistic_models",
    "probabilistic_runs",
    "data_mart_snapshots",
    "asset_runs",
    "retention_policies",
]


def upgrade() -> None:
    bind = op.get_bind()
    existing = set(sa.inspect(bind).get_table_names())
    for table_name in NEW_TABLES:
        if table_name not in existing:
            Base.metadata.tables[table_name].create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return
    for table_name in reversed(NEW_TABLES):
        op.drop_table(table_name)
