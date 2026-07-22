import argparse
import asyncio
import importlib.metadata
import json
import os
import platform
import resource
import tempfile
import time
import uuid
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

import pyarrow as pa
import pyarrow.parquet as pq
from eduwork_databridge.config_loader import load_yaml_model
from eduwork_databridge.connectors.base import Connector, ExtractionBatch
from eduwork_databridge.connectors.files import (
    CSVConnector,
    JSONConnector,
    ParquetConnector,
    XLSXConnector,
)
from eduwork_databridge.mapping import MappingEngine, load_lookup
from eduwork_databridge.marts import MartBuilder
from eduwork_databridge.matching import (
    DeterministicMatcher,
    load_synthetic_identity_fixture,
)
from eduwork_databridge.matching.probabilistic import ProbabilisticMatcher
from eduwork_databridge.profiling import DataProfiler
from eduwork_databridge.schemas.config import (
    DeterministicMatchConfig,
    MappingConfig,
    MartDefinitionConfig,
    ProbabilisticMatchConfig,
    ProfileConfig,
    SourceObjectConfig,
    ValidationConfig,
)
from eduwork_databridge.synthetic import PresetName, generate_dataset
from eduwork_databridge.validation import ValidationEngine

StageFunction = Callable[[], Any]


def package_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def max_rss_kb() -> int:
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(usage if platform.system() != "Darwin" else usage / 1024)


def measure(name: str, record_count: int, function: StageFunction) -> tuple[Any, dict[str, Any]]:
    before_rss = max_rss_kb()
    started = time.perf_counter()
    value = function()
    duration = time.perf_counter() - started
    after_rss = max_rss_kb()
    return value, {
        "stage": name,
        "duration_seconds": round(duration, 6),
        "record_count": record_count,
        "records_per_second": round(record_count / duration, 2) if duration else None,
        "max_rss_kb": after_rss,
        "rss_increase_kb": max(0, after_rss - before_rss),
    }


def file_batch(
    connector: Connector,
    root: Path,
    relative: str,
    key: str,
    sheet: str | None = None,
) -> ExtractionBatch:
    source = SourceObjectConfig(
        key=key,
        object_type="file",
        location=str(root / relative),
        contract_version="1.0",
        sheet_name=sheet,
    )
    return asyncio.run(connector.extract(source))


def run(preset: PresetName, seed: int, output_path: Path) -> dict[str, Any]:
    temporary_root = Path(tempfile.mkdtemp(prefix="eduwork-benchmark-"))
    results: list[dict[str, Any]] = []
    manifest, stage = measure(
        "synthetic_generation",
        1,
        lambda: generate_dataset(temporary_root, preset, seed),
    )
    stage["generated_counts"] = manifest["counts"]
    results.append(stage)
    root = temporary_root / preset
    allowed = [temporary_root]
    max_bytes = 2 * 1024 * 1024 * 1024

    hris_batch, stage = measure(
        "csv_connector",
        manifest["counts"]["hris_people"],
        lambda: file_batch(
            CSVConnector(allowed, max_bytes), root, "hris/employees.csv", "employees"
        ),
    )
    results.append(stage)
    lms_batch, stage = measure(
        "json_connector",
        manifest["counts"]["lms_participations"],
        lambda: file_batch(
            JSONConnector(allowed, max_bytes),
            root,
            "lms/participation.json",
            "participation",
        ),
    )
    results.append(stage)
    assessment_batch, stage = measure(
        "xlsx_connector",
        manifest["counts"]["assessment_results"],
        lambda: file_batch(
            XLSXConnector(allowed, max_bytes),
            root,
            "assessment/assessment_results.xlsx",
            "assessment_results",
            "assessment_results",
        ),
    )
    results.append(stage)
    credential_batch, stage = measure(
        "parquet_connector",
        manifest["counts"]["credential_awards"],
        lambda: file_batch(
            ParquetConnector(allowed, max_bytes),
            root,
            "credential/credential_awards.parquet",
            "credential_awards",
        ),
    )
    results.append(stage)

    profile_config = load_yaml_model(Path("configs/demo/profiles/default_v1.yml"), ProfileConfig)
    _, stage = measure(
        "profiling",
        len(lms_batch.records),
        lambda: DataProfiler().profile(lms_batch.records, profile_config),
    )
    results.append(stage)

    lookup_id, _, lookup = load_lookup(Path("configs/demo/lookups/employment_status_v1.yml"))
    person_mapping = load_yaml_model(
        Path("configs/demo/mappings/hris_person_v1.yml"), MappingConfig
    )
    mapped_people, stage = measure(
        "mapping",
        len(hris_batch.records),
        lambda: MappingEngine().execute(
            hris_batch.records,
            person_mapping,
            {lookup_id: lookup},
            context={"output_defaults": {"organization_id": "benchmark-org"}},
        ),
    )
    results.append(stage)

    person_validation = load_yaml_model(
        Path("configs/demo/validations/person_v1.yml"), ValidationConfig
    )
    _, stage = measure(
        "validation",
        len(mapped_people.outputs),
        lambda: ValidationEngine().validate(mapped_people.outputs, person_validation),
    )
    results.append(stage)

    organization_id = uuid.uuid5(uuid.NAMESPACE_URL, f"eduwork:benchmark:{seed}")
    identity_records, truth = load_synthetic_identity_fixture(root, organization_id)
    deterministic_config = load_yaml_model(
        Path("configs/demo/matching/person_v1.yml"), DeterministicMatchConfig
    )
    deterministic, stage = measure(
        "deterministic_matching",
        len(identity_records),
        lambda: DeterministicMatcher().match(identity_records, deterministic_config),
    )
    results.append(stage)

    probabilistic_config = load_yaml_model(
        Path("configs/demo/matching/person_probabilistic_v1.yml"),
        ProbabilisticMatchConfig,
    )
    probabilistic, stage = measure(
        "probabilistic_matching",
        len(identity_records),
        lambda: ProbabilisticMatcher().run(
            identity_records,
            probabilistic_config,
            truth=truth,
        ),
    )
    stage["metrics"] = asdict(probabilistic.metrics) if probabilistic.metrics else None
    results.append(stage)

    participation_mapping = load_yaml_model(
        Path("configs/demo/mappings/lms_participation_v1.yml"), MappingConfig
    )
    mapped_participation = MappingEngine().execute(
        lms_batch.records,
        participation_mapping,
        {},
        context={"output_defaults": {"organization_id": "benchmark-org"}},
    )
    mart_config = load_yaml_model(
        Path("configs/demo/marts/training_participation_v1.yml"),
        MartDefinitionConfig,
    )
    mart, stage = measure(
        "training_mart",
        len(mapped_participation.outputs),
        lambda: MartBuilder().build(mapped_participation.outputs, mart_config),
    )
    results.append(stage)

    export_path = temporary_root / "training_mart.parquet"
    _, stage = measure(
        "parquet_export",
        len(mart),
        lambda: pq.write_table(pa.Table.from_pylist(mart), export_path, compression="zstd"),
    )
    stage["bytes"] = export_path.stat().st_size
    results.append(stage)

    report = {
        "benchmark_version": "1.0",
        "project_version": "0.15.0",
        "preset": preset,
        "seed": seed,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "cpu_count": os.cpu_count(),
            "packages": {
                "polars": package_version("polars"),
                "pyarrow": package_version("pyarrow"),
                "rapidfuzz": package_version("rapidfuzz"),
                "sqlalchemy": package_version("sqlalchemy"),
            },
        },
        "input_counts": manifest["counts"],
        "stages": results,
        "limitations": [
            "Synthetic data only",
            "Single-process sandbox measurement",
            "Not a production SLA or cloud benchmark",
            "Filesystem cache and shared-host load may affect results",
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--preset", choices=["small", "medium", "benchmark"], default="small")
    parser.add_argument("--seed", type=int, default=20260719)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    run(cast(PresetName, arguments.preset), arguments.seed, arguments.output)
