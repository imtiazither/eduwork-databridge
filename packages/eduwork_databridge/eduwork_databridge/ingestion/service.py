import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from eduwork_databridge.config_loader import load_yaml_model, source_config_path
from eduwork_databridge.connectors import ConnectorError, build_connector
from eduwork_databridge.db.models.control import (
    IngestionRun,
    RawSnapshot,
    SourceObject,
    SourceSystem,
)
from eduwork_databridge.ingestion.store import RawSnapshotStore
from eduwork_databridge.schemas.config import SourceConfig, SourceObjectConfig
from eduwork_databridge.settings import Settings

logger = structlog.get_logger()


@dataclass(frozen=True)
class IngestionOutcome:
    run_id: uuid.UUID
    snapshot_id: uuid.UUID
    checksum_sha256: str
    storage_uri: str
    row_count: int
    reused_snapshot: bool
    cursor: dict[str, Any]


class IngestionService:
    def __init__(
        self,
        session: Session,
        settings: Settings,
        config_root: Path = Path("configs/demo"),
    ) -> None:
        self.session = session
        self.settings = settings
        self.config_root = config_root
        self.store = RawSnapshotStore(settings.raw_store_root)

    def _configuration(self, source_id: str) -> SourceConfig:
        return load_yaml_model(source_config_path(self.config_root, source_id), SourceConfig)

    def _metadata(
        self,
        organization_id: uuid.UUID,
        source_id: str,
        object_key: str,
    ) -> tuple[SourceSystem, SourceObject]:
        source = self.session.scalar(
            select(SourceSystem).where(
                SourceSystem.organization_id == organization_id,
                SourceSystem.source_key == source_id,
                SourceSystem.active.is_(True),
            )
        )
        if source is None:
            raise ConnectorError("source_not_registered", "Source metadata is not registered")
        source_object = self.session.scalar(
            select(SourceObject).where(
                SourceObject.source_system_id == source.id,
                SourceObject.object_key == object_key,
            )
        )
        if source_object is None:
            raise ConnectorError("source_object_not_registered", "Source object is not registered")
        return source, source_object

    @staticmethod
    def _object(config: SourceConfig, object_key: str) -> SourceObjectConfig:
        for source_object in config.objects:
            if source_object.key == object_key:
                return source_object
        raise ConnectorError("object_not_configured", "Source object is not configured")

    def _resume_cursor(
        self,
        resume_from_run_id: uuid.UUID | None,
        organization_id: uuid.UUID,
        source_system_id: uuid.UUID,
    ) -> tuple[dict[str, Any], int]:
        if resume_from_run_id is None:
            return {}, 1
        previous = self.session.get(IngestionRun, resume_from_run_id)
        if (
            previous is None
            or previous.organization_id != organization_id
            or previous.source_system_id != source_system_id
        ):
            raise ConnectorError("invalid_resume_run", "Resume run is not valid for this source")
        return previous.cursor_json, previous.attempt_number + 1

    async def extract(
        self,
        organization_id: uuid.UUID,
        source_id: str,
        object_key: str,
        resume_from_run_id: uuid.UUID | None = None,
    ) -> IngestionOutcome:
        config = self._configuration(source_id)
        source_config_object = self._object(config, object_key)
        source, source_object = self._metadata(organization_id, source_id, object_key)
        cursor, attempt = self._resume_cursor(resume_from_run_id, organization_id, source.id)
        run = IngestionRun(
            organization_id=organization_id,
            source_system_id=source.id,
            status="running",
            started_at=datetime.now(UTC),
            cursor_json=cursor,
            correlation_id=str(uuid.uuid4()),
            resume_from_run_id=resume_from_run_id,
            attempt_number=attempt,
        )
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        connector = build_connector(config, self.settings)
        try:
            batch = await connector.extract(source_config_object, cursor or None)
            stored = self.store.store(
                batch=batch,
                source_id=source_id,
                object_key=object_key,
                connector_type=connector.connector_type,
                connector_version=connector.connector_version,
                contract_version=source_config_object.contract_version,
                extracted_at=datetime.now(UTC),
            )
            snapshot = self.session.scalar(
                select(RawSnapshot).where(
                    RawSnapshot.source_object_id == source_object.id,
                    RawSnapshot.checksum_sha256 == stored.manifest.checksum_sha256,
                )
            )
            reused_snapshot = snapshot is not None
            if snapshot is None:
                snapshot = RawSnapshot(
                    ingestion_run_id=run.id,
                    source_object_id=source_object.id,
                    storage_uri=stored.manifest.storage_uri,
                    checksum_sha256=stored.manifest.checksum_sha256,
                    row_count=stored.manifest.row_count,
                    schema_fingerprint=stored.manifest.schema_fingerprint,
                    manifest_json={
                        "source_id": stored.manifest.source_id,
                        "object_key": stored.manifest.object_key,
                        "connector_type": stored.manifest.connector_type,
                        "connector_version": stored.manifest.connector_version,
                        "contract_version": stored.manifest.contract_version,
                        "extracted_at": stored.manifest.extracted_at,
                        "content_type": stored.manifest.content_type,
                        "cursor": stored.manifest.cursor,
                    },
                )
                self.session.add(snapshot)
                self.session.flush()
            run.status = "succeeded"
            run.ended_at = datetime.now(UTC)
            run.cursor_json = batch.cursor
            run.failure_code = None
            run.failure_summary = None
            self.session.commit()
            self.session.refresh(snapshot)
            logger.info(
                "ingestion_succeeded",
                source_id=source_id,
                object_key=object_key,
                run_id=str(run.id),
                snapshot_id=str(snapshot.id),
                reused_snapshot=reused_snapshot,
                row_count=snapshot.row_count or 0,
            )
            return IngestionOutcome(
                run_id=run.id,
                snapshot_id=snapshot.id,
                checksum_sha256=snapshot.checksum_sha256,
                storage_uri=snapshot.storage_uri,
                row_count=snapshot.row_count or 0,
                reused_snapshot=reused_snapshot,
                cursor=batch.cursor,
            )
        except ConnectorError as exc:
            run.status = "failed"
            run.ended_at = datetime.now(UTC)
            run.failure_code = exc.code
            run.failure_summary = exc.safe_message
            self.session.commit()
            logger.warning(
                "ingestion_failed",
                source_id=source_id,
                object_key=object_key,
                run_id=str(run.id),
                failure_code=exc.code,
            )
            raise
        except Exception as exc:
            run.status = "failed"
            run.ended_at = datetime.now(UTC)
            run.failure_code = "unexpected_connector_failure"
            run.failure_summary = "Unexpected connector failure"
            self.session.commit()
            logger.error(
                "ingestion_failed",
                source_id=source_id,
                object_key=object_key,
                run_id=str(run.id),
                failure_code="unexpected_connector_failure",
            )
            raise ConnectorError(
                "unexpected_connector_failure", "Unexpected connector failure"
            ) from exc
        finally:
            await connector.close()
