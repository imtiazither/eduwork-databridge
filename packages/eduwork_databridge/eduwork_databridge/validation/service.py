import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from eduwork_databridge.connectors.base import ConnectorError
from eduwork_databridge.db.models.control import (
    IngestionRun,
    QuarantineRecord,
    QuarantineResolution,
    RawSnapshot,
    SourceObject,
    SourceSystem,
    ValidationResult,
    ValidationRule,
)
from eduwork_databridge.schemas.config import ValidationConfig, ValidationRuleConfig
from eduwork_databridge.validation.engine import ValidationEngine, ValidationRunResult

ATTENTION_STATUSES = ("open", "acknowledged")


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
        *,
        expected_revision: int,
        commit: bool = True,
    ) -> QuarantineRecord:
        allowed = {
            "open",
            "acknowledged",
            "corrected_upstream",
            "corrected_mapping",
            "waived",
            "closed",
        }
        if status not in allowed:
            raise ConnectorError("invalid_quarantine_status", "Quarantine status is invalid")
        record = self.get_quarantine(organization_id, quarantine_id)
        if not note.strip():
            raise ConnectorError("resolution_note_required", "Resolution note is required")
        if corrected_snapshot_id:
            corrected, _ = self._snapshot_context(organization_id, corrected_snapshot_id)
            original = self.session.get(RawSnapshot, record.raw_snapshot_id)
            if original is None or corrected.source_object_id != original.source_object_id:
                raise ConnectorError(
                    "corrected_snapshot_mismatch",
                    "Corrected snapshot must describe the same source object",
                )
        now = datetime.now(UTC)
        changed = self.session.scalar(
            update(QuarantineRecord)
            .where(
                QuarantineRecord.id == quarantine_id,
                QuarantineRecord.organization_id == organization_id,
                QuarantineRecord.revision == expected_revision,
            )
            .values(
                status=status,
                reviewer_id=reviewer_id,
                resolution_note=note.strip(),
                waiver_reason=note.strip() if status == "waived" else None,
                corrected_snapshot_id=corrected_snapshot_id,
                resolved_at=None if status in ATTENTION_STATUSES else now,
                revision=expected_revision + 1,
            )
            .returning(QuarantineRecord.id)
            .execution_options(synchronize_session=False)
        )
        if changed is None:
            self.session.rollback()
            raise ConnectorError(
                "quarantine_conflict", "Exception changed. Refresh before recording a resolution."
            )
        self.session.add(
            QuarantineResolution(
                organization_id=organization_id,
                quarantine_id=quarantine_id,
                revision=expected_revision + 1,
                status=status,
                reviewer_id=reviewer_id,
                note=note.strip(),
                recorded_at=now,
                corrected_snapshot_id=corrected_snapshot_id,
                imported=False,
            )
        )
        self.session.expire(record)
        if commit:
            self.session.commit()
        else:
            self.session.flush()
        return record

    def get_quarantine(
        self, organization_id: uuid.UUID, quarantine_id: uuid.UUID
    ) -> QuarantineRecord:
        record = self.session.get(QuarantineRecord, quarantine_id)
        if record is None or record.organization_id != organization_id:
            raise ConnectorError("quarantine_not_found", "Exception was not found")
        return record

    def review_queue(
        self,
        organization_id: uuid.UUID,
        *,
        status: str | None = None,
        severity: str | None = None,
        needs_attention: bool = False,
        q: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[tuple[QuarantineRecord, ValidationRule]]:
        query = (
            select(QuarantineRecord, ValidationRule)
            .join(ValidationRule, QuarantineRecord.validation_rule_id == ValidationRule.id)
            .where(
                QuarantineRecord.organization_id == organization_id,
                ValidationRule.organization_id == organization_id,
            )
        )
        if status is not None:
            query = query.where(QuarantineRecord.status == status)
        if severity is not None:
            query = query.where(ValidationRule.severity == severity)
        if needs_attention:
            query = query.where(QuarantineRecord.status.in_(ATTENTION_STATUSES))
        if q and q.strip():
            query = query.where(
                or_(
                    QuarantineRecord.source_record_key.icontains(q.strip(), autoescape=True),
                    ValidationRule.title.icontains(q.strip(), autoescape=True),
                    ValidationRule.rule_key.icontains(q.strip(), autoescape=True),
                )
            )
        query = (
            query.order_by(QuarantineRecord.created_at, QuarantineRecord.id)
            .limit(limit)
            .offset(offset)
        )
        return [(record, rule) for record, rule in self.session.execute(query)]

    def queue_summary(self, organization_id: uuid.UUID) -> dict[str, Any]:
        by_status = {
            status: count
            for status, count in self.session.execute(
                select(QuarantineRecord.status, func.count())
                .where(QuarantineRecord.organization_id == organization_id)
                .group_by(QuarantineRecord.status)
            ).all()
        }
        by_severity = {
            severity: count
            for severity, count in self.session.execute(
                select(ValidationRule.severity, func.count())
                .join(QuarantineRecord, QuarantineRecord.validation_rule_id == ValidationRule.id)
                .where(
                    QuarantineRecord.organization_id == organization_id,
                    ValidationRule.organization_id == organization_id,
                )
                .group_by(ValidationRule.severity)
            ).all()
        }
        return {
            "total": sum(by_status.values()),
            "needs_attention": sum(by_status.get(status, 0) for status in ATTENTION_STATUSES),
            "by_status": by_status,
            "by_severity": by_severity,
        }

    def resolution_history(
        self,
        organization_id: uuid.UUID,
        quarantine_id: uuid.UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[QuarantineResolution]:
        self.get_quarantine(organization_id, quarantine_id)
        return list(
            self.session.scalars(
                select(QuarantineResolution)
                .where(
                    QuarantineResolution.organization_id == organization_id,
                    QuarantineResolution.quarantine_id == quarantine_id,
                )
                .order_by(QuarantineResolution.revision.desc())
                .limit(limit)
                .offset(offset)
            )
        )

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
