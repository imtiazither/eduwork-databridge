from datetime import UTC, datetime
from pathlib import Path

from eduwork_databridge.config_loader import load_yaml_model
from eduwork_databridge.db.models.control import DataMartSnapshot
from eduwork_databridge.marts import MartBuilder, MartService, read_mart_records
from eduwork_databridge.schemas.config import MartDefinitionConfig

from tests.factories import build_snapshot_session


def load(name: str) -> MartDefinitionConfig:
    return load_yaml_model(Path(f"configs/demo/marts/{name}.yml"), MartDefinitionConfig)


def test_training_credential_and_quality_marts() -> None:
    builder = MartBuilder()
    training = builder.build(
        [
            {
                "source_record_key": "A-1",
                "person_external_id": "E-1",
                "offering_external_id": "C-1",
                "status": "completed",
                "assigned_at": "2026-01-01T00:00:00+00:00",
                "completed_at": "2026-01-05T00:00:00+00:00",
                "progress_percent": 100,
                "updated_at": "2026-01-05T00:00:00+00:00",
            }
        ],
        load("training_participation_v1"),
    )
    assert training[0]["is_completed"] is True
    assert training[0]["has_progress"] is True

    credential = builder.build(
        [
            {
                "assessment_person_id": "P-1",
                "credential_code": "CERT-1",
                "awarded_at": "2025-01-01T00:00:00+00:00",
                "expires_at": "2025-12-31T00:00:00+00:00",
                "status": "active",
            }
        ],
        load("credential_status_v1"),
        as_of=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert credential[0]["current_status"] == "expired"

    quality = builder.build(
        [{"run_id": "R-1", "dimension": "validity", "evaluated": 100, "failed": 5}],
        load("quality_trend_v1"),
    )
    assert quality[0]["pass_rate"] == 0.95


def test_mart_service_persists_reproducible_parquet(tmp_path: Path) -> None:
    session, organization_id, snapshot_id = build_snapshot_session(tmp_path, [{"id": "seed"}])
    records = [
        {
            "source_record_key": "A-1",
            "person_external_id": "E-1",
            "offering_external_id": "C-1",
            "status": "completed",
            "assigned_at": "2026-01-01T00:00:00+00:00",
            "completed_at": "2026-01-05T00:00:00+00:00",
            "progress_percent": 100,
            "updated_at": "2026-01-05T00:00:00+00:00",
        }
    ]
    service = MartService(session, tmp_path / "marts")
    first = service.build(
        organization_id,
        records,
        load("training_participation_v1"),
        {"input_snapshot_id": str(snapshot_id)},
    )
    second = service.build(
        organization_id,
        records,
        load("training_participation_v1"),
        {"input_snapshot_id": str(snapshot_id)},
    )
    assert first.snapshot_id == second.snapshot_id
    assert second.reused is True
    snapshot = session.get(DataMartSnapshot, first.snapshot_id)
    assert snapshot is not None
    assert read_mart_records(snapshot)[0]["is_completed"] is True
    session.close()
