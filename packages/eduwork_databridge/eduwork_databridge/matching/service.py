import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import exists, func, or_, select, update
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

REVIEW_STATUSES = ("pending", "review", "trusted_id_conflict", "defer", "escalate")


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
    needs_review_candidates: int
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
        expected_revision: int,
        *,
        commit: bool = True,
    ) -> MatchDecision:
        if decision not in {"match", "no_match", "defer", "escalate"}:
            raise ConnectorError("invalid_match_decision", "Match decision is invalid")
        candidate = self.session.get(MatchCandidate, candidate_id)
        if candidate is None or candidate.organization_id != organization_id:
            raise ConnectorError("candidate_not_found", "Match candidate was not found")
        if not reason.strip():
            raise ConnectorError("decision_reason_required", "Match decision reason is required")
        # Compare and advance in one database statement. A competing writer must
        # observe the new revision before it can append another decision.
        updated_id = self.session.scalar(
            update(MatchCandidate)
            .where(
                MatchCandidate.id == candidate_id,
                MatchCandidate.organization_id == organization_id,
                MatchCandidate.revision == expected_revision,
            )
            .values(status=decision, revision=expected_revision + 1)
            .returning(MatchCandidate.id)
            .execution_options(synchronize_session=False)
        )
        if updated_id is None:
            self.session.rollback()
            raise ConnectorError(
                "decision_conflict", "Candidate changed. Refresh the queue before deciding."
            )
        prior = self.session.scalar(
            select(MatchDecision)
            .where(
                MatchDecision.candidate_id == candidate.id,
                MatchDecision.organization_id == organization_id,
            )
            .order_by(MatchDecision.revision.desc())
            .limit(1)
        )
        row = MatchDecision(
            organization_id=organization_id,
            candidate_id=candidate.id,
            decision=decision,
            revision=expected_revision + 1,
            reason=reason.strip(),
            reviewer_id=reviewer_id,
            decided_at=datetime.now(UTC),
            supersedes_decision_id=prior.id if prior else None,
        )
        self.session.add(row)
        self.session.expire(candidate)
        if commit:
            self.session.commit()
        else:
            self.session.flush()
        return row

    def list_decisions(
        self,
        organization_id: uuid.UUID,
        candidate_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[MatchDecision]:
        candidate = self.session.get(MatchCandidate, candidate_id)
        if candidate is None or candidate.organization_id != organization_id:
            raise ConnectorError("candidate_not_found", "Match candidate was not found")
        return list(
            self.session.scalars(
                select(MatchDecision)
                .where(
                    MatchDecision.candidate_id == candidate.id,
                    MatchDecision.organization_id == organization_id,
                )
                .order_by(MatchDecision.revision.desc())
                .offset(offset)
                .limit(limit)
            )
        )

    def list_review_queue(
        self,
        organization_id: uuid.UUID,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
        needs_review: bool = False,
        unreviewed: bool = False,
        q: str | None = None,
    ) -> list[MatchQueueItem]:
        query = select(MatchCandidate).where(MatchCandidate.organization_id == organization_id)
        if status is not None:
            query = query.where(MatchCandidate.status == status)
        if needs_review:
            query = query.where(MatchCandidate.status.in_(REVIEW_STATUSES))
        if unreviewed:
            query = query.where(
                ~exists().where(
                    MatchDecision.candidate_id == MatchCandidate.id,
                    MatchDecision.organization_id == organization_id,
                )
            )
        if q and q.strip():
            query = query.where(
                or_(
                    MatchCandidate.left_record_key.icontains(q.strip(), autoescape=True),
                    MatchCandidate.right_record_key.icontains(q.strip(), autoescape=True),
                )
            )
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
        counts = {
            candidate_id: count
            for candidate_id, count in self.session.execute(
                select(MatchDecision.candidate_id, func.count())
                .where(
                    MatchDecision.candidate_id.in_(candidate_ids),
                    MatchDecision.organization_id == organization_id,
                )
                .group_by(MatchDecision.candidate_id)
            ).all()
        }
        latest = {
            row.candidate_id: row
            for row in self.session.scalars(
                select(MatchDecision)
                .join(MatchCandidate, MatchCandidate.id == MatchDecision.candidate_id)
                .where(
                    MatchDecision.candidate_id.in_(candidate_ids),
                    MatchDecision.organization_id == organization_id,
                    MatchDecision.revision == MatchCandidate.revision,
                )
            )
        }
        items: list[MatchQueueItem] = []
        for candidate in candidates:
            items.append(
                MatchQueueItem(
                    candidate=candidate,
                    latest_decision=latest.get(candidate.id),
                    decision_count=counts.get(candidate.id, 0),
                )
            )
        return items

    def review_queue_summary(self, organization_id: uuid.UUID) -> MatchQueueSummary:
        by_status = {
            status: count
            for status, count in self.session.execute(
                select(MatchCandidate.status, func.count())
                .where(MatchCandidate.organization_id == organization_id)
                .group_by(MatchCandidate.status)
                .order_by(MatchCandidate.status)
            ).all()
        }
        unreviewed = self.session.scalar(
            select(func.count())
            .select_from(MatchCandidate)
            .where(
                MatchCandidate.organization_id == organization_id,
                ~exists().where(
                    MatchDecision.candidate_id == MatchCandidate.id,
                    MatchDecision.organization_id == organization_id,
                ),
            )
        )
        return MatchQueueSummary(
            total_candidates=sum(by_status.values()),
            unreviewed_candidates=unreviewed or 0,
            needs_review_candidates=sum(by_status.get(status, 0) for status in REVIEW_STATUSES),
            by_status=by_status,
        )
