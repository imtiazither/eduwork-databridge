from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import unquote, urlparse

import pytest
from eduwork_databridge.config_loader import load_yaml_model
from eduwork_databridge.connectors.base import ConnectorError
from eduwork_databridge.db.models.control import DataMartSnapshot, ExportSnapshot
from eduwork_databridge.lineage import LineageService
from eduwork_databridge.marts import MartService
from eduwork_databridge.publishing import ExportService, RetentionService
from eduwork_databridge.schemas.config import (
    ExportConfig,
    MartDefinitionConfig,
    RetentionPolicyConfig,
)
from sqlalchemy import select

from tests.factories import build_snapshot_session


def test_authorized_masked_export_lineage_and_retention(tmp_path: Path) -> None:
    session, organization_id, raw_snapshot_id = build_snapshot_session(tmp_path, [{"id": "seed"}])
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
    mart_config = load_yaml_model(
        Path("configs/demo/marts/training_participation_v1.yml"),
        MartDefinitionConfig,
    )
    mart = MartService(session, tmp_path / "marts").build(
        organization_id,
        records,
        mart_config,
        {"raw_snapshot_id": str(raw_snapshot_id)},
    )
    mart_row = session.get(DataMartSnapshot, mart.snapshot_id)
    assert mart_row is not None
    export_config = load_yaml_model(
        Path("configs/demo/exports/training_participation_csv_v1.yml"),
        ExportConfig,
    )
    lineage = LineageService(session, tmp_path / "lineage")
    exporter = ExportService(session, tmp_path / "exports", lineage)
    with pytest.raises(ConnectorError, match="permission"):
        exporter.publish(organization_id, mart.snapshot_id, mart.records, export_config, set())
    outcome = exporter.publish(
        organization_id,
        mart.snapshot_id,
        mart.records,
        export_config,
        {"exports:write"},
    )
    export_path = Path(unquote(urlparse(outcome.storage_uri).path))
    content = export_path.read_text(encoding="utf-8")
    assert "E-1" not in content
    assert "sha256:" in content
    assert Path(unquote(urlparse(outcome.dictionary_uri).path)).exists()

    retention_config = load_yaml_model(
        Path("configs/demo/retention/default_v1.yml"),
        RetentionPolicyConfig,
    )
    retention = RetentionService(session, tmp_path / "exports")
    policy = retention.upsert_policy(organization_id, retention_config)
    snapshot = session.get(ExportSnapshot, outcome.export_snapshot_id)
    assert snapshot is not None
    snapshot.published_at = datetime.now(UTC) - timedelta(days=60)
    session.commit()
    preview = retention.apply_export_retention(
        organization_id, policy, dry_run=True, as_of=datetime.now(UTC)
    )
    assert preview.candidate_ids == [snapshot.id]
    assert export_path.exists()
    applied = retention.apply_export_retention(
        organization_id, policy, dry_run=False, as_of=datetime.now(UTC)
    )
    assert applied.deleted_files
    assert not export_path.exists()
    assert (
        session.scalar(
            select(ExportSnapshot).where(ExportSnapshot.id == outcome.export_snapshot_id)
        )
        is None
    )
    session.close()
