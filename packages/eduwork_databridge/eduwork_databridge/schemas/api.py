import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")


class HealthResponse(APIModel):
    status: str
    service: str
    version: str


class ReadyResponse(APIModel):
    status: str
    database: str


class VersionResponse(APIModel):
    version: str
    maturity: str
    completed_phases: list[int]


class DemoSummaryResponse(APIModel):
    preset: str
    seed: int
    generated_at: datetime
    synthetic: bool
    privacy_notice: str
    counts: dict[str, int]
    defect_summary: dict[str, int]
    defect_catalog: dict[str, str]


class OrganizationRead(APIModel):
    id: uuid.UUID
    name: str
    organization_type: str
    status: str
    created_at: datetime
    updated_at: datetime


class SourceSystemRead(APIModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    source_key: str
    name: str
    connector_type: str
    data_classification: str
    active: bool
    created_at: datetime
    updated_at: datetime


class SourceConnectionTestResponse(APIModel):
    ok: bool
    connector: str
    checked_at: datetime
    details: dict[str, str | int | float | bool]


class DiscoveredFieldRead(APIModel):
    name: str
    observed_type: str
    nullable: bool


class SourceDiscoveryResponse(APIModel):
    object_key: str
    fields: list[DiscoveredFieldRead]
    sample_count: int
    metadata: dict[str, str | int | float | bool]


class IngestionRequest(APIModel):
    object_key: str
    resume_from_run_id: uuid.UUID | None = None


class IngestionResponse(APIModel):
    run_id: uuid.UUID
    snapshot_id: uuid.UUID
    checksum_sha256: str
    storage_uri: str
    row_count: int
    reused_snapshot: bool
    cursor: dict[str, object]


class ProfileRequest(APIModel):
    snapshot_id: uuid.UUID
    profile_config_id: str = "default_v1"
    baseline_profile_id: uuid.UUID | None = None


class ProfileResponse(APIModel):
    profile_id: uuid.UUID
    schema_fingerprint: str
    drift_status: str | None
    comparison_id: uuid.UUID | None
    profile: dict[str, object]
    comparison: dict[str, object] | None


class MappingPreviewRequest(APIModel):
    snapshot_id: uuid.UUID
    mapping_id: str
    lookup_ids: list[str] = Field(default_factory=list)
    preview_limit: int = 25


class MappingResponse(APIModel):
    execution_id: uuid.UUID
    status: str
    input_count: int
    output_count: int
    error_count: int
    output_uri: str | None
    outputs: list[dict[str, object]]
    issues: list[dict[str, object]]


class ValidationRequest(APIModel):
    snapshot_id: uuid.UUID
    validation_set_id: str
    reference_sets: dict[str, list[str]] = Field(default_factory=dict)


class ValidationResponse(APIModel):
    issue_count: int
    blocking_failures: int
    quality_dimensions: dict[str, dict[str, int | float]]
    persisted_result_ids: list[uuid.UUID]
    quarantine_ids: list[uuid.UUID]


class QuarantineResolveRequest(APIModel):
    status: str
    reviewer_id: uuid.UUID
    note: str
    corrected_snapshot_id: uuid.UUID | None = None


class DeterministicMatchRequest(APIModel):
    match_config_id: str
    dataset_preset: str = "small"


class DeterministicMatchResponse(APIModel):
    candidate_ids: list[uuid.UUID]
    evaluation_id: uuid.UUID | None
    cluster_count: int
    link_count: int
    conflict_count: int
    metrics: dict[str, int | float] | None


class ProbabilisticMatchRequest(APIModel):
    match_config_id: str
    dataset_preset: str = "small"


class ProbabilisticMatchResponse(APIModel):
    model_id: uuid.UUID
    run_id: uuid.UUID
    candidate_count: int
    status_counts: dict[str, int]
    metrics: dict[str, int | float] | None


class MartBuildRequest(APIModel):
    mart_config_id: str
    records: list[dict[str, object]]
    lineage: dict[str, object] = Field(default_factory=dict)


class MartBuildResponse(APIModel):
    mart_snapshot_id: uuid.UUID
    storage_uri: str
    checksum_sha256: str
    row_count: int
    reused: bool


class ExportPublishRequest(APIModel):
    mart_snapshot_id: uuid.UUID
    export_config_id: str


class ExportPublishResponse(APIModel):
    export_snapshot_id: uuid.UUID
    storage_uri: str
    checksum_sha256: str
    row_count: int
    dictionary_uri: str
    expires_at: str


class AssetRunRequest(APIModel):
    asset_key: str
    partition_key: str | None = None
    watermark: dict[str, object] = Field(default_factory=dict)


class AssetRunResponse(APIModel):
    run_id: uuid.UUID
    asset_key: str
    status: str
    change_hash: str
    watermark: dict[str, object]


class RetentionApplyRequest(APIModel):
    policy_id: str
    dry_run: bool = True


class RetentionApplyResponse(APIModel):
    candidate_ids: list[uuid.UUID]
    deleted_files: list[str]
    dry_run: bool


class ActorResponse(APIModel):
    actor_id: uuid.UUID
    subject: str
    display_name: str
    roles: list[str]
    permissions: list[str]
    authentication_method: str


class AuditEventResponse(APIModel):
    id: uuid.UUID
    occurred_at: datetime
    actor_id: uuid.UUID | None
    action: str
    resource_type: str
    resource_id: str
    correlation_id: str | None
    details: dict[str, object]


class LineageTraceResponse(APIModel):
    nodes: list[dict[str, object]]
    edges: list[dict[str, object]]
