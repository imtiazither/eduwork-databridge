import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from eduwork_databridge.connectors.base import ConnectorError
from eduwork_databridge.db.models.control import (
    ProfileComparison,
    RawSnapshot,
    SchemaProfile,
    SourceObject,
    SourceSystem,
)
from eduwork_databridge.profiling.profiler import DataProfiler
from eduwork_databridge.schemas.config import ProfileConfig


@dataclass(frozen=True)
class ProfileOutcome:
    profile_id: uuid.UUID
    schema_fingerprint: str
    profile: dict[str, Any]
    comparison_id: uuid.UUID | None = None
    drift_status: str | None = None
    comparison: dict[str, Any] | None = None


class ProfilingService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.profiler = DataProfiler()

    def _snapshot(self, organization_id: uuid.UUID, snapshot_id: uuid.UUID) -> RawSnapshot:
        snapshot = self.session.get(RawSnapshot, snapshot_id)
        if snapshot is None:
            raise ConnectorError("snapshot_not_found", "Raw snapshot was not found")
        source_object = self.session.get(SourceObject, snapshot.source_object_id)
        source = (
            self.session.get(SourceSystem, source_object.source_system_id)
            if source_object
            else None
        )
        if source is None or source.organization_id != organization_id:
            raise ConnectorError(
                "snapshot_scope_mismatch", "Raw snapshot is outside organization scope"
            )
        return snapshot

    def create_profile(
        self,
        organization_id: uuid.UUID,
        snapshot_id: uuid.UUID,
        records: list[dict[str, Any]],
        config: ProfileConfig,
        baseline_profile_id: uuid.UUID | None = None,
    ) -> ProfileOutcome:
        self._snapshot(organization_id, snapshot_id)
        result = self.profiler.profile(records, config)
        baseline = (
            self.session.get(SchemaProfile, baseline_profile_id) if baseline_profile_id else None
        )
        if baseline_profile_id and baseline is None:
            raise ConnectorError("baseline_not_found", "Baseline profile was not found")
        profile = SchemaProfile(
            raw_snapshot_id=snapshot_id,
            profile_version=self.profiler.version,
            profile_json=result.profile,
            baseline_profile_id=baseline_profile_id,
        )
        self.session.add(profile)
        self.session.flush()
        comparison_row: ProfileComparison | None = None
        drift_status: str | None = None
        comparison_json: dict[str, Any] | None = None
        if baseline is not None:
            drift = self.profiler.compare(baseline.profile_json, result.profile, config)
            drift_status = drift.status
            comparison_json = drift.comparison
            comparison_row = ProfileComparison(
                organization_id=organization_id,
                baseline_profile_id=baseline.id,
                current_profile_id=profile.id,
                status=drift.status,
                comparison_json=drift.comparison,
            )
            self.session.add(comparison_row)
            self.session.flush()
        self.session.commit()
        return ProfileOutcome(
            profile_id=profile.id,
            schema_fingerprint=result.schema_fingerprint,
            profile=result.profile,
            comparison_id=comparison_row.id if comparison_row else None,
            drift_status=drift_status,
            comparison=comparison_json,
        )
