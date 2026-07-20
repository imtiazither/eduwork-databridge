import hashlib
import itertools
import uuid
from dataclasses import dataclass
from typing import Any

from eduwork_databridge.matching.normalization import normalize_value
from eduwork_databridge.schemas.config import DeterministicMatchConfig, DeterministicMatchRuleConfig


@dataclass(frozen=True)
class MatchLink:
    left_record_key: str
    right_record_key: str
    rule_id: str
    status: str
    evidence_fingerprints: dict[str, str]


@dataclass(frozen=True)
class MatchMetrics:
    total_records: int
    predicted_links: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    coverage: float


@dataclass(frozen=True)
class DeterministicMatchResult:
    clusters: dict[str, str]
    links: list[MatchLink]
    conflicts: list[MatchLink]


class UnionFind:
    def __init__(self, keys: list[str]) -> None:
        self.parent = {key: key for key in keys}

    def find(self, key: str) -> str:
        parent = self.parent[key]
        if parent != key:
            self.parent[key] = self.find(parent)
        return self.parent[key]

    def union(self, left: str, right: str) -> str:
        left_root, right_root = self.find(left), self.find(right)
        if left_root == right_root:
            return left_root
        winner, loser = sorted((left_root, right_root))
        self.parent[loser] = winner
        return winner


class DeterministicMatcher:
    def _key(
        self,
        record: dict[str, Any],
        rule: DeterministicMatchRuleConfig,
    ) -> tuple[str, ...] | None:
        values = tuple(normalize_value(field, record.get(field)) for field in rule.fields)
        if rule.require_all and any(not value for value in values):
            return None
        if not any(values):
            return None
        return values

    @staticmethod
    def _fingerprints(record: dict[str, Any], fields: list[str]) -> dict[str, str]:
        return {
            field: hashlib.sha256(str(record.get(field, "")).encode()).hexdigest()[:16]
            for field in fields
        }

    def match(
        self,
        records: list[dict[str, Any]],
        config: DeterministicMatchConfig,
    ) -> DeterministicMatchResult:
        record_key_field = config.record_key_field
        organization_field = config.organization_field
        record_by_key: dict[str, dict[str, Any]] = {}
        organizations: set[str] = set()
        for record in records:
            record_key = str(record.get(record_key_field, "")).strip()
            organization = str(record.get(organization_field, "")).strip()
            if not record_key or not organization:
                raise ValueError("Every matching record requires record_key and organization_id")
            if record_key in record_by_key:
                raise ValueError("Matching record keys must be unique")
            record_by_key[record_key] = record
            organizations.add(organization)
        if len(organizations) > 1:
            raise ValueError("Cross-organization matching is prohibited")
        union_find = UnionFind(list(record_by_key))
        links: list[MatchLink] = []
        conflicts: list[MatchLink] = []
        trusted_rules = sorted(
            (rule for rule in config.rules if rule.trusted), key=lambda rule: rule.priority
        )
        composite_rules = sorted(
            (rule for rule in config.rules if not rule.trusted), key=lambda rule: rule.priority
        )

        for rule in trusted_rules:
            trusted_groups: dict[tuple[str, ...], list[str]] = {}
            for record_key, record in record_by_key.items():
                key = self._key(record, rule)
                if key is not None:
                    trusted_groups.setdefault(key, []).append(record_key)
            for members in trusted_groups.values():
                for left, right in zip(sorted(members), sorted(members)[1:], strict=False):
                    union_find.union(left, right)
                    links.append(
                        MatchLink(
                            left_record_key=left,
                            right_record_key=right,
                            rule_id=rule.rule_id,
                            status="auto_match",
                            evidence_fingerprints=self._fingerprints(
                                record_by_key[left], rule.fields
                            ),
                        )
                    )

        def cluster_trusted_values(root: str) -> set[tuple[str, ...]]:
            values: set[tuple[str, ...]] = set()
            for record_key, record in record_by_key.items():
                if union_find.find(record_key) != root:
                    continue
                for rule in trusted_rules:
                    key = self._key(record, rule)
                    if key is not None:
                        values.add(key)
            return values

        for rule in composite_rules:
            composite_groups: dict[tuple[str, ...], list[str]] = {}
            for record_key, record in record_by_key.items():
                key = self._key(record, rule)
                if key is not None:
                    composite_groups.setdefault(key, []).append(record_key)
            for members in composite_groups.values():
                ordered = sorted(members)
                for left, right in itertools.combinations(ordered, 2):
                    left_root, right_root = union_find.find(left), union_find.find(right)
                    if left_root == right_root:
                        continue
                    left_trusted = cluster_trusted_values(left_root)
                    right_trusted = cluster_trusted_values(right_root)
                    link = MatchLink(
                        left_record_key=left,
                        right_record_key=right,
                        rule_id=rule.rule_id,
                        status="auto_match",
                        evidence_fingerprints=self._fingerprints(record_by_key[left], rule.fields),
                    )
                    if left_trusted and right_trusted and left_trusted.isdisjoint(right_trusted):
                        conflicts.append(
                            MatchLink(
                                left_record_key=link.left_record_key,
                                right_record_key=link.right_record_key,
                                rule_id=link.rule_id,
                                status="trusted_id_conflict",
                                evidence_fingerprints=link.evidence_fingerprints,
                            )
                        )
                        continue
                    union_find.union(left, right)
                    links.append(link)

        cluster_members: dict[str, list[str]] = {}
        for record_key in record_by_key:
            cluster_members.setdefault(union_find.find(record_key), []).append(record_key)
        cluster_ids = {
            root: str(
                uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    "eduwork:deterministic-cluster:" + "|".join(sorted(members)),
                )
            )
            for root, members in cluster_members.items()
        }
        clusters = {
            record_key: cluster_ids[union_find.find(record_key)] for record_key in record_by_key
        }
        return DeterministicMatchResult(clusters=clusters, links=links, conflicts=conflicts)


def evaluate_matches(
    clusters: dict[str, str],
    truth: dict[str, str],
) -> MatchMetrics:
    shared_keys = sorted(set(clusters) & set(truth))
    predicted_pairs = {
        pair
        for pair in itertools.combinations(shared_keys, 2)
        if clusters[pair[0]] == clusters[pair[1]]
    }
    truth_pairs = {
        pair for pair in itertools.combinations(shared_keys, 2) if truth[pair[0]] == truth[pair[1]]
    }
    true_positives = len(predicted_pairs & truth_pairs)
    false_positives = len(predicted_pairs - truth_pairs)
    false_negatives = len(truth_pairs - predicted_pairs)
    precision = true_positives / len(predicted_pairs) if predicted_pairs else 1.0
    recall = true_positives / len(truth_pairs) if truth_pairs else 1.0
    cluster_sizes: dict[str, int] = {}
    for record_key in shared_keys:
        cluster_sizes[clusters[record_key]] = cluster_sizes.get(clusters[record_key], 0) + 1
    covered = sum(cluster_sizes[clusters[key]] > 1 for key in shared_keys)
    coverage = covered / len(shared_keys) if shared_keys else 0.0
    return MatchMetrics(
        total_records=len(shared_keys),
        predicted_links=len(predicted_pairs),
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        precision=round(precision, 8),
        recall=round(recall, 8),
        coverage=round(coverage, 8),
    )
