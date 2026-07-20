from pathlib import Path
from typing import Any

import yaml

from eduwork_databridge.mapping.engine import MappingCompileError


def load_lookup(path: Path) -> tuple[str, str, dict[str, Any]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != {"lookup_id", "version", "values"}:
        raise MappingCompileError("Lookup file must contain lookup_id, version, and values only")
    if not isinstance(payload["values"], dict):
        raise MappingCompileError("Lookup values must be an object")
    values = {str(key).strip().lower(): value for key, value in payload["values"].items()}
    return str(payload["lookup_id"]), str(payload["version"]), values
