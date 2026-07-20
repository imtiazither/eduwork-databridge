"""Add Phase 4 ingestion resume, failure, and content-idempotency metadata.

Revision ID: 20260719_0002
Revises: 20260719_0001
Create Date: 2026-07-19
"""

from alembic import op
import sqlalchemy as sa

revision = "20260719_0002"
down_revision = "20260719_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {item["name"] for item in inspector.get_columns("ingestion_runs")}
    additions = [
        sa.Column("resume_from_run_id", sa.Uuid(), nullable=True),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("failure_code", sa.String(length=100), nullable=True),
        sa.Column("failure_summary", sa.String(length=500), nullable=True),
    ]
    for column in additions:
        if column.name not in columns:
            op.add_column("ingestion_runs", column)
    if bind.dialect.name != "sqlite":
        foreign_keys = {item["name"] for item in inspector.get_foreign_keys("ingestion_runs")}
        name = "fk_ingestion_runs_resume_from_run_id_ingestion_runs"
        if name not in foreign_keys:
            op.create_foreign_key(
                name,
                "ingestion_runs",
                "ingestion_runs",
                ["resume_from_run_id"],
                ["id"],
            )
    unique_names = {item["name"] for item in inspector.get_unique_constraints("raw_snapshots")}
    if "uq_snapshot_content" not in unique_names:
        if bind.dialect.name == "sqlite":
            with op.batch_alter_table("raw_snapshots") as batch:
                batch.create_unique_constraint(
                    "uq_snapshot_content", ["source_object_id", "checksum_sha256"]
                )
        else:
            op.create_unique_constraint(
                "uq_snapshot_content",
                "raw_snapshots",
                ["source_object_id", "checksum_sha256"],
            )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        # SQLite development databases are normally rebuilt; downgrade-to-base remains supported.
        return
    op.drop_constraint("uq_snapshot_content", "raw_snapshots", type_="unique")
    op.drop_constraint(
        "fk_ingestion_runs_resume_from_run_id_ingestion_runs",
        "ingestion_runs",
        type_="foreignkey",
    )
    op.drop_column("ingestion_runs", "failure_summary")
    op.drop_column("ingestion_runs", "failure_code")
    op.drop_column("ingestion_runs", "attempt_number")
    op.drop_column("ingestion_runs", "resume_from_run_id")
