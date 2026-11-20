import argparse
import json
from pathlib import Path

from eduwork_databridge.schemas.config import (
    DeterministicMatchConfig,
    ExportConfig,
    MappingConfig,
    MartDefinitionConfig,
    OrchestrationConfig,
    PipelineConfig,
    ProbabilisticMatchConfig,
    ProfileConfig,
    RetentionPolicyConfig,
    SourceConfig,
    ValidationConfig,
)
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS: dict[str, type[BaseModel]] = {
    "source-config.schema.json": SourceConfig,
    "mapping-config.schema.json": MappingConfig,
    "validation-config.schema.json": ValidationConfig,
    "pipeline-config.schema.json": PipelineConfig,
    "profile-config.schema.json": ProfileConfig,
    "deterministic-match-config.schema.json": DeterministicMatchConfig,
    "probabilistic-match-config.schema.json": ProbabilisticMatchConfig,
    "mart-definition-config.schema.json": MartDefinitionConfig,
    "export-config.schema.json": ExportConfig,
    "orchestration-config.schema.json": OrchestrationConfig,
    "retention-policy-config.schema.json": RetentionPolicyConfig,
}


def render(model: type[BaseModel]) -> str:
    schema = model.model_json_schema(mode="validation")
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def main(check: bool = False) -> None:
    out = ROOT / "schemas"
    out.mkdir(exist_ok=True)
    drift: list[str] = []
    for name, model in SCHEMAS.items():
        path = out / name
        expected = render(model)
        if check:
            if not path.exists() or path.read_text(encoding="utf-8") != expected:
                drift.append(str(path.relative_to(ROOT)))
        else:
            path.write_text(expected, encoding="utf-8")
    if drift:
        raise SystemExit("Generated schema drift: " + ", ".join(drift))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    main(parser.parse_args().check)
