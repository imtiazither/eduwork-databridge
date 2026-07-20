import uuid

from eduwork_databridge.connectors.base import ConnectorError
from eduwork_databridge.security.identity import Actor


def require_organization(actor: Actor, organization_id: uuid.UUID) -> None:
    if "*" not in actor.organization_ids and str(organization_id) not in actor.organization_ids:
        raise ConnectorError("organization_forbidden", "Actor cannot access this organization")


def require_permission(actor: Actor, permission: str) -> None:
    if permission not in actor.permissions:
        raise ConnectorError("permission_forbidden", "Actor lacks the required permission")
