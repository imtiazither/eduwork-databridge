from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from eduwork_databridge.schemas.config import SourceObjectConfig


class ConnectorError(RuntimeError):
    """A safe connector failure with a non-sensitive public code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.safe_message = message


@dataclass(frozen=True)
class ConnectionTestResult:
    ok: bool
    connector: str
    checked_at: datetime
    details: dict[str, str | int | float | bool] = field(default_factory=dict)


@dataclass(frozen=True)
class FieldDiscovery:
    name: str
    observed_type: str
    nullable: bool


@dataclass(frozen=True)
class DiscoveryResult:
    object_key: str
    fields: list[FieldDiscovery]
    sample_count: int
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)


@dataclass(frozen=True)
class ExtractionBatch:
    records: list[dict[str, Any]]
    raw_bytes: bytes
    content_type: str
    cursor: dict[str, Any]
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)


class Connector(ABC):
    connector_type: str
    connector_version = "0.4.0"

    @abstractmethod
    async def test_connection(self) -> ConnectionTestResult:
        raise NotImplementedError

    @abstractmethod
    async def discover_schema(self, source_object: SourceObjectConfig) -> DiscoveryResult:
        raise NotImplementedError

    @abstractmethod
    async def extract(
        self,
        source_object: SourceObjectConfig,
        cursor: dict[str, Any] | None = None,
    ) -> ExtractionBatch:
        raise NotImplementedError

    async def close(self) -> None:
        return None
