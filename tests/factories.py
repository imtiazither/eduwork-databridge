import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from eduwork_databridge.db import Base
from eduwork_databridge.db.models.control import (
    IngestionRun,
    RawSnapshot,
    SourceObject,
    SourceSystem,
)
from eduwork_databridge.db.models.core import Organization
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def build_snapshot_session(
    tmp_path: Path,
    records: list[dict],
) -> tuple[Session, uuid.UUID, uuid.UUID]:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'control.db'}")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    session = session_factory()
    organization = Organization(name="Synthetic Org", organization_type="employer", status="active")
    session.add(organization)
    session.flush()
    source = SourceSystem(
        organization_id=organization.id,
        source_key="synthetic_json",
        name="Synthetic JSON",
        connector_type="json",
    )
    session.add(source)
    session.flush()
    source_object = SourceObject(
        source_system_id=source.id,
        object_key="records",
        object_type="file",
        location_template="synthetic.json",
    )
    session.add(source_object)
    session.flush()
    run = IngestionRun(
        organization_id=organization.id,
        source_system_id=source.id,
        status="succeeded",
        started_at=datetime.now(UTC),
        ended_at=datetime.now(UTC),
        cursor_json={},
        correlation_id=str(uuid.uuid4()),
    )
    session.add(run)
    session.flush()
    raw = (json.dumps(records, sort_keys=True) + "\n").encode()
    path = tmp_path / "snapshot.json"
    path.write_bytes(raw)
    snapshot = RawSnapshot(
        ingestion_run_id=run.id,
        source_object_id=source_object.id,
        storage_uri=path.resolve().as_uri(),
        checksum_sha256=hashlib.sha256(raw).hexdigest(),
        row_count=len(records),
        schema_fingerprint="synthetic",
        manifest_json={"content_type": "application/json"},
    )
    session.add(snapshot)
    session.commit()
    return session, organization.id, snapshot.id
