import asyncio
from collections.abc import Generator

import httpx
from eduwork_databridge.db.models.control import SourceSystem
from eduwork_databridge.db.session import get_session
from eduwork_databridge.main import app
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.factories import build_snapshot_session


async def request(method: str, path: str, headers: dict[str, str] | None = None) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path, headers=headers)


def test_health_and_version() -> None:
    health = asyncio.run(request("GET", "/healthz"))
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    version = asyncio.run(request("GET", "/api/v1/version"))
    assert version.status_code == 200
    assert version.json() == {"version": "0.50.0"}


def test_demo_summary_comes_from_public_synthetic_manifest() -> None:
    response = asyncio.run(request("GET", "/api/v1/demo/summary"))
    assert response.status_code == 200
    summary = response.json()
    assert summary["synthetic"] is True
    assert summary["counts"]["hris_people"] == 120
    assert summary["counts"]["lms_participations"] == 366
    assert summary["defect_summary"]["missing_employee_id"] == 9


def test_local_reviewer_origin_is_allowed() -> None:
    response = asyncio.run(
        request(
            "OPTIONS",
            "/api/v1/demo/summary",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_sources_requires_explicit_organization_scope() -> None:
    response = asyncio.run(request("GET", "/api/v1/sources", {"X-Demo-User": "demo-admin"}))
    assert response.status_code == 400


def test_file_source_connection_and_discovery(tmp_path) -> None:
    session, organization_id, _ = build_snapshot_session(tmp_path, [])
    source = session.scalar(select(SourceSystem))
    assert source is not None
    source.source_key = "demo_hris"
    session.commit()

    def override_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_session] = override_session
    headers = {"X-Demo-User": "demo-admin", "X-Organization-ID": str(organization_id)}
    try:
        connection = asyncio.run(request("POST", "/api/v1/sources/demo_hris/test", headers))
        assert connection.status_code == 200
        assert connection.json()["ok"] is True
        discovery = asyncio.run(
            request("GET", "/api/v1/sources/demo_hris/objects/employees/discover", headers)
        )
        assert discovery.status_code == 200
        field_names = {field["name"] for field in discovery.json()["fields"]}
        assert {"employee_id", "display_name", "updated_at"} <= field_names
    finally:
        app.dependency_overrides.clear()
        session.close()
