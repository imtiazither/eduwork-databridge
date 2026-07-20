import hashlib
import json
from pathlib import Path

import pytest
from eduwork_databridge.db.models.control import ProfileComparison, RawSnapshot
from eduwork_databridge.profiling import DataProfiler, ProfilingService
from eduwork_databridge.schemas.config import ProfileConfig

from tests.factories import build_snapshot_session


def test_profiler_masks_top_values_and_computes_numeric_metrics() -> None:
    records = [
        {"department": "Finance", "score": 10},
        {"department": "Finance", "score": 20},
        {"department": None, "score": 30},
    ]
    result = DataProfiler().profile(records, ProfileConfig(profile_id="test"))
    department = result.profile["fields"]["department"]
    score = result.profile["fields"]["score"]
    assert department["null_rate"] == pytest.approx(1 / 3)
    assert department["top_values"][0]["fingerprint"] != "Finance"
    assert score["numeric"]["mean"] == 20
    assert len(result.schema_fingerprint) == 64


def test_drift_comparison_reports_schema_and_metric_changes() -> None:
    profiler = DataProfiler()
    config = ProfileConfig(profile_id="test")
    baseline = profiler.profile(
        [{"id": "1", "department": "A", "score": 10}, {"id": "2", "department": "A", "score": 20}],
        config,
    )
    current = profiler.profile(
        [{"id": "1", "score": 100, "new_field": "x"}, {"id": "2", "score": 120, "new_field": "x"}],
        config,
    )
    drift = profiler.compare(baseline.profile, current.profile, config)
    assert drift.status == "drift"
    assert drift.comparison["removed_fields"] == ["department"]
    assert drift.comparison["added_fields"] == ["new_field"]
    assert any(item["field"] == "score" for item in drift.comparison["threshold_breaches"])


def test_profiling_service_persists_baseline_comparison(tmp_path: Path) -> None:
    baseline_records = [{"id": "1", "score": 10}, {"id": "2", "score": 20}]
    session, organization_id, baseline_snapshot_id = build_snapshot_session(
        tmp_path, baseline_records
    )
    config = ProfileConfig(profile_id="default")
    service = ProfilingService(session)
    baseline = service.create_profile(
        organization_id, baseline_snapshot_id, baseline_records, config
    )

    first_snapshot = session.get(RawSnapshot, baseline_snapshot_id)
    assert first_snapshot is not None
    current_records = [{"id": "1", "score": 100}, {"id": "2", "score": None}]
    raw = (json.dumps(current_records, sort_keys=True) + "\n").encode()
    current_path = tmp_path / "current.json"
    current_path.write_bytes(raw)
    current_snapshot = RawSnapshot(
        ingestion_run_id=first_snapshot.ingestion_run_id,
        source_object_id=first_snapshot.source_object_id,
        storage_uri=current_path.resolve().as_uri(),
        checksum_sha256=hashlib.sha256(raw).hexdigest(),
        row_count=2,
        schema_fingerprint="current",
        manifest_json={"content_type": "application/json"},
    )
    session.add(current_snapshot)
    session.commit()
    current = service.create_profile(
        organization_id,
        current_snapshot.id,
        current_records,
        config,
        baseline_profile_id=baseline.profile_id,
    )
    assert current.comparison_id is not None
    assert current.drift_status == "drift"
    assert session.get(ProfileComparison, current.comparison_id) is not None
    session.close()
