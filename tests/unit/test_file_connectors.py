import asyncio
from pathlib import Path

import pytest
from eduwork_databridge.connectors.base import ConnectorError
from eduwork_databridge.connectors.files import (
    CSVConnector,
    JSONConnector,
    ParquetConnector,
    XLSXConnector,
)
from eduwork_databridge.schemas.config import SourceObjectConfig


@pytest.mark.parametrize(
    ("connector_class", "relative", "object_key", "expected"),
    [
        (CSVConnector, "small/hris/employees.csv", "employees", 120),
        (JSONConnector, "small/lms/participation.json", "participation", 366),
        (XLSXConnector, "small/assessment/assessment_results.xlsx", "assessment_results", 120),
        (ParquetConnector, "small/credential/credential_awards.parquet", "credential_awards", 25),
    ],
)
def test_file_connectors_extract_and_discover(
    connector_class, relative: str, object_key: str, expected: int
) -> None:
    root = Path("data/synthetic")
    connector = connector_class([root], 100 * 1024 * 1024)
    source_object = SourceObjectConfig(
        key=object_key,
        object_type="file",
        location=str(root / relative),
        contract_version="1.0",
        sheet_name="assessment_results" if relative.endswith(".xlsx") else None,
    )
    batch = asyncio.run(connector.extract(source_object))
    discovery = asyncio.run(connector.discover_schema(source_object))
    assert len(batch.records) == expected
    assert batch.raw_bytes
    assert batch.cursor["sha256"]
    assert discovery.fields
    unchanged = asyncio.run(connector.extract(source_object, batch.cursor))
    assert unchanged.records == []
    assert unchanged.metadata["unchanged"] is True


def test_file_connector_rejects_path_outside_allowed_root(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside.csv"
    outside.write_text("id\n1\n", encoding="utf-8")
    connector = CSVConnector([allowed], 1024)
    source_object = SourceObjectConfig(
        key="outside",
        object_type="file",
        location=str(outside),
        contract_version="1.0",
    )
    with pytest.raises(ConnectorError, match="outside an allowed root"):
        asyncio.run(connector.extract(source_object))


def test_file_connector_enforces_size_limit(tmp_path: Path) -> None:
    source = tmp_path / "large.csv"
    source.write_text("id\n" + "1\n" * 20, encoding="utf-8")
    connector = CSVConnector([tmp_path], 10)
    source_object = SourceObjectConfig(
        key="large", object_type="file", location=str(source), contract_version="1.0"
    )
    with pytest.raises(ConnectorError, match="size limit"):
        asyncio.run(connector.extract(source_object))
