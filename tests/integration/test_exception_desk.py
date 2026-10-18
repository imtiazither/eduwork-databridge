import asyncio
import uuid
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Barrier

import httpx
import pytest
from eduwork_databridge.connectors import ConnectorError
from eduwork_databridge.db.models.control import AuditEvent, QuarantineRecord, QuarantineResolution
from eduwork_databridge.db.models.core import Organization
from eduwork_databridge.db.session import get_session
from eduwork_databridge.main import app
from eduwork_databridge.schemas.config import ValidationConfig, ValidationRuleConfig
from eduwork_databridge.security import AuditService, DemoIdentityProvider, get_actor
from eduwork_databridge.validation import ValidationService
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tests.factories import build_snapshot_session


@pytest.fixture
def exceptions(tmp_path):
    records = [
        {"record_key": "ROW-100%", "employee_id": "", "status": "bad"},
        {"record_key": "ROW-2", "employee_id": "", "status": "active"},
    ]
    session, org, snapshot = build_snapshot_session(tmp_path, records)
    config = ValidationConfig(
        validation_set_id="desk",
        entity="Person",
        rules=[
            ValidationRuleConfig(
                rule_id="required_id",
                title="Missing employee ID",
                entity="Person",
                severity="blocking",
                rule_type="required",
                fields=["employee_id"],
                explanation="An employee ID is required.",
                remediation="Ask the source owner to correct it.",
            ),
            ValidationRuleConfig(
                rule_id="status",
                title="Unexpected status",
                entity="Person",
                severity="warning",
                rule_type="allowed_values",
                fields=["status"],
                parameters={"values": ["active"]},
                explanation="Use the agreed status codes.",
            ),
        ],
    )
    outcome = ValidationService(session).validate(org, snapshot, records, config)

    def override_session() -> Generator[Session, None, None]:
        with Session(session.get_bind(), expire_on_commit=False) as request_session:
            yield request_session

    app.dependency_overrides[get_session] = override_session
    yield session, org, snapshot, outcome.quarantine_ids
    app.dependency_overrides.clear()
    session.close()


def call(method, path, org, payload=None, user="demo-admin"):
    async def run():
        headers = {"X-Organization-ID": str(org)}
        if user:
            headers["X-Demo-User"] = user
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as client:
            return await client.request(method, path, headers=headers, json=payload)

    return asyncio.run(run())


def test_queue_filters_literal_search_and_bounds(exceptions):
    _, org, snapshot, _ = exceptions
    summary = call("GET", "/api/v1/quarantine/summary", org).json()
    assert summary == {
        "total": 3,
        "needs_attention": 3,
        "by_status": {"open": 3},
        "by_severity": {"blocking": 2, "warning": 1},
    }
    queue = call("GET", "/api/v1/quarantine?severity=blocking&limit=1", org).json()
    assert len(queue) == 1 and queue[0]["raw_snapshot_id"] == str(snapshot)
    assert queue[0]["rule_key"] == "required_id" and queue[0]["remediation"]
    assert "storage_uri" not in queue[0]
    next_page = call("GET", "/api/v1/quarantine?severity=blocking&limit=1&offset=1", org).json()
    assert next_page[0]["quarantine_id"] != queue[0]["quarantine_id"]
    assert len(call("GET", "/api/v1/quarantine?q=%25", org).json()) == 2
    assert len(call("GET", "/api/v1/quarantine?q=missing", org).json()) == 2
    assert call("GET", "/api/v1/quarantine?status=closed", org).json() == []
    for query in [
        "limit=201",
        "limit=0",
        "offset=-1",
        "status=no",
        "severity=no",
        "q=" + "x" * 101,
    ]:
        assert call("GET", f"/api/v1/quarantine?{query}", org).status_code == 422


def test_save_history_reopen_and_summary(exceptions):
    session, org, snapshot, ids = exceptions
    path = f"/api/v1/quarantine/{ids[0]}"
    for revision, status in enumerate(["acknowledged", "waived", "open"]):
        saved = call(
            "POST",
            path + "/resolve",
            org,
            {
                "status": status,
                "note": f"Review {revision}",
                "expected_revision": revision,
                "corrected_snapshot_id": str(snapshot),
            },
        )
        assert saved.status_code == 200, saved.text
        assert saved.json()["revision"] == revision + 1
        assert saved.json()["recorded_at"].endswith("Z")
        assert saved.json()["reviewer_id"] == str(
            DemoIdentityProvider(True, "test").authenticate("demo-admin").actor_id
        )
        assert call("GET", "/api/v1/quarantine/summary", org).json()["needs_attention"] == (
            2 if status == "waived" else 3
        )
    history = call("GET", path + "/history", org).json()
    assert [item["note"] for item in history] == ["Review 2", "Review 1", "Review 0"]
    assert all(not item["imported"] for item in history)
    assert [
        item["revision"] for item in call("GET", path + "/history?limit=1&offset=1", org).json()
    ] == [2]
    session.expire_all()
    assert session.get(QuarantineRecord, ids[0]).resolved_at is None
    assert session.scalar(select(func.count()).select_from(AuditEvent)) == 3
    assert "Review 2" not in str(session.scalars(select(AuditEvent.details_json)).all())


def test_conflict_and_invalid_requests_do_not_append(exceptions):
    session, org, _, ids = exceptions
    path = f"/api/v1/quarantine/{ids[0]}/resolve"
    payload = {"status": "closed", "note": "Checked the source", "expected_revision": 0}
    assert call("POST", path, org, payload).status_code == 200
    stale = call("POST", path, org, payload)
    assert stale.status_code == 409 and stale.json()["detail"]["code"] == "quarantine_conflict"
    assert session.scalar(select(func.count()).select_from(QuarantineResolution)) == 1
    assert session.scalar(select(func.count()).select_from(AuditEvent)) == 1
    for invalid in [
        {"status": "closed", "note": "No revision"},
        {**payload, "expected_revision": -1},
        {**payload, "note": " "},
        {**payload, "note": "x" * 2001},
        {**payload, "status": "unknown"},
        {**payload, "reviewer_id": str(uuid.uuid4())},
    ]:
        assert call("POST", path, org, invalid).status_code in {400, 422}


def test_resolution_and_audit_are_atomic(exceptions, monkeypatch):
    session, org, _, ids = exceptions

    def fail_audit(*args, **kwargs):
        raise RuntimeError("Audit unavailable")

    monkeypatch.setattr(AuditService, "record", fail_audit)
    assert (
        call(
            "POST",
            f"/api/v1/quarantine/{ids[0]}/resolve",
            org,
            {"status": "closed", "note": "Review", "expected_revision": 0},
        ).status_code
        == 500
    )
    session.expire_all()
    assert session.get(QuarantineRecord, ids[0]).revision == 0
    assert session.scalar(select(func.count()).select_from(QuarantineResolution)) == 0


def test_competing_exception_reviewers(exceptions):
    session, org, _, ids = exceptions
    barrier = Barrier(2)

    def save(reviewer):
        with Session(session.get_bind()) as concurrent:
            barrier.wait(timeout=10)
            try:
                ValidationService(concurrent).resolve_quarantine(
                    org,
                    ids[0],
                    "acknowledged",
                    reviewer,
                    "Source owner contacted",
                    expected_revision=0,
                )
                return "saved"
            except ConnectorError as exc:
                return exc.code

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(save, [uuid.uuid4(), uuid.uuid4()]))
    assert sorted(results) == ["quarantine_conflict", "saved"]
    assert session.scalar(select(func.count()).select_from(QuarantineResolution)) == 1


def test_exception_access_and_foreign_snapshots(exceptions):
    session, org, _, ids = exceptions
    other = Organization(name="Other", organization_type="employer", status="active")
    session.add(other)
    session.commit()
    root = f"/api/v1/quarantine/{ids[0]}"
    payload = {"status": "closed", "note": "Review", "expected_revision": 0}
    for method, path, body in [
        ("GET", "/api/v1/quarantine", None),
        ("GET", "/api/v1/quarantine/summary", None),
        ("GET", root + "/history", None),
        ("POST", root + "/resolve", payload),
    ]:
        assert call(method, path, org, body, user=None).status_code == 401
        assert call(method, path, org, body, user="demo-viewer").status_code == 403
    assert call("GET", "/api/v1/quarantine", other.id).json() == []
    assert call("GET", root + "/history", other.id).status_code == 404
    assert call("POST", root + "/resolve", other.id, payload).status_code == 404
    assert (
        call(
            "POST", root + "/resolve", org, {**payload, "corrected_snapshot_id": str(uuid.uuid4())}
        ).status_code
        == 400
    )
    actor = replace(
        DemoIdentityProvider(True, "test").authenticate("demo-admin"),
        organization_ids=frozenset({str(org)}),
    )
    app.dependency_overrides[get_actor] = lambda: actor
    assert call("GET", "/api/v1/quarantine", other.id).status_code == 403
