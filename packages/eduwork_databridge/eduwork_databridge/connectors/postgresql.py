import asyncio
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import MetaData, Table, create_engine, inspect, select, text
from sqlalchemy.engine import Engine

from eduwork_databridge.connectors.base import (
    ConnectionTestResult,
    Connector,
    ConnectorError,
    DiscoveryResult,
    ExtractionBatch,
    FieldDiscovery,
)
from eduwork_databridge.connectors.security import validate_sql_identifier
from eduwork_databridge.schemas.config import SourceObjectConfig


class PostgreSQLConnector(Connector):
    connector_type = "postgresql"

    def __init__(self, database_url: str, allow_test_sqlite: bool = False) -> None:
        if not database_url.startswith(("postgresql", "postgres")) and not (
            allow_test_sqlite and database_url.startswith("sqlite")
        ):
            raise ConnectorError("postgresql_url_required", "PostgreSQL database URL is required")
        self.database_url = database_url
        self.engine: Engine = create_engine(database_url, pool_pre_ping=True)

    def _table_parts(self, location: str) -> tuple[str | None, str]:
        parts = location.split(".")
        if len(parts) == 1:
            return None, validate_sql_identifier(parts[0])
        if len(parts) == 2:
            return validate_sql_identifier(parts[0]), validate_sql_identifier(parts[1])
        raise ConnectorError(
            "invalid_table_location", "Table location must be table or schema.table"
        )

    async def test_connection(self) -> ConnectionTestResult:
        def check() -> None:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))

        await asyncio.to_thread(check)
        return ConnectionTestResult(
            ok=True,
            connector=self.connector_type,
            checked_at=datetime.now(UTC),
            details={"database_reachable": True},
        )

    async def discover_schema(self, source_object: SourceObjectConfig) -> DiscoveryResult:
        schema, table_name = self._table_parts(source_object.location)

        def discover() -> DiscoveryResult:
            columns = inspect(self.engine).get_columns(table_name, schema=schema)
            if not columns:
                raise ConnectorError("table_not_found", "Configured source table was not found")
            fields = [
                FieldDiscovery(
                    name=str(column["name"]),
                    observed_type=str(column["type"]),
                    nullable=bool(column["nullable"]),
                )
                for column in columns
            ]
            return DiscoveryResult(
                object_key=source_object.key,
                fields=fields,
                sample_count=0,
                metadata={"table": table_name, "schema": schema or "default"},
            )

        return await asyncio.to_thread(discover)

    async def extract(
        self,
        source_object: SourceObjectConfig,
        cursor: dict[str, Any] | None = None,
    ) -> ExtractionBatch:
        schema, table_name = self._table_parts(source_object.location)
        max_rows = int(source_object.options.get("max_rows", 100_000))
        if max_rows <= 0 or max_rows > 5_000_000:
            raise ConnectorError(
                "invalid_row_limit", "PostgreSQL max_rows is outside allowed range"
            )

        def read() -> ExtractionBatch:
            table = Table(table_name, MetaData(), schema=schema, autoload_with=self.engine)
            statement = select(table)
            incremental = source_object.incremental_field
            if incremental:
                validate_sql_identifier(incremental)
                if incremental not in table.c:
                    raise ConnectorError(
                        "incremental_field_missing", "Incremental field was not found"
                    )
                if cursor and cursor.get("value") is not None:
                    statement = statement.where(table.c[incremental] > cursor["value"])
                statement = statement.order_by(table.c[incremental])
            statement = statement.limit(max_rows)
            with self.engine.connect() as connection:
                rows = [dict(row) for row in connection.execute(statement).mappings()]
            cursor_value: Any = None
            if incremental and rows:
                cursor_value = rows[-1][incremental]
                if isinstance(cursor_value, datetime):
                    cursor_value = cursor_value.isoformat()
            raw = (
                json.dumps(rows, sort_keys=True, default=str, separators=(",", ":")) + "\n"
            ).encode()
            return ExtractionBatch(
                records=rows,
                raw_bytes=raw,
                content_type="application/x-ndjson",
                cursor={"field": incremental, "value": cursor_value},
                metadata={"row_count": len(rows), "table": table_name},
            )

        return await asyncio.to_thread(read)

    async def close(self) -> None:
        await asyncio.to_thread(self.engine.dispose)
