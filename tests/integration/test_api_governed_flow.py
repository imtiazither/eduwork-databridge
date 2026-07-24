"""API-level coverage for the governed flow an external evaluator exercises.

These tests drive the real FastAPI app end to end: extract, mapped
validation, matching, mart, export, lineage trace, and audit. They exist
because the service-level tests cannot see gaps between documented API
behavior and service behavior.
"""

import asyncio
import uuid
from pathlib import Path
from typing import Any

import httpx
import pytest
from eduwork_databridge import seed as seed_module
from eduwork_databridge.db import Base
from eduwork_databridge.db.models.core import Organization
from eduwork_databridge.db.session import SessionLocal, engine
from eduwork_databridge.main import app, settings
from sqlalchemy import select

ADMIN = "demo-admin"


@pytest.fixture(scope="module", autouse=True)
def governed_flow_environment(tmp_path_factory: pytest.TempPathFactory):
    roots = tmp_path_factory.mktemp("governed-roots")
    patcher = pytest.MonkeyPatch()
    patcher.setattr(settings, "raw_store_root", roots / "raw")
    patcher.setattr(settings, "mart_root", roots / "marts")
    patcher.setattr(settings, "export_root", roots / "exports")
    patcher.setattr(settings, "lineage_root", roots / "lineage")
    Base.metadata.create_all(engine)
    seed_module.seed()
    yield roots
    patcher.undo()


@pytest.fixture(scope="module")
def organization_id() -> uuid.UUID:
    with SessionLocal() as session:
        organization = session.scalar(
            select(Organization).where(Organization.name == "Northstar Learning Labs")
        )
        assert organization is not None
        return organization.id


def call(
    method: str,
    path: str,
    organization_id: uuid.UUID,
    payload: dict[str, Any] | None = None,
) -> httpx.Response:
    async def run() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        headers = {"X-Demo-User": ADMIN, "X-Organization-ID": str(organization_id)}
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path, headers=headers, json=payload)

    return asyncio.run(run())


def extract_lms(organization_id: uuid.UUID) -> str:
    response = call(
        "POST",
        "/api/v1/sources/demo_lms/extract",
        organization_id,
        {"object_key": "participation"},
    )
    assert response.status_code == 200, response.text
    return str(response.json()["snapshot_id"])


@pytest.mark.integration
def test_mapped_validation_catches_planted_defects_without_raw_noise(
    organization_id: uuid.UUID,
) -> None:
    snapshot_id = extract_lms(organization_id)
    response = call(
        "POST",
        "/api/v1/validations",
        organization_id,
        {
            "snapshot_id": snapshot_id,
            "validation_set_id": "participation_v1",
            "mapping_id": "lms_participation_v1",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["record_source"] == "mapped"
    assert body["validated_record_count"] == 366
    dimensions = body["quality_dimensions"]
    # Canonical keys exist after mapping, so completeness noise disappears.
    assert dimensions["completeness"]["failed"] == 0
    # The fixture plants exactly seven invalid completion statuses.
    assert dimensions["validity"]["failed"] == 7
    # The fixture plants exactly five completions before assignment.
    assert body["blocking_failures"] == 5


@pytest.mark.integration
def test_raw_validation_still_available_and_labeled(organization_id: uuid.UUID) -> None:
    snapshot_id = extract_lms(organization_id)
    response = call(
        "POST",
        "/api/v1/validations",
        organization_id,
        {"snapshot_id": snapshot_id, "validation_set_id": "participation_v1"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["record_source"] == "raw"


@pytest.mark.integration
def test_lineage_trace_resolves_business_ids_back_to_raw_snapshot(
    organization_id: uuid.UUID, governed_flow_environment: Path
) -> None:
    snapshot_id = extract_lms(organization_id)
    preview = call(
        "POST",
        "/api/v1/mappings/preview",
        organization_id,
        {
            "snapshot_id": snapshot_id,
            "mapping_id": "lms_participation_v1",
            "preview_limit": 500,
        },
    )
    assert preview.status_code == 200, preview.text
    records = preview.json()["outputs"]
    mart = call(
        "POST",
        "/api/v1/marts",
        organization_id,
        {
            "mart_config_id": "training_participation_v1",
            "records": records,
            "source_snapshot_id": snapshot_id,
            "mapping_id": "lms_participation_v1",
        },
    )
    assert mart.status_code == 200, mart.text
    mart_snapshot_id = mart.json()["mart_snapshot_id"]
    export = call(
        "POST",
        "/api/v1/exports",
        organization_id,
        {
            "mart_snapshot_id": mart_snapshot_id,
            "export_config_id": "training_participation_csv_v1",
        },
    )
    assert export.status_code == 200, export.text
    export_snapshot_id = export.json()["export_snapshot_id"]

    trace = call("GET", f"/api/v1/lineage/{export_snapshot_id}", organization_id)
    assert trace.status_code == 200, trace.text
    graph = trace.json()
    namespaces = {node["namespace"] for node in graph["nodes"]}
    assert {"eduwork.raw", "eduwork.mapping", "eduwork.mart", "eduwork.export"} <= namespaces
    names = {node["name"] for node in graph["nodes"]}
    assert snapshot_id in names
    assert export_snapshot_id in names
    assert len(graph["edges"]) >= 3
    # The mart id also resolves as a starting point.
    mart_trace = call("GET", f"/api/v1/lineage/{mart_snapshot_id}", organization_id)
    assert mart_trace.status_code == 200
    assert mart_trace.json()["nodes"]

    # Storage roots configured in settings are the ones actually written.
    roots = governed_flow_environment
    assert list((roots / "marts").rglob("*.parquet"))
    assert list((roots / "exports").rglob("*.csv"))
    assert list((roots / "raw").rglob("*")), "raw store root was not honored"


@pytest.mark.integration
def test_audit_covers_the_full_governed_session(organization_id: uuid.UUID) -> None:
    snapshot_id = extract_lms(organization_id)
    call(
        "POST",
        "/api/v1/validations",
        organization_id,
        {
            "snapshot_id": snapshot_id,
            "validation_set_id": "participation_v1",
            "mapping_id": "lms_participation_v1",
        },
    )
    match = call(
        "POST",
        "/api/v1/matches/deterministic/synthetic",
        organization_id,
        {"match_config_id": "person_v1"},
    )
    assert match.status_code == 200, match.text
    audit = call("GET", "/api/v1/audit", organization_id)
    assert audit.status_code == 200, audit.text
    actions = {event["action"] for event in audit.json()}
    assert {
        "ingestion.completed",
        "validation.completed",
        "matching.deterministic.completed",
        "mapping.previewed",
        "mart.created",
        "export.created",
    } <= actions


@pytest.mark.integration
def test_write_endpoints_reject_the_viewer_role(organization_id: uuid.UUID) -> None:
    async def run() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        headers = {"X-Demo-User": "demo-viewer", "X-Organization-ID": str(organization_id)}
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(
                "POST",
                "/api/v1/sources/demo_lms/extract",
                headers=headers,
                json={"object_key": "participation"},
            )

    response = asyncio.run(run())
    assert response.status_code == 403
