import time
import uuid
from dataclasses import dataclass
from typing import Any, Protocol

from eduwork_databridge.connectors.base import ConnectorError


@dataclass(frozen=True)
class Actor:
    actor_id: uuid.UUID
    subject: str
    display_name: str
    organization_ids: frozenset[str]
    roles: frozenset[str]
    permissions: frozenset[str]
    authentication_method: str


class IdentityProvider(Protocol):
    def authenticate(self, credential: str | None) -> Actor: ...


class DemoIdentityProvider:
    """Isolated local identity provider. Never enable in production."""

    def __init__(self, enabled: bool, environment: str) -> None:
        self.enabled = enabled
        self.environment = environment

    def authenticate(self, credential: str | None) -> Actor:
        if not self.enabled or self.environment == "production":
            raise ConnectorError("identity_required", "Production identity is required")
        user = credential or "demo-admin"
        if user == "demo-admin":
            return Actor(
                actor_id=uuid.uuid5(uuid.NAMESPACE_URL, "eduwork:demo-admin"),
                subject="demo-admin",
                display_name="Demo Administrator",
                organization_ids=frozenset({"*"}),
                roles=frozenset({"administrator"}),
                permissions=frozenset(
                    {
                        "sources:read",
                        "ingestion:write",
                        "profiles:write",
                        "mappings:write",
                        "validation:write",
                        "matching:write",
                        "marts:write",
                        "exports:write",
                        "lineage:read",
                        "audit:read",
                        "retention:write",
                    }
                ),
                authentication_method="demo",
            )
        if user == "demo-viewer":
            return Actor(
                actor_id=uuid.uuid5(uuid.NAMESPACE_URL, "eduwork:demo-viewer"),
                subject="demo-viewer",
                display_name="Demo Viewer",
                organization_ids=frozenset({"*"}),
                roles=frozenset({"viewer"}),
                permissions=frozenset({"sources:read", "lineage:read"}),
                authentication_method="demo",
            )
        raise ConnectorError("identity_invalid", "Demo identity is invalid")


class OIDCClaimsAdapter:
    """Converts already signature-verified OIDC claims into an Actor."""

    def __init__(self, issuer: str, audience: str) -> None:
        self.issuer = issuer
        self.audience = audience

    def claims_to_actor(self, claims: dict[str, Any]) -> Actor:
        if claims.get("iss") != self.issuer:
            raise ConnectorError("oidc_issuer_invalid", "OIDC issuer is invalid")
        audience = claims.get("aud")
        audiences = {audience} if isinstance(audience, str) else set(audience or [])
        if self.audience not in audiences:
            raise ConnectorError("oidc_audience_invalid", "OIDC audience is invalid")
        if int(claims.get("exp", 0)) <= int(time.time()):
            raise ConnectorError("oidc_token_expired", "OIDC token is expired")
        subject = str(claims.get("sub", ""))
        if not subject:
            raise ConnectorError("oidc_subject_missing", "OIDC subject is missing")
        return Actor(
            actor_id=uuid.uuid5(uuid.NAMESPACE_URL, f"eduwork:oidc:{self.issuer}:{subject}"),
            subject=subject,
            display_name=str(claims.get("name", subject)),
            organization_ids=frozenset(str(value) for value in claims.get("eduwork_orgs", [])),
            roles=frozenset(str(value) for value in claims.get("eduwork_roles", [])),
            permissions=frozenset(str(value) for value in claims.get("eduwork_permissions", [])),
            authentication_method="oidc",
        )
