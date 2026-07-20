import csv
import hashlib
import json
import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq
from sqlalchemy import select
from sqlalchemy.orm import Session

from eduwork_databridge.connectors.base import ConnectorError
from eduwork_databridge.connectors.security import sanitize_spreadsheet_cell
from eduwork_databridge.db.models.control import (
    DataMartSnapshot,
    ExportDefinition,
    ExportSnapshot,
)
from eduwork_databridge.lineage import LineageService
from eduwork_databridge.schemas.config import ExportConfig


@dataclass(frozen=True)
class ExportOutcome:
    export_snapshot_id: uuid.UUID
    storage_uri: str
    checksum_sha256: str
    row_count: int
    dictionary_uri: str
    expires_at: str


class ExportService:
    def __init__(
        self,
        session: Session,
        root: Path = Path("var/exports"),
        lineage: LineageService | None = None,
    ) -> None:
        self.session = session
        self.root = root.expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.lineage = lineage or LineageService(session)

    @staticmethod
    def _masked(value: Any) -> str | None:
        if value in (None, ""):
            return None
        return "sha256:" + hashlib.sha256(str(value).encode()).hexdigest()[:16]

    @staticmethod
    def _checksum(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _definition(
        self,
        organization_id: uuid.UUID,
        config: ExportConfig,
        mart: DataMartSnapshot,
    ) -> ExportDefinition:
        definition = self.session.scalar(
            select(ExportDefinition).where(
                ExportDefinition.organization_id == organization_id,
                ExportDefinition.export_key == config.export_id,
                ExportDefinition.version == config.version,
            )
        )
        if definition is None:
            definition = ExportDefinition(
                organization_id=organization_id,
                export_key=config.export_id,
                version=config.version,
                format=config.format,
                contract_json={
                    "mart_id": str(mart.id),
                    "fields": config.fields,
                    "masked_fields": config.masked_fields,
                    "retention_days": config.retention_days,
                },
                active=True,
            )
            self.session.add(definition)
            self.session.flush()
        return definition

    def publish(
        self,
        organization_id: uuid.UUID,
        mart_snapshot_id: uuid.UUID,
        records: list[dict[str, Any]],
        config: ExportConfig,
        permissions: set[str],
    ) -> ExportOutcome:
        if "exports:write" not in permissions:
            raise ConnectorError("export_forbidden", "Export permission is required")
        mart = self.session.get(DataMartSnapshot, mart_snapshot_id)
        if mart is None or mart.organization_id != organization_id:
            raise ConnectorError("mart_not_found", "Mart snapshot was not found")
        missing = [field for field in config.fields if field not in mart.dictionary_json]
        if missing:
            raise ConnectorError("export_field_undocumented", "Export contains undocumented fields")
        selected = []
        for record in records:
            row: dict[str, Any] = {}
            for field in config.fields:
                value = record.get(field)
                if field in config.masked_fields:
                    value = self._masked(value)
                if isinstance(value, str):
                    value = sanitize_spreadsheet_cell(value)
                row[field] = value
            selected.append(row)
        directory = self.root / str(organization_id) / config.export_id
        directory.mkdir(parents=True, exist_ok=True)
        temporary = directory / f".{uuid.uuid4().hex}.tmp"
        if config.format == "csv":
            with temporary.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=config.fields)
                writer.writeheader()
                writer.writerows(selected)
        else:
            pq.write_table(pa.Table.from_pylist(selected), temporary, compression="zstd")
        digest = self._checksum(temporary)
        target = directory / f"{digest}.{config.format}"
        if target.exists():
            temporary.unlink()
        else:
            os.replace(temporary, target)
        dictionary_path = directory / f"{digest}.dictionary.json"
        dictionary_path.write_text(
            json.dumps(
                {
                    "export_id": config.export_id,
                    "version": config.version,
                    "fields": {field: mart.dictionary_json[field] for field in config.fields},
                    "masked_fields": config.masked_fields,
                    "source_mart_snapshot_id": str(mart.id),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        definition = self._definition(organization_id, config, mart)
        existing = self.session.scalar(
            select(ExportSnapshot).where(
                ExportSnapshot.organization_id == organization_id,
                ExportSnapshot.export_definition_id == definition.id,
                ExportSnapshot.checksum_sha256 == digest,
            )
        )
        if existing is None:
            existing = ExportSnapshot(
                organization_id=organization_id,
                export_definition_id=definition.id,
                storage_uri=target.as_uri(),
                checksum_sha256=digest,
                row_count=len(selected),
                published_at=datetime.now(UTC),
            )
            self.session.add(existing)
            self.session.flush()
            self.lineage.record_export(organization_id, mart.id, existing.id, config.fields)
        self.session.commit()
        expires_at = datetime.now(UTC) + timedelta(days=config.retention_days)
        return ExportOutcome(
            export_snapshot_id=existing.id,
            storage_uri=existing.storage_uri,
            checksum_sha256=existing.checksum_sha256,
            row_count=existing.row_count or 0,
            dictionary_uri=dictionary_path.as_uri(),
            expires_at=expires_at.isoformat(),
        )
