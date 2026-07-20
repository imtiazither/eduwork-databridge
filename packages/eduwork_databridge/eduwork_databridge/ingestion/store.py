import hashlib
import json
import os
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from eduwork_databridge.connectors.base import ExtractionBatch

CONTENT_EXTENSIONS = {
    "text/csv": ".csv",
    "application/json": ".json",
    "application/x-ndjson": ".ndjson",
    "application/vnd.apache.parquet": ".parquet",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
}


@dataclass(frozen=True)
class SnapshotManifest:
    source_id: str
    object_key: str
    connector_type: str
    connector_version: str
    contract_version: str
    extracted_at: str
    checksum_sha256: str
    row_count: int
    schema_fingerprint: str
    storage_uri: str
    content_type: str
    cursor: dict[str, Any]


@dataclass(frozen=True)
class StoredSnapshot:
    path: Path
    manifest_path: Path
    manifest: SnapshotManifest
    reused: bool


def checksum(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def schema_fingerprint(records: list[dict[str, Any]]) -> str:
    fields: dict[str, set[str]] = {}
    for record in records[:1000]:
        for name, value in record.items():
            fields.setdefault(name, set()).add(type(value).__name__)
    normalized = {name: sorted(types) for name, types in sorted(fields.items())}
    return hashlib.sha256(json.dumps(normalized, sort_keys=True).encode()).hexdigest()


class RawSnapshotStore:
    def __init__(self, root: Path) -> None:
        self.root = root.expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def store(
        self,
        batch: ExtractionBatch,
        source_id: str,
        object_key: str,
        connector_type: str,
        connector_version: str,
        contract_version: str,
        extracted_at: datetime,
    ) -> StoredSnapshot:
        digest = checksum(batch.raw_bytes)
        extension = CONTENT_EXTENSIONS.get(batch.content_type, ".bin")
        directory = self.root / source_id / object_key / digest[:2]
        directory.mkdir(parents=True, exist_ok=True)
        payload_path = directory / f"{digest}{extension}"
        manifest_path = directory / f"{digest}.manifest.json"
        reused = payload_path.exists()
        if not reused:
            temporary = directory / f".{digest}.{uuid.uuid4().hex}.tmp"
            with temporary.open("xb") as handle:
                handle.write(batch.raw_bytes)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, payload_path)
        manifest = SnapshotManifest(
            source_id=source_id,
            object_key=object_key,
            connector_type=connector_type,
            connector_version=connector_version,
            contract_version=contract_version,
            extracted_at=extracted_at.isoformat(),
            checksum_sha256=digest,
            row_count=len(batch.records),
            schema_fingerprint=schema_fingerprint(batch.records),
            storage_uri=payload_path.as_uri(),
            content_type=batch.content_type,
            cursor=batch.cursor,
        )
        if not manifest_path.exists():
            temporary_manifest = directory / f".{digest}.{uuid.uuid4().hex}.manifest.tmp"
            temporary_manifest.write_text(
                json.dumps(asdict(manifest), indent=2, sort_keys=True, default=str) + "\n",
                encoding="utf-8",
            )
            os.replace(temporary_manifest, manifest_path)
        return StoredSnapshot(
            path=payload_path,
            manifest_path=manifest_path,
            manifest=manifest,
            reused=reused,
        )
