import json
import uuid
from pathlib import Path

from eduwork_databridge.db.models.control import LineageNode
from eduwork_databridge.lineage import LineageService
from sqlalchemy import select

from tests.factories import build_snapshot_session


def test_field_lineage_trace_and_openlineage_event(tmp_path: Path) -> None:
    session, organization_id, snapshot_id = build_snapshot_session(
        tmp_path, [{"employee_id": "E-1"}]
    )
    service = LineageService(session, tmp_path / "lineage")
    node_ids = service.record_mapping(
        organization_id,
        snapshot_id,
        "hris_person_v1",
        "1.0",
        [
            {"source": "employee_id", "target": "record_key", "transform": "trim"},
            {"source": "email", "target": "email", "transform": "lower"},
        ],
    )
    assert len(node_ids) == 4
    field = session.scalar(select(LineageNode).where(LineageNode.name == "hris_person_v1.email"))
    assert field is not None
    trace = service.trace(organization_id, field.id)
    assert any(node["namespace"] == "eduwork.raw" for node in trace.nodes)
    assert any(edge["relation"] == "generated" for edge in trace.edges)

    event_path = service.emit_openlineage_event(
        organization_id,
        "phase10_export",
        uuid.uuid4(),
        "COMPLETE",
        [f"raw:{snapshot_id}"],
        ["mart:training"],
    )
    event = json.loads(event_path.read_text(encoding="utf-8"))
    assert event["eventType"] == "COMPLETE"
    assert event["job"]["namespace"] == "eduwork"
    assert "employee_id" not in event_path.read_text(encoding="utf-8")
    session.close()
