from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from eduwork_databridge.connectors.base import ConnectorError
from eduwork_databridge.connectors.security import validate_sql_identifier


def load_yaml_model[ModelT: BaseModel](path: Path, model: type[ModelT]) -> ModelT:
    value: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    return model.model_validate(value)


def named_config_path(config_root: Path, category: str, config_id: str) -> Path:
    validate_sql_identifier(category)
    validate_sql_identifier(config_id)
    root = config_root.expanduser().resolve(strict=True)
    path = (root / category / f"{config_id}.yml").resolve(strict=True)
    if not path.is_relative_to(root):
        raise ConnectorError("config_outside_root", "Configuration is outside config root")
    return path


def source_config_path(config_root: Path, source_id: str) -> Path:
    return named_config_path(config_root, "sources", source_id)
