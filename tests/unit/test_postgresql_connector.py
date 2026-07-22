import asyncio
from pathlib import Path

import pytest
from eduwork_databridge.connectors.base import ConnectorError
from eduwork_databridge.connectors.postgresql import PostgreSQLConnector
from eduwork_databridge.schemas.config import SourceObjectConfig
from sqlalchemy import create_engine, text


def test_postgresql_connector_contract_with_sqlite_fixture(tmp_path: Path) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'source.db'}"
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE training_assignments "
                "(assignment_id TEXT, updated_at INTEGER, status TEXT)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO training_assignments VALUES "
                "('A-1', 1, 'assigned'), ('A-2', 2, 'completed')"
            )
        )
    engine.dispose()
    connector = PostgreSQLConnector(database_url, allow_test_sqlite=True)
    source_object = SourceObjectConfig(
        key="training_assignments",
        object_type="table",
        location="training_assignments",
        contract_version="1.0",
        incremental_field="updated_at",
        options={"max_rows": 100},
    )
    discovery = asyncio.run(connector.discover_schema(source_object))
    first = asyncio.run(connector.extract(source_object))
    second = asyncio.run(connector.extract(source_object, {"value": 1}))
    asyncio.run(connector.close())
    assert {field.name for field in discovery.fields} == {"assignment_id", "updated_at", "status"}
    assert len(first.records) == 2
    assert [item["assignment_id"] for item in second.records] == ["A-2"]


def test_postgresql_connector_rejects_non_database_url() -> None:
    with pytest.raises(ConnectorError, match="PostgreSQL"):
        PostgreSQLConnector("https://example.test")
