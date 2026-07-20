import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from typing import Any

import polars as pl

from eduwork_databridge.profiling.models import DriftResult, ProfileResult
from eduwork_databridge.schemas.config import ProfileConfig


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(str(value).encode()).hexdigest()[:16]


def _safe_ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 8) if denominator else 0.0


def _relative_delta(current: float, baseline: float) -> float:
    if baseline == 0:
        return 0.0 if current == 0 else 1.0
    return round(abs(current - baseline) / abs(baseline), 8)


class DataProfiler:
    version = "1.0"

    def profile(self, records: list[dict[str, Any]], config: ProfileConfig) -> ProfileResult:
        sampled = records[: config.sample_limit]
        dataframe = (
            pl.from_dicts(sampled, strict=False, infer_schema_length=None)
            if sampled
            else pl.DataFrame()
        )
        row_count = len(records)
        sample_count = len(sampled)
        fields: dict[str, dict[str, Any]] = {}
        for name in dataframe.columns:
            series = dataframe.get_column(name)
            values = series.to_list()
            null_count = sum(value is None for value in values)
            blank_count = sum(isinstance(value, str) and not value.strip() for value in values)
            non_null = [value for value in values if value is not None]
            counts = Counter(str(value) for value in non_null)
            top_values = [
                {
                    "fingerprint": _fingerprint(value) if config.mask_samples else value,
                    "count": count,
                    "share": _safe_ratio(count, sample_count),
                }
                for value, count in counts.most_common(config.top_values_limit)
            ]
            field_profile: dict[str, Any] = {
                "observed_type": str(series.dtype),
                "null_count": null_count,
                "null_rate": _safe_ratio(null_count, sample_count),
                "blank_count": blank_count,
                "distinct_count": len(counts),
                "distinct_rate": _safe_ratio(len(counts), sample_count),
                "top_values": top_values,
            }
            if series.dtype.is_numeric():
                numeric = series.cast(pl.Float64, strict=False).drop_nulls()
                if numeric.len():
                    field_profile["numeric"] = {
                        "minimum": numeric.min(),
                        "maximum": numeric.max(),
                        "mean": numeric.mean(),
                        "median": numeric.median(),
                        "p05": numeric.quantile(0.05, interpolation="nearest"),
                        "p95": numeric.quantile(0.95, interpolation="nearest"),
                    }
            string_lengths = [len(value) for value in non_null if isinstance(value, str)]
            if string_lengths:
                field_profile["string_length"] = {
                    "minimum": min(string_lengths),
                    "maximum": max(string_lengths),
                    "mean": round(sum(string_lengths) / len(string_lengths), 4),
                }
            fields[name] = field_profile
        schema_material = {name: value["observed_type"] for name, value in sorted(fields.items())}
        schema_fingerprint = hashlib.sha256(
            json.dumps(schema_material, sort_keys=True).encode()
        ).hexdigest()
        profile = {
            "profile_version": self.version,
            "profile_id": config.profile_id,
            "generated_at": datetime.now(UTC).isoformat(),
            "row_count": row_count,
            "sample_count": sample_count,
            "masked_top_values": config.mask_samples,
            "fields": fields,
        }
        return ProfileResult(profile=profile, schema_fingerprint=schema_fingerprint)

    def compare(
        self,
        baseline: dict[str, Any],
        current: dict[str, Any],
        config: ProfileConfig,
    ) -> DriftResult:
        baseline_fields = baseline.get("fields", {})
        current_fields = current.get("fields", {})
        baseline_names = set(baseline_fields)
        current_names = set(current_fields)
        added = sorted(current_names - baseline_names)
        removed = sorted(baseline_names - current_names)
        type_changes: list[dict[str, str]] = []
        metric_changes: list[dict[str, Any]] = []
        breached: list[dict[str, Any]] = []
        for name in sorted(baseline_names & current_names):
            before = baseline_fields[name]
            after = current_fields[name]
            if before.get("observed_type") != after.get("observed_type"):
                type_changes.append(
                    {
                        "field": name,
                        "baseline": str(before.get("observed_type")),
                        "current": str(after.get("observed_type")),
                    }
                )
            null_delta = round(after.get("null_rate", 0.0) - before.get("null_rate", 0.0), 8)
            distinct_delta = round(
                after.get("distinct_rate", 0.0) - before.get("distinct_rate", 0.0), 8
            )
            before_mean = before.get("numeric", {}).get("mean")
            after_mean = after.get("numeric", {}).get("mean")
            mean_relative_delta = (
                _relative_delta(float(after_mean), float(before_mean))
                if before_mean is not None and after_mean is not None
                else None
            )
            before_top = before.get("top_values", [{}])
            after_top = after.get("top_values", [{}])
            before_share = float(before_top[0].get("share", 0.0)) if before_top else 0.0
            after_share = float(after_top[0].get("share", 0.0)) if after_top else 0.0
            top_share_delta = round(after_share - before_share, 8)
            change = {
                "field": name,
                "null_rate_delta": null_delta,
                "distinct_rate_delta": distinct_delta,
                "numeric_mean_relative_delta": mean_relative_delta,
                "top_value_share_delta": top_share_delta,
            }
            metric_changes.append(change)
            threshold_checks = {
                "null_rate_delta": config.thresholds.null_rate_delta,
                "distinct_rate_delta": config.thresholds.distinct_rate_delta,
                "numeric_mean_relative_delta": config.thresholds.numeric_mean_relative_delta,
                "top_value_share_delta": config.thresholds.top_value_share_delta,
            }
            for metric, threshold in threshold_checks.items():
                value = change[metric]
                if value is not None and abs(float(value)) > threshold:
                    breached.append(
                        {
                            "field": name,
                            "metric": metric,
                            "value": value,
                            "threshold": threshold,
                        }
                    )
        status = (
            "drift" if removed or type_changes or breached else ("warning" if added else "stable")
        )
        return DriftResult(
            status=status,
            comparison={
                "status": status,
                "added_fields": added,
                "removed_fields": removed,
                "type_changes": type_changes,
                "metric_changes": metric_changes,
                "threshold_breaches": breached,
                "baseline_row_count": baseline.get("row_count", 0),
                "current_row_count": current.get("row_count", 0),
            },
        )
