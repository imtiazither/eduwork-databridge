from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


@pytest.mark.integration
def test_baseline_upgrade_and_downgrade(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "migration.db"
    url = f"sqlite+pysqlite:///{db_path}"
    monkeypatch.setenv("EDUWORK_DATABASE_URL", url)
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    engine = create_engine(url)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert {
        "organizations",
        "persons",
        "source_systems",
        "data_contracts",
        "audit_events",
        "profile_comparisons",
        "lookup_tables",
        "mapping_executions",
        "mapping_errors",
        "match_evaluations",
        "probabilistic_models",
        "probabilistic_runs",
        "data_mart_snapshots",
        "asset_runs",
        "retention_policies",
    } <= tables
    ingestion_columns = {column["name"] for column in inspector.get_columns("ingestion_runs")}
    assert {"resume_from_run_id", "attempt_number", "failure_code", "failure_summary"} <= (
        ingestion_columns
    )
    snapshot_constraints = {
        constraint["name"] for constraint in inspector.get_unique_constraints("raw_snapshots")
    }
    assert "uq_snapshot_content" in snapshot_constraints
    quarantine_columns = {column["name"] for column in inspector.get_columns("quarantine_records")}
    assert {
        "waiver_reason",
        "resolution_note",
        "resolved_at",
        "supersedes_quarantine_id",
        "corrected_snapshot_id",
    } <= quarantine_columns
    engine.dispose()
    command.downgrade(config, "base")
    downgraded_engine = create_engine(url)
    remaining = set(inspect(downgraded_engine).get_table_names())
    downgraded_engine.dispose()
    assert remaining <= {"alembic_version"}
