import json
import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from eduwork_databridge.connectors.base import ConnectorError
from eduwork_databridge.db.models.control import (
    MappingError,
    MappingExecution,
    RawSnapshot,
    SourceObject,
    SourceSystem,
)
from eduwork_databridge.mapping.engine import MappingEngine, MappingIssue, Plugin
from eduwork_databridge.schemas.config import MappingConfig


@dataclass(frozen=True)
class MappingOutcome:
    execution_id: uuid.UUID
    status: str
    input_count: int
    output_count: int
    error_count: int
    output_uri: str | None
    outputs: list[dict[str, Any]]
    issues: list[MappingIssue]


class MappingService:
    def __init__(
        self,
        session: Session,
        output_root: Path = Path("var/mapped"),
        plugins: dict[str, Plugin] | None = None,
    ) -> None:
        self.session = session
        self.output_root = output_root.expanduser().resolve()
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.engine = MappingEngine(plugins)

    def _verify_snapshot(self, organization_id: uuid.UUID, snapshot_id: uuid.UUID) -> None:
        snapshot = self.session.get(RawSnapshot, snapshot_id)
        source_object = (
            self.session.get(SourceObject, snapshot.source_object_id) if snapshot else None
        )
        source = (
            self.session.get(SourceSystem, source_object.source_system_id)
            if source_object
            else None
        )
        if snapshot is None or source is None or source.organization_id != organization_id:
            raise ConnectorError(
                "snapshot_scope_mismatch", "Raw snapshot is outside organization scope"
            )

    def execute(
        self,
        organization_id: uuid.UUID,
        snapshot_id: uuid.UUID,
        records: list[dict[str, Any]],
        config: MappingConfig,
        lookups: dict[str, dict[str, Any]],
        context: dict[str, Any] | None = None,
        dry_run: bool = False,
        preview_limit: int | None = None,
    ) -> MappingOutcome:
        self._verify_snapshot(organization_id, snapshot_id)
        started = datetime.now(UTC)
        execution = MappingExecution(
            organization_id=organization_id,
            raw_snapshot_id=snapshot_id,
            mapping_key=config.mapping_id,
            mapping_version=config.schema_version,
            status="running",
            dry_run=dry_run,
            started_at=started,
        )
        self.session.add(execution)
        self.session.flush()
        result = self.engine.execute(
            records=records,
            config=config,
            lookups=lookups,
            context=context,
            limit=preview_limit if dry_run else None,
        )
        for issue in result.issues:
            self.session.add(
                MappingError(
                    mapping_execution_id=execution.id,
                    source_record_key=issue.source_record_key,
                    rule_sequence=issue.rule_sequence,
                    target_field=issue.target_field,
                    error_code=issue.error_code,
                    explanation=issue.explanation,
                    evidence_masked=issue.evidence_masked,
                )
            )
        output_uri: str | None = None
        if dry_run:
            status = "previewed"
        else:
            status = (
                "succeeded"
                if not result.issues
                else ("partially_succeeded" if result.outputs else "failed")
            )
            output_path = self.output_root / f"{execution.id}.json"
            temporary = self.output_root / f".{execution.id}.{uuid.uuid4().hex}.tmp"
            temporary.write_text(
                json.dumps(result.outputs, indent=2, sort_keys=True, default=str) + "\n",
                encoding="utf-8",
            )
            os.replace(temporary, output_path)
            output_uri = output_path.as_uri()
        execution.status = status
        execution.input_count = result.input_count
        execution.output_count = len(result.outputs)
        execution.error_count = len(result.issues)
        execution.output_uri = output_uri
        execution.ended_at = datetime.now(UTC)
        self.session.commit()
        return MappingOutcome(
            execution_id=execution.id,
            status=status,
            input_count=result.input_count,
            output_count=len(result.outputs),
            error_count=len(result.issues),
            output_uri=output_uri,
            outputs=result.outputs,
            issues=result.issues,
        )
