from pathlib import Path

import pytest
from eduwork_databridge.config_loader import load_yaml_model
from eduwork_databridge.db.models.control import MappingError, MappingExecution
from eduwork_databridge.mapping import (
    MappingCompileError,
    MappingEngine,
    MappingService,
    diff_mappings,
    load_lookup,
)
from eduwork_databridge.schemas.config import MappingConfig
from sqlalchemy import func, select

from tests.factories import build_snapshot_session


def demo_mapping() -> tuple[MappingConfig, dict[str, dict]]:
    config = load_yaml_model(Path("configs/demo/mappings/hris_person_v1.yml"), MappingConfig)
    lookup_id, _, values = load_lookup(Path("configs/demo/lookups/employment_status_v1.yml"))
    return config, {lookup_id: values}


def test_mapping_engine_executes_bounded_dsl_and_masks_errors() -> None:
    config, lookups = demo_mapping()
    records = [
        {
            "employee_id": " E-1 ",
            "display_name": " Amina Adams ",
            "given_name": "Amina",
            "family_name": "Adams",
            "email": "AMINA@EXAMPLE.TEST",
            "department_code": "technology",
            "employment_status": "ACTIVE",
            "updated_at": "2026-01-01T00:00:00+00:00",
        },
        {
            "employee_id": "",
            "display_name": "Missing Identifier",
            "employment_status": "unknown-code",
            "updated_at": "not-a-date",
        },
    ]
    result = MappingEngine().execute(
        records,
        config,
        lookups,
        context={"output_defaults": {"organization_id": "org-1"}},
    )
    assert result.input_count == 2
    assert len(result.outputs) == 1
    assert result.outputs[0]["record_key"] == "E-1"
    assert result.outputs[0]["email"] == "amina@example.test"
    assert result.outputs[0]["status"] == "active"
    assert result.issues
    assert all(
        issue.evidence_masked is None or issue.evidence_masked.startswith("sha256:")
        for issue in result.issues
    )


def test_mapping_compile_rejects_unregistered_lookup_and_plugin() -> None:
    config, _ = demo_mapping()
    with pytest.raises(MappingCompileError, match="Lookup"):
        MappingEngine().compile(config, {})
    plugin_config = config.model_copy(deep=True)
    plugin_config.rules[0].transform = "plugin"
    plugin_config.rules[0].plugin = "unknown"
    with pytest.raises(MappingCompileError, match="Plugin"):
        MappingEngine().compile(plugin_config, {"employment_status_v1": {}})


def test_mapping_diff_reports_changed_targets() -> None:
    before, _ = demo_mapping()
    after = before.model_copy(deep=True)
    after.rules[1].transform = "upper"
    difference = diff_mappings(before, after)
    assert difference["changed_targets"] == ["employee_id"]


def test_mapping_service_persists_preview_and_row_errors(tmp_path: Path) -> None:
    records = [
        {
            "employee_id": "E-1",
            "display_name": "Amina",
            "employment_status": "active",
            "updated_at": "2026-01-01T00:00:00+00:00",
        },
        {"employee_id": "", "display_name": "No ID", "employment_status": "active"},
    ]
    session, organization_id, snapshot_id = build_snapshot_session(tmp_path, records)
    config, lookups = demo_mapping()
    outcome = MappingService(session, tmp_path / "mapped").execute(
        organization_id=organization_id,
        snapshot_id=snapshot_id,
        records=records,
        config=config,
        lookups=lookups,
        context={"output_defaults": {"organization_id": str(organization_id)}},
        dry_run=True,
        preview_limit=25,
    )
    assert outcome.status == "previewed"
    assert outcome.output_count == 1
    assert outcome.error_count >= 1
    assert session.scalar(select(func.count()).select_from(MappingExecution)) == 1
    assert session.scalar(select(func.count()).select_from(MappingError)) >= 1
    session.close()
