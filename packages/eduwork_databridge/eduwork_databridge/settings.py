from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from EDUWORK_* environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="EDUWORK_", env_file=".env", extra="ignore", case_sensitive=False
    )

    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite+pysqlite:///./eduwork_phase2.db"
    log_level: str = "INFO"
    demo_mode: bool = True
    api_title: str = "EduWork DataBridge API"
    api_version: str = "0.15.0"
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    raw_store_root: Path = Path("var/raw")
    allowed_file_roots: list[Path] = Field(default_factory=lambda: [Path("data/synthetic")])
    max_source_bytes: int = 100 * 1024 * 1024
    max_archive_members: int = 1000
    allow_private_network_sources: bool = False
    http_timeout_seconds: float = 30.0
    export_root: Path = Path("var/exports")
    lineage_root: Path = Path("var/lineage")
    telemetry_enabled: bool = True
    telemetry_service_name: str = "eduwork-databridge"
    demo_identity_enabled: bool = True
    rate_limit_per_minute: int = 120
    max_request_bytes: int = 5 * 1024 * 1024
    raw_retention_days: int = 30
    export_retention_days: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
