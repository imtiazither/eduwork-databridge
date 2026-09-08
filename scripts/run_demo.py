import asyncio
import json
from dataclasses import asdict
from pathlib import Path

from eduwork_databridge.config_loader import load_yaml_model
from eduwork_databridge.db.models.control import RawSnapshot
from eduwork_databridge.db.models.core import Organization
from eduwork_databridge.db.session import SessionLocal
from eduwork_databridge.ingestion import IngestionService, read_snapshot_records
from eduwork_databridge.mapping import MappingService, load_lookup
from eduwork_databridge.matching import DeterministicMatchService, load_synthetic_identity_fixture
from eduwork_databridge.profiling import ProfilingService
from eduwork_databridge.schemas.config import (
    DeterministicMatchConfig,
    MappingConfig,
    ProfileConfig,
    ValidationConfig,
)
from eduwork_databridge.settings import get_settings
from eduwork_databridge.validation import ValidationService
from sqlalchemy import select


async def run() -> dict[str, object]:
    settings = get_settings()
    with SessionLocal() as session:
        organization = session.scalar(
            select(Organization).where(Organization.name == "Northstar Learning Labs")
        )
        if organization is None:
            raise SystemExit("Run migrations and seed metadata before the demo")
        ingestion = IngestionService(session, settings)
        hris = await ingestion.extract(organization.id, "demo_hris", "employees")
        snapshot = session.get(RawSnapshot, hris.snapshot_id)
        if snapshot is None:
            raise SystemExit("HRIS snapshot was not created")
        records = read_snapshot_records(snapshot)
        profile_config = load_yaml_model(
            Path("configs/demo/profiles/default_v1.yml"), ProfileConfig
        )
        profile = ProfilingService(session).create_profile(
            organization.id, snapshot.id, records, profile_config
        )
        mapping_config = load_yaml_model(
            Path("configs/demo/mappings/hris_person_v1.yml"), MappingConfig
        )
        lookup_id, _, lookup = load_lookup(Path("configs/demo/lookups/employment_status_v1.yml"))
        mapping = MappingService(session).execute(
            organization.id,
            snapshot.id,
            records,
            mapping_config,
            {lookup_id: lookup},
            context={"output_defaults": {"organization_id": str(organization.id)}},
        )
        validation_config = load_yaml_model(
            Path("configs/demo/validations/person_v1.yml"), ValidationConfig
        )
        validation = ValidationService(session).validate(
            organization.id,
            snapshot.id,
            mapping.outputs,
            validation_config,
        )
        match_config = load_yaml_model(
            Path("configs/demo/matching/person_v1.yml"), DeterministicMatchConfig
        )
        identity_records, truth = load_synthetic_identity_fixture(
            Path("data/synthetic/small"), organization.id
        )
        matching = DeterministicMatchService(session).execute(
            organization.id,
            identity_records,
            match_config,
            truth=truth,
            truth_set_name="small_identity_truth",
        )
        return {
            "snapshot_id": str(snapshot.id),
            "profile_id": str(profile.profile_id),
            "mapping": {
                "outputs": mapping.output_count,
                "errors": mapping.error_count,
            },
            "validation": {
                "issues": len(validation.result.issues),
                "blocking_failures": validation.result.blocking_failures,
                "quarantine_records": len(validation.quarantine_ids),
            },
            "matching": asdict(matching.metrics) if matching.metrics else None,
        }


if __name__ == "__main__":
    print(json.dumps(asyncio.run(run()), indent=2, sort_keys=True))
