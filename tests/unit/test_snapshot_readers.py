import uuid
from pathlib import Path

import pytest
from eduwork_databridge.db.models.control import RawSnapshot
from eduwork_databridge.ingestion.readers import read_snapshot_records


@pytest.mark.parametrize(
    ("relative", "content_type", "expected"),
    [
        ("small/hris/employees.csv", "text/csv", 120),
        ("small/lms/participation.json", "application/json", 366),
        (
            "small/assessment/assessment_results.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            120,
        ),
        ("small/credential/credential_awards.parquet", "application/vnd.apache.parquet", 25),
    ],
)
def test_snapshot_reader_supports_committed_formats(
    relative: str, content_type: str, expected: int
) -> None:
    path = (Path("data/synthetic") / relative).resolve()
    snapshot = RawSnapshot(
        ingestion_run_id=uuid.uuid4(),
        source_object_id=uuid.uuid4(),
        storage_uri=path.as_uri(),
        checksum_sha256="0" * 64,
        row_count=expected,
        schema_fingerprint="synthetic",
        manifest_json={"content_type": content_type},
    )
    assert len(read_snapshot_records(snapshot)) == expected
