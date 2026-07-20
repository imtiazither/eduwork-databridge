import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from eduwork_databridge.connectors.base import ConnectorError
from eduwork_databridge.db.models.control import (
    IngestionRun,
    QuarantineRecord,
    RawSnapshot,
    SourceObject,
    SourceSystem,
    ValidationResult,
    ValidationRule,
)
from eduwork_databridge.schemas.config import ValidationConfig, ValidationRuleConfig
from eduwork_databridge.validation.engine import ValidationEngine, ValidationRunResult


@dataclass(frozen=True)
class ValidationOutcome:
    result: ValidationRunResult
    persisted_result_ids: list[uuid.UUID]
    quarantine_ids: list[uuid.UUID]


class ValidationService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.engine = ValidationEngine()

    def _snapshot_context(
        self, organization_id: uuid.UUID, snapshot_id: uuid.UUID
    ) -> tuple[RawSnapshot, IngestionRun]:
        snapshot = self.session.get(RawSnapshot, snapshot_id)
        source_object = (
            self.session.get(SourceObject, snapshot.source_object_id) if snapshot else None
        )
        source = (
            self.session.get(SourceSystem, source_object.source_system_id)
            if source_object
            else None
        )
        run = self.session.get(IngestionRun, snapshot.ingestion_run_id) if snapshot else None
        if (
            snapshot is None
            or source is None
            or run is None
            or source.organization_id != organization_id
        ):
            raise ConnectorError(
                "snapshot_scope_mismatch", "Raw snapshot is outside organization scope"
            )
        return snapshot, run

    def _rule_model(
        self, organization_id: uuid.UUID, config_rule: ValidationRuleConfig
    ) -> ValidationRule:
        rule = self.session.scalar(
            select(ValidationRule).where(
                ValidationRule.organization_id == organization_id,
                ValidationRule.rule_key == config_rule.rule_id,
                ValidationRule.version == "1.0",
            )
        )
        if rule is None:
            rule = ValidationRule(
                organization_id=organization_id,
                rule_key=config_rule.rule_id,
                version="1.0",
                title=config_rule.title,
                entity_name=config_rule.entity,
                severity=config_rule.severity,
                expression_type=config_rule.rule_type,
                expression_json=config_rule.parameters,
                explanation=config_rule.explanation,
                remediation=config_rule.remediation,
                active=True,
            )
            self.session.add(rule)
            self.session.flush()
        return rule

    def validate(
        self,
        organization_id: uuid.UUID,
        snapshot_id: uuid.UUID,
        records: list[dict[str, Any]],
        config: ValidationConfig,
        reference_sets: dict[str, set[str]] | None = None,
    ) -> ValidationOutcome:
        snapshot, run = self._snapshot_context(organization_id, snapshot_id)
        result = self.engine.validate(records, config, reference_sets)
        persisted_result_ids: list[uuid.UUID] = []
        quarantine_ids: list[uuid.UUID] = []
        rules = {rule.rule_id: self._rule_model(organization_id, rule) for rule in config.rules}
        summaries = {summary.rule_id: summary for summary in result.summaries}
        for rule_id, rule_model in rules.items():
            summary = summaries[rule_id]
            persisted = ValidationResult(
                organization_id=organization_id,
                ingestion_run_id=run.id,
                validation_rule_id=rule_model.id,
                passed=summary.passed,
                evaluated_count=summary.evaluated_count,
                failed_count=summary.failed_count,
                result_json={
                    "category": summary.category,
                    "validation_set_id": config.validation_set_id,
                    "blocking_failures": sum(
                        issue.rule_id == rule_id and issue.severity == "blocking"
                        for issue in result.issues
                    ),
                },
            )
            self.session.add(persisted)
            self.session.flush()
            persisted_result_ids.append(persisted.id)
        for issue in result.issues:
            rule_model = rules[issue.rule_id]
            field_name = ",".join(issue.fields) if issue.fields else None
            quarantine = QuarantineRecord(
                organization_id=organization_id,
                ingestion_run_id=run.id,
                validation_rule_id=rule_model.id,
                raw_snapshot_id=snapshot.id,
                source_record_key=issue.source_record_key,
                field_name=field_name,
                evidence_masked=issue.evidence_masked,
                explanation=issue.explanation,
                status="open",
            )
            self.session.add(quarantine)
            self.session.flush()
            quarantine_ids.append(quarantine.id)
        self.session.commit()
        return ValidationOutcome(
            result=result,
            persisted_result_ids=persisted_result_ids,
            quarantine_ids=quarantine_ids,
        )

    def resolve_quarantine(
        self,
        organization_id: uuid.UUID,
        quarantine_id: uuid.UUID,
        status: str,
        reviewer_id: uuid.UUID,
        note: str,
        corrected_snapshot_id: uuid.UUID | None = None,
    ) -> QuarantineRecord:
        allowed = {"acknowledged", "corrected_upstream", "corrected_mapping", "waived", "closed"}
        if status not in allowed:
            raise ConnectorError("invalid_quarantine_status", "Quarantine status is invalid")
        record = self.session.get(QuarantineRecord, quarantine_id)
        if record is None or record.organization_id != organization_id:
            raise ConnectorError("quarantine_not_found", "Quarantine record was not found")
        if not note.strip():
            raise ConnectorError("resolution_note_required", "Resolution note is required")
        if corrected_snapshot_id:
            self._snapshot_context(organization_id, corrected_snapshot_id)
        record.status = status
        record.reviewer_id = reviewer_id
        record.resolution_note = note.strip()
        record.waiver_reason = note.strip() if status == "waived" else None
        record.corrected_snapshot_id = corrected_snapshot_id
        record.resolved_at = datetime.now(UTC)
        self.session.commit()
        return record

    def reprocess_link(
        self,
        organization_id: uuid.UUID,
        prior_quarantine_id: uuid.UUID,
        new_quarantine_id: uuid.UUID,
    ) -> QuarantineRecord:
        prior = self.session.get(QuarantineRecord, prior_quarantine_id)
        current = self.session.get(QuarantineRecord, new_quarantine_id)
        if (
            prior is None
            or current is None
            or prior.organization_id != organization_id
            or current.organization_id != organization_id
        ):
            raise ConnectorError("quarantine_not_found", "Quarantine record was not found")
        current.supersedes_quarantine_id = prior.id
        self.session.commit()
        return current
