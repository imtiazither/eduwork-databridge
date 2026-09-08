import asyncio
from collections.abc import Generator

import httpx
from eduwork_databridge.db.session import get_session
from eduwork_databridge.main import app
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


def test_match_decisions_are_reasoned_reversible_and_audited(tmp_path) -> None:
    session, organization_id, _ = build_snapshot_session(tmp_path, [{"id": "seed"}])

    def override_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        match = asyncio.run(
            request(
                "POST",
                "/api/v1/matches/deterministic/synthetic",
                str(organization_id),
                {"match_config_id": "person_v1"},
            )
        )
        assert match.status_code == 200, match.text
        candidate_id = match.json()["candidate_ids"][0]
        candidate_count = len(match.json()["candidate_ids"])

        queue = asyncio.run(
            request("GET", "/api/v1/matches/review-queue?limit=1", str(organization_id))
        )
        assert queue.status_code == 200, queue.text
        assert len(queue.json()) == 1
        assert queue.json()[0]["decision_count"] == 0
        assert queue.json()[0]["latest_decision"] is None
        assert set(queue.json()[0]["evidence"]) == {"rule_id", "fingerprints"}

        summary = asyncio.run(
            request("GET", "/api/v1/matches/review-queue/summary", str(organization_id))
        )
        assert summary.status_code == 200, summary.text
        assert summary.json()["total_candidates"] == candidate_count
        assert summary.json()["unreviewed_candidates"] == candidate_count

        viewer_queue = asyncio.run(
            request(
                "GET",
                "/api/v1/matches/review-queue",
                str(organization_id),
                user="demo-viewer",
            )
        )
        assert viewer_queue.status_code == 403

        missing_reason = asyncio.run(
            request(
                "POST",
                f"/api/v1/matches/{candidate_id}/decisions",
                str(organization_id),
                {"decision": "defer", "reason": "   "},
            )
        )
        assert missing_reason.status_code == 400

        first = asyncio.run(
            request(
                "POST",
                f"/api/v1/matches/{candidate_id}/decisions",
                str(organization_id),
                {
                    "decision": "defer",
                    "reason": "Duplicate account needs source-owner review.",
                },
            )
        )
        assert first.status_code == 200, first.text
        first_body = first.json()
        assert first_body["decision"] == "defer"
        assert first_body["supersedes_decision_id"] is None

        viewer = asyncio.run(
            request(
                "POST",
                f"/api/v1/matches/{candidate_id}/decisions",
                str(organization_id),
                {"decision": "match", "reason": "Viewer must not decide."},
                user="demo-viewer",
            )
        )
        assert viewer.status_code == 403

        second = asyncio.run(
            request(
                "POST",
                f"/api/v1/matches/{candidate_id}/decisions",
                str(organization_id),
                {
                    "decision": "no_match",
                    "reason": "Source owner confirmed the accounts are separate.",
                },
            )
        )
        assert second.status_code == 200, second.text
        assert second.json()["supersedes_decision_id"] == first_body["id"]

        decided_queue = asyncio.run(
            request(
                "GET",
                "/api/v1/matches/review-queue?status=no_match",
                str(organization_id),
            )
        )
        assert decided_queue.status_code == 200, decided_queue.text
        assert len(decided_queue.json()) == 1
        assert decided_queue.json()[0]["candidate_id"] == candidate_id
        assert decided_queue.json()[0]["decision_count"] == 2
        assert decided_queue.json()[0]["latest_decision"]["decision"] == "no_match"

        updated_summary = asyncio.run(
            request("GET", "/api/v1/matches/review-queue/summary", str(organization_id))
        )
        assert updated_summary.status_code == 200, updated_summary.text
        assert updated_summary.json()["unreviewed_candidates"] == candidate_count - 1
        assert updated_summary.json()["by_status"]["no_match"] == 1

        history = asyncio.run(
            request("GET", f"/api/v1/matches/{candidate_id}/decisions", str(organization_id))
        )
        assert history.status_code == 200, history.text
        assert [row["decision"] for row in history.json()] == ["no_match", "defer"]

        audit = asyncio.run(request("GET", "/api/v1/audit", str(organization_id)))
        assert audit.status_code == 200, audit.text
        recorded = [item for item in audit.json() if item["action"] == "matching.decision.recorded"]
        assert len(recorded) == 2
        assert {item["details"]["decision"] for item in recorded} == {"defer", "no_match"}
        assert all(item["details"]["candidate_id"] == candidate_id for item in recorded)
    finally:
        app.dependency_overrides.clear()
        session.close()
