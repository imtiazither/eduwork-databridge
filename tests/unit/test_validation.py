import uuid
from pathlib import Path

import pytest
from eduwork_databridge.config_loader import load_yaml_model
from eduwork_databridge.db.models.control import QuarantineRecord, ValidationResult
from eduwork_databridge.schemas.config import ValidationConfig, ValidationRuleConfig
from eduwork_databridge.validation import ValidationEngine, ValidationService
from sqlalchemy import func, select

from tests.factories import build_snapshot_session


def comprehensive_config() -> ValidationConfig:
    rules = [
        ValidationRuleConfig(
            rule_id="schema",
            title="Schema",
            entity="Participation",
            severity="blocking",
            rule_type="schema",
            fields=["record_key", "progress"],
            parameters={"types": ["str", "number"]},
            explanation="Types must match.",
        ),
        ValidationRuleConfig(
            rule_id="required",
            title="Required",
            entity="Participation",
            severity="blocking",
            rule_type="required",
            fields=["record_key"],
            explanation="Key is required.",
        ),
        ValidationRuleConfig(
            rule_id="allowed",
            title="Allowed",
            entity="Participation",
            severity="error",
            rule_type="allowed_values",
            fields=["status"],
            parameters={"values": ["assigned", "completed"]},
            explanation="Status is governed.",
        ),
        ValidationRuleConfig(
            rule_id="range",
            title="Range",
            entity="Participation",
            severity="error",
            rule_type="range",
            fields=["progress"],
            parameters={"min": 0, "max": 100},
            explanation="Progress is bounded.",
        ),
        ValidationRuleConfig(
            rule_id="pattern",
            title="Pattern",
            entity="Participation",
            severity="warning",
            rule_type="pattern",
            fields=["email"],
            parameters={"regex": "^[^@]+@[^@]+[.][^@]+$", "allow_blank": False},
            explanation="Email pattern.",
        ),
        ValidationRuleConfig(
            rule_id="unique",
            title="Unique",
            entity="Participation",
            severity="blocking",
            rule_type="unique",
            fields=["record_key"],
            explanation="Key is unique.",
        ),
        ValidationRuleConfig(
            rule_id="reference",
            title="Reference",
            entity="Participation",
            severity="error",
            rule_type="reference",
            fields=["person_id"],
            parameters={"reference_set": "people"},
            explanation="Person exists.",
        ),
        ValidationRuleConfig(
            rule_id="temporal",
            title="Temporal",
            entity="Participation",
            severity="blocking",
            rule_type="temporal",
            fields=["assigned_at", "completed_at"],
            parameters={"relation": "before_or_equal", "allow_blank_right": True},
            explanation="Dates are ordered.",
        ),
        ValidationRuleConfig(
            rule_id="cross",
            title="Cross source",
            entity="Participation",
            severity="warning",
            rule_type="cross_source",
            fields=["record_key", "status"],
            parameters={"key_fields": ["record_key"], "compare_fields": ["status"]},
            explanation="Repeated status agrees.",
        ),
        ValidationRuleConfig(
            rule_id="timely",
            title="Timely",
            entity="Participation",
            severity="warning",
            rule_type="timeliness",
            fields=["updated_at"],
            parameters={"as_of": "2026-07-19T00:00:00+00:00", "max_age_days": 30},
            explanation="Record is current.",
        ),
    ]
    return ValidationConfig(validation_set_id="comprehensive", entity="Participation", rules=rules)


def defective_records() -> list[dict]:
    return [
        {
            "record_key": "A-1",
            "progress": 50,
            "status": "assigned",
            "email": "good@example.test",
            "person_id": "P-1",
            "assigned_at": "2026-07-01T00:00:00+00:00",
            "completed_at": "",
            "updated_at": "2026-07-10T00:00:00+00:00",
        },
        {
            "record_key": "A-1",
            "progress": 120,
            "status": "bad",
            "email": "not-an-email",
            "person_id": "P-X",
            "assigned_at": "2026-07-10T00:00:00+00:00",
            "completed_at": "2026-07-01T00:00:00+00:00",
            "updated_at": "2025-01-01T00:00:00+00:00",
        },
    ]


def test_validation_engine_covers_all_quality_categories() -> None:
    result = ValidationEngine().validate(
        defective_records(), comprehensive_config(), {"people": {"P-1"}}
    )
    assert result.issues
    assert result.blocking_failures > 0
    assert set(result.quality_dimensions) == {
        "structural",
        "completeness",
        "validity",
        "uniqueness",
        "consistency",
        "timeliness",
    }
    failed_rules = {issue.rule_id for issue in result.issues}
    assert {
        "allowed",
        "range",
        "pattern",
        "unique",
        "reference",
        "temporal",
        "cross",
        "timely",
    } <= failed_rules


def test_validation_service_persists_and_resolves_quarantine(tmp_path: Path) -> None:
    records = defective_records()
    session, organization_id, snapshot_id = build_snapshot_session(tmp_path, records)
    service = ValidationService(session)
    outcome = service.validate(
        organization_id,
        snapshot_id,
        records,
        comprehensive_config(),
        {"people": {"P-1"}},
    )
    assert outcome.quarantine_ids
    assert session.scalar(select(func.count()).select_from(ValidationResult)) == 10
    assert session.scalar(select(func.count()).select_from(QuarantineRecord)) == len(
        outcome.quarantine_ids
    )
    reviewer = uuid.uuid4()
    resolved = service.resolve_quarantine(
        organization_id,
        outcome.quarantine_ids[0],
        "waived",
        reviewer,
        "Synthetic exception reviewed for test only.",
    )
    assert resolved.status == "waived"
    assert resolved.waiver_reason
    linked = service.reprocess_link(
        organization_id, outcome.quarantine_ids[0], outcome.quarantine_ids[1]
    )
    assert linked.supersedes_quarantine_id == outcome.quarantine_ids[0]
    with pytest.raises(Exception, match="Resolution note"):
        service.resolve_quarantine(
            organization_id,
            outcome.quarantine_ids[1],
            "closed",
            reviewer,
            "",
        )
    session.close()


def test_demo_validation_configs_parse() -> None:
    for path in [
        Path("configs/demo/validations/person_v1.yml"),
        Path("configs/demo/validations/participation_v1.yml"),
    ]:
        config = load_yaml_model(path, ValidationConfig)
        assert config.rules
