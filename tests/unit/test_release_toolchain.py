import re
from pathlib import Path

import pytest
import yaml


@pytest.mark.parametrize("workflow", ["ci", "pages", "release"])
def test_workflows_pin_the_patched_uv_toolchain(workflow):
    document = yaml.safe_load(Path(f".github/workflows/{workflow}.yml").read_text())
    pins = [
        match.group(1)
        for job in document["jobs"].values()
        for step in job.get("steps", [])
        for match in re.finditer(r"uv==([0-9.]+)", step.get("run", ""))
    ]
    assert pins and set(pins) == {"0.13.4"}


def test_container_pins_the_same_patched_toolchain():
    dockerfile = Path("infra/docker/api.Dockerfile").read_text()
    assert re.findall(r"uv==([0-9.]+)", dockerfile) == ["0.13.4"]
