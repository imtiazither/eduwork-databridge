import asyncio
import uuid
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from threading import Barrier

import httpx
import pytest
from eduwork_databridge.connectors import ConnectorError
from eduwork_databridge.db.models.control import (
    AuditEvent,
    IngestionRun,
    MatchCandidate,
    MatchDecision,
    MatchRuleSet,
    QuarantineRecord,
    RawSnapshot,
    SchemaProfile,
    SourceObject,
    SourceSystem,
)
from eduwork_databridge.db.models.core import Organization
from eduwork_databridge.db.session import get_session
from eduwork_databridge.main import app
from eduwork_databridge.matching import DeterministicMatchService
from eduwork_databridge.security import AuditService, DemoIdentityProvider, get_actor
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tests.factories import build_snapshot_session


@pytest.fixture
def review_environment(tmp_path: Path):
    session, organization_id, snapshot_id = build_snapshot_session(tmp_path, [{"employee_id": ""}])
    rule = MatchRuleSet(
        organization_id=organization_id,
        rule_set_key="review-test",
        version="1.0",
        entity_type="Person",
        deterministic_rules_json=[],
        probabilistic_config_json={},
        status="active",
    )
    session.add(rule)
    session.flush()
    candidates = [
        MatchCandidate(
            organization_id=organization_id,
            rule_set_id=rule.id,
            left_record_key=left,
            right_record_key=right,
            status=status,
            evidence_json={"rule_id": "exact_id", "fingerprints": {"employee_id": "sha256:masked"}},
        )
        for left, right, status in [
            ("HR-100%", "LMS-1", "review"),
            ("HR-2", "LMS-2", "auto_match"),
            ("HR-3", "LMS-3", "trusted_id_conflict"),
        ]
    ]
    session.add_all(candidates)
    session.commit()

    def override_session() -> Generator[Session, None, None]:
        with Session(session.get_bind(), expire_on_commit=False) as request_session:
            yield request_session

    app.dependency_overrides[get_session] = override_session
    yield session, organization_id, snapshot_id, candidates
    app.dependency_overrides.clear()
    session.close()


def call(method: str, path: str, org: uuid.UUID, payload=None, user="demo-admin"):
    async def run():
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        headers = {"X-Organization-ID": str(org)}
        if user is not None:
            headers["X-Demo-User"] = user
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path, headers=headers, json=payload)

    return asyncio.run(run())


def test_queue_filters_literal_search_and_bounded_history(review_environment):
    _, org, _, candidates = review_environment
    summary = call("GET", "/api/v1/matches/review-queue/summary", org).json()
    assert summary["needs_review_candidates"] == 2
    assert summary["unreviewed_candidates"] == 3
    needed = call("GET", "/api/v1/matches/review-queue?needs_review=true", org).json()
    assert {item["status"] for item in needed} == {"review", "trusted_id_conflict"}
    literal = call("GET", "/api/v1/matches/review-queue?q=%25", org).json()
    assert [item["left_record_key"] for item in literal] == ["HR-100%"]
    assert len(call("GET", "/api/v1/matches/review-queue?q=hr", org).json()) == 3
    candidate = candidates[0]
    for revision in range(3):
        saved = call(
            "POST",
            f"/api/v1/matches/{candidate.id}/decisions",
            org,
            {
                "decision": "defer",
                "reason": f"Evidence review {revision}",
                "expected_revision": revision,
            },
        )
        assert saved.status_code == 200, saved.text
        assert saved.json()["revision"] == revision + 1
    assert len(call("GET", "/api/v1/matches/review-queue?unreviewed=true", org).json()) == 2
    history = call("GET", f"/api/v1/matches/{candidate.id}/decisions?limit=1&offset=1", org)
    assert [item["revision"] for item in history.json()] == [2]
    for query in ["limit=201", "offset=-1", "status=unknown", "q=" + "x" * 101]:
        assert call("GET", f"/api/v1/matches/review-queue?{query}", org).status_code == 422


def test_stale_decisions_do_not_change_history_or_audit(review_environment):
    session, org, _, candidates = review_environment
    path = f"/api/v1/matches/{candidates[0].id}/decisions"
    payload = {"decision": "defer", "reason": "Needs source confirmation", "expected_revision": 0}
    first = call("POST", path, org, payload)
    assert first.status_code == 200
    stale = call("POST", path, org, {**payload, "decision": "match"})
    assert stale.status_code == 409
    assert stale.json()["detail"]["code"] == "decision_conflict"
    assert session.scalar(select(func.count()).select_from(MatchDecision)) == 1
    assert session.scalar(select(func.count()).select_from(AuditEvent)) == 1
    queue = call("GET", "/api/v1/matches/review-queue?status=defer", org).json()
    assert queue[0]["revision"] == 1
    assert queue[0]["latest_decision"]["id"] == first.json()["id"]
    assert (
        call("POST", path, org, {"decision": "match", "reason": "Missing revision"}).status_code
        == 422
    )


def test_decision_and_audit_roll_back_together(review_environment, monkeypatch):
    session, org, _, candidates = review_environment

    def fail_audit(*args, **kwargs):
        raise RuntimeError("Simulated audit failure")

    monkeypatch.setattr(AuditService, "record", fail_audit)
    response = call(
        "POST",
        f"/api/v1/matches/{candidates[0].id}/decisions",
        org,
        {
            "decision": "match",
            "reason": "Reviewed",
            "expected_revision": 0,
        },
    )
    assert response.status_code == 500
    session.expire_all()
    assert session.get(MatchCandidate, candidates[0].id).revision == 0
    assert session.scalar(select(func.count()).select_from(MatchDecision)) == 0


def test_simultaneous_reviewers_cannot_both_save(review_environment):
    session, org, _, candidates = review_environment
    candidate_id = candidates[0].id
    barrier = Barrier(2)

    def save(reviewer):
        with Session(session.get_bind()) as concurrent_session:
            barrier.wait(timeout=10)
            try:
                DeterministicMatchService(concurrent_session).record_decision(
                    org,
                    candidate_id,
                    "defer",
                    "Concurrent review",
                    reviewer,
                    expected_revision=0,
                )
                return "saved"
            except ConnectorError as exc:
                return exc.code

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(save, [uuid.uuid4(), uuid.uuid4()]))
    assert sorted(results) == ["decision_conflict", "saved"]
    assert session.scalar(select(func.count()).select_from(MatchDecision)) == 1


@pytest.mark.parametrize(
    "method,path,payload",
    [
        ("GET", "/api/v1/organizations", None),
        ("GET", "/api/v1/sources", None),
        ("POST", "/api/v1/sources/demo_hris/test", None),
        ("GET", "/api/v1/sources/demo_hris/objects/employees/discover", None),
        ("POST", "/api/v1/profiles", {"snapshot_id": str(uuid.uuid4())}),
        (
            "POST",
            f"/api/v1/quarantine/{uuid.uuid4()}/resolve",
            {"status": "closed", "note": "Review"},
        ),
    ],
)
def test_protected_routes_require_explicit_identity(review_environment, method, path, payload):
    _, org, _, _ = review_environment
    assert call(method, path, org, payload, user=None).status_code == 401


def test_tenant_scope_is_checked_before_snapshot_io(review_environment, monkeypatch):
    session, org, snapshot, candidates = review_environment
    other = Organization(name="Other", organization_type="employer", status="active")
    session.add(other)
    session.commit()

    def forbidden_read(*args):
        pytest.fail("Foreign snapshot must never be read")

    monkeypatch.setattr("eduwork_databridge.main.read_snapshot_records", forbidden_read)
    routes = [
        ("/api/v1/profiles", {"snapshot_id": str(snapshot)}),
        (
            "/api/v1/mappings/preview",
            {"snapshot_id": str(snapshot), "mapping_id": "hris_person_v1"},
        ),
        ("/api/v1/validations", {"snapshot_id": str(snapshot), "validation_set_id": "person_v1"}),
        (
            "/api/v1/marts",
            {
                "source_snapshot_id": str(snapshot),
                "records": [],
                "mart_config_id": "training_participation_v1",
            },
        ),
    ]
    for path, payload in routes:
        assert call("POST", path, other.id, payload).status_code == 404
    assert call("GET", f"/api/v1/matches/{candidates[0].id}/decisions", other.id).status_code == 400
    actor = replace(
        DemoIdentityProvider(True, "test").authenticate("demo-admin"),
        organization_ids=frozenset({str(org)}),
    )
    app.dependency_overrides[get_actor] = lambda: actor
    organizations = call("GET", "/api/v1/organizations", org).json()
    assert [item["id"] for item in organizations] == [str(org)]
    assert call("GET", "/api/v1/sources", other.id).status_code == 403
    assert call("POST", "/api/v1/sources/demo_hris/test", other.id).status_code == 403


def test_profile_and_quarantine_permissions_and_actor_attribution(review_environment):
    session, org, snapshot, _ = review_environment
    assert (
        call(
            "POST", "/api/v1/profiles", org, {"snapshot_id": str(snapshot)}, user="demo-viewer"
        ).status_code
        == 403
    )
    validation = call(
        "POST",
        "/api/v1/validations",
        org,
        {"snapshot_id": str(snapshot), "validation_set_id": "person_v1"},
    )
    quarantine_id = validation.json()["quarantine_ids"][0]
    path = f"/api/v1/quarantine/{quarantine_id}/resolve"
    assert (
        call(
            "POST", path, org, {"status": "waived", "note": "Source reviewed"}, user="demo-viewer"
        ).status_code
        == 403
    )
    assert (
        call(
            "POST",
            path,
            org,
            {"status": "waived", "note": "Source reviewed", "reviewer_id": str(uuid.uuid4())},
        ).status_code
        == 422
    )
    resolved = call("POST", path, org, {"status": "waived", "note": "Source reviewed"})
    assert resolved.status_code == 200
    row = session.get(QuarantineRecord, uuid.UUID(quarantine_id))
    assert row.reviewer_id == DemoIdentityProvider(True, "test").authenticate("demo-admin").actor_id
    audit = session.scalar(select(AuditEvent).where(AuditEvent.action == "quarantine.resolved"))
    assert audit.actor_id == row.reviewer_id


def test_foreign_profile_baseline_cannot_be_compared(review_environment):
    session, org, snapshot, _ = review_environment
    other = Organization(name="Baseline owner", organization_type="employer", status="active")
    session.add(other)
    session.flush()
    source = SourceSystem(
        organization_id=other.id, source_key="foreign", name="Foreign", connector_type="json"
    )
    session.add(source)
    session.flush()
    source_object = SourceObject(
        source_system_id=source.id, object_key="records", object_type="file"
    )
    run = IngestionRun(
        organization_id=other.id,
        source_system_id=source.id,
        status="succeeded",
        started_at=datetime.now(UTC),
        correlation_id=str(uuid.uuid4()),
    )
    session.add_all([source_object, run])
    session.flush()
    foreign = RawSnapshot(
        source_object_id=source_object.id,
        ingestion_run_id=run.id,
        storage_uri="file:///unreadable-foreign.json",
        checksum_sha256="a" * 64,
    )
    session.add(foreign)
    session.flush()
    baseline = SchemaProfile(
        raw_snapshot_id=foreign.id,
        profile_version="1",
        profile_json={"private": "must not compare"},
    )
    session.add(baseline)
    session.commit()
    response = call(
        "POST",
        "/api/v1/profiles",
        org,
        {"snapshot_id": str(snapshot), "baseline_profile_id": str(baseline.id)},
    )
    assert response.status_code == 400
    assert "outside organization scope" in response.text
    assert session.scalar(select(func.count()).select_from(SchemaProfile)) == 1
