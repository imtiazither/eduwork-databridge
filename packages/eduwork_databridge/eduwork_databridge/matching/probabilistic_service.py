import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from eduwork_databridge.connectors.base import ConnectorError
from eduwork_databridge.db.models.control import (
    MatchCandidate,
    MatchRuleSet,
    ProbabilisticModel,
    ProbabilisticRun,
)
from eduwork_databridge.matching.probabilistic import (
    ProbabilisticMatcher,
    ProbabilisticMetrics,
    ProbabilisticResult,
)
from eduwork_databridge.schemas.config import ProbabilisticMatchConfig


@dataclass(frozen=True)
class ProbabilisticOutcome:
    model_id: uuid.UUID
    run_id: uuid.UUID
    candidate_ids: list[uuid.UUID]
    result: ProbabilisticResult


class ProbabilisticMatchService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.matcher = ProbabilisticMatcher()

    def _model(
        self,
        organization_id: uuid.UUID,
        config: ProbabilisticMatchConfig,
        parameters: dict[str, dict[str, float]],
        truth_set_name: str | None,
    ) -> tuple[ProbabilisticModel, MatchRuleSet]:
        version = config.schema_version
        model = self.session.scalar(
            select(ProbabilisticModel).where(
                ProbabilisticModel.organization_id == organization_id,
                ProbabilisticModel.model_key == config.model_id,
                ProbabilisticModel.version == version,
            )
        )
        if model is None:
            model = ProbabilisticModel(
                organization_id=organization_id,
                model_key=config.model_id,
                version=version,
                status="synthetic_evaluated" if truth_set_name else "configured",
                comparison_config_json={
                    "blocking_rules": [
                        rule.model_dump(mode="json") for rule in config.blocking_rules
                    ],
                    "comparisons": [item.model_dump(mode="json") for item in config.comparisons],
                },
                parameters_json=parameters,
                review_low=config.review_low,
                auto_match=config.auto_match,
                trained_on_truth_set=truth_set_name,
                trained_at=datetime.now(UTC) if truth_set_name else None,
            )
            self.session.add(model)
            self.session.flush()
        rule_set_key = f"probabilistic_{config.model_id}"
        rule_set = self.session.scalar(
            select(MatchRuleSet).where(
                MatchRuleSet.organization_id == organization_id,
                MatchRuleSet.rule_set_key == rule_set_key,
                MatchRuleSet.version == version,
            )
        )
        if rule_set is None:
            rule_set = MatchRuleSet(
                organization_id=organization_id,
                rule_set_key=rule_set_key,
                version=version,
                entity_type="Person",
                deterministic_rules_json=[],
                probabilistic_config_json=config.model_dump(mode="json"),
                status="active",
            )
            self.session.add(rule_set)
            self.session.flush()
        return model, rule_set

    def execute(
        self,
        organization_id: uuid.UUID,
        records: list[dict[str, Any]],
        config: ProbabilisticMatchConfig,
        truth: dict[str, str] | None = None,
        truth_set_name: str | None = None,
        parameters: dict[str, dict[str, float]] | None = None,
    ) -> ProbabilisticOutcome:
        for record in records:
            if str(record.get(config.organization_field, "")) != str(organization_id):
                raise ConnectorError(
                    "matching_scope_mismatch", "Matching record is outside organization scope"
                )
        started = datetime.now(UTC)
        result = self.matcher.run(records, config, truth=truth, parameters=parameters)
        model, rule_set = self._model(
            organization_id,
            config,
            result.model_parameters,
            truth_set_name if truth is not None else None,
        )
        run = ProbabilisticRun(
            organization_id=organization_id,
            model_id=model.id,
            status="succeeded",
            candidate_count=len(result.candidates),
            auto_match_count=sum(item.status == "auto_match" for item in result.candidates),
            review_count=sum(item.status == "review" for item in result.candidates),
            no_match_count=sum(item.status == "no_match" for item in result.candidates),
            conflict_count=sum(item.status == "trusted_id_conflict" for item in result.candidates),
            metrics_json=asdict(result.metrics) if result.metrics else {},
            started_at=started,
            ended_at=datetime.now(UTC),
        )
        self.session.add(run)
        self.session.flush()
        candidate_ids: list[uuid.UUID] = []
        for item in result.candidates:
            candidate = MatchCandidate(
                organization_id=organization_id,
                rule_set_id=rule_set.id,
                left_record_key=item.left_record_key,
                right_record_key=item.right_record_key,
                score=item.probability,
                evidence_json={
                    "model_id": str(model.id),
                    "block_rule_ids": item.block_rule_ids,
                    "features": item.features,
                    "fingerprints": item.evidence_fingerprints,
                    "cluster_impact": item.cluster_impact,
                },
                status=item.status,
            )
            self.session.add(candidate)
            self.session.flush()
            candidate_ids.append(candidate.id)
        self.session.commit()
        return ProbabilisticOutcome(
            model_id=model.id,
            run_id=run.id,
            candidate_ids=candidate_ids,
            result=result,
        )


def metrics_dict(metrics: ProbabilisticMetrics | None) -> dict[str, int | float] | None:
    return asdict(metrics) if metrics else None
