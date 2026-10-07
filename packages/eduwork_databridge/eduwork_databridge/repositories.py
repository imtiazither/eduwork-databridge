import uuid

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from eduwork_databridge.connectors import ConnectorError
from eduwork_databridge.db.models.control import RawSnapshot, SourceObject, SourceSystem
from eduwork_databridge.db.models.core import Organization


def scoped_statement(
    model: type[SourceSystem], organization_id: uuid.UUID
) -> Select[tuple[SourceSystem]]:
    """Build an explicit organization-scoped statement for organization-owned data."""
    return select(model).where(model.organization_id == organization_id)


def list_organizations(
    session: Session, organization_ids: frozenset[str] | None = None
) -> list[Organization]:
    query = select(Organization).order_by(Organization.name)
    if organization_ids is not None and "*" not in organization_ids:
        allowed = [uuid.UUID(value) for value in organization_ids if _is_uuid(value)]
        query = query.where(Organization.id.in_(allowed))
    return list(session.scalars(query))


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True


def get_scoped_source(session: Session, organization_id: uuid.UUID, key: str) -> SourceSystem:
    source = session.scalar(
        scoped_statement(SourceSystem, organization_id).where(
            SourceSystem.source_key == key, SourceSystem.active.is_(True)
        )
    )
    if source is None:
        raise ConnectorError("source_not_found", "Source was not found")
    return source


def get_scoped_snapshot(
    session: Session, organization_id: uuid.UUID, snapshot_id: uuid.UUID
) -> RawSnapshot:
    snapshot = session.scalar(
        select(RawSnapshot)
        .join(SourceObject, RawSnapshot.source_object_id == SourceObject.id)
        .join(SourceSystem, SourceObject.source_system_id == SourceSystem.id)
        .where(RawSnapshot.id == snapshot_id, SourceSystem.organization_id == organization_id)
    )
    if snapshot is None:
        raise ConnectorError("snapshot_not_found", "Raw snapshot was not found")
    return snapshot


def list_sources(session: Session, organization_id: uuid.UUID) -> list[SourceSystem]:
    return list(
        session.scalars(scoped_statement(SourceSystem, organization_id).order_by(SourceSystem.name))
    )
