import uuid

from eduwork_databridge.db import Base
from eduwork_databridge.db.models.control import SourceSystem
from eduwork_databridge.db.models.core import Organization
from eduwork_databridge.repositories import list_sources
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session


def test_metadata_creates_and_scopes_sources() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        left = Organization(name="Left", organization_type="employer", status="active")
        right = Organization(name="Right", organization_type="employer", status="active")
        session.add_all([left, right])
        session.flush()
        session.add_all(
            [
                SourceSystem(
                    organization_id=left.id, source_key="lms", name="Left LMS", connector_type="csv"
                ),
                SourceSystem(
                    organization_id=right.id,
                    source_key="lms",
                    name="Right LMS",
                    connector_type="csv",
                ),
            ]
        )
        session.commit()
        scoped = list_sources(session, left.id)
        assert [item.name for item in scoped] == ["Left LMS"]
        assert session.scalar(
            select(Organization).where(Organization.id == uuid.UUID(str(left.id)))
        )
    engine.dispose()
