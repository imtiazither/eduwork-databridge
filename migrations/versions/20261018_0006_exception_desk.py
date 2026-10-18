"""Preserve quarantine resolutions and protect concurrent updates."""

import sqlalchemy as sa
from alembic import op

revision = "20261018_0006"
down_revision = "20261007_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("quarantine_records") as batch:
        batch.add_column(sa.Column("revision", sa.Integer(), nullable=False, server_default="0"))
        batch.create_check_constraint("ck_quarantine_revision", "revision >= 0")
        batch.create_index("ix_quarantine_queue", ["organization_id", "status", "created_at", "id"])
    op.create_table(
        "quarantine_resolutions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("quarantine_id", sa.Uuid(), sa.ForeignKey("quarantine_records.id"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("reviewer_id", sa.Uuid(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("corrected_snapshot_id", sa.Uuid(), sa.ForeignKey("raw_snapshots.id")),
        sa.Column("imported", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("quarantine_id", "revision", name="uq_quarantine_resolution_revision"),
        sa.CheckConstraint("revision > 0", name="ck_quarantine_resolution_revision"),
    )
    op.create_index("ix_quarantine_resolutions_organization_id", "quarantine_resolutions", ["organization_id"])
    op.create_index("ix_quarantine_resolutions_quarantine_id", "quarantine_resolutions", ["quarantine_id"])
    # Older versions retained only the latest note. Import it without inventing prior history.
    op.execute(sa.text("""
        INSERT INTO quarantine_resolutions
            (id, created_at, updated_at, organization_id, quarantine_id, revision,
             status, note, reviewer_id, recorded_at, corrected_snapshot_id, imported)
        SELECT id, created_at, updated_at, organization_id, id, 1,
            status, resolution_note, reviewer_id, COALESCE(resolved_at, updated_at),
            corrected_snapshot_id, TRUE
        FROM quarantine_records
        WHERE resolution_note IS NOT NULL AND TRIM(resolution_note) <> ''
    """))
    op.execute(sa.text("""
        UPDATE quarantine_records SET revision = 1
        WHERE id IN (SELECT quarantine_id FROM quarantine_resolutions)
    """))


def downgrade() -> None:
    if op.get_bind().scalar(sa.text("SELECT COUNT(*) FROM quarantine_resolutions WHERE imported = FALSE")):
        raise RuntimeError("Downgrade would discard resolution history. Restore a pre-upgrade backup instead.")
    op.drop_table("quarantine_resolutions")
    with op.batch_alter_table("quarantine_records") as batch:
        batch.drop_index("ix_quarantine_queue")
        batch.drop_constraint("ck_quarantine_revision", type_="check")
        batch.drop_column("revision")
