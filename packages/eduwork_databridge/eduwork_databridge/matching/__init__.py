from eduwork_databridge.matching.deterministic import (
    DeterministicMatcher,
    DeterministicMatchResult,
    MatchLink,
    MatchMetrics,
    evaluate_matches,
)
from eduwork_databridge.matching.fixtures import load_synthetic_identity_fixture
from eduwork_databridge.matching.normalization import normalize_text, normalize_value
from eduwork_databridge.matching.probabilistic import (
    ProbabilisticCandidate,
    ProbabilisticMatcher,
    ProbabilisticMetrics,
    ProbabilisticResult,
)
from eduwork_databridge.matching.probabilistic_service import (
    ProbabilisticMatchService,
    ProbabilisticOutcome,
    metrics_dict,
)
from eduwork_databridge.matching.service import DeterministicMatchService, MatchOutcome

__all__ = [
    "DeterministicMatcher",
    "DeterministicMatchResult",
    "DeterministicMatchService",
    "MatchLink",
    "MatchMetrics",
    "MatchOutcome",
    "ProbabilisticCandidate",
    "ProbabilisticMatchService",
    "ProbabilisticMatcher",
    "ProbabilisticMetrics",
    "ProbabilisticOutcome",
    "ProbabilisticResult",
    "evaluate_matches",
    "metrics_dict",
    "load_synthetic_identity_fixture",
    "normalize_text",
    "normalize_value",
]
