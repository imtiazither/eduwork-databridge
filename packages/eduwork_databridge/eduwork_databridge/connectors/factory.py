from pathlib import Path

from eduwork_databridge.connectors.base import Connector, ConnectorError
from eduwork_databridge.connectors.files import (
    CSVConnector,
    JSONConnector,
    ParquetConnector,
    XLSXConnector,
)
from eduwork_databridge.connectors.postgresql import PostgreSQLConnector
from eduwork_databridge.connectors.rest import RESTConnector
from eduwork_databridge.connectors.security import resolve_secret_reference
from eduwork_databridge.schemas.config import SourceConfig
from eduwork_databridge.settings import Settings


def build_connector(source: SourceConfig, settings: Settings) -> Connector:
    allowed_roots = [Path(value) for value in source.allowed_roots] or settings.allowed_file_roots
    max_bytes = min(source.max_bytes, settings.max_source_bytes)
    file_connectors: dict[str, type[Connector]] = {
        "csv": CSVConnector,
        "xlsx": XLSXConnector,
        "json": JSONConnector,
        "parquet": ParquetConnector,
    }
    if source.connector in file_connectors:
        connector_class = file_connectors[source.connector]
        return connector_class(allowed_roots=allowed_roots, max_bytes=max_bytes)  # type: ignore[call-arg]
    secret = resolve_secret_reference(
        source.secret_reference.get_secret_value() if source.secret_reference else None
    )
    if source.connector == "rest":
        if source.base_url is None:
            raise ConnectorError("base_url_required", "REST connector requires a base URL")
        return RESTConnector(
            base_url=str(source.base_url),
            timeout_seconds=source.request_timeout_seconds,
            retry=source.retry,
            allow_private_network=source.allow_private_network
            and settings.allow_private_network_sources,
            bearer_token=secret,
        )
    if source.connector == "postgresql":
        if secret is None:
            raise ConnectorError(
                "database_secret_required",
                "PostgreSQL connector requires an env:// secret reference",
            )
        return PostgreSQLConnector(secret)
    raise ConnectorError("unsupported_connector", "Configured connector is not supported")
