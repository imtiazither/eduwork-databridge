"""Add Phase 5–8 processing, drift, mapping, quarantine, and evaluation metadata.

Revision ID: 20260719_0003
Revises: 20260719_0002
Create Date: 2026-07-19
"""

from alembic import op
import sqlalchemy as sa

from eduwork_databridge.db import Base, models  # noqa: F401

revision = "20260719_0003"
down_revision = "20260719_0002"
branch_labels = None
depends_on = None

NEW_TABLES = [
    "profile_comparisons",
    "lookup_tables",
    "mapping_executions",
    "mapping_errors",
    "match_evaluations",
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    for table_name in NEW_TABLES:
        if table_name not in existing_tables:
            Base.metadata.tables[table_name].create(bind=bind, checkfirst=True)

    columns = {item["name"] for item in inspector.get_columns("quarantine_records")}
    additions = [
        sa.Column("waiver_reason", sa.Text(), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("supersedes_quarantine_id", sa.Uuid(), nullable=True),
        sa.Column("corrected_snapshot_id", sa.Uuid(), nullable=True),
    ]
    for column in additions:
        if column.name not in columns:
            op.add_column("quarantine_records", column)
    if bind.dialect.name != "sqlite":
        foreign_keys = {item["name"] for item in inspector.get_foreign_keys("quarantine_records")}
        definitions = [
            (
                "fk_quarantine_records_supersedes_quarantine_id",
                "quarantine_records",
                ["supersedes_quarantine_id"],
                ["id"],
            ),
            (
                "fk_quarantine_records_corrected_snapshot_id_raw_snapshots",
                "raw_snapshots",
                ["corrected_snapshot_id"],
                ["id"],
            ),
        ]
        for name, target, local_columns, remote_columns in definitions:
            if name not in foreign_keys:
                op.create_foreign_key(
                    name,
                    "quarantine_records",
                    target,
                    local_columns,
                    remote_columns,
                )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return
    op.drop_constraint(
        "fk_quarantine_records_corrected_snapshot_id_raw_snapshots",
        "quarantine_records",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_quarantine_records_supersedes_quarantine_id",
        "quarantine_records",
        type_="foreignkey",
    )
    for name in [
        "corrected_snapshot_id",
        "supersedes_quarantine_id",
        "resolved_at",
        "resolution_note",
        "waiver_reason",
    ]:
        op.drop_column("quarantine_records", name)
    for table_name in reversed(NEW_TABLES):
        op.drop_table(table_name)
