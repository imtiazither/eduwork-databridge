from pathlib import Path

from eduwork_databridge.db.models.control import AssetRun
from eduwork_databridge.observability import Telemetry, sanitize_attributes
from eduwork_databridge.orchestration import AssetOrchestrator, AssetSpec, defs
from sqlalchemy import func, select

from tests.factories import build_snapshot_session


def test_asset_orchestration_dependencies_incremental_skip_and_retry(tmp_path: Path) -> None:
    session, organization_id, _ = build_snapshot_session(tmp_path, [{"id": "seed"}])
    telemetry = Telemetry("test")
    failures: list[tuple[str, str]] = []
    orchestrator = AssetOrchestrator(
        session,
        "phase11_test",
        telemetry=telemetry,
        failure_hooks=[lambda asset, code: failures.append((asset, code))],
    )
    calls = {"raw": 0, "profile": 0}

    def raw(context: dict) -> dict:
        del context
        calls["raw"] += 1
        return {"row_count": 10, "checksum_sha256": "a" * 64}

    def profile(context: dict) -> dict:
        assert "raw" in context["dependencies"]
        calls["profile"] += 1
        if calls["profile"] == 1:
            raise RuntimeError("synthetic failure")
        return {"row_count": 10, "profile_id": "P-1"}

    orchestrator.register(AssetSpec("raw", raw, max_attempts=1))
    orchestrator.register(AssetSpec("profile", profile, dependencies=["raw"], max_attempts=2))
    first = orchestrator.run(
        organization_id,
        "profile",
        partition_key="2026-07-20",
        context={"input_version": "v1"},
        watermark={"updated_at": "2026-07-20T00:00:00Z"},
    )
    second = orchestrator.run(
        organization_id,
        "profile",
        partition_key="2026-07-20",
        context={"input_version": "v1"},
        watermark={"updated_at": "2026-07-20T00:00:00Z"},
    )
    assert first.status == "succeeded"
    assert second.status == "skipped_unchanged"
    assert calls == {"raw": 1, "profile": 2}
    assert failures == [("profile", "RuntimeError")]
    assert session.scalar(select(func.count()).select_from(AssetRun)) == 5
    assert telemetry.events
    session.close()


def test_telemetry_attribute_sanitization_and_dagster_definitions() -> None:
    safe = sanitize_attributes(
        {
            "asset_key": "profile",
            "secret_token": "do-not-record",
            "raw_record": "do-not-record",
            "row_count": 10,
        }
    )
    assert safe == {"asset_key": "profile", "row_count": 10}
    assert defs.resolve_all_job_defs()
    assert [schedule.name for schedule in defs.schedules] == ["phase11_daily_schedule"]
