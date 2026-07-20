import asyncio
import time
import uuid

import httpx
import pytest
from eduwork_databridge.connectors.base import ConnectorError
from eduwork_databridge.db.models.control import AuditEvent
from eduwork_databridge.security import (
    AuditService,
    DemoIdentityProvider,
    OIDCClaimsAdapter,
    RateLimitMiddleware,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
    require_organization,
    require_permission,
)
from fastapi import FastAPI
from sqlalchemy import select

from tests.factories import build_snapshot_session


def test_demo_and_oidc_identity_boundaries() -> None:
    admin = DemoIdentityProvider(True, "development").authenticate("demo-admin")
    viewer = DemoIdentityProvider(True, "development").authenticate("demo-viewer")
    assert "exports:write" in admin.permissions
    assert "exports:write" not in viewer.permissions
    require_organization(admin, uuid.uuid4())
    with pytest.raises(ConnectorError, match="permission"):
        require_permission(viewer, "exports:write")
    with pytest.raises(ConnectorError, match="Production"):
        DemoIdentityProvider(True, "production").authenticate("demo-admin")

    adapter = OIDCClaimsAdapter("https://issuer.example", "eduwork-api")
    actor = adapter.claims_to_actor(
        {
            "iss": "https://issuer.example",
            "aud": ["eduwork-api"],
            "exp": int(time.time()) + 300,
            "sub": "user-1",
            "eduwork_orgs": ["org-1"],
            "eduwork_roles": ["viewer"],
            "eduwork_permissions": ["lineage:read"],
        }
    )
    assert actor.authentication_method == "oidc"
    assert actor.organization_ids == frozenset({"org-1"})


def test_audit_sanitizes_details(tmp_path) -> None:
    session, organization_id, _ = build_snapshot_session(tmp_path, [{"id": "seed"}])
    actor = DemoIdentityProvider(True, "test").authenticate("demo-admin")
    event = AuditService(session).record(
        actor,
        "export.created",
        "export",
        "E-1",
        organization_id,
        details={"row_count": 10, "secret_token": "hidden", "raw_record": "hidden"},
    )
    stored = session.scalar(select(AuditEvent).where(AuditEvent.id == event.id))
    assert stored is not None
    assert stored.details_json == {"row_count": 10}
    session.close()


def test_security_headers_size_limit_and_rate_limit() -> None:
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestSizeLimitMiddleware, max_bytes=10)
    app.add_middleware(RateLimitMiddleware, requests_per_minute=2)

    @app.post("/echo")
    async def echo() -> dict[str, bool]:
        return {"ok": True}

    async def exercise() -> tuple[httpx.Response, httpx.Response, httpx.Response, httpx.Response]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            first = await client.post("/echo", content=b"a", headers={"X-Demo-User": "one"})
            second = await client.post("/echo", content=b"b", headers={"X-Demo-User": "one"})
            limited = await client.post("/echo", content=b"c", headers={"X-Demo-User": "one"})
            oversized = await client.post(
                "/echo", content=b"01234567890", headers={"X-Demo-User": "two"}
            )
            return first, second, limited, oversized

    first, second, limited, oversized = asyncio.run(exercise())
    assert first.status_code == second.status_code == 200
    assert first.headers["x-content-type-options"] == "nosniff"
    assert limited.status_code == 429
    assert oversized.status_code == 413
