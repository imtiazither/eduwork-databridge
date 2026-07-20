import uuid
from pathlib import Path

import pytest
from eduwork_databridge.config_loader import load_yaml_model
from eduwork_databridge.connectors.base import ConnectorError
from eduwork_databridge.db.models.control import MatchCandidate, MatchDecision, MatchEvaluation
from eduwork_databridge.matching import (
    DeterministicMatcher,
    DeterministicMatchService,
    evaluate_matches,
    load_synthetic_identity_fixture,
    normalize_text,
)
from eduwork_databridge.schemas.config import (
    DeterministicMatchConfig,
    DeterministicMatchRuleConfig,
)
from sqlalchemy import func, select

from tests.factories import build_snapshot_session


def demo_config() -> DeterministicMatchConfig:
    return load_yaml_model(Path("configs/demo/matching/person_v1.yml"), DeterministicMatchConfig)


def test_normalization_is_unicode_and_whitespace_stable() -> None:
    assert normalize_text("  AMÍNA   Adams! ") == "amína adams"


def test_matcher_links_trusted_ids_and_blocks_conflicting_composite() -> None:
    organization_id = uuid.uuid4()
    records = [
        {
            "organization_id": str(organization_id),
            "record_key": "a",
            "employee_id": "E-1",
            "email": "",
            "display_name": "Amina Adams",
            "organization_unit_key": "TECH",
        },
        {
            "organization_id": str(organization_id),
            "record_key": "b",
            "employee_id": "E-1",
            "email": "",
            "display_name": "AMINA  ADAMS",
            "organization_unit_key": "TECH",
        },
        {
            "organization_id": str(organization_id),
            "record_key": "c",
            "employee_id": "E-2",
            "email": "",
            "display_name": "Shared Name",
            "organization_unit_key": "OPS",
        },
        {
            "organization_id": str(organization_id),
            "record_key": "d",
            "employee_id": "E-3",
            "email": "",
            "display_name": "Shared Name",
            "organization_unit_key": "OPS",
        },
    ]
    config = demo_config().model_copy(deep=True)
    config.rules.append(
        DeterministicMatchRuleConfig(
            rule_id="exact_name_and_department",
            priority=3,
            fields=["display_name", "organization_unit_key"],
        )
    )
    result = DeterministicMatcher().match(records, config)
    assert result.clusters["a"] == result.clusters["b"]
    assert result.clusters["c"] != result.clusters["d"]
    assert any(link.status == "trusted_id_conflict" for link in result.conflicts)


def test_matcher_rejects_cross_organization_input() -> None:
    records = [
        {"organization_id": "one", "record_key": "a", "employee_id": "E-1"},
        {"organization_id": "two", "record_key": "b", "employee_id": "E-1"},
    ]
    with pytest.raises(ValueError, match="Cross-organization"):
        DeterministicMatcher().match(records, demo_config())


def test_synthetic_truth_evaluation_and_persistence(tmp_path: Path) -> None:
    session, organization_id, _ = build_snapshot_session(tmp_path, [{"id": "seed"}])
    records, truth = load_synthetic_identity_fixture(Path("data/synthetic/small"), organization_id)
    outcome = DeterministicMatchService(session).execute(
        organization_id,
        records,
        demo_config(),
        truth=truth,
        truth_set_name="small_identity_truth",
    )
    assert outcome.metrics is not None
    assert outcome.metrics.total_records == len(records)
    assert outcome.metrics.precision >= 0.8
    assert outcome.metrics.recall >= 0.8
    assert session.scalar(select(func.count()).select_from(MatchEvaluation)) == 1
    assert session.scalar(select(func.count()).select_from(MatchCandidate)) == len(
        outcome.candidate_ids
    )
    candidate_id = outcome.candidate_ids[0]
    reviewer = uuid.uuid4()
    first = DeterministicMatchService(session).record_decision(
        organization_id, candidate_id, "defer", "Needs synthetic review.", reviewer
    )
    second = DeterministicMatchService(session).record_decision(
        organization_id, candidate_id, "match", "Evidence reviewed.", reviewer
    )
    assert second.supersedes_decision_id == first.id
    assert session.scalar(select(func.count()).select_from(MatchDecision)) == 2
    with pytest.raises(ConnectorError, match="reason"):
        DeterministicMatchService(session).record_decision(
            organization_id, candidate_id, "match", "", reviewer
        )
    session.close()


def test_pairwise_metric_calculation() -> None:
    clusters = {"a": "1", "b": "1", "c": "2"}
    truth = {"a": "x", "b": "x", "c": "y"}
    metrics = evaluate_matches(clusters, truth)
    assert metrics.precision == 1
    assert metrics.recall == 1
    assert metrics.false_positives == 0
