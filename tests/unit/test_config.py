from pathlib import Path

import pytest
import yaml
from eduwork_databridge.schemas.config import SourceConfig
from pydantic import ValidationError


def test_demo_source_config_is_valid() -> None:
    data = yaml.safe_load(Path("configs/demo/sources/demo_hris.yml").read_text(encoding="utf-8"))
    config = SourceConfig.model_validate(data)
    assert config.source_id == "demo_hris"
    assert config.objects[0].key == "employees"


def test_source_config_rejects_unknown_fields() -> None:
    data = {
        "source_id": "bad",
        "name": "Bad",
        "connector": "csv",
        "owner_role": "Owner",
        "data_classification": "internal",
        "objects": [
            {"key": "x", "object_type": "file", "location": "x.csv", "contract_version": "1"}
        ],
        "unknown": True,
    }
    with pytest.raises(ValidationError):
        SourceConfig.model_validate(data)
