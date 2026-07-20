from datetime import UTC, datetime
from pathlib import Path

from eduwork_databridge.connectors.base import ExtractionBatch
from eduwork_databridge.ingestion.store import RawSnapshotStore


def test_snapshot_store_is_content_addressed_and_immutable(tmp_path: Path) -> None:
    store = RawSnapshotStore(tmp_path)
    batch = ExtractionBatch(
        records=[{"id": "1", "status": "assigned"}],
        raw_bytes=b'[{"id":"1","status":"assigned"}]\n',
        content_type="application/json",
        cursor={"offset": 1},
    )
    first = store.store(
        batch,
        source_id="demo",
        object_key="items",
        connector_type="json",
        connector_version="0.4.0",
        contract_version="1.0",
        extracted_at=datetime(2026, 7, 19, tzinfo=UTC),
    )
    second = store.store(
        batch,
        source_id="demo",
        object_key="items",
        connector_type="json",
        connector_version="0.4.0",
        contract_version="1.0",
        extracted_at=datetime(2026, 7, 20, tzinfo=UTC),
    )
    assert first.path == second.path
    assert first.reused is False
    assert second.reused is True
    assert first.path.read_bytes() == batch.raw_bytes
    assert first.manifest.checksum_sha256 in first.path.name
