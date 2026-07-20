import hashlib
import itertools
import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from rapidfuzz.fuzz import ratio

from eduwork_databridge.matching.deterministic import UnionFind
from eduwork_databridge.matching.normalization import normalize_value
from eduwork_databridge.schemas.config import (
    ComparisonFieldConfig,
    ProbabilisticMatchConfig,
)


@dataclass(frozen=True)
class ProbabilisticCandidate:
    left_record_key: str
    right_record_key: str
    probability: float
    status: str
    block_rule_ids: list[str]
    features: dict[str, float]
    evidence_fingerprints: dict[str, str]
    cluster_impact: dict[str, int]


@dataclass(frozen=True)
class ProbabilisticMetrics:
    total_truth_pairs: int
    auto_match_pairs: int
    review_pairs: int
    auto_true_positives: int
    auto_false_positives: int
    false_negatives_after_review: int
    auto_precision: float
    potential_recall_with_review: float
    review_capture: float


@dataclass(frozen=True)
class ProbabilisticResult:
    candidates: list[ProbabilisticCandidate]
    model_parameters: dict[str, dict[str, float]]
    metrics: ProbabilisticMetrics | None


class ProbabilisticMatcher:
    def _blocking_key(
        self,
        record: dict[str, Any],
        fields: list[str],
        require_all: bool,
    ) -> tuple[str, ...] | None:
        values = tuple(normalize_value(field, record.get(field)) for field in fields)
        if require_all and any(not value for value in values):
            return None
        return values if any(values) else None

    def generate_candidates(
        self,
        records: list[dict[str, Any]],
        config: ProbabilisticMatchConfig,
    ) -> dict[tuple[str, str], list[str]]:
        record_key_field = config.record_key_field
        organizations = {str(record.get(config.organization_field, "")) for record in records}
        if "" in organizations or len(organizations) != 1:
            raise ValueError("Probabilistic matching requires exactly one organization")
        candidates: dict[tuple[str, str], list[str]] = {}
        for blocking_rule in config.blocking_rules:
            groups: dict[tuple[str, ...], list[str]] = {}
            for record in records:
                record_key = str(record.get(record_key_field, "")).strip()
                if not record_key:
                    raise ValueError("Probabilistic matching requires record keys")
                key = self._blocking_key(record, blocking_rule.fields, blocking_rule.require_all)
                if key is not None:
                    groups.setdefault(key, []).append(record_key)
            for members in groups.values():
                for left, right in itertools.combinations(sorted(set(members)), 2):
                    pair = (left, right)
                    candidates.setdefault(pair, []).append(blocking_rule.rule_id)
                    if len(candidates) > config.max_candidates:
                        raise ValueError("Probabilistic candidate limit exceeded")
        return candidates

    @staticmethod
    def _similarity(
        left: Any,
        right: Any,
        comparison: ComparisonFieldConfig,
    ) -> float:
        if left in (None, "") or right in (None, ""):
            return -1.0
        if comparison.method == "exact":
            return float(
                normalize_value(comparison.field, left) == normalize_value(comparison.field, right)
            )
        if comparison.method == "string_similarity":
            return (
                ratio(
                    normalize_value(comparison.field, left),
                    normalize_value(comparison.field, right),
                )
                / 100.0
            )
        if comparison.method == "date_distance":
            try:
                left_date = datetime.fromisoformat(str(left).replace("Z", "+00:00"))
                right_date = datetime.fromisoformat(str(right).replace("Z", "+00:00"))
            except ValueError:
                return 0.0
            distance = abs((left_date - right_date).total_seconds()) / 86_400
            tolerance = comparison.tolerance or 1.0
            return max(0.0, 1 - distance / tolerance)
        if comparison.method == "numeric_distance":
            try:
                distance = abs(float(left) - float(right))
            except (TypeError, ValueError):
                return 0.0
            tolerance = comparison.tolerance or 1.0
            return max(0.0, 1 - distance / tolerance)
        return 0.0

    def estimate_parameters(
        self,
        records: list[dict[str, Any]],
        candidates: dict[tuple[str, str], list[str]],
        truth: dict[str, str],
        config: ProbabilisticMatchConfig,
    ) -> dict[str, dict[str, float]]:
        del candidates
        record_by_key = {str(record[config.record_key_field]): record for record in records}
        truth_keys = sorted(set(record_by_key) & set(truth))
        estimation_pairs = itertools.islice(itertools.combinations(truth_keys, 2), 100_000)
        labeled_pairs = [
            (left_key, right_key, truth[left_key] == truth[right_key])
            for left_key, right_key in estimation_pairs
        ]
        parameters: dict[str, dict[str, float]] = {}
        for comparison in config.comparisons:
            matching: list[float] = []
            nonmatching: list[float] = []
            for left_key, right_key, is_match in labeled_pairs:
                similarity = self._similarity(
                    record_by_key[left_key].get(comparison.field),
                    record_by_key[right_key].get(comparison.field),
                    comparison,
                )
                if similarity >= 0:
                    target = matching if is_match else nonmatching
                    target.append(similarity)
            estimated_m = (
                sum(matching) / len(matching) if matching else comparison.agreement_probability
            )
            estimated_u = (
                sum(nonmatching) / len(nonmatching)
                if nonmatching
                else comparison.random_agreement_probability
            )
            parameters[comparison.field] = {
                "m": min(0.99, max(0.01, estimated_m)),
                "u": min(0.99, max(0.01, estimated_u)),
                "weight": comparison.weight,
            }
        return parameters

    @staticmethod
    def _probability(
        features: dict[str, float],
        parameters: dict[str, dict[str, float]],
        prior: float,
    ) -> float:
        log_odds = math.log(prior / (1 - prior))
        for field, similarity in features.items():
            if similarity < 0:
                continue
            values = parameters[field]
            m, u, weight = values["m"], values["u"], values["weight"]
            agreement = math.log(m / u)
            disagreement = math.log((1 - m) / (1 - u))
            log_odds += weight * (disagreement + similarity * (agreement - disagreement))
        return 1 / (1 + math.exp(-max(-50.0, min(50.0, log_odds))))

    @staticmethod
    def _fingerprint(value: Any) -> str:
        return hashlib.sha256(str(value).encode()).hexdigest()[:16]

    def run(
        self,
        records: list[dict[str, Any]],
        config: ProbabilisticMatchConfig,
        truth: dict[str, str] | None = None,
        parameters: dict[str, dict[str, float]] | None = None,
    ) -> ProbabilisticResult:
        candidates = self.generate_candidates(records, config)
        record_by_key = {str(record[config.record_key_field]): record for record in records}
        model_parameters = parameters or (
            self.estimate_parameters(records, candidates, truth, config)
            if truth is not None
            else {
                comparison.field: {
                    "m": comparison.agreement_probability,
                    "u": comparison.random_agreement_probability,
                    "weight": comparison.weight,
                }
                for comparison in config.comparisons
            }
        )
        scored: list[tuple[tuple[str, str], list[str], dict[str, float], float]] = []
        for pair, block_rules in candidates.items():
            left_record = record_by_key[pair[0]]
            right_record = record_by_key[pair[1]]
            features = {
                comparison.field: self._similarity(
                    left_record.get(comparison.field),
                    right_record.get(comparison.field),
                    comparison,
                )
                for comparison in config.comparisons
            }
            probability = self._probability(
                features, model_parameters, config.prior_match_probability
            )
            scored.append((pair, block_rules, features, probability))
        union_find = UnionFind(list(record_by_key))
        results: list[ProbabilisticCandidate] = []
        for pair, block_rules, features, probability in sorted(
            scored, key=lambda item: item[3], reverse=True
        ):
            left, right = pair
            left_employee = normalize_value("employee_id", record_by_key[left].get("employee_id"))
            right_employee = normalize_value("employee_id", record_by_key[right].get("employee_id"))
            trusted_conflict = (
                bool(left_employee) and bool(right_employee) and left_employee != right_employee
            )
            if trusted_conflict:
                status = "trusted_id_conflict"
            elif probability >= config.auto_match:
                status = "auto_match"
            elif probability >= config.review_low:
                status = "review"
            else:
                status = "no_match"
            left_root, right_root = union_find.find(left), union_find.find(right)
            left_size = sum(union_find.find(key) == left_root for key in record_by_key)
            right_size = sum(union_find.find(key) == right_root for key in record_by_key)
            if status == "auto_match" and left_root != right_root:
                union_find.union(left, right)
            results.append(
                ProbabilisticCandidate(
                    left_record_key=left,
                    right_record_key=right,
                    probability=round(probability, 8),
                    status=status,
                    block_rule_ids=sorted(block_rules),
                    features={key: round(value, 8) for key, value in features.items()},
                    evidence_fingerprints={
                        comparison.field: self._fingerprint(
                            record_by_key[left].get(comparison.field)
                        )
                        for comparison in config.comparisons
                    },
                    cluster_impact={
                        "left_cluster_size": left_size,
                        "right_cluster_size": right_size,
                        "merged_size": left_size + right_size,
                    },
                )
            )
        metrics = self.evaluate(results, truth) if truth is not None else None
        return ProbabilisticResult(
            candidates=results,
            model_parameters=model_parameters,
            metrics=metrics,
        )

    @staticmethod
    def evaluate(
        candidates: list[ProbabilisticCandidate],
        truth: dict[str, str],
    ) -> ProbabilisticMetrics:
        truth_pairs = {
            tuple(sorted((left, right)))
            for left, right in itertools.combinations(sorted(truth), 2)
            if truth[left] == truth[right]
        }
        auto_pairs = {
            tuple(sorted((candidate.left_record_key, candidate.right_record_key)))
            for candidate in candidates
            if candidate.status == "auto_match"
        }
        review_pairs = {
            tuple(sorted((candidate.left_record_key, candidate.right_record_key)))
            for candidate in candidates
            if candidate.status == "review"
        }
        true_positives = len(auto_pairs & truth_pairs)
        false_positives = len(auto_pairs - truth_pairs)
        captured = len((auto_pairs | review_pairs) & truth_pairs)
        false_negatives_after_review = len(truth_pairs - auto_pairs - review_pairs)
        auto_precision = true_positives / len(auto_pairs) if auto_pairs else 1.0
        potential_recall = captured / len(truth_pairs) if truth_pairs else 1.0
        review_capture = (
            len(review_pairs & truth_pairs) / len(review_pairs) if review_pairs else 1.0
        )
        return ProbabilisticMetrics(
            total_truth_pairs=len(truth_pairs),
            auto_match_pairs=len(auto_pairs),
            review_pairs=len(review_pairs),
            auto_true_positives=true_positives,
            auto_false_positives=false_positives,
            false_negatives_after_review=false_negatives_after_review,
            auto_precision=round(auto_precision, 8),
            potential_recall_with_review=round(potential_recall, 8),
            review_capture=round(review_capture, 8),
        )
