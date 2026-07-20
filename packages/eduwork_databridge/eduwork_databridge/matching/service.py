import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from eduwork_databridge.connectors.base import ConnectorError
from eduwork_databridge.db.models.control import (
    MatchCandidate,
    MatchDecision,
    MatchEvaluation,
    MatchRuleSet,
)
from eduwork_databridge.matching.deterministic import (
    DeterministicMatcher,
    DeterministicMatchResult,
    MatchMetrics,
    evaluate_matches,
)
from eduwork_databridge.schemas.config import DeterministicMatchConfig


@dataclass(frozen=True)
class MatchOutcome:
    result: DeterministicMatchResult
    candidate_ids: list[uuid.UUID]
    evaluation_id: uuid.UUID | None
    metrics: MatchMetrics | None


class DeterministicMatchService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.matcher = DeterministicMatcher()

    def _rule_set(
        self,
        organization_id: uuid.UUID,
        config: DeterministicMatchConfig,
    ) -> MatchRuleSet:
        rule_set = self.session.scalar(
            select(MatchRuleSet).where(
                MatchRuleSet.organization_id == organization_id,
                MatchRuleSet.rule_set_key == config.rule_set_id,
                MatchRuleSet.version == config.schema_version,
            )
        )
        if rule_set is None:
            rule_set = MatchRuleSet(
                organization_id=organization_id,
                rule_set_key=config.rule_set_id,
                version=config.schema_version,
                entity_type="Person",
                deterministic_rules_json=[rule.model_dump(mode="json") for rule in config.rules],
                probabilistic_config_json={},
                status="active",
            )
            self.session.add(rule_set)
            self.session.flush()
        return rule_set

    def execute(
        self,
        organization_id: uuid.UUID,
        records: list[dict[str, Any]],
        config: DeterministicMatchConfig,
        truth: dict[str, str] | None = None,
        truth_set_name: str = "synthetic_identity_truth",
    ) -> MatchOutcome:
        for record in records:
            if str(record.get(config.organization_field, "")) != str(organization_id):
                raise ConnectorError(
                    "matching_scope_mismatch", "Matching record is outside organization scope"
                )
        rule_set = self._rule_set(organization_id, config)
        result = self.matcher.match(records, config)
        candidate_ids: list[uuid.UUID] = []
        for link in [*result.links, *result.conflicts]:
            candidate = MatchCandidate(
                organization_id=organization_id,
                rule_set_id=rule_set.id,
                left_record_key=link.left_record_key,
                right_record_key=link.right_record_key,
                score=None,
                evidence_json={
                    "rule_id": link.rule_id,
                    "fingerprints": link.evidence_fingerprints,
                },
                status=link.status,
            )
            self.session.add(candidate)
            self.session.flush()
            candidate_ids.append(candidate.id)
        metrics: MatchMetrics | None = None
        evaluation: MatchEvaluation | None = None
        if truth is not None:
            metrics = evaluate_matches(result.clusters, truth)
            evaluation = MatchEvaluation(
                organization_id=organization_id,
                rule_set_key=config.rule_set_id,
                rule_set_version=config.schema_version,
                truth_set_name=truth_set_name,
                evaluated_at=datetime.now(UTC),
                total_records=metrics.total_records,
                predicted_links=metrics.predicted_links,
                true_positives=metrics.true_positives,
                false_positives=metrics.false_positives,
                false_negatives=metrics.false_negatives,
                precision=metrics.precision,
                recall=metrics.recall,
                coverage=metrics.coverage,
                details_json=asdict(metrics),
            )
            self.session.add(evaluation)
            self.session.flush()
        self.session.commit()
        return MatchOutcome(
            result=result,
            candidate_ids=candidate_ids,
            evaluation_id=evaluation.id if evaluation else None,
            metrics=metrics,
        )

    def record_decision(
        self,
        organization_id: uuid.UUID,
        candidate_id: uuid.UUID,
        decision: str,
        reason: str,
        reviewer_id: uuid.UUID,
    ) -> MatchDecision:
        if decision not in {"match", "no_match", "defer", "escalate"}:
            raise ConnectorError("invalid_match_decision", "Match decision is invalid")
        candidate = self.session.get(MatchCandidate, candidate_id)
        if candidate is None or candidate.organization_id != organization_id:
            raise ConnectorError("candidate_not_found", "Match candidate was not found")
        if not reason.strip():
            raise ConnectorError("decision_reason_required", "Match decision reason is required")
        prior = self.session.scalar(
            select(MatchDecision)
            .where(MatchDecision.candidate_id == candidate.id)
            .order_by(MatchDecision.decided_at.desc())
        )
        row = MatchDecision(
            organization_id=organization_id,
            candidate_id=candidate.id,
            decision=decision,
            reason=reason.strip(),
            reviewer_id=reviewer_id,
            decided_at=datetime.now(UTC),
            supersedes_decision_id=prior.id if prior else None,
        )
        self.session.add(row)
        candidate.status = decision
        self.session.commit()
        return row
