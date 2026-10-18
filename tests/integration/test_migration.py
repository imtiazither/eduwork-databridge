import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData, Table, create_engine, inspect, select


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
        "quarantine_resolutions",
    } <= tables
    ingestion_columns = {column["name"] for column in inspector.get_columns("ingestion_runs")}
    assert {"resume_from_run_id", "attempt_number", "failure_code", "failure_summary"} <= (
        ingestion_columns
    )
    snapshot_constraints = {
        constraint["name"] for constraint in inspector.get_unique_constraints("raw_snapshots")
    }
    assert "uq_snapshot_content" in snapshot_constraints
    assert "revision" in {column["name"] for column in inspector.get_columns("match_candidates")}
    assert "uq_match_decision_revision" in {
        constraint["name"] for constraint in inspector.get_unique_constraints("match_decisions")
    }
    quarantine_columns = {column["name"] for column in inspector.get_columns("quarantine_records")}
    assert {
        "revision",
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


@pytest.mark.integration
def test_exception_upgrade_preserves_latest_note_and_protects_new_history(tmp_path, monkeypatch):
    from eduwork_databridge.db.models.control import QuarantineRecord, QuarantineResolution
    from eduwork_databridge.schemas.config import ValidationConfig, ValidationRuleConfig
    from eduwork_databridge.validation import ValidationService
    from sqlalchemy import text
    from sqlalchemy.orm import Session

    from tests.factories import build_snapshot_session

    url = f"sqlite+pysqlite:///{tmp_path / 'control.db'}"
    monkeypatch.setenv("EDUWORK_DATABASE_URL", url)
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    session, org, snapshot = build_snapshot_session(tmp_path, [{"record_key": "R-1"}])
    outcome = ValidationService(session).validate(
        org,
        snapshot,
        [{"record_key": "R-1"}],
        ValidationConfig(
            validation_set_id="upgrade",
            entity="Person",
            rules=[
                ValidationRuleConfig(
                    rule_id="id",
                    title="Missing ID",
                    entity="Person",
                    severity="blocking",
                    rule_type="required",
                    fields=["employee_id"],
                    explanation="ID required.",
                )
            ],
        ),
    )
    issue_id = outcome.quarantine_ids[0]
    session.close()
    command.downgrade(config, "20261007_0005")
    engine = create_engine(url)
    reviewer = uuid.uuid4()
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE quarantine_records SET status='waived', resolution_note='Original note', "
                "reviewer_id=:reviewer WHERE id=:id"
            ),
            {"reviewer": reviewer.hex, "id": issue_id.hex},
        )
    command.upgrade(config, "head")
    with Session(engine) as upgraded:
        history = ValidationService(upgraded).resolution_history(org, issue_id)
        assert len(history) == 1 and history[0].imported
        assert history[0].note == "Original note" and history[0].reviewer_id == reviewer
        assert upgraded.get(QuarantineRecord, issue_id).revision == 1
        ValidationService(upgraded).resolve_quarantine(
            org, issue_id, "open", reviewer, "More evidence needed", expected_revision=1
        )
        assert len(upgraded.scalars(select(QuarantineResolution)).all()) == 2
    with pytest.raises(RuntimeError, match="discard resolution history"):
        command.downgrade(config, "20261007_0005")
    with Session(engine) as checked:
        assert len(checked.scalars(select(QuarantineResolution)).all()) == 2
    engine.dispose()


@pytest.mark.integration
def test_upgrade_preserves_existing_review_history(tmp_path, monkeypatch):
    url = f"sqlite+pysqlite:///{tmp_path / 'existing-reviews.db'}"
    monkeypatch.setenv("EDUWORK_DATABASE_URL", url)
    config = Config("alembic.ini")
    command.upgrade(config, "20260720_0004")
    engine = create_engine(url)
    metadata = MetaData()
    tables = {
        name: Table(name, metadata, autoload_with=engine)
        for name in [
            "organizations",
            "match_rule_sets",
            "match_candidates",
            "match_decisions",
        ]
    }
    assert "revision" not in tables["match_candidates"].c
    org, rule, candidate, reviewer = [uuid.uuid4().hex for _ in range(4)]
    first, second = uuid.UUID(int=1).hex, uuid.UUID(int=2).hex
    now = datetime.now(UTC)

    def values(id):
        return {"id": id, "created_at": now, "updated_at": now}

    with engine.begin() as connection:
        connection.execute(
            tables["organizations"]
            .insert()
            .values(
                **values(org),
                name="Upgrade fixture",
                organization_type="employer",
                status="active",
                metadata_json={},
            )
        )
        connection.execute(
            tables["match_rule_sets"]
            .insert()
            .values(
                **values(rule),
                organization_id=org,
                rule_set_key="test",
                version="1",
                entity_type="Person",
                deterministic_rules_json=[],
                probabilistic_config_json={},
                status="active",
            )
        )
        connection.execute(
            tables["match_candidates"]
            .insert()
            .values(
                **values(candidate),
                organization_id=org,
                rule_set_id=rule,
                left_record_key="HR-1",
                right_record_key="LMS-1",
                evidence_json={},
                status="defer",
            )
        )
        for id, prior in [(first, None), (second, first)]:
            connection.execute(
                tables["match_decisions"]
                .insert()
                .values(
                    **values(id),
                    organization_id=org,
                    candidate_id=candidate,
                    decision="defer",
                    reason="Original reason",
                    reviewer_id=reviewer,
                    decided_at=now,
                    supersedes_decision_id=prior,
                )
            )
    command.upgrade(config, "head")
    decisions = Table("match_decisions", MetaData(), autoload_with=engine)
    candidates = Table("match_candidates", MetaData(), autoload_with=engine)
    with engine.connect() as connection:
        rows = connection.execute(select(decisions).order_by(decisions.c.revision)).mappings().all()
        assert [row["revision"] for row in rows] == [1, 2]
        assert rows[1]["supersedes_decision_id"] == first
        assert all(row["reason"] == "Original reason" for row in rows)
        assert connection.scalar(select(candidates.c.revision)) == 2
    command.downgrade(config, "20260720_0004")
    assert "revision" not in {
        column["name"] for column in inspect(engine).get_columns("match_candidates")
    }
    with engine.connect() as connection:
        assert len(connection.execute(select(tables["match_decisions"])).all()) == 2
    engine.dispose()
