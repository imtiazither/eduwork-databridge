from dagster import AssetSelection, Definitions, ScheduleDefinition, asset, define_asset_job


@asset
def raw_snapshot_asset() -> dict[str, str]:
    return {"status": "configured"}


@asset
def profile_asset(raw_snapshot_asset: dict[str, str]) -> dict[str, str]:
    del raw_snapshot_asset
    return {"status": "configured"}


@asset
def validated_asset(profile_asset: dict[str, str]) -> dict[str, str]:
    del profile_asset
    return {"status": "configured"}


@asset
def mart_asset(validated_asset: dict[str, str]) -> dict[str, str]:
    del validated_asset
    return {"status": "configured"}


phase11_job = define_asset_job("phase11_daily", selection=AssetSelection.all())
phase11_schedule = ScheduleDefinition(job=phase11_job, cron_schedule="0 2 * * *")

defs = Definitions(
    assets=[raw_snapshot_asset, profile_asset, validated_asset, mart_asset],
    schedules=[phase11_schedule],
)
