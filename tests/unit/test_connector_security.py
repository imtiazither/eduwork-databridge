import socket
import zipfile
from pathlib import Path

import pytest
from eduwork_databridge.connectors.base import ConnectorError
from eduwork_databridge.connectors.security import (
    resolve_secret_reference,
    sanitize_spreadsheet_cell,
    validate_remote_url,
    validate_sql_identifier,
    validate_zip_archive,
)


def test_remote_url_blocks_http_and_private_destinations(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ConnectorError, match="HTTPS"):
        validate_remote_url("http://example.com/data")

    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))],
    )
    with pytest.raises(ConnectorError, match="blocked network"):
        validate_remote_url("https://example.test/data")


def test_remote_url_rejects_embedded_credentials() -> None:
    with pytest.raises(ConnectorError, match="embedded"):
        validate_remote_url("https://user:secret@example.com/data", allow_private_network=True)


def test_sql_identifier_and_secret_reference(monkeypatch: pytest.MonkeyPatch) -> None:
    assert validate_sql_identifier("training_assignments") == "training_assignments"
    with pytest.raises(ConnectorError):
        validate_sql_identifier("training;drop table")
    monkeypatch.setenv("EDUWORK_TEST_SECRET", "synthetic-secret")
    assert resolve_secret_reference("env://EDUWORK_TEST_SECRET") == "synthetic-secret"
    with pytest.raises(ConnectorError):
        resolve_secret_reference("literal://secret")


def test_spreadsheet_sanitizer() -> None:
    assert sanitize_spreadsheet_cell("=2+2") == "'=2+2"
    assert sanitize_spreadsheet_cell("safe") == "safe"


def test_zip_archive_rejects_traversal(tmp_path: Path) -> None:
    archive_path = tmp_path / "unsafe.xlsx"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("../escape.txt", "synthetic")
    with pytest.raises(ConnectorError, match="unsafe member"):
        validate_zip_archive(archive_path)
