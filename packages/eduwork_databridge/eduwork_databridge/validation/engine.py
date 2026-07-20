import hashlib
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast

from eduwork_databridge.schemas.config import ValidationConfig, ValidationRuleConfig


@dataclass(frozen=True)
class ValidationIssue:
    rule_id: str
    severity: str
    source_record_key: str
    fields: list[str]
    explanation: str
    evidence_masked: str | None


@dataclass(frozen=True)
class RuleSummary:
    rule_id: str
    category: str
    evaluated_count: int
    failed_count: int
    passed: bool


@dataclass(frozen=True)
class ValidationRunResult:
    issues: list[ValidationIssue]
    summaries: list[RuleSummary]
    quality_dimensions: dict[str, dict[str, int | float]]
    blocking_failures: int


CATEGORY_BY_RULE = {
    "schema": "structural",
    "required": "completeness",
    "allowed_values": "validity",
    "range": "validity",
    "pattern": "validity",
    "unique": "uniqueness",
    "reference": "consistency",
    "temporal": "consistency",
    "cross_source": "consistency",
    "timeliness": "timeliness",
}


class ValidationEngine:
    @staticmethod
    def _record_key(record: dict[str, Any], index: int) -> str:
        for field in ("record_key", "source_record_key", "employee_id", "assignment_id"):
            if record.get(field):
                return str(record[field])
        return f"row-{index + 1}"

    @staticmethod
    def _masked(record: dict[str, Any], fields: list[str]) -> str | None:
        present = [
            str(record.get(field)) for field in fields if record.get(field) not in (None, "")
        ]
        if not present:
            return None
        return "sha256:" + hashlib.sha256("|".join(present).encode()).hexdigest()[:16]

    @staticmethod
    def _parse_datetime(value: Any) -> datetime:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)

    def _record_issue(
        self,
        rule: ValidationRuleConfig,
        record: dict[str, Any],
        index: int,
    ) -> ValidationIssue:
        return ValidationIssue(
            rule_id=rule.rule_id,
            severity=rule.severity,
            source_record_key=self._record_key(record, index),
            fields=rule.fields,
            explanation=rule.explanation,
            evidence_masked=self._masked(record, rule.fields),
        )

    def _evaluate_record_rule(
        self,
        rule: ValidationRuleConfig,
        record: dict[str, Any],
    ) -> bool:
        values = [record.get(field) for field in rule.fields]
        parameters = rule.parameters
        if rule.rule_type == "schema":
            raw_types = parameters.get("types", [])
            expected_types = raw_types if isinstance(raw_types, list) else []
            if len(expected_types) != len(rule.fields):
                return False
            for field, expected in zip(rule.fields, expected_types, strict=True):
                value = record.get(field)
                if value is None:
                    continue
                valid = {
                    "str": isinstance(value, str),
                    "int": isinstance(value, int) and not isinstance(value, bool),
                    "number": isinstance(value, int | float) and not isinstance(value, bool),
                    "bool": isinstance(value, bool),
                    "object": isinstance(value, dict),
                    "list": isinstance(value, list),
                }.get(str(expected), False)
                if not valid:
                    return False
            return True
        if rule.rule_type == "required":
            return all(value not in (None, "") for value in values)
        if rule.rule_type == "allowed_values":
            raw_allowed = parameters.get("values", [])
            allowed_values = raw_allowed if isinstance(raw_allowed, list) else [raw_allowed]
            allowed = {str(value) for value in allowed_values}
            return all(value in (None, "") or str(value) in allowed for value in values)
        if rule.rule_type == "range":
            raw_minimum = parameters.get("min")
            raw_maximum = parameters.get("max")
            minimum = (
                float(raw_minimum)
                if isinstance(raw_minimum, str | int | float) and not isinstance(raw_minimum, bool)
                else float("-inf")
            )
            maximum = (
                float(raw_maximum)
                if isinstance(raw_maximum, str | int | float) and not isinstance(raw_maximum, bool)
                else float("inf")
            )
            try:
                for value in values:
                    if value in (None, ""):
                        continue
                    if not minimum <= float(cast(Any, value)) <= maximum:
                        return False
                return True
            except (TypeError, ValueError):
                return False
        if rule.rule_type == "pattern":
            pattern = re.compile(str(parameters.get("regex", ".*")))
            allow_blank = bool(parameters.get("allow_blank", False))
            return all(
                (allow_blank and value in (None, ""))
                or (value not in (None, "") and bool(pattern.fullmatch(str(value))))
                for value in values
            )
        if rule.rule_type == "temporal":
            if len(values) != 2:
                return False
            left, right = values
            if right in (None, "") and bool(parameters.get("allow_blank_right", False)):
                return True
            if left in (None, "") or right in (None, ""):
                return False
            try:
                left_time, right_time = self._parse_datetime(left), self._parse_datetime(right)
            except (TypeError, ValueError):
                return False
            relation = str(parameters.get("relation", "before_or_equal"))
            return (
                left_time <= right_time if relation == "before_or_equal" else left_time < right_time
            )
        if rule.rule_type == "timeliness":
            if not values or values[0] in (None, ""):
                return False
            try:
                observed = self._parse_datetime(values[0])
                as_of = self._parse_datetime(parameters["as_of"])
                raw_max_age = parameters["max_age_days"]
                if isinstance(raw_max_age, list | bool):
                    return False
                max_age_days = int(raw_max_age)
            except (KeyError, TypeError, ValueError):
                return False
            return 0 <= (as_of - observed).days <= max_age_days
        return True

    def validate(
        self,
        records: list[dict[str, Any]],
        config: ValidationConfig,
        reference_sets: dict[str, set[str]] | None = None,
    ) -> ValidationRunResult:
        references = reference_sets or {}
        issues: list[ValidationIssue] = []
        summaries: list[RuleSummary] = []
        for rule in config.rules:
            failed_indices: set[int] = set()
            if rule.rule_type == "unique":
                groups: dict[tuple[Any, ...], list[int]] = defaultdict(list)
                for index, record in enumerate(records):
                    groups[tuple(record.get(field) for field in rule.fields)].append(index)
                failed_indices = {
                    index
                    for key, indices in groups.items()
                    if any(value not in (None, "") for value in key) and len(indices) > 1
                    for index in indices
                }
            elif rule.rule_type == "reference":
                reference_name = str(rule.parameters.get("reference_set", ""))
                allowed = references.get(reference_name, set())
                for index, record in enumerate(records):
                    if any(
                        record.get(field) not in (None, "")
                        and str(record.get(field)) not in allowed
                        for field in rule.fields
                    ):
                        failed_indices.add(index)
            elif rule.rule_type == "cross_source":
                raw_keys = rule.parameters.get("key_fields", [])
                raw_compares = rule.parameters.get("compare_fields", [])
                key_fields = (
                    [str(value) for value in raw_keys] if isinstance(raw_keys, list) else []
                )
                compare_fields = (
                    [str(value) for value in raw_compares] if isinstance(raw_compares, list) else []
                )
                cross_groups: dict[tuple[Any, ...], list[int]] = defaultdict(list)
                for index, record in enumerate(records):
                    cross_groups[tuple(record.get(field) for field in key_fields)].append(index)
                for indices in cross_groups.values():
                    for field in compare_fields:
                        observed = {
                            records[index].get(field)
                            for index in indices
                            if records[index].get(field) not in (None, "")
                        }
                        if len(observed) > 1:
                            failed_indices.update(indices)
            else:
                failed_indices = {
                    index
                    for index, record in enumerate(records)
                    if not self._evaluate_record_rule(rule, record)
                }
            issues.extend(
                self._record_issue(rule, records[index], index) for index in sorted(failed_indices)
            )
            summaries.append(
                RuleSummary(
                    rule_id=rule.rule_id,
                    category=CATEGORY_BY_RULE[rule.rule_type],
                    evaluated_count=len(records),
                    failed_count=len(failed_indices),
                    passed=not failed_indices,
                )
            )
        dimension_totals: dict[str, dict[str, int]] = defaultdict(
            lambda: {"evaluated": 0, "failed": 0}
        )
        for summary in summaries:
            dimension_totals[summary.category]["evaluated"] += summary.evaluated_count
            dimension_totals[summary.category]["failed"] += summary.failed_count
        dimensions = {
            name: {
                "evaluated": values["evaluated"],
                "failed": values["failed"],
                "pass_rate": round(1 - values["failed"] / values["evaluated"], 8)
                if values["evaluated"]
                else 1.0,
            }
            for name, values in sorted(dimension_totals.items())
        }
        blocking_rule_ids = {rule.rule_id for rule in config.rules if rule.severity == "blocking"}
        blocking_failures = sum(issue.rule_id in blocking_rule_ids for issue in issues)
        return ValidationRunResult(
            issues=issues,
            summaries=summaries,
            quality_dimensions=dimensions,
            blocking_failures=blocking_failures,
        )
