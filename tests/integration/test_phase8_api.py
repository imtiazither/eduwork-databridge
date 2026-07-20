import asyncio
from collections.abc import Generator
from pathlib import Path

import httpx
from eduwork_databridge.db.session import get_session
from eduwork_databridge.main import app
from sqlalchemy.orm import Session

from tests.factories import build_snapshot_session


async def api_request(
    method: str,
    path: str,
    organization_id: str,
    payload: dict | None = None,
) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(
            method,
            path,
            headers={"X-Organization-ID": organization_id},
            json=payload,
        )


def test_phase5_to_8_api_paths(tmp_path: Path) -> None:
    records = [
        {
            "employee_id": "E-1",
            "display_name": "Amina Adams",
            "given_name": "Amina",
            "family_name": "Adams",
            "email": "amina@example.test",
            "department_code": "TECHNOLOGY",
            "employment_status": "active",
            "updated_at": "2026-07-10T00:00:00+00:00",
        },
        {
            "employee_id": "",
            "display_name": "Missing ID",
            "given_name": "Missing",
            "family_name": "ID",
            "email": "missing@example.test",
            "department_code": "OPS",
            "employment_status": "active",
            "updated_at": "2026-07-10T00:00:00+00:00",
        },
    ]
    session, organization_id, snapshot_id = build_snapshot_session(tmp_path, records)

    def override_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        profile = asyncio.run(
            api_request(
                "POST",
                "/api/v1/profiles",
                str(organization_id),
                {"snapshot_id": str(snapshot_id), "profile_config_id": "default_v1"},
            )
        )
        assert profile.status_code == 200, profile.text
        assert profile.json()["schema_fingerprint"]

        mapping = asyncio.run(
            api_request(
                "POST",
                "/api/v1/mappings/preview",
                str(organization_id),
                {
                    "snapshot_id": str(snapshot_id),
                    "mapping_id": "hris_person_v1",
                    "lookup_ids": ["employment_status_v1"],
                    "preview_limit": 25,
                },
            )
        )
        assert mapping.status_code == 200, mapping.text
        assert mapping.json()["output_count"] == 1
        assert mapping.json()["error_count"] >= 1

        validation = asyncio.run(
            api_request(
                "POST",
                "/api/v1/validations",
                str(organization_id),
                {
                    "snapshot_id": str(snapshot_id),
                    "validation_set_id": "person_v1",
                    "reference_sets": {},
                },
            )
        )
        assert validation.status_code == 200, validation.text
        assert validation.json()["issue_count"] >= 1

        matching = asyncio.run(
            api_request(
                "POST",
                "/api/v1/matches/deterministic/synthetic",
                str(organization_id),
                {"match_config_id": "person_v1", "dataset_preset": "small"},
            )
        )
        assert matching.status_code == 200, matching.text
        assert matching.json()["metrics"]["precision"] >= 0.8
    finally:
        app.dependency_overrides.clear()
        session.close()
