import uuid
from pathlib import Path

from eduwork_databridge.config_loader import load_yaml_model
from eduwork_databridge.db.models.control import (
    MatchCandidate,
    ProbabilisticModel,
    ProbabilisticRun,
)
from eduwork_databridge.matching import load_synthetic_identity_fixture
from eduwork_databridge.matching.probabilistic import ProbabilisticMatcher
from eduwork_databridge.matching.probabilistic_service import ProbabilisticMatchService
from eduwork_databridge.schemas.config import ProbabilisticMatchConfig
from sqlalchemy import func, select

from tests.factories import build_snapshot_session


def config() -> ProbabilisticMatchConfig:
    return load_yaml_model(
        Path("configs/demo/matching/person_probabilistic_v1.yml"),
        ProbabilisticMatchConfig,
    )


def test_probabilistic_matching_creates_gray_zone_and_safe_auto_matches() -> None:
    organization_id = uuid.uuid4()
    records, truth = load_synthetic_identity_fixture(Path("data/synthetic/small"), organization_id)
    result = ProbabilisticMatcher().run(records, config(), truth=truth)
    assert result.metrics is not None
    assert result.metrics.auto_precision == 1.0
    assert result.metrics.potential_recall_with_review == 1.0
    assert result.metrics.review_pairs == 29
    assert result.metrics.false_negatives_after_review == 0
    assert any(candidate.status == "review" for candidate in result.candidates)
    assert any(candidate.status == "trusted_id_conflict" for candidate in result.candidates)
    assert all(
        raw_value not in str(candidate.evidence_fingerprints)
        for candidate in result.candidates[:10]
        for raw_value in ["Amina Adams", "EMP-0000001"]
    )


def test_probabilistic_service_persists_model_run_and_candidates(tmp_path: Path) -> None:
    session, organization_id, _ = build_snapshot_session(tmp_path, [{"id": "seed"}])
    records, truth = load_synthetic_identity_fixture(Path("data/synthetic/small"), organization_id)
    outcome = ProbabilisticMatchService(session).execute(
        organization_id,
        records,
        config(),
        truth=truth,
        truth_set_name="small_identity_truth",
    )
    assert outcome.result.metrics is not None
    assert session.scalar(select(func.count()).select_from(ProbabilisticModel)) == 1
    assert session.scalar(select(func.count()).select_from(ProbabilisticRun)) == 1
    assert session.scalar(select(func.count()).select_from(MatchCandidate)) == len(
        outcome.candidate_ids
    )
    model = session.get(ProbabilisticModel, outcome.model_id)
    assert model is not None
    original_parameters = dict(model.parameters_json)
    candidate = session.get(MatchCandidate, outcome.candidate_ids[0])
    assert candidate is not None
    candidate.status = "review"
    session.commit()
    session.refresh(model)
    assert model.parameters_json == original_parameters
    session.close()
