import asyncio
import uuid
from pathlib import Path

import pytest
from eduwork_databridge.connectors.base import ConnectorError
from eduwork_databridge.db import Base
from eduwork_databridge.db.models.control import (
    IngestionRun,
    RawSnapshot,
    SourceObject,
    SourceSystem,
)
from eduwork_databridge.db.models.core import Organization
from eduwork_databridge.ingestion.service import IngestionService
from eduwork_databridge.settings import Settings
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker


def build_service(
    tmp_path: Path, source_id: str, location: Path
) -> tuple[IngestionService, Session, uuid.UUID]:
    config_root = tmp_path / "configs"
    source_dir = config_root / "sources"
    source_dir.mkdir(parents=True)
    source_dir.joinpath(f"{source_id}.yml").write_text(
        f"""schema_version: "1.0"
source_id: {source_id}
name: Synthetic CSV
connector: csv
owner_role: Test Steward
data_classification: internal
allowed_roots: [{tmp_path / "allowed"}]
objects:
  - key: employees
    object_type: file
    location: {location}
    contract_version: "1.0"
    primary_key: [employee_id]
""",
        encoding="utf-8",
    )
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'control.db'}")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
    session = session_factory()
    organization = Organization(name="Synthetic Org", organization_type="employer", status="active")
    session.add(organization)
    session.flush()
    source = SourceSystem(
        organization_id=organization.id,
        source_key=source_id,
        name="Synthetic CSV",
        connector_type="csv",
    )
    session.add(source)
    session.flush()
    session.add(
        SourceObject(
            source_system_id=source.id,
            object_key="employees",
            object_type="file",
            location_template=str(location),
        )
    )
    session.commit()
    settings = Settings(
        environment="test",
        database_url=str(engine.url),
        raw_store_root=tmp_path / "raw",
        allowed_file_roots=[tmp_path / "allowed"],
    )
    return IngestionService(session, settings, config_root), session, organization.id


@pytest.mark.integration
def test_ingestion_is_idempotent_and_resume_uses_previous_cursor(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    source_file = allowed / "employees.csv"
    source_file.write_text("employee_id,name\nE-1,Amina\nE-2,Carlos\n", encoding="utf-8")
    service, session, organization_id = build_service(tmp_path, "demo_csv", source_file)

    first = asyncio.run(service.extract(organization_id, "demo_csv", "employees"))
    second = asyncio.run(
        service.extract(
            organization_id,
            "demo_csv",
            "employees",
            resume_from_run_id=first.run_id,
        )
    )

    assert first.snapshot_id == second.snapshot_id
    assert second.reused_snapshot is True
    assert second.row_count == 2
    assert session.scalar(select(func.count()).select_from(RawSnapshot)) == 1
    runs = list(session.scalars(select(IngestionRun).order_by(IngestionRun.created_at)))
    assert [run.status for run in runs] == ["succeeded", "succeeded"]
    assert runs[1].attempt_number == 2
    assert runs[1].resume_from_run_id == runs[0].id
    session.close()


@pytest.mark.integration
def test_failed_ingestion_records_safe_failure_without_raw_value(tmp_path: Path) -> None:
    (tmp_path / "allowed").mkdir()
    outside = tmp_path / "outside.csv"
    outside.write_text("employee_id,name\nE-1,TOP-SECRET-SYNTHETIC\n", encoding="utf-8")
    service, session, organization_id = build_service(tmp_path, "bad_csv", outside)

    with pytest.raises(ConnectorError, match="outside an allowed root"):
        asyncio.run(service.extract(organization_id, "bad_csv", "employees"))

    run = session.scalar(select(IngestionRun))
    assert run is not None
    assert run.status == "failed"
    assert run.failure_code == "file_outside_allowed_root"
    assert "TOP-SECRET-SYNTHETIC" not in (run.failure_summary or "")
    session.close()
