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


@dataclass(frozen=True)
class MatchQueueItem:
    candidate: MatchCandidate
    latest_decision: MatchDecision | None
    decision_count: int


@dataclass(frozen=True)
class MatchQueueSummary:
    total_candidates: int
    unreviewed_candidates: int
    by_status: dict[str, int]


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

    def list_decisions(
        self,
        organization_id: uuid.UUID,
        candidate_id: uuid.UUID,
    ) -> list[MatchDecision]:
        candidate = self.session.get(MatchCandidate, candidate_id)
        if candidate is None or candidate.organization_id != organization_id:
            raise ConnectorError("candidate_not_found", "Match candidate was not found")
        return list(
            self.session.scalars(
                select(MatchDecision)
                .where(MatchDecision.candidate_id == candidate.id)
                .order_by(MatchDecision.decided_at.desc(), MatchDecision.id.desc())
            )
        )

    def list_review_queue(
        self,
        organization_id: uuid.UUID,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[MatchQueueItem]:
        query = select(MatchCandidate).where(MatchCandidate.organization_id == organization_id)
        if status is not None:
            query = query.where(MatchCandidate.status == status)
        candidates = list(
            self.session.scalars(
                query.order_by(MatchCandidate.created_at.asc(), MatchCandidate.id.asc())
                .offset(offset)
                .limit(limit)
            )
        )
        if not candidates:
            return []

        candidate_ids = [candidate.id for candidate in candidates]
        decisions = list(
            self.session.scalars(
                select(MatchDecision)
                .where(MatchDecision.candidate_id.in_(candidate_ids))
                .order_by(MatchDecision.decided_at.desc(), MatchDecision.id.desc())
            )
        )
        decisions_by_candidate: dict[uuid.UUID, list[MatchDecision]] = {}
        for decision in decisions:
            decisions_by_candidate.setdefault(decision.candidate_id, []).append(decision)
        items: list[MatchQueueItem] = []
        for candidate in candidates:
            candidate_decisions = decisions_by_candidate.get(candidate.id, [])
            items.append(
                MatchQueueItem(
                    candidate=candidate,
                    latest_decision=candidate_decisions[0] if candidate_decisions else None,
                    decision_count=len(candidate_decisions),
                )
            )
        return items

    def review_queue_summary(self, organization_id: uuid.UUID) -> MatchQueueSummary:
        candidates = list(
            self.session.scalars(
                select(MatchCandidate).where(MatchCandidate.organization_id == organization_id)
            )
        )
        reviewed_candidate_ids = set(
            self.session.scalars(
                select(MatchDecision.candidate_id)
                .where(MatchDecision.organization_id == organization_id)
                .distinct()
            )
        )
        by_status: dict[str, int] = {}
        for candidate in candidates:
            by_status[candidate.status] = by_status.get(candidate.status, 0) + 1
        return MatchQueueSummary(
            total_candidates=len(candidates),
            unreviewed_candidates=sum(
                candidate.id not in reviewed_candidate_ids for candidate in candidates
            ),
            by_status=dict(sorted(by_status.items())),
        )
