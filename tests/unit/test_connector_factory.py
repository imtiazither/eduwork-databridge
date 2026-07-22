import asyncio
from pathlib import Path

from eduwork_databridge.connectors.factory import build_connector
from eduwork_databridge.connectors.files import CSVConnector
from eduwork_databridge.connectors.postgresql import PostgreSQLConnector
from eduwork_databridge.connectors.rest import RESTConnector
from eduwork_databridge.schemas.config import SourceConfig
from eduwork_databridge.settings import Settings


def source_values(connector: str) -> dict:
    return {
        "source_id": f"demo_{connector}",
        "name": "Synthetic Source",
        "connector": connector,
        "owner_role": "Owner",
        "data_classification": "internal",
        "objects": [
            {
                "key": "items",
                "object_type": "file" if connector == "csv" else "api_resource",
                "location": "data/synthetic/small/hris/employees.csv",
                "contract_version": "1.0",
            }
        ],
    }


def test_factory_builds_file_and_rest_connectors() -> None:
    settings = Settings(
        environment="test",
        allowed_file_roots=[Path("data/synthetic")],
        allow_private_network_sources=True,
    )
    csv_config = SourceConfig.model_validate(source_values("csv"))
    rest_values = source_values("rest")
    rest_values["base_url"] = "https://example.test/"
    rest_config = SourceConfig.model_validate(rest_values)
    assert isinstance(build_connector(csv_config, settings), CSVConnector)
    assert isinstance(build_connector(rest_config, settings), RESTConnector)


def test_factory_resolves_postgresql_secret(monkeypatch) -> None:
    monkeypatch.setenv(
        "EDUWORK_TEST_DATABASE_URL", "postgresql+psycopg://user:pass@example.test/db"
    )
    values = source_values("postgresql")
    values["secret_reference"] = "env://EDUWORK_TEST_DATABASE_URL"
    values["objects"][0]["object_type"] = "table"
    values["objects"][0]["location"] = "public.assignments"
    config = SourceConfig.model_validate(values)
    connector = build_connector(config, Settings(environment="test"))
    assert isinstance(connector, PostgreSQLConnector)
    asyncio.run(connector.close())
