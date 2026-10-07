"""Frozen schema for the pre-0.50 reference release.

Revision ID: 20260719_0001
Revises:

The original baseline created tables from application metadata. Its deployed
schema included all 0.20 models. This freezes that schema so fresh databases
and upgrades take the same path when application models change.
"""

import sqlalchemy as sa
from alembic import op

revision = "20260719_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("organization_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("parent_organization_id", sa.Uuid(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["parent_organization_id"],
            ["organizations.id"],
            name=op.f("fk_organizations_parent_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organizations")),
    )
    op.create_index(
        op.f("ix_organizations_parent_organization_id"),
        "organizations",
        ["parent_organization_id"],
        unique=False,
    )
    op.create_table(
        "permissions",
        sa.Column("permission_key", sa.String(length=150), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_permissions")),
        sa.UniqueConstraint("permission_key", name=op.f("uq_permissions_permission_key")),
    )
    op.create_table(
        "roles",
        sa.Column("role_key", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_roles")),
        sa.UniqueConstraint("role_key", name=op.f("uq_roles_role_key")),
    )
    op.create_table(
        "users",
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("subject", name=op.f("uq_users_subject")),
    )
    op.create_table(
        "assessment_definitions",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("external_key", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("maximum_score", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("passing_score", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_assessment_definitions_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessment_definitions")),
    )
    op.create_index(
        op.f("ix_assessment_definitions_organization_id"),
        "assessment_definitions",
        ["organization_id"],
        unique=False,
    )
    op.create_table(
        "asset_runs",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("orchestration_key", sa.String(length=255), nullable=False),
        sa.Column("asset_key", sa.String(length=255), nullable=False),
        sa.Column("partition_key", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("watermark_json", sa.JSON(), nullable=False),
        sa.Column("change_hash", sa.String(length=64), nullable=True),
        sa.Column("backfill_of_run_id", sa.Uuid(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_code", sa.String(length=100), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["backfill_of_run_id"],
            ["asset_runs.id"],
            name=op.f("fk_asset_runs_backfill_of_run_id_asset_runs"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_asset_runs_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_asset_runs")),
    )
    op.create_index(op.f("ix_asset_runs_asset_key"), "asset_runs", ["asset_key"], unique=False)
    op.create_index(
        op.f("ix_asset_runs_organization_id"), "asset_runs", ["organization_id"], unique=False
    )
    op.create_table(
        "audit_events",
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("resource_id", sa.String(length=255), nullable=False),
        sa.Column("correlation_id", sa.String(length=100), nullable=True),
        sa.Column("details_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_audit_events_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_events")),
    )
    op.create_index(
        op.f("ix_audit_events_correlation_id"), "audit_events", ["correlation_id"], unique=False
    )
    op.create_index(
        op.f("ix_audit_events_organization_id"), "audit_events", ["organization_id"], unique=False
    )
    op.create_table(
        "canonical_entity_versions",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_canonical_entity_versions_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_canonical_entity_versions")),
    )
    op.create_index(
        op.f("ix_canonical_entity_versions_entity_id"),
        "canonical_entity_versions",
        ["entity_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_canonical_entity_versions_organization_id"),
        "canonical_entity_versions",
        ["organization_id"],
        unique=False,
    )
    op.create_table(
        "competency_definitions",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("external_key", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("framework_uri", sa.String(length=1000), nullable=True),
        sa.Column("parent_competency_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_competency_definitions_organization_id_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["parent_competency_id"],
            ["competency_definitions.id"],
            name="fk_competency_definitions_parent_competency_id",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_competency_definitions")),
    )
    op.create_index(
        op.f("ix_competency_definitions_organization_id"),
        "competency_definitions",
        ["organization_id"],
        unique=False,
    )
    op.create_table(
        "credential_definitions",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("external_key", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("credential_type", sa.String(length=50), nullable=False),
        sa.Column("issuer_name", sa.String(length=255), nullable=True),
        sa.Column("public_uri", sa.String(length=1000), nullable=True),
        sa.Column("expires", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_credential_definitions_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_credential_definitions")),
    )
    op.create_index(
        op.f("ix_credential_definitions_organization_id"),
        "credential_definitions",
        ["organization_id"],
        unique=False,
    )
    op.create_table(
        "data_mart_snapshots",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("mart_key", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("storage_uri", sa.String(length=1000), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("dictionary_json", sa.JSON(), nullable=False),
        sa.Column("lineage_json", sa.JSON(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_data_mart_snapshots_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_data_mart_snapshots")),
        sa.UniqueConstraint(
            "organization_id",
            "mart_key",
            "version",
            "checksum_sha256",
            name="uq_mart_snapshot_content",
        ),
    )
    op.create_index(
        op.f("ix_data_mart_snapshots_organization_id"),
        "data_mart_snapshots",
        ["organization_id"],
        unique=False,
    )
    op.create_table(
        "export_definitions",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("export_key", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("format", sa.String(length=30), nullable=False),
        sa.Column("contract_json", sa.JSON(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_export_definitions_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_export_definitions")),
    )
    op.create_index(
        op.f("ix_export_definitions_organization_id"),
        "export_definitions",
        ["organization_id"],
        unique=False,
    )
    op.create_table(
        "learning_programs",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("external_key", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("program_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_learning_programs_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_learning_programs")),
        sa.UniqueConstraint("organization_id", "external_key", name="uq_program_external_key"),
    )
    op.create_index(
        op.f("ix_learning_programs_organization_id"),
        "learning_programs",
        ["organization_id"],
        unique=False,
    )
    op.create_table(
        "lineage_nodes",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("node_type", sa.String(length=50), nullable=False),
        sa.Column("namespace", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("facets_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_lineage_nodes_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lineage_nodes")),
    )
    op.create_index(
        op.f("ix_lineage_nodes_organization_id"), "lineage_nodes", ["organization_id"], unique=False
    )
    op.create_table(
        "lookup_tables",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("lookup_key", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("values_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_lookup_tables_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lookup_tables")),
        sa.UniqueConstraint("organization_id", "lookup_key", "version", name="uq_lookup_version"),
    )
    op.create_index(
        op.f("ix_lookup_tables_organization_id"), "lookup_tables", ["organization_id"], unique=False
    )
    op.create_table(
        "mapping_sets",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("mapping_key", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("canonical_entity", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_mapping_sets_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mapping_sets")),
        sa.UniqueConstraint("organization_id", "mapping_key", "version", name="uq_mapping_version"),
    )
    op.create_index(
        op.f("ix_mapping_sets_organization_id"), "mapping_sets", ["organization_id"], unique=False
    )
    op.create_table(
        "match_evaluations",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("rule_set_key", sa.String(length=255), nullable=False),
        sa.Column("rule_set_version", sa.String(length=50), nullable=False),
        sa.Column("truth_set_name", sa.String(length=255), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_records", sa.Integer(), nullable=False),
        sa.Column("predicted_links", sa.Integer(), nullable=False),
        sa.Column("true_positives", sa.Integer(), nullable=False),
        sa.Column("false_positives", sa.Integer(), nullable=False),
        sa.Column("false_negatives", sa.Integer(), nullable=False),
        sa.Column("precision", sa.Numeric(precision=8, scale=6), nullable=False),
        sa.Column("recall", sa.Numeric(precision=8, scale=6), nullable=False),
        sa.Column("coverage", sa.Numeric(precision=8, scale=6), nullable=False),
        sa.Column("details_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_match_evaluations_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_match_evaluations")),
    )
    op.create_index(
        op.f("ix_match_evaluations_organization_id"),
        "match_evaluations",
        ["organization_id"],
        unique=False,
    )
    op.create_table(
        "match_rule_sets",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("rule_set_key", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("deterministic_rules_json", sa.JSON(), nullable=False),
        sa.Column("probabilistic_config_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_match_rule_sets_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_match_rule_sets")),
        sa.UniqueConstraint("organization_id", "rule_set_key", "version", name="uq_match_ruleset"),
    )
    op.create_index(
        op.f("ix_match_rule_sets_organization_id"),
        "match_rule_sets",
        ["organization_id"],
        unique=False,
    )
    op.create_table(
        "organization_units",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("parent_unit_id", sa.Uuid(), nullable=True),
        sa.Column("external_key", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("unit_type", sa.String(length=50), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_organization_units_organization_id_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["parent_unit_id"],
            ["organization_units.id"],
            name=op.f("fk_organization_units_parent_unit_id_organization_units"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organization_units")),
        sa.UniqueConstraint("organization_id", "external_key", name="uq_org_unit_external_key"),
    )
    op.create_index(
        op.f("ix_organization_units_organization_id"),
        "organization_units",
        ["organization_id"],
        unique=False,
    )
    op.create_table(
        "persons",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("given_name", sa.String(length=150), nullable=True),
        sa.Column("family_name", sa.String(length=150), nullable=True),
        sa.Column("preferred_name", sa.String(length=150), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_persons_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_persons")),
    )
    op.create_index("ix_person_org_status", "persons", ["organization_id", "status"], unique=False)
    op.create_index(
        op.f("ix_persons_organization_id"), "persons", ["organization_id"], unique=False
    )
    op.create_table(
        "probabilistic_models",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("model_key", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("comparison_config_json", sa.JSON(), nullable=False),
        sa.Column("parameters_json", sa.JSON(), nullable=False),
        sa.Column("review_low", sa.Numeric(precision=8, scale=6), nullable=False),
        sa.Column("auto_match", sa.Numeric(precision=8, scale=6), nullable=False),
        sa.Column("trained_on_truth_set", sa.String(length=255), nullable=True),
        sa.Column("trained_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_probabilistic_models_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_probabilistic_models")),
        sa.UniqueConstraint(
            "organization_id", "model_key", "version", name="uq_prob_model_version"
        ),
    )
    op.create_index(
        op.f("ix_probabilistic_models_organization_id"),
        "probabilistic_models",
        ["organization_id"],
        unique=False,
    )
    op.create_table(
        "retention_policies",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("policy_key", sa.String(length=255), nullable=False),
        sa.Column("raw_days", sa.Integer(), nullable=False),
        sa.Column("quarantine_days", sa.Integer(), nullable=False),
        sa.Column("export_days", sa.Integer(), nullable=False),
        sa.Column("audit_days", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_retention_policies_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_retention_policies")),
        sa.UniqueConstraint("organization_id", "policy_key", name="uq_retention_policy"),
    )
    op.create_index(
        op.f("ix_retention_policies_organization_id"),
        "retention_policies",
        ["organization_id"],
        unique=False,
    )
    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("permission_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["permissions.id"],
            name=op.f("fk_role_permissions_permission_id_permissions"),
        ),
        sa.ForeignKeyConstraint(
            ["role_id"], ["roles.id"], name=op.f("fk_role_permissions_role_id_roles")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_role_permissions")),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )
    op.create_index(
        op.f("ix_role_permissions_permission_id"),
        "role_permissions",
        ["permission_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_role_permissions_role_id"), "role_permissions", ["role_id"], unique=False
    )
    op.create_table(
        "source_systems",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("source_key", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("connector_type", sa.String(length=50), nullable=False),
        sa.Column("owner_role", sa.String(length=255), nullable=True),
        sa.Column("data_classification", sa.String(length=30), nullable=False),
        sa.Column("secret_reference", sa.String(length=500), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_source_systems_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_systems")),
        sa.UniqueConstraint("organization_id", "source_key", name="uq_source_key"),
    )
    op.create_index(
        op.f("ix_source_systems_organization_id"),
        "source_systems",
        ["organization_id"],
        unique=False,
    )
    op.create_table(
        "user_organizations",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_user_organizations_organization_id_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_user_organizations_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_organizations")),
        sa.UniqueConstraint("user_id", "organization_id", name="uq_user_organization"),
    )
    op.create_index(
        op.f("ix_user_organizations_organization_id"),
        "user_organizations",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_organizations_user_id"), "user_organizations", ["user_id"], unique=False
    )
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_user_roles_organization_id_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["role_id"], ["roles.id"], name=op.f("fk_user_roles_role_id_roles")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_user_roles_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_roles")),
        sa.UniqueConstraint("user_id", "organization_id", "role_id", name="uq_user_role_scope"),
    )
    op.create_index(
        op.f("ix_user_roles_organization_id"), "user_roles", ["organization_id"], unique=False
    )
    op.create_index(op.f("ix_user_roles_role_id"), "user_roles", ["role_id"], unique=False)
    op.create_index(op.f("ix_user_roles_user_id"), "user_roles", ["user_id"], unique=False)
    op.create_table(
        "validation_rules",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("rule_key", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("entity_name", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=30), nullable=False),
        sa.Column("expression_type", sa.String(length=100), nullable=False),
        sa.Column("expression_json", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("remediation", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_validation_rules_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_validation_rules")),
        sa.UniqueConstraint(
            "organization_id", "rule_key", "version", name="uq_validation_rule_version"
        ),
    )
    op.create_index(
        op.f("ix_validation_rules_organization_id"),
        "validation_rules",
        ["organization_id"],
        unique=False,
    )
    op.create_table(
        "assessment_attempts",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["assessment_id"],
            ["assessment_definitions.id"],
            name=op.f("fk_assessment_attempts_assessment_id_assessment_definitions"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_assessment_attempts_organization_id_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["person_id"], ["persons.id"], name=op.f("fk_assessment_attempts_person_id_persons")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessment_attempts")),
    )
    op.create_index(
        op.f("ix_assessment_attempts_assessment_id"),
        "assessment_attempts",
        ["assessment_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assessment_attempts_organization_id"),
        "assessment_attempts",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assessment_attempts_person_id"), "assessment_attempts", ["person_id"], unique=False
    )
    op.create_table(
        "competency_alignments",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("competency_id", sa.Uuid(), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("alignment_type", sa.String(length=50), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["competency_id"],
            ["competency_definitions.id"],
            name=op.f("fk_competency_alignments_competency_id_competency_definitions"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_competency_alignments_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_competency_alignments")),
    )
    op.create_index(
        op.f("ix_competency_alignments_competency_id"),
        "competency_alignments",
        ["competency_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_competency_alignments_organization_id"),
        "competency_alignments",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_competency_alignments_target_id"),
        "competency_alignments",
        ["target_id"],
        unique=False,
    )
    op.create_table(
        "credential_awards",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("credential_definition_id", sa.Uuid(), nullable=False),
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("awarded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("evidence_uri", sa.String(length=1000), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["credential_definition_id"],
            ["credential_definitions.id"],
            name="fk_credential_awards_credential_definition_id",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_credential_awards_organization_id_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["person_id"], ["persons.id"], name=op.f("fk_credential_awards_person_id_persons")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_credential_awards")),
    )
    op.create_index(
        op.f("ix_credential_awards_credential_definition_id"),
        "credential_awards",
        ["credential_definition_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_credential_awards_organization_id"),
        "credential_awards",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_credential_awards_person_id"), "credential_awards", ["person_id"], unique=False
    )
    op.create_table(
        "export_snapshots",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("export_definition_id", sa.Uuid(), nullable=False),
        sa.Column("storage_uri", sa.String(length=1000), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["export_definition_id"],
            ["export_definitions.id"],
            name=op.f("fk_export_snapshots_export_definition_id_export_definitions"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_export_snapshots_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_export_snapshots")),
    )
    op.create_index(
        op.f("ix_export_snapshots_export_definition_id"),
        "export_snapshots",
        ["export_definition_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_export_snapshots_organization_id"),
        "export_snapshots",
        ["organization_id"],
        unique=False,
    )
    op.create_table(
        "external_identities",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("source_system_id", sa.Uuid(), nullable=False),
        sa.Column("identity_type", sa.String(length=50), nullable=False),
        sa.Column("identity_value", sa.String(length=512), nullable=False),
        sa.Column("identity_value_hash", sa.String(length=64), nullable=False),
        sa.Column("trusted", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_external_identities_organization_id_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["person_id"], ["persons.id"], name=op.f("fk_external_identities_person_id_persons")
        ),
        sa.ForeignKeyConstraint(
            ["source_system_id"],
            ["source_systems.id"],
            name=op.f("fk_external_identities_source_system_id_source_systems"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_external_identities")),
        sa.UniqueConstraint(
            "organization_id",
            "source_system_id",
            "identity_type",
            "identity_value_hash",
            name="uq_external_identity_scope",
        ),
    )
    op.create_index(
        op.f("ix_external_identities_organization_id"),
        "external_identities",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_external_identities_person_id"), "external_identities", ["person_id"], unique=False
    )
    op.create_index(
        op.f("ix_external_identities_source_system_id"),
        "external_identities",
        ["source_system_id"],
        unique=False,
    )
    op.create_table(
        "ingestion_runs",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("source_system_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cursor_json", sa.JSON(), nullable=False),
        sa.Column("correlation_id", sa.String(length=100), nullable=False),
        sa.Column("resume_from_run_id", sa.Uuid(), nullable=True),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("failure_code", sa.String(length=100), nullable=True),
        sa.Column("failure_summary", sa.String(length=500), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_ingestion_runs_organization_id_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["resume_from_run_id"],
            ["ingestion_runs.id"],
            name=op.f("fk_ingestion_runs_resume_from_run_id_ingestion_runs"),
        ),
        sa.ForeignKeyConstraint(
            ["source_system_id"],
            ["source_systems.id"],
            name=op.f("fk_ingestion_runs_source_system_id_source_systems"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ingestion_runs")),
        sa.UniqueConstraint("correlation_id", name=op.f("uq_ingestion_runs_correlation_id")),
    )
    op.create_index(
        op.f("ix_ingestion_runs_organization_id"),
        "ingestion_runs",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ingestion_runs_source_system_id"),
        "ingestion_runs",
        ["source_system_id"],
        unique=False,
    )
    op.create_table(
        "learning_offerings",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("program_id", sa.Uuid(), nullable=True),
        sa.Column("external_key", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("offering_type", sa.String(length=50), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_learning_offerings_organization_id_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["program_id"],
            ["learning_programs.id"],
            name=op.f("fk_learning_offerings_program_id_learning_programs"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_learning_offerings")),
        sa.UniqueConstraint("organization_id", "external_key", name="uq_offering_external_key"),
    )
    op.create_index(
        op.f("ix_learning_offerings_organization_id"),
        "learning_offerings",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_learning_offerings_program_id"), "learning_offerings", ["program_id"], unique=False
    )
    op.create_table(
        "lineage_edges",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("from_node_id", sa.Uuid(), nullable=False),
        sa.Column("to_node_id", sa.Uuid(), nullable=False),
        sa.Column("relation_type", sa.String(length=50), nullable=False),
        sa.Column("field_mapping_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["from_node_id"],
            ["lineage_nodes.id"],
            name=op.f("fk_lineage_edges_from_node_id_lineage_nodes"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_lineage_edges_organization_id_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["to_node_id"],
            ["lineage_nodes.id"],
            name=op.f("fk_lineage_edges_to_node_id_lineage_nodes"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lineage_edges")),
    )
    op.create_index(
        op.f("ix_lineage_edges_from_node_id"), "lineage_edges", ["from_node_id"], unique=False
    )
    op.create_index(
        op.f("ix_lineage_edges_organization_id"), "lineage_edges", ["organization_id"], unique=False
    )
    op.create_index(
        op.f("ix_lineage_edges_to_node_id"), "lineage_edges", ["to_node_id"], unique=False
    )
    op.create_table(
        "mapping_rules",
        sa.Column("mapping_set_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("target_field", sa.String(length=255), nullable=False),
        sa.Column("source_expression", sa.String(length=1000), nullable=True),
        sa.Column("transform_type", sa.String(length=100), nullable=False),
        sa.Column("parameters_json", sa.JSON(), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["mapping_set_id"],
            ["mapping_sets.id"],
            name=op.f("fk_mapping_rules_mapping_set_id_mapping_sets"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mapping_rules")),
    )
    op.create_index(
        op.f("ix_mapping_rules_mapping_set_id"), "mapping_rules", ["mapping_set_id"], unique=False
    )
    op.create_table(
        "match_candidates",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("rule_set_id", sa.Uuid(), nullable=False),
        sa.Column("left_record_key", sa.String(length=255), nullable=False),
        sa.Column("right_record_key", sa.String(length=255), nullable=False),
        sa.Column("score", sa.Numeric(precision=8, scale=6), nullable=True),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_match_candidates_organization_id_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["rule_set_id"],
            ["match_rule_sets.id"],
            name=op.f("fk_match_candidates_rule_set_id_match_rule_sets"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_match_candidates")),
    )
    op.create_index(
        op.f("ix_match_candidates_organization_id"),
        "match_candidates",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_match_candidates_rule_set_id"), "match_candidates", ["rule_set_id"], unique=False
    )
    op.create_table(
        "probabilistic_runs",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("model_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("candidate_count", sa.Integer(), nullable=False),
        sa.Column("auto_match_count", sa.Integer(), nullable=False),
        sa.Column("review_count", sa.Integer(), nullable=False),
        sa.Column("no_match_count", sa.Integer(), nullable=False),
        sa.Column("conflict_count", sa.Integer(), nullable=False),
        sa.Column("metrics_json", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["model_id"],
            ["probabilistic_models.id"],
            name=op.f("fk_probabilistic_runs_model_id_probabilistic_models"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_probabilistic_runs_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_probabilistic_runs")),
    )
    op.create_index(
        op.f("ix_probabilistic_runs_model_id"), "probabilistic_runs", ["model_id"], unique=False
    )
    op.create_index(
        op.f("ix_probabilistic_runs_organization_id"),
        "probabilistic_runs",
        ["organization_id"],
        unique=False,
    )
    op.create_table(
        "role_assignments",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("organization_unit_id", sa.Uuid(), nullable=True),
        sa.Column("role_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_role_assignments_organization_id_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_unit_id"],
            ["organization_units.id"],
            name=op.f("fk_role_assignments_organization_unit_id_organization_units"),
        ),
        sa.ForeignKeyConstraint(
            ["person_id"], ["persons.id"], name=op.f("fk_role_assignments_person_id_persons")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_role_assignments")),
    )
    op.create_index(
        op.f("ix_role_assignments_organization_id"),
        "role_assignments",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_role_assignments_person_id"), "role_assignments", ["person_id"], unique=False
    )
    op.create_table(
        "source_objects",
        sa.Column("source_system_id", sa.Uuid(), nullable=False),
        sa.Column("object_key", sa.String(length=255), nullable=False),
        sa.Column("object_type", sa.String(length=50), nullable=False),
        sa.Column("location_template", sa.String(length=1000), nullable=True),
        sa.Column("refresh_expectation", sa.String(length=100), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["source_system_id"],
            ["source_systems.id"],
            name=op.f("fk_source_objects_source_system_id_source_systems"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_objects")),
        sa.UniqueConstraint("source_system_id", "object_key", name="uq_source_object_key"),
    )
    op.create_index(
        op.f("ix_source_objects_source_system_id"),
        "source_objects",
        ["source_system_id"],
        unique=False,
    )
    op.create_table(
        "assessment_results",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_id", sa.Uuid(), nullable=False),
        sa.Column("raw_score", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("normalized_score", sa.Numeric(precision=8, scale=6), nullable=True),
        sa.Column("outcome", sa.String(length=50), nullable=True),
        sa.Column("graded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["attempt_id"],
            ["assessment_attempts.id"],
            name=op.f("fk_assessment_results_attempt_id_assessment_attempts"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_assessment_results_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assessment_results")),
        sa.UniqueConstraint("attempt_id", name=op.f("uq_assessment_results_attempt_id")),
    )
    op.create_index(
        op.f("ix_assessment_results_organization_id"),
        "assessment_results",
        ["organization_id"],
        unique=False,
    )
    op.create_table(
        "data_contracts",
        sa.Column("source_object_id", sa.Uuid(), nullable=False),
        sa.Column("contract_key", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("schema_uri", sa.String(length=1000), nullable=True),
        sa.Column("schema_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["source_object_id"],
            ["source_objects.id"],
            name=op.f("fk_data_contracts_source_object_id_source_objects"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_data_contracts")),
        sa.UniqueConstraint(
            "source_object_id", "contract_key", "version", name="uq_contract_version"
        ),
    )
    op.create_index(
        op.f("ix_data_contracts_source_object_id"),
        "data_contracts",
        ["source_object_id"],
        unique=False,
    )
    op.create_table(
        "experience_events",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("source_system_id", sa.Uuid(), nullable=False),
        sa.Column("person_id", sa.Uuid(), nullable=True),
        sa.Column("offering_id", sa.Uuid(), nullable=True),
        sa.Column("event_key", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["offering_id"],
            ["learning_offerings.id"],
            name=op.f("fk_experience_events_offering_id_learning_offerings"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_experience_events_organization_id_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["person_id"], ["persons.id"], name=op.f("fk_experience_events_person_id_persons")
        ),
        sa.ForeignKeyConstraint(
            ["source_system_id"],
            ["source_systems.id"],
            name=op.f("fk_experience_events_source_system_id_source_systems"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_experience_events")),
        sa.UniqueConstraint(
            "organization_id", "source_system_id", "event_key", name="uq_event_key"
        ),
    )
    op.create_index(
        op.f("ix_experience_events_organization_id"),
        "experience_events",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_experience_events_person_id"), "experience_events", ["person_id"], unique=False
    )
    op.create_index(
        op.f("ix_experience_events_source_system_id"),
        "experience_events",
        ["source_system_id"],
        unique=False,
    )
    op.create_table(
        "match_decisions",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(length=30), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("reviewer_id", sa.Uuid(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supersedes_decision_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["match_candidates.id"],
            name=op.f("fk_match_decisions_candidate_id_match_candidates"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_match_decisions_organization_id_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_decision_id"],
            ["match_decisions.id"],
            name=op.f("fk_match_decisions_supersedes_decision_id_match_decisions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_match_decisions")),
    )
    op.create_index(
        op.f("ix_match_decisions_candidate_id"), "match_decisions", ["candidate_id"], unique=False
    )
    op.create_index(
        op.f("ix_match_decisions_organization_id"),
        "match_decisions",
        ["organization_id"],
        unique=False,
    )
    op.create_table(
        "participations",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("person_id", sa.Uuid(), nullable=False),
        sa.Column("offering_id", sa.Uuid(), nullable=False),
        sa.Column("source_record_key", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completion_percent", sa.Integer(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["offering_id"],
            ["learning_offerings.id"],
            name=op.f("fk_participations_offering_id_learning_offerings"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_participations_organization_id_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["person_id"], ["persons.id"], name=op.f("fk_participations_person_id_persons")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_participations")),
        sa.UniqueConstraint(
            "organization_id",
            "person_id",
            "offering_id",
            "source_record_key",
            name="uq_participation_source_record",
        ),
    )
    op.create_index(
        op.f("ix_participations_offering_id"), "participations", ["offering_id"], unique=False
    )
    op.create_index(
        op.f("ix_participations_organization_id"),
        "participations",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_participations_person_id"), "participations", ["person_id"], unique=False
    )
    op.create_table(
        "raw_snapshots",
        sa.Column("ingestion_run_id", sa.Uuid(), nullable=False),
        sa.Column("source_object_id", sa.Uuid(), nullable=False),
        sa.Column("storage_uri", sa.String(length=1000), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("schema_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("manifest_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["ingestion_run_id"],
            ["ingestion_runs.id"],
            name=op.f("fk_raw_snapshots_ingestion_run_id_ingestion_runs"),
        ),
        sa.ForeignKeyConstraint(
            ["source_object_id"],
            ["source_objects.id"],
            name=op.f("fk_raw_snapshots_source_object_id_source_objects"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_raw_snapshots")),
        sa.UniqueConstraint("source_object_id", "checksum_sha256", name="uq_snapshot_content"),
    )
    op.create_index(
        op.f("ix_raw_snapshots_ingestion_run_id"),
        "raw_snapshots",
        ["ingestion_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_raw_snapshots_source_object_id"),
        "raw_snapshots",
        ["source_object_id"],
        unique=False,
    )
    op.create_table(
        "validation_results",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("ingestion_run_id", sa.Uuid(), nullable=False),
        sa.Column("validation_rule_id", sa.Uuid(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("evaluated_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["ingestion_run_id"],
            ["ingestion_runs.id"],
            name=op.f("fk_validation_results_ingestion_run_id_ingestion_runs"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_validation_results_organization_id_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["validation_rule_id"],
            ["validation_rules.id"],
            name=op.f("fk_validation_results_validation_rule_id_validation_rules"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_validation_results")),
    )
    op.create_index(
        op.f("ix_validation_results_ingestion_run_id"),
        "validation_results",
        ["ingestion_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_validation_results_organization_id"),
        "validation_results",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_validation_results_validation_rule_id"),
        "validation_results",
        ["validation_rule_id"],
        unique=False,
    )
    op.create_table(
        "mapping_executions",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("raw_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("mapping_key", sa.String(length=255), nullable=False),
        sa.Column("mapping_version", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("dry_run", sa.Boolean(), nullable=False),
        sa.Column("input_count", sa.Integer(), nullable=False),
        sa.Column("output_count", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("output_uri", sa.String(length=1000), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_mapping_executions_organization_id_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["raw_snapshot_id"],
            ["raw_snapshots.id"],
            name=op.f("fk_mapping_executions_raw_snapshot_id_raw_snapshots"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mapping_executions")),
    )
    op.create_index(
        op.f("ix_mapping_executions_organization_id"),
        "mapping_executions",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_mapping_executions_raw_snapshot_id"),
        "mapping_executions",
        ["raw_snapshot_id"],
        unique=False,
    )
    op.create_table(
        "quarantine_records",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("ingestion_run_id", sa.Uuid(), nullable=False),
        sa.Column("validation_rule_id", sa.Uuid(), nullable=False),
        sa.Column("raw_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("source_record_key", sa.String(length=255), nullable=False),
        sa.Column("field_name", sa.String(length=255), nullable=True),
        sa.Column("evidence_masked", sa.Text(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("reviewer_id", sa.Uuid(), nullable=True),
        sa.Column("waiver_reason", sa.Text(), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("supersedes_quarantine_id", sa.Uuid(), nullable=True),
        sa.Column("corrected_snapshot_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["corrected_snapshot_id"],
            ["raw_snapshots.id"],
            name=op.f("fk_quarantine_records_corrected_snapshot_id_raw_snapshots"),
        ),
        sa.ForeignKeyConstraint(
            ["ingestion_run_id"],
            ["ingestion_runs.id"],
            name=op.f("fk_quarantine_records_ingestion_run_id_ingestion_runs"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_quarantine_records_organization_id_organizations"),
        ),
        sa.ForeignKeyConstraint(
            ["raw_snapshot_id"],
            ["raw_snapshots.id"],
            name=op.f("fk_quarantine_records_raw_snapshot_id_raw_snapshots"),
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_quarantine_id"],
            ["quarantine_records.id"],
            name="fk_quarantine_records_supersedes_quarantine_id",
        ),
        sa.ForeignKeyConstraint(
            ["validation_rule_id"],
            ["validation_rules.id"],
            name=op.f("fk_quarantine_records_validation_rule_id_validation_rules"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quarantine_records")),
    )
    op.create_index(
        op.f("ix_quarantine_records_ingestion_run_id"),
        "quarantine_records",
        ["ingestion_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_quarantine_records_organization_id"),
        "quarantine_records",
        ["organization_id"],
        unique=False,
    )
    op.create_table(
        "schema_profiles",
        sa.Column("raw_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("profile_version", sa.String(length=50), nullable=False),
        sa.Column("profile_json", sa.JSON(), nullable=False),
        sa.Column("baseline_profile_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["baseline_profile_id"],
            ["schema_profiles.id"],
            name=op.f("fk_schema_profiles_baseline_profile_id_schema_profiles"),
        ),
        sa.ForeignKeyConstraint(
            ["raw_snapshot_id"],
            ["raw_snapshots.id"],
            name=op.f("fk_schema_profiles_raw_snapshot_id_raw_snapshots"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_schema_profiles")),
    )
    op.create_index(
        op.f("ix_schema_profiles_raw_snapshot_id"),
        "schema_profiles",
        ["raw_snapshot_id"],
        unique=False,
    )
    op.create_table(
        "mapping_errors",
        sa.Column("mapping_execution_id", sa.Uuid(), nullable=False),
        sa.Column("source_record_key", sa.String(length=255), nullable=False),
        sa.Column("rule_sequence", sa.Integer(), nullable=False),
        sa.Column("target_field", sa.String(length=255), nullable=False),
        sa.Column("error_code", sa.String(length=100), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("evidence_masked", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["mapping_execution_id"],
            ["mapping_executions.id"],
            name=op.f("fk_mapping_errors_mapping_execution_id_mapping_executions"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mapping_errors")),
    )
    op.create_index(
        op.f("ix_mapping_errors_mapping_execution_id"),
        "mapping_errors",
        ["mapping_execution_id"],
        unique=False,
    )
    op.create_table(
        "profile_comparisons",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("baseline_profile_id", sa.Uuid(), nullable=False),
        sa.Column("current_profile_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("comparison_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["baseline_profile_id"],
            ["schema_profiles.id"],
            name=op.f("fk_profile_comparisons_baseline_profile_id_schema_profiles"),
        ),
        sa.ForeignKeyConstraint(
            ["current_profile_id"],
            ["schema_profiles.id"],
            name=op.f("fk_profile_comparisons_current_profile_id_schema_profiles"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_profile_comparisons_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_profile_comparisons")),
    )
    op.create_index(
        op.f("ix_profile_comparisons_baseline_profile_id"),
        "profile_comparisons",
        ["baseline_profile_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_profile_comparisons_current_profile_id"),
        "profile_comparisons",
        ["current_profile_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_profile_comparisons_organization_id"),
        "profile_comparisons",
        ["organization_id"],
        unique=False,
    )


def downgrade() -> None:
    # Earlier PostgreSQL downgrades may already have removed some tables.
    tables = [
        "profile_comparisons",
        "mapping_errors",
        "schema_profiles",
        "quarantine_records",
        "mapping_executions",
        "validation_results",
        "raw_snapshots",
        "participations",
        "match_decisions",
        "experience_events",
        "data_contracts",
        "assessment_results",
        "source_objects",
        "role_assignments",
        "probabilistic_runs",
        "match_candidates",
        "mapping_rules",
        "lineage_edges",
        "learning_offerings",
        "ingestion_runs",
        "external_identities",
        "export_snapshots",
        "credential_awards",
        "competency_alignments",
        "assessment_attempts",
        "validation_rules",
        "user_roles",
        "user_organizations",
        "source_systems",
        "role_permissions",
        "retention_policies",
        "probabilistic_models",
        "persons",
        "organization_units",
        "match_rule_sets",
        "match_evaluations",
        "mapping_sets",
        "lookup_tables",
        "lineage_nodes",
        "learning_programs",
        "export_definitions",
        "data_mart_snapshots",
        "credential_definitions",
        "competency_definitions",
        "canonical_entity_versions",
        "audit_events",
        "asset_runs",
        "assessment_definitions",
        "users",
        "roles",
        "permissions",
        "organizations",
    ]
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    for table in tables:
        if table in existing:
            op.drop_table(table)
