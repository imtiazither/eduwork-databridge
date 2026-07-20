import argparse
import json
from pathlib import Path
from typing import Any, cast

REQUIRED_STAGES = {
    "synthetic_generation",
    "csv_connector",
    "json_connector",
    "xlsx_connector",
    "parquet_connector",
    "profiling",
    "mapping",
    "validation",
    "deterministic_matching",
    "probabilistic_matching",
    "training_mart",
    "parquet_export",
}


def load(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def verify(current_path: Path, baseline_path: Path | None, budgets_path: Path | None) -> None:
    current = load(current_path)
    stages = {item["stage"]: item for item in current["stages"]}
    missing = REQUIRED_STAGES - set(stages)
    if missing:
        raise SystemExit("Benchmark stages missing: " + ", ".join(sorted(missing)))
    for name, item in stages.items():
        if item["duration_seconds"] <= 0:
            raise SystemExit(f"Benchmark duration is invalid: {name}")
        if item["record_count"] < 0:
            raise SystemExit(f"Benchmark record count is invalid: {name}")
    if baseline_path is None or budgets_path is None:
        return
    baseline = load(baseline_path)
    baseline_stages = {item["stage"]: item for item in baseline["stages"]}
    budgets = load(budgets_path)
    default_multiplier = float(budgets["default_duration_multiplier"])
    default_slack = float(budgets["default_absolute_slack_seconds"])
    failures = []
    for name in REQUIRED_STAGES:
        base_duration = float(baseline_stages[name]["duration_seconds"])
        current_duration = float(stages[name]["duration_seconds"])
        stage_budget = budgets.get("stages", {}).get(name, {})
        multiplier = float(stage_budget.get("duration_multiplier", default_multiplier))
        slack = float(stage_budget.get("absolute_slack_seconds", default_slack))
        limit = base_duration * multiplier + slack
        if current_duration > limit:
            failures.append(f"{name}: {current_duration:.4f}s > {limit:.4f}s")
    if failures:
        raise SystemExit("Benchmark regression budget exceeded: " + "; ".join(failures))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--budgets", type=Path)
    args = parser.parse_args()
    verify(args.current, args.baseline, args.budgets)
