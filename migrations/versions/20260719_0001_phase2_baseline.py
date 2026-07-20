"""Phase 2 canonical and control-plane baseline.

Revision ID: 20260719_0001
Revises:
Create Date: 2026-07-19

The initial prototype baseline uses SQLAlchemy metadata to create the complete schema. Future
revisions should use explicit Alembic operations generated and reviewed as schema changes occur.
"""
from alembic import op

from eduwork_databridge.db import Base, models  # noqa: F401

revision = "20260719_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
