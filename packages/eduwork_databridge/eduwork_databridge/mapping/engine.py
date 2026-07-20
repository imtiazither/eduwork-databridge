import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from eduwork_databridge.schemas.config import MappingConfig, MappingRuleConfig


class MappingCompileError(ValueError):
    pass


@dataclass(frozen=True)
class MappingIssue:
    source_record_key: str
    rule_sequence: int
    target_field: str
    error_code: str
    explanation: str
    evidence_masked: str | None


@dataclass(frozen=True)
class MappingResult:
    outputs: list[dict[str, Any]]
    issues: list[MappingIssue]
    input_count: int


Plugin = Callable[[Any, dict[str, Any], dict[str, Any]], Any]


class MappingEngine:
    transforms = {
        "copy",
        "trim",
        "lower",
        "upper",
        "parse_datetime_utc",
        "lookup",
        "default",
        "concat",
        "split",
        "conditional",
        "sha256_pseudonymize",
        "plugin",
    }

    def __init__(self, plugins: dict[str, Plugin] | None = None) -> None:
        self.plugins = plugins or {}

    def compile(
        self,
        config: MappingConfig,
        lookups: dict[str, dict[str, Any]],
    ) -> None:
        targets: set[str] = set()
        for rule in config.rules:
            if rule.transform not in self.transforms:
                raise MappingCompileError(f"Unsupported transformation: {rule.transform}")
            if rule.target in targets:
                raise MappingCompileError(f"Duplicate target field: {rule.target}")
            targets.add(rule.target)
            if rule.transform == "lookup" and (not rule.lookup or rule.lookup not in lookups):
                raise MappingCompileError(f"Lookup is unavailable for {rule.target}")
            if rule.transform == "plugin" and (not rule.plugin or rule.plugin not in self.plugins):
                raise MappingCompileError(f"Plugin is not registered for {rule.target}")
            if rule.transform == "sha256_pseudonymize" and "salt_key" not in rule.parameters:
                raise MappingCompileError("Pseudonymization requires a context salt_key name")

    @staticmethod
    def _mask(value: Any) -> str | None:
        if value in (None, ""):
            return None
        return f"sha256:{hashlib.sha256(str(value).encode()).hexdigest()[:12]}"

    @staticmethod
    def _record_key(record: dict[str, Any], index: int) -> str:
        for field in ("record_key", "employee_id", "assignment_id", "source_record_key"):
            if record.get(field):
                return str(record[field])
        return f"row-{index + 1}"

    def _transform(
        self,
        rule: MappingRuleConfig,
        value: Any,
        record: dict[str, Any],
        context: dict[str, Any],
        lookups: dict[str, dict[str, Any]],
    ) -> Any:
        if rule.transform == "copy":
            return value
        if rule.transform == "trim":
            return value.strip() if isinstance(value, str) else value
        if rule.transform == "lower":
            return value.strip().lower() if isinstance(value, str) else value
        if rule.transform == "upper":
            return value.strip().upper() if isinstance(value, str) else value
        if rule.transform == "parse_datetime_utc":
            if value in (None, ""):
                return None
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC).isoformat()
        if rule.transform == "lookup":
            table = lookups[rule.lookup or ""]
            key = str(value).strip().lower()
            if key not in table:
                raise ValueError("lookup value is not mapped")
            return table[key]
        if rule.transform == "default":
            return value if value not in (None, "") else rule.default
        if rule.transform == "concat":
            fields = rule.parameters.get("fields", [])
            separator = str(rule.parameters.get("separator", " "))
            if not isinstance(fields, list):
                raise ValueError("concat fields must be a list")
            return separator.join(str(record.get(field, "")) for field in fields).strip()
        if rule.transform == "split":
            if value in (None, ""):
                return None
            delimiter = str(rule.parameters.get("delimiter", ","))
            raw_position = rule.parameters.get("index", 0)
            if isinstance(raw_position, list | bool):
                raise ValueError("split index must be an integer")
            position = int(raw_position)
            parts = str(value).split(delimiter)
            if position >= len(parts) or position < -len(parts):
                raise ValueError("split index is outside the value")
            return parts[position].strip()
        if rule.transform == "conditional":
            field = str(rule.parameters.get("field", ""))
            expected = rule.parameters.get("equals")
            return (
                rule.parameters.get("then")
                if record.get(field) == expected
                else rule.parameters.get("else")
            )
        if rule.transform == "sha256_pseudonymize":
            if value in (None, ""):
                return None
            salt_key = str(rule.parameters["salt_key"])
            salt = context.get(salt_key)
            if not salt:
                raise ValueError("pseudonymization salt is unavailable")
            return hashlib.sha256(f"{salt}:{value}".encode()).hexdigest()
        if rule.transform == "plugin":
            return self.plugins[rule.plugin or ""](value, record, context)
        raise MappingCompileError(f"Unsupported transformation: {rule.transform}")

    def execute(
        self,
        records: list[dict[str, Any]],
        config: MappingConfig,
        lookups: dict[str, dict[str, Any]],
        context: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> MappingResult:
        self.compile(config, lookups)
        execution_context = context or {}
        selected = records[:limit] if limit is not None else records
        outputs: list[dict[str, Any]] = []
        issues: list[MappingIssue] = []
        for index, record in enumerate(selected):
            output = dict(execution_context.get("output_defaults", {}))
            record_issues: list[MappingIssue] = []
            source_key = self._record_key(record, index)
            for sequence, rule in enumerate(config.rules, start=1):
                value = record.get(rule.source) if rule.source else None
                try:
                    transformed = self._transform(rule, value, record, execution_context, lookups)
                    if rule.required and transformed in (None, ""):
                        raise ValueError("required mapped value is blank")
                    output[rule.target] = transformed
                except (KeyError, TypeError, ValueError) as exc:
                    record_issues.append(
                        MappingIssue(
                            source_record_key=source_key,
                            rule_sequence=sequence,
                            target_field=rule.target,
                            error_code="mapping_rule_failed",
                            explanation=str(exc),
                            evidence_masked=self._mask(value),
                        )
                    )
            if record_issues:
                issues.extend(record_issues)
            else:
                output["source_record_key"] = source_key
                outputs.append(output)
        return MappingResult(outputs=outputs, issues=issues, input_count=len(selected))


def diff_mappings(before: MappingConfig, after: MappingConfig) -> dict[str, Any]:
    before_rules = {rule.target: rule.model_dump(mode="json") for rule in before.rules}
    after_rules = {rule.target: rule.model_dump(mode="json") for rule in after.rules}
    before_targets = set(before_rules)
    after_targets = set(after_rules)
    return {
        "mapping_id_changed": before.mapping_id != after.mapping_id,
        "added_targets": sorted(after_targets - before_targets),
        "removed_targets": sorted(before_targets - after_targets),
        "changed_targets": sorted(
            target
            for target in before_targets & after_targets
            if before_rules[target] != after_rules[target]
        ),
    }
