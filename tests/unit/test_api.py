import asyncio

import httpx
from eduwork_databridge.main import app


async def request(method: str, path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path)


def test_health_and_version() -> None:
    health = asyncio.run(request("GET", "/healthz"))
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    version = asyncio.run(request("GET", "/api/v1/version"))
    assert version.status_code == 200
    assert version.json()["maturity"] == "release-candidate"
    assert version.json()["completed_phases"] == list(range(15))


def test_sources_requires_explicit_organization_scope() -> None:
    response = asyncio.run(request("GET", "/api/v1/sources"))
    assert response.status_code == 400


def test_file_source_connection_and_discovery() -> None:
    connection = asyncio.run(request("POST", "/api/v1/sources/demo_hris/test"))
    assert connection.status_code == 200
    assert connection.json()["ok"] is True
    discovery = asyncio.run(request("GET", "/api/v1/sources/demo_hris/objects/employees/discover"))
    assert discovery.status_code == 200
    field_names = {field["name"] for field in discovery.json()["fields"]}
    assert {"employee_id", "display_name", "updated_at"} <= field_names
