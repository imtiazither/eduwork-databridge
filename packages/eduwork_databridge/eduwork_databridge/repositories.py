import uuid

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from eduwork_databridge.db.models.control import SourceSystem
from eduwork_databridge.db.models.core import Organization


def scoped_statement(
    model: type[SourceSystem], organization_id: uuid.UUID
) -> Select[tuple[SourceSystem]]:
    """Build an explicit organization-scoped statement for organization-owned data."""
    return select(model).where(model.organization_id == organization_id)


def list_organizations(session: Session) -> list[Organization]:
    return list(session.scalars(select(Organization).order_by(Organization.name)))


def list_sources(session: Session, organization_id: uuid.UUID) -> list[SourceSystem]:
    return list(
        session.scalars(scoped_statement(SourceSystem, organization_id).order_by(SourceSystem.name))
    )
