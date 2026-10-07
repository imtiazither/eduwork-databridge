"""Add concurrency control and stable ordering for match review.

Revision ID: 20261007_0005
Revises: 20260720_0004
"""

import sqlalchemy as sa
from alembic import op

revision = "20261007_0005"
down_revision = "20260720_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "match_candidates",
        sa.Column("revision", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "match_decisions",
        sa.Column("revision", sa.Integer(), nullable=False, server_default="0"),
    )
    # Preserve existing append-only history. UUID breaks equal timestamp ties.
    op.execute(
        sa.text("""
        WITH ranked AS (
            SELECT id, ROW_NUMBER() OVER (
                PARTITION BY candidate_id ORDER BY decided_at, id
            ) AS revision
            FROM match_decisions
        )
        UPDATE match_decisions SET revision = (
            SELECT revision FROM ranked WHERE ranked.id = match_decisions.id
        )
    """)
    )
    op.execute(
        sa.text("""
        UPDATE match_candidates SET revision = (
            SELECT COUNT(*) FROM match_decisions
            WHERE match_decisions.candidate_id = match_candidates.id
        )
    """)
    )
    with op.batch_alter_table("match_candidates") as batch:
        batch.create_check_constraint("ck_match_candidate_revision", "revision >= 0")
        batch.create_index("ix_match_queue", ["organization_id", "status", "created_at", "id"])
    with op.batch_alter_table("match_decisions") as batch:
        batch.alter_column("revision", server_default=None, existing_type=sa.Integer())
        batch.create_check_constraint("ck_match_decision_revision", "revision > 0")
        batch.create_unique_constraint("uq_match_decision_revision", ["candidate_id", "revision"])


def downgrade() -> None:
    with op.batch_alter_table("match_decisions") as batch:
        batch.drop_constraint("uq_match_decision_revision", type_="unique")
        batch.drop_constraint("ck_match_decision_revision", type_="check")
        batch.drop_column("revision")
    with op.batch_alter_table("match_candidates") as batch:
        batch.drop_index("ix_match_queue")
        batch.drop_constraint("ck_match_candidate_revision", type_="check")
        batch.drop_column("revision")
