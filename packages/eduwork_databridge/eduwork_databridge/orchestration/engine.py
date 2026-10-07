import hashlib
import json
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from eduwork_databridge.connectors.base import ConnectorError
from eduwork_databridge.db.models.control import AssetRun
from eduwork_databridge.observability import Telemetry

AssetFunction = Callable[[dict[str, Any]], dict[str, Any]]
FailureHook = Callable[[str, str], None]


@dataclass(frozen=True)
class AssetSpec:
    key: str
    compute: AssetFunction
    dependencies: list[str] = field(default_factory=list)
    max_attempts: int = 3


@dataclass(frozen=True)
class AssetOutcome:
    asset_key: str
    run_id: uuid.UUID
    status: str
    change_hash: str
    output: dict[str, Any]
    watermark: dict[str, Any]


class AssetOrchestrator:
    def __init__(
        self,
        session: Session,
        orchestration_key: str,
        telemetry: Telemetry | None = None,
        failure_hooks: list[FailureHook] | None = None,
    ) -> None:
        self.session = session
        self.orchestration_key = orchestration_key
        self.telemetry = telemetry or Telemetry()
        self.failure_hooks = failure_hooks or []
        self.assets: dict[str, AssetSpec] = {}

    def register(self, spec: AssetSpec) -> None:
        if spec.key in self.assets:
            raise ValueError(f"Duplicate asset key: {spec.key}")
        if spec.max_attempts < 1 or spec.max_attempts > 10:
            raise ValueError("Asset attempts must be between one and ten")
        self.assets[spec.key] = spec

    @staticmethod
    def _change_hash(
        asset_key: str,
        partition_key: str | None,
        watermark: dict[str, Any],
        context: dict[str, Any],
    ) -> str:
        material = {
            "asset_key": asset_key,
            "partition_key": partition_key,
            "watermark": watermark,
            "context": context,
        }
        return hashlib.sha256(
            json.dumps(material, sort_keys=True, default=str).encode()
        ).hexdigest()

    @staticmethod
    def _safe_metadata(output: dict[str, Any]) -> dict[str, Any]:
        allowed = {
            "row_count",
            "checksum_sha256",
            "snapshot_id",
            "profile_id",
            "validation_issue_count",
            "export_snapshot_id",
        }
        return {key: value for key, value in output.items() if key in allowed}

    def run(
        self,
        organization_id: uuid.UUID,
        asset_key: str,
        partition_key: str | None = None,
        context: dict[str, Any] | None = None,
        watermark: dict[str, Any] | None = None,
        backfill_of_run_id: uuid.UUID | None = None,
    ) -> AssetOutcome:
        if asset_key not in self.assets:
            raise ConnectorError("asset_not_registered", "Asset is not registered")
        execution_context = dict(context or {})
        spec = self.assets[asset_key]
        dependency_outputs: dict[str, Any] = {}
        for dependency in spec.dependencies:
            outcome = self.run(
                organization_id,
                dependency,
                partition_key=partition_key,
                context=execution_context,
                watermark=watermark,
                backfill_of_run_id=backfill_of_run_id,
            )
            dependency_outputs[dependency] = outcome.output
        execution_context["dependencies"] = dependency_outputs
        current_watermark = watermark or {}
        change_hash = self._change_hash(
            asset_key, partition_key, current_watermark, execution_context
        )
        prior = self.session.scalar(
            select(AssetRun)
            .where(
                AssetRun.organization_id == organization_id,
                AssetRun.asset_key == asset_key,
                AssetRun.partition_key == partition_key,
                AssetRun.change_hash == change_hash,
                AssetRun.status == "succeeded",
            )
            .order_by(AssetRun.ended_at.desc())
        )
        if prior and backfill_of_run_id is None:
            skipped = AssetRun(
                organization_id=organization_id,
                orchestration_key=self.orchestration_key,
                asset_key=asset_key,
                partition_key=partition_key,
                status="skipped_unchanged",
                attempt_number=1,
                watermark_json=current_watermark,
                change_hash=change_hash,
                started_at=datetime.now(UTC),
                ended_at=datetime.now(UTC),
                metadata_json={"prior_run_id": str(prior.id)},
            )
            self.session.add(skipped)
            self.session.commit()
            return AssetOutcome(
                asset_key=asset_key,
                run_id=skipped.id,
                status=skipped.status,
                change_hash=change_hash,
                output=prior.metadata_json,
                watermark=prior.watermark_json,
            )
        last_error: Exception | None = None
        for attempt in range(1, spec.max_attempts + 1):
            started = datetime.now(UTC)
            run = AssetRun(
                organization_id=organization_id,
                orchestration_key=self.orchestration_key,
                asset_key=asset_key,
                partition_key=partition_key,
                status="running",
                attempt_number=attempt,
                watermark_json=current_watermark,
                change_hash=change_hash,
                backfill_of_run_id=backfill_of_run_id,
                started_at=started,
                metadata_json={},
            )
            self.session.add(run)
            self.session.commit()
            clock = time.perf_counter()
            try:
                with self.telemetry.span(
                    "eduwork.asset",
                    {
                        "asset_key": asset_key,
                        "partition_key": partition_key or "none",
                        "attempt": attempt,
                    },
                ):
                    output = spec.compute(execution_context)
                duration_ms = (time.perf_counter() - clock) * 1000
                run.status = "succeeded"
                run.ended_at = datetime.now(UTC)
                run.metadata_json = self._safe_metadata(output)
                self.session.commit()
                self.telemetry.record_run(
                    "succeeded",
                    duration_ms,
                    {"asset_key": asset_key, "attempt": attempt},
                )
                return AssetOutcome(
                    asset_key=asset_key,
                    run_id=run.id,
                    status=run.status,
                    change_hash=change_hash,
                    output=output,
                    watermark=current_watermark,
                )
            except Exception as exc:
                last_error = exc
                duration_ms = (time.perf_counter() - clock) * 1000
                run.status = "failed"
                run.ended_at = datetime.now(UTC)
                run.failure_code = type(exc).__name__
                run.metadata_json = {}
                self.session.commit()
                self.telemetry.record_run(
                    "failed",
                    duration_ms,
                    {"asset_key": asset_key, "attempt": attempt},
                )
                for hook in self.failure_hooks:
                    hook(asset_key, type(exc).__name__)
        raise ConnectorError(
            "asset_failed", f"Asset failed after {spec.max_attempts} attempts"
        ) from last_error
