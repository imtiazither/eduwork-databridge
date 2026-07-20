import asyncio
from collections.abc import Generator
from pathlib import Path

import httpx
from eduwork_databridge.db.models.control import LineageNode
from eduwork_databridge.db.session import get_session
from eduwork_databridge.main import app
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.factories import build_snapshot_session


async def request(
    method: str,
    path: str,
    organization_id: str,
    payload: dict | None = None,
    user: str = "demo-admin",
) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(
            method,
            path,
            headers={"X-Organization-ID": organization_id, "X-Demo-User": user},
            json=payload,
        )


def test_phase9_to_12_api_paths_and_authorization(tmp_path: Path) -> None:
    session, organization_id, _ = build_snapshot_session(tmp_path, [{"id": "seed"}])

    def override_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        me = asyncio.run(request("GET", "/api/v1/me", str(organization_id), user="demo-viewer"))
        assert me.status_code == 200
        assert me.json()["roles"] == ["viewer"]

        probabilistic = asyncio.run(
            request(
                "POST",
                "/api/v1/matches/probabilistic/synthetic",
                str(organization_id),
                {
                    "match_config_id": "person_probabilistic_v1",
                    "dataset_preset": "small",
                },
            )
        )
        assert probabilistic.status_code == 200, probabilistic.text
        assert probabilistic.json()["status_counts"]["review"] == 29
        assert probabilistic.json()["metrics"]["auto_precision"] == 1.0

        mart_records = [
            {
                "source_record_key": "A-1",
                "person_external_id": "E-1",
                "offering_external_id": "C-1",
                "status": "completed",
                "assigned_at": "2026-01-01T00:00:00+00:00",
                "completed_at": "2026-01-05T00:00:00+00:00",
                "progress_percent": 100,
                "updated_at": "2026-01-05T00:00:00+00:00",
            }
        ]
        mart = asyncio.run(
            request(
                "POST",
                "/api/v1/marts",
                str(organization_id),
                {
                    "mart_config_id": "training_participation_v1",
                    "records": mart_records,
                    "lineage": {"source": "synthetic-api-test"},
                },
            )
        )
        assert mart.status_code == 200, mart.text
        mart_id = mart.json()["mart_snapshot_id"]

        forbidden = asyncio.run(
            request(
                "POST",
                "/api/v1/exports",
                str(organization_id),
                {
                    "mart_snapshot_id": mart_id,
                    "export_config_id": "training_participation_csv_v1",
                },
                user="demo-viewer",
            )
        )
        assert forbidden.status_code == 403

        export = asyncio.run(
            request(
                "POST",
                "/api/v1/exports",
                str(organization_id),
                {
                    "mart_snapshot_id": mart_id,
                    "export_config_id": "training_participation_csv_v1",
                },
            )
        )
        assert export.status_code == 200, export.text
        assert export.json()["row_count"] == 1

        node = session.scalar(select(LineageNode).where(LineageNode.namespace == "eduwork.export"))
        assert node is not None
        lineage = asyncio.run(request("GET", f"/api/v1/lineage/{node.id}", str(organization_id)))
        assert lineage.status_code == 200
        assert lineage.json()["edges"]

        asset = asyncio.run(
            request(
                "POST",
                "/api/v1/orchestration/runs",
                str(organization_id),
                {
                    "asset_key": "training_mart",
                    "partition_key": "2026-07-20",
                    "watermark": {"updated_at": "2026-07-20T00:00:00Z"},
                },
            )
        )
        assert asset.status_code == 200, asset.text
        assert asset.json()["status"] == "succeeded"

        retention = asyncio.run(
            request(
                "POST",
                "/api/v1/retention/apply",
                str(organization_id),
                {"policy_id": "default_v1", "dry_run": True},
            )
        )
        assert retention.status_code == 200
        assert retention.json()["dry_run"] is True

        audit = asyncio.run(request("GET", "/api/v1/audit", str(organization_id)))
        assert audit.status_code == 200
        assert {item["action"] for item in audit.json()} >= {
            "matching.probabilistic.completed",
            "mart.created",
            "export.created",
            "orchestration.asset.completed",
            "retention.applied",
        }
    finally:
        app.dependency_overrides.clear()
        session.close()
