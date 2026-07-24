import json
import uuid
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from eduwork_databridge import __version__
from eduwork_databridge.config_loader import (
    load_yaml_model,
    named_config_path,
    source_config_path,
)
from eduwork_databridge.connectors import ConnectorError, build_connector
from eduwork_databridge.db.models.control import DataMartSnapshot, RawSnapshot
from eduwork_databridge.db.session import get_session
from eduwork_databridge.ingestion import IngestionService, read_snapshot_records
from eduwork_databridge.lineage import LineageService
from eduwork_databridge.mapping import MappingCompileError, MappingService, load_lookup
from eduwork_databridge.marts import MartService, read_mart_records
from eduwork_databridge.matching import (
    DeterministicMatchService,
    ProbabilisticMatchService,
    load_synthetic_identity_fixture,
    metrics_dict,
)
from eduwork_databridge.orchestration import AssetOrchestrator, AssetSpec
from eduwork_databridge.profiling import ProfilingService
from eduwork_databridge.publishing import ExportService, RetentionService
from eduwork_databridge.repositories import list_organizations, list_sources
from eduwork_databridge.schemas.api import (
    ActorResponse,
    AssetRunRequest,
    AssetRunResponse,
    AuditEventResponse,
    DemoSummaryResponse,
    DeterministicMatchRequest,
    DeterministicMatchResponse,
    DiscoveredFieldRead,
    ExportPublishRequest,
    ExportPublishResponse,
    HealthResponse,
    IngestionRequest,
    IngestionResponse,
    LineageTraceResponse,
    MappingPreviewRequest,
    MappingResponse,
    MartBuildRequest,
    MartBuildResponse,
    OrganizationRead,
    ProbabilisticMatchRequest,
    ProbabilisticMatchResponse,
    ProfileRequest,
    ProfileResponse,
    QuarantineResolveRequest,
    ReadyResponse,
    RetentionApplyRequest,
    RetentionApplyResponse,
    SourceConnectionTestResponse,
    SourceDiscoveryResponse,
    SourceSystemRead,
    ValidationRequest,
    ValidationResponse,
    VersionResponse,
)
from eduwork_databridge.schemas.config import (
    DeterministicMatchConfig,
    ExportConfig,
    MappingConfig,
    MartDefinitionConfig,
    OrchestrationConfig,
    ProbabilisticMatchConfig,
    ProfileConfig,
    RetentionPolicyConfig,
    SourceConfig,
    SourceObjectConfig,
    ValidationConfig,
)
from eduwork_databridge.security import (
    Actor,
    AuditService,
    RateLimitMiddleware,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
    get_actor,
    require_organization,
    require_permission,
)
from eduwork_databridge.settings import get_settings
from eduwork_databridge.validation import ValidationService

settings = get_settings()
SessionDep = Annotated[Session, Depends(get_session)]
ActorDep = Annotated[Actor, Depends(get_actor)]
OrganizationHeader = Annotated[uuid.UUID | None, Header(alias="X-Organization-ID")]
CONFIG_ROOT = Path("configs/demo")


def _source_config(source_id: str) -> SourceConfig:
    try:
        return load_yaml_model(source_config_path(CONFIG_ROOT, source_id), SourceConfig)
    except (ConnectorError, FileNotFoundError, ValueError) as exc:
        code = exc.code if isinstance(exc, ConnectorError) else "source_config_unavailable"
        raise HTTPException(
            status_code=400,
            detail={"code": code, "message": "Source configuration is unavailable"},
        ) from exc


def _named_config[ModelT: BaseModel](
    category: str,
    config_id: str,
    model: type[ModelT],
) -> ModelT:
    try:
        return load_yaml_model(named_config_path(CONFIG_ROOT, category, config_id), model)
    except (ConnectorError, FileNotFoundError, ValueError) as exc:
        code = exc.code if isinstance(exc, ConnectorError) else "configuration_unavailable"
        raise HTTPException(
            status_code=400,
            detail={"code": code, "message": "Requested configuration is unavailable"},
        ) from exc


def _required_organization(value: uuid.UUID | None) -> uuid.UUID:
    if value is None:
        raise HTTPException(status_code=400, detail="X-Organization-ID is required")
    return value


def _demo_asset_compute(asset_key: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def compute(context: dict[str, Any]) -> dict[str, Any]:
        return {
            "row_count": int(context.get("row_count", 0)),
            "checksum_sha256": uuid.uuid5(uuid.NAMESPACE_URL, f"eduwork:{asset_key}").hex,
        }

    return compute


def _source_object(config: SourceConfig, object_key: str) -> SourceObjectConfig:
    for source_object in config.objects:
        if source_object.key == object_key:
            return source_object
    raise HTTPException(
        status_code=404,
        detail={"code": "object_not_configured", "message": "Source object is not configured"},
    )


def _load_lookups(lookup_ids: list[str]) -> dict[str, dict[str, object]]:
    lookups: dict[str, dict[str, object]] = {}
    for lookup_id in lookup_ids:
        loaded_id, _, values = load_lookup(named_config_path(CONFIG_ROOT, "lookups", lookup_id))
        if loaded_id != lookup_id:
            raise HTTPException(status_code=400, detail="Lookup identifier mismatch")
        lookups[lookup_id] = values
    return lookups


def _mapping_rules(config: MappingConfig) -> list[dict[str, Any]]:
    return [
        {"target": rule.target, "source": rule.source, "transform": rule.transform}
        for rule in config.rules
    ]


app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="Phase 0–12 reference implementation for EduWork DataBridge.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Demo-User", "X-Organization-ID"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=settings.max_request_bytes)
app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.rate_limit_per_minute)


@app.exception_handler(ConnectorError)
async def connector_error_handler(request: Request, exc: ConnectorError) -> JSONResponse:
    del request
    status = 403 if exc.code.endswith("forbidden") else 400
    return JSONResponse(
        {"detail": {"code": exc.code, "message": exc.safe_message}},
        status_code=status,
    )


@app.get("/healthz", response_model=HealthResponse, tags=["operations"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="eduwork-databridge", version=__version__)


@app.get("/readyz", response_model=ReadyResponse, tags=["operations"])
def ready(session: SessionDep) -> ReadyResponse:
    session.execute(text("SELECT 1"))
    return ReadyResponse(status="ready", database="reachable")


@app.get("/api/v1/version", response_model=VersionResponse, tags=["metadata"])
def version() -> VersionResponse:
    return VersionResponse(
        version=__version__, maturity="release-candidate", completed_phases=list(range(15))
    )


@app.get("/api/v1/demo/summary", response_model=DemoSummaryResponse, tags=["metadata"])
def demo_summary() -> DemoSummaryResponse:
    """Return the public synthetic case-file summary used by the reviewer UI."""
    manifest_path = Path("data/synthetic/small/dataset_manifest.json")
    try:
        manifest = json.loads(manifest_path.read_text())
        return DemoSummaryResponse(
            preset=manifest["preset"],
            seed=manifest["seed"],
            generated_at=manifest["generated_at"],
            synthetic=manifest["synthetic"],
            privacy_notice=manifest["privacy_notice"],
            counts=manifest["counts"],
            defect_summary=manifest["defect_summary"],
            defect_catalog=manifest["defect_catalog"],
        )
    except (KeyError, OSError, ValueError) as exc:
        raise HTTPException(
            status_code=503, detail="Synthetic demo summary is unavailable"
        ) from exc


@app.get("/api/v1/organizations", response_model=list[OrganizationRead], tags=["metadata"])
def organizations(session: SessionDep) -> list[OrganizationRead]:
    return [OrganizationRead.model_validate(item) for item in list_organizations(session)]


@app.get("/api/v1/sources", response_model=list[SourceSystemRead], tags=["metadata"])
def sources(
    session: SessionDep,
    x_organization_id: OrganizationHeader = None,
) -> list[SourceSystemRead]:
    if x_organization_id is None:
        raise HTTPException(status_code=400, detail="X-Organization-ID is required")
    return [
        SourceSystemRead.model_validate(item) for item in list_sources(session, x_organization_id)
    ]


@app.post(
    "/api/v1/sources/{source_id}/test",
    response_model=SourceConnectionTestResponse,
    tags=["sources"],
)
async def test_source_connection(source_id: str) -> SourceConnectionTestResponse:
    config = _source_config(source_id)
    connector = build_connector(config, settings)
    try:
        result = await connector.test_connection()
        return SourceConnectionTestResponse.model_validate(result)
    except ConnectorError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": exc.code, "message": exc.safe_message},
        ) from exc
    finally:
        await connector.close()


@app.get(
    "/api/v1/sources/{source_id}/objects/{object_key}/discover",
    response_model=SourceDiscoveryResponse,
    tags=["sources"],
)
async def discover_source(source_id: str, object_key: str) -> SourceDiscoveryResponse:
    config = _source_config(source_id)
    source_object = _source_object(config, object_key)
    connector = build_connector(config, settings)
    try:
        result = await connector.discover_schema(source_object)
        return SourceDiscoveryResponse(
            object_key=result.object_key,
            fields=[DiscoveredFieldRead.model_validate(field) for field in result.fields],
            sample_count=result.sample_count,
            metadata=result.metadata,
        )
    except ConnectorError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": exc.code, "message": exc.safe_message},
        ) from exc
    finally:
        await connector.close()


@app.post(
    "/api/v1/sources/{source_id}/extract",
    response_model=IngestionResponse,
    tags=["ingestion"],
)
async def extract_source(
    source_id: str,
    request: IngestionRequest,
    session: SessionDep,
    actor: ActorDep,
    x_organization_id: OrganizationHeader = None,
) -> IngestionResponse:
    organization_id = _required_organization(x_organization_id)
    require_organization(actor, organization_id)
    require_permission(actor, "ingestion:write")
    service = IngestionService(session, settings, CONFIG_ROOT)
    try:
        outcome = await service.extract(
            organization_id=organization_id,
            source_id=source_id,
            object_key=request.object_key,
            resume_from_run_id=request.resume_from_run_id,
        )
    except ConnectorError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": exc.code, "message": exc.safe_message},
        ) from exc
    AuditService(session).record(
        actor,
        "ingestion.completed",
        "ingestion_run",
        str(outcome.run_id),
        organization_id,
        details={
            "source_id": source_id,
            "object_key": request.object_key,
            "row_count": outcome.row_count,
            "reused_snapshot": outcome.reused_snapshot,
        },
    )
    return IngestionResponse(
        run_id=outcome.run_id,
        snapshot_id=outcome.snapshot_id,
        checksum_sha256=outcome.checksum_sha256,
        storage_uri=outcome.storage_uri,
        row_count=outcome.row_count,
        reused_snapshot=outcome.reused_snapshot,
        cursor=outcome.cursor,
    )


@app.post("/api/v1/profiles", response_model=ProfileResponse, tags=["profiling"])
def create_profile(
    request: ProfileRequest,
    session: SessionDep,
    x_organization_id: OrganizationHeader = None,
) -> ProfileResponse:
    organization_id = _required_organization(x_organization_id)
    config = _named_config("profiles", request.profile_config_id, ProfileConfig)
    snapshot = session.get(RawSnapshot, request.snapshot_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Raw snapshot was not found")
    try:
        records = read_snapshot_records(snapshot)
        outcome = ProfilingService(session).create_profile(
            organization_id=organization_id,
            snapshot_id=request.snapshot_id,
            records=records,
            config=config,
            baseline_profile_id=request.baseline_profile_id,
        )
    except ConnectorError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": exc.code, "message": exc.safe_message},
        ) from exc
    return ProfileResponse(
        profile_id=outcome.profile_id,
        schema_fingerprint=outcome.schema_fingerprint,
        drift_status=outcome.drift_status,
        comparison_id=outcome.comparison_id,
        profile=outcome.profile,
        comparison=outcome.comparison,
    )


@app.post("/api/v1/mappings/preview", response_model=MappingResponse, tags=["mapping"])
def preview_mapping(
    request: MappingPreviewRequest,
    session: SessionDep,
    actor: ActorDep,
    x_organization_id: OrganizationHeader = None,
) -> MappingResponse:
    organization_id = _required_organization(x_organization_id)
    require_organization(actor, organization_id)
    require_permission(actor, "mappings:write")
    config = _named_config("mappings", request.mapping_id, MappingConfig)
    snapshot = session.get(RawSnapshot, request.snapshot_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Raw snapshot was not found")
    lookups = _load_lookups(request.lookup_ids)
    try:
        outcome = MappingService(session).execute(
            organization_id=organization_id,
            snapshot_id=request.snapshot_id,
            records=read_snapshot_records(snapshot),
            config=config,
            lookups=lookups,
            context={"output_defaults": {"organization_id": str(organization_id)}},
            dry_run=True,
            preview_limit=request.preview_limit,
        )
    except (ConnectorError, MappingCompileError) as exc:
        message = exc.safe_message if isinstance(exc, ConnectorError) else "Mapping cannot compile"
        raise HTTPException(status_code=400, detail=message) from exc
    LineageService(session, settings.lineage_root).record_mapping(
        organization_id,
        request.snapshot_id,
        config.mapping_id,
        config.source_contract,
        _mapping_rules(config),
    )
    AuditService(session).record(
        actor,
        "mapping.previewed",
        "mapping_execution",
        str(outcome.execution_id),
        organization_id,
        details={"mapping_id": config.mapping_id, "output_count": outcome.output_count},
    )
    return MappingResponse(
        execution_id=outcome.execution_id,
        status=outcome.status,
        input_count=outcome.input_count,
        output_count=outcome.output_count,
        error_count=outcome.error_count,
        output_uri=outcome.output_uri,
        outputs=outcome.outputs,
        issues=[asdict(issue) for issue in outcome.issues],
    )


@app.post("/api/v1/validations", response_model=ValidationResponse, tags=["validation"])
def validate_snapshot(
    request: ValidationRequest,
    session: SessionDep,
    actor: ActorDep,
    x_organization_id: OrganizationHeader = None,
) -> ValidationResponse:
    organization_id = _required_organization(x_organization_id)
    require_organization(actor, organization_id)
    require_permission(actor, "validation:write")
    config = _named_config("validations", request.validation_set_id, ValidationConfig)
    snapshot = session.get(RawSnapshot, request.snapshot_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Raw snapshot was not found")
    records = read_snapshot_records(snapshot)
    record_source = "raw"
    if request.mapping_id is not None:
        mapping_config = _named_config("mappings", request.mapping_id, MappingConfig)
        try:
            mapped = MappingService(session).execute(
                organization_id=organization_id,
                snapshot_id=request.snapshot_id,
                records=records,
                config=mapping_config,
                lookups=_load_lookups(request.lookup_ids),
                context={"output_defaults": {"organization_id": str(organization_id)}},
                dry_run=True,
            )
        except (ConnectorError, MappingCompileError) as exc:
            message = (
                exc.safe_message if isinstance(exc, ConnectorError) else "Mapping cannot compile"
            )
            raise HTTPException(status_code=400, detail=message) from exc
        records = mapped.outputs
        record_source = "mapped"
        LineageService(session, settings.lineage_root).record_mapping(
            organization_id,
            request.snapshot_id,
            mapping_config.mapping_id,
            mapping_config.source_contract,
            _mapping_rules(mapping_config),
        )
    try:
        outcome = ValidationService(session).validate(
            organization_id=organization_id,
            snapshot_id=request.snapshot_id,
            records=records,
            config=config,
            reference_sets={key: set(values) for key, values in request.reference_sets.items()},
        )
    except ConnectorError as exc:
        raise HTTPException(status_code=400, detail=exc.safe_message) from exc
    AuditService(session).record(
        actor,
        "validation.completed",
        "raw_snapshot",
        str(request.snapshot_id),
        organization_id,
        details={
            "validation_set_id": request.validation_set_id,
            "record_source": record_source,
            "issue_count": len(outcome.result.issues),
            "blocking_failures": outcome.result.blocking_failures,
            "quarantine_count": len(outcome.quarantine_ids),
        },
    )
    return ValidationResponse(
        issue_count=len(outcome.result.issues),
        blocking_failures=outcome.result.blocking_failures,
        quality_dimensions=outcome.result.quality_dimensions,
        persisted_result_ids=outcome.persisted_result_ids,
        quarantine_ids=outcome.quarantine_ids,
        validated_record_count=len(records),
        record_source=record_source,
    )


@app.post("/api/v1/quarantine/{quarantine_id}/resolve", tags=["validation"])
def resolve_quarantine(
    quarantine_id: uuid.UUID,
    request: QuarantineResolveRequest,
    session: SessionDep,
    x_organization_id: OrganizationHeader = None,
) -> dict[str, str]:
    organization_id = _required_organization(x_organization_id)
    try:
        row = ValidationService(session).resolve_quarantine(
            organization_id=organization_id,
            quarantine_id=quarantine_id,
            status=request.status,
            reviewer_id=request.reviewer_id,
            note=request.note,
            corrected_snapshot_id=request.corrected_snapshot_id,
        )
    except ConnectorError as exc:
        raise HTTPException(status_code=400, detail=exc.safe_message) from exc
    return {"quarantine_id": str(row.id), "status": row.status}


@app.post(
    "/api/v1/matches/deterministic/synthetic",
    response_model=DeterministicMatchResponse,
    tags=["matching"],
)
def deterministic_synthetic_match(
    request: DeterministicMatchRequest,
    session: SessionDep,
    actor: ActorDep,
    x_organization_id: OrganizationHeader = None,
) -> DeterministicMatchResponse:
    organization_id = _required_organization(x_organization_id)
    require_organization(actor, organization_id)
    require_permission(actor, "matching:write")
    if request.dataset_preset not in {"small", "medium"}:
        raise HTTPException(status_code=400, detail="Dataset preset must be small or medium")
    config = _named_config("matching", request.match_config_id, DeterministicMatchConfig)
    records, truth = load_synthetic_identity_fixture(
        Path("data/synthetic") / request.dataset_preset,
        organization_id,
    )
    try:
        outcome = DeterministicMatchService(session).execute(
            organization_id=organization_id,
            records=records,
            config=config,
            truth=truth,
            truth_set_name=f"{request.dataset_preset}_identity_truth",
        )
    except (ConnectorError, ValueError) as exc:
        message = (
            exc.safe_message if isinstance(exc, ConnectorError) else "Matching input is invalid"
        )
        raise HTTPException(status_code=400, detail=message) from exc
    AuditService(session).record(
        actor,
        "matching.deterministic.completed",
        "match_evaluation",
        str(outcome.evaluation_id) if outcome.evaluation_id else "synthetic-run",
        organization_id,
        details={
            "candidate_count": len(outcome.candidate_ids),
            "link_count": len(outcome.result.links),
            "conflict_count": len(outcome.result.conflicts),
        },
    )
    return DeterministicMatchResponse(
        candidate_ids=outcome.candidate_ids,
        evaluation_id=outcome.evaluation_id,
        cluster_count=len(set(outcome.result.clusters.values())),
        link_count=len(outcome.result.links),
        conflict_count=len(outcome.result.conflicts),
        metrics=asdict(outcome.metrics) if outcome.metrics else None,
    )


@app.get("/api/v1/me", response_model=ActorResponse, tags=["security"])
def current_actor(actor: ActorDep) -> ActorResponse:
    return ActorResponse(
        actor_id=actor.actor_id,
        subject=actor.subject,
        display_name=actor.display_name,
        roles=sorted(actor.roles),
        permissions=sorted(actor.permissions),
        authentication_method=actor.authentication_method,
    )


@app.post(
    "/api/v1/matches/probabilistic/synthetic",
    response_model=ProbabilisticMatchResponse,
    tags=["matching"],
)
def probabilistic_synthetic_match(
    request: ProbabilisticMatchRequest,
    session: SessionDep,
    actor: ActorDep,
    x_organization_id: OrganizationHeader = None,
) -> ProbabilisticMatchResponse:
    organization_id = _required_organization(x_organization_id)
    require_organization(actor, organization_id)
    require_permission(actor, "matching:write")
    if request.dataset_preset not in {"small", "medium"}:
        raise HTTPException(status_code=400, detail="Dataset preset must be small or medium")
    config = _named_config("matching", request.match_config_id, ProbabilisticMatchConfig)
    records, truth = load_synthetic_identity_fixture(
        Path("data/synthetic") / request.dataset_preset,
        organization_id,
    )
    try:
        outcome = ProbabilisticMatchService(session).execute(
            organization_id,
            records,
            config,
            truth=truth,
            truth_set_name=f"{request.dataset_preset}_identity_truth",
        )
    except (ConnectorError, ValueError) as exc:
        message = (
            exc.safe_message if isinstance(exc, ConnectorError) else "Matching input is invalid"
        )
        raise HTTPException(status_code=400, detail=message) from exc
    counts: dict[str, int] = {}
    for candidate in outcome.result.candidates:
        counts[candidate.status] = counts.get(candidate.status, 0) + 1
    AuditService(session).record(
        actor,
        "matching.probabilistic.completed",
        "probabilistic_run",
        str(outcome.run_id),
        organization_id,
        details={"candidate_count": len(outcome.candidate_ids)},
    )
    return ProbabilisticMatchResponse(
        model_id=outcome.model_id,
        run_id=outcome.run_id,
        candidate_count=len(outcome.candidate_ids),
        status_counts=counts,
        metrics=metrics_dict(outcome.result.metrics),
    )


@app.post("/api/v1/marts", response_model=MartBuildResponse, tags=["publishing"])
def build_mart(
    request: MartBuildRequest,
    session: SessionDep,
    actor: ActorDep,
    x_organization_id: OrganizationHeader = None,
) -> MartBuildResponse:
    organization_id = _required_organization(x_organization_id)
    require_organization(actor, organization_id)
    require_permission(actor, "marts:write")
    config = _named_config("marts", request.mart_config_id, MartDefinitionConfig)
    mapping_config: MappingConfig | None = None
    if request.mapping_id is not None:
        mapping_config = _named_config("mappings", request.mapping_id, MappingConfig)
    if request.source_snapshot_id is not None and (
        session.get(RawSnapshot, request.source_snapshot_id) is None
    ):
        raise HTTPException(status_code=404, detail="Source snapshot was not found")
    outcome = MartService(session, settings.mart_root).build(
        organization_id,
        [dict(record) for record in request.records],
        config,
        dict(request.lineage),
    )
    LineageService(session, settings.lineage_root).record_mart(
        organization_id,
        outcome.snapshot_id,
        source_snapshot_id=request.source_snapshot_id,
        mapping_id=mapping_config.mapping_id if mapping_config else None,
        mapping_version=mapping_config.source_contract if mapping_config else None,
    )
    AuditService(session).record(
        actor,
        "mart.created",
        "data_mart_snapshot",
        str(outcome.snapshot_id),
        organization_id,
        details={"row_count": outcome.row_count},
    )
    return MartBuildResponse(
        mart_snapshot_id=outcome.snapshot_id,
        storage_uri=outcome.storage_uri,
        checksum_sha256=outcome.checksum_sha256,
        row_count=outcome.row_count,
        reused=outcome.reused,
    )


@app.post("/api/v1/exports", response_model=ExportPublishResponse, tags=["publishing"])
def publish_export(
    request: ExportPublishRequest,
    session: SessionDep,
    actor: ActorDep,
    x_organization_id: OrganizationHeader = None,
) -> ExportPublishResponse:
    organization_id = _required_organization(x_organization_id)
    require_organization(actor, organization_id)
    require_permission(actor, "exports:write")
    mart = session.get(DataMartSnapshot, request.mart_snapshot_id)
    if mart is None or mart.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Mart snapshot was not found")
    config = _named_config("exports", request.export_config_id, ExportConfig)
    outcome = ExportService(
        session,
        settings.export_root,
        LineageService(session, settings.lineage_root),
    ).publish(
        organization_id,
        mart.id,
        read_mart_records(mart),
        config,
        set(actor.permissions),
    )
    AuditService(session).record(
        actor,
        "export.created",
        "export_snapshot",
        str(outcome.export_snapshot_id),
        organization_id,
        details={"row_count": outcome.row_count},
    )
    return ExportPublishResponse(**asdict(outcome))


@app.get(
    "/api/v1/lineage/{node_id}",
    response_model=LineageTraceResponse,
    tags=["lineage"],
)
def lineage_trace(
    node_id: uuid.UUID,
    session: SessionDep,
    actor: ActorDep,
    x_organization_id: OrganizationHeader = None,
) -> LineageTraceResponse:
    organization_id = _required_organization(x_organization_id)
    require_organization(actor, organization_id)
    require_permission(actor, "lineage:read")
    trace = LineageService(session).trace(organization_id, node_id)
    return LineageTraceResponse(nodes=trace.nodes, edges=trace.edges)


@app.post(
    "/api/v1/orchestration/runs",
    response_model=AssetRunResponse,
    tags=["orchestration"],
)
def run_asset(
    request: AssetRunRequest,
    session: SessionDep,
    actor: ActorDep,
    x_organization_id: OrganizationHeader = None,
) -> AssetRunResponse:
    organization_id = _required_organization(x_organization_id)
    require_organization(actor, organization_id)
    require_permission(actor, "ingestion:write")
    config = _named_config("orchestration", "phase11_daily_v1", OrchestrationConfig)
    dependencies = {
        "raw_snapshot": [],
        "profile": ["raw_snapshot"],
        "validated": ["profile"],
        "training_mart": ["validated"],
    }
    orchestrator = AssetOrchestrator(session, config.orchestration_id)
    for item in config.assets:
        orchestrator.register(
            AssetSpec(
                key=item.asset_key,
                dependencies=dependencies.get(item.asset_key, []),
                max_attempts=item.max_attempts,
                compute=_demo_asset_compute(item.asset_key),
            )
        )
    outcome = orchestrator.run(
        organization_id,
        request.asset_key,
        partition_key=request.partition_key,
        context={},
        watermark=dict(request.watermark),
    )
    AuditService(session).record(
        actor,
        "orchestration.asset.completed",
        "asset_run",
        str(outcome.run_id),
        organization_id,
        details={"asset_key": outcome.asset_key, "status": outcome.status},
    )
    return AssetRunResponse(
        run_id=outcome.run_id,
        asset_key=outcome.asset_key,
        status=outcome.status,
        change_hash=outcome.change_hash,
        watermark=outcome.watermark,
    )


@app.post(
    "/api/v1/retention/apply",
    response_model=RetentionApplyResponse,
    tags=["security"],
)
def apply_retention(
    request: RetentionApplyRequest,
    session: SessionDep,
    actor: ActorDep,
    x_organization_id: OrganizationHeader = None,
) -> RetentionApplyResponse:
    organization_id = _required_organization(x_organization_id)
    require_organization(actor, organization_id)
    require_permission(actor, "retention:write")
    config = _named_config("retention", request.policy_id, RetentionPolicyConfig)
    service = RetentionService(session)
    policy = service.upsert_policy(organization_id, config)
    outcome = service.apply_export_retention(organization_id, policy, dry_run=request.dry_run)
    AuditService(session).record(
        actor,
        "retention.applied",
        "retention_policy",
        str(policy.id),
        organization_id,
        details={"candidate_count": len(outcome.candidate_ids), "dry_run": outcome.dry_run},
    )
    return RetentionApplyResponse(**asdict(outcome))


@app.get(
    "/api/v1/audit",
    response_model=list[AuditEventResponse],
    tags=["security"],
)
def list_audit(
    session: SessionDep,
    actor: ActorDep,
    x_organization_id: OrganizationHeader = None,
) -> list[AuditEventResponse]:
    organization_id = _required_organization(x_organization_id)
    require_organization(actor, organization_id)
    require_permission(actor, "audit:read")
    return [
        AuditEventResponse(
            id=event.id,
            occurred_at=event.occurred_at,
            actor_id=event.actor_id,
            action=event.action,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            correlation_id=event.correlation_id,
            details=event.details_json,
        )
        for event in AuditService(session).list_for_organization(organization_id)
    ]
