import hashlib
import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from urllib.parse import unquote, urlparse

import pyarrow as pa
import pyarrow.parquet as pq
from sqlalchemy import select
from sqlalchemy.orm import Session

from eduwork_databridge.db.models.control import DataMartSnapshot
from eduwork_databridge.marts.builder import MartBuilder
from eduwork_databridge.schemas.config import MartDefinitionConfig


@dataclass(frozen=True)
class MartOutcome:
    snapshot_id: uuid.UUID
    storage_uri: str
    checksum_sha256: str
    row_count: int
    reused: bool
    records: list[dict[str, Any]]


class MartService:
    def __init__(self, session: Session, root: Path = Path("var/marts")) -> None:
        self.session = session
        self.root = root.expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.builder = MartBuilder()

    @staticmethod
    def _checksum(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def build(
        self,
        organization_id: uuid.UUID,
        records: list[dict[str, Any]],
        config: MartDefinitionConfig,
        lineage: dict[str, Any],
        as_of: datetime | None = None,
    ) -> MartOutcome:
        output = self.builder.build(records, config, as_of)
        directory = self.root / str(organization_id) / config.mart_id
        directory.mkdir(parents=True, exist_ok=True)
        temporary = directory / f".{uuid.uuid4().hex}.tmp.parquet"
        pq.write_table(pa.Table.from_pylist(output), temporary, compression="zstd")
        digest = self._checksum(temporary)
        target = directory / f"{digest}.parquet"
        reused_file = target.exists()
        if reused_file:
            temporary.unlink()
        else:
            os.replace(temporary, target)
        existing = self.session.scalar(
            select(DataMartSnapshot).where(
                DataMartSnapshot.organization_id == organization_id,
                DataMartSnapshot.mart_key == config.mart_id,
                DataMartSnapshot.version == config.version,
                DataMartSnapshot.checksum_sha256 == digest,
            )
        )
        reused = existing is not None
        if existing is None:
            existing = DataMartSnapshot(
                organization_id=organization_id,
                mart_key=config.mart_id,
                version=config.version,
                storage_uri=target.as_uri(),
                checksum_sha256=digest,
                row_count=len(output),
                dictionary_json={
                    field: config.definitions.get(field, "Undocumented field")
                    for field in [*config.fields, *self._derived_fields(config.entity)]
                },
                lineage_json=lineage,
                published_at=datetime.now(UTC),
            )
            self.session.add(existing)
            self.session.commit()
        return MartOutcome(
            snapshot_id=existing.id,
            storage_uri=existing.storage_uri,
            checksum_sha256=existing.checksum_sha256,
            row_count=existing.row_count,
            reused=reused or reused_file,
            records=output,
        )

    @staticmethod
    def _derived_fields(entity: str) -> list[str]:
        if entity == "training_participation":
            return ["is_completed", "has_progress"]
        if entity == "credential_status":
            return ["current_status"]
        if entity == "quality_trend":
            return ["pass_rate"]
        return []


def read_mart_records(snapshot: DataMartSnapshot) -> list[dict[str, Any]]:
    parsed = urlparse(snapshot.storage_uri)
    if parsed.scheme != "file":
        raise ValueError("Mart snapshot URI is not a local file")
    path = Path(unquote(parsed.path)).resolve(strict=True)
    return cast(list[dict[str, Any]], pq.read_table(path).to_pylist())
