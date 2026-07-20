import ipaddress
import os
import re
import socket
import zipfile
from pathlib import Path
from urllib.parse import urlparse

from eduwork_databridge.connectors.base import ConnectorError

SAFE_SQL_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
FORMULA_PREFIXES = ("=", "+", "-", "@")


def ensure_allowed_file(
    path: Path,
    allowed_roots: list[Path],
    max_bytes: int,
    allowed_suffixes: set[str],
) -> Path:
    expanded = path.expanduser()
    if expanded.is_symlink():
        raise ConnectorError("symlink_not_allowed", "Symbolic-link source files are not allowed")
    resolved = expanded.resolve(strict=True)
    roots = [root.expanduser().resolve(strict=True) for root in allowed_roots]
    if not any(resolved.is_relative_to(root) for root in roots):
        raise ConnectorError("file_outside_allowed_root", "Source file is outside an allowed root")
    if resolved.suffix.lower() not in allowed_suffixes:
        raise ConnectorError("unsupported_file_type", "Source file type is not allowed")
    if resolved.stat().st_size > max_bytes:
        raise ConnectorError("source_too_large", "Source file exceeds the configured size limit")
    return resolved


def validate_zip_archive(
    path: Path,
    max_members: int = 1000,
    max_total_uncompressed_bytes: int = 500 * 1024 * 1024,
) -> None:
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        if len(members) > max_members:
            raise ConnectorError("archive_too_many_members", "Archive contains too many members")
        total = 0
        for member in members:
            target = Path(member.filename)
            if target.is_absolute() or ".." in target.parts:
                raise ConnectorError(
                    "unsafe_archive_path", "Archive contains an unsafe member path"
                )
            total += member.file_size
            if total > max_total_uncompressed_bytes:
                raise ConnectorError(
                    "archive_too_large", "Archive expands beyond the configured limit"
                )


def sanitize_spreadsheet_cell(value: str) -> str:
    """Prevent derived CSV/XLSX exports from becoming spreadsheet formulas."""
    return f"'{value}" if value.startswith(FORMULA_PREFIXES) else value


def validate_remote_url(url: str, allow_private_network: bool = False) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" and not allow_private_network:
        raise ConnectorError("https_required", "REST sources require HTTPS")
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ConnectorError("invalid_remote_url", "REST source URL is invalid")
    if parsed.username or parsed.password:
        raise ConnectorError("credentials_in_url", "Credentials must not be embedded in a URL")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(parsed.hostname, parsed.port or 443)}
    except socket.gaierror as exc:
        raise ConnectorError(
            "host_resolution_failed", "REST source host could not be resolved"
        ) from exc
    for address in addresses:
        ip = ipaddress.ip_address(address)
        blocked = (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        )
        if blocked and not allow_private_network:
            raise ConnectorError(
                "private_network_blocked", "REST source resolves to a blocked network"
            )
    return url


def validate_sql_identifier(value: str) -> str:
    if not SAFE_SQL_IDENTIFIER.fullmatch(value):
        raise ConnectorError("unsafe_sql_identifier", "Table or column identifier is not allowed")
    return value


def resolve_secret_reference(reference: str | None) -> str | None:
    if reference is None:
        return None
    if not reference.startswith("env://"):
        raise ConnectorError(
            "unsupported_secret_reference", "Only env:// secret references are supported"
        )
    variable = reference.removeprefix("env://")
    if not SAFE_SQL_IDENTIFIER.fullmatch(variable):
        raise ConnectorError("invalid_secret_reference", "Secret reference name is invalid")
    value = os.getenv(variable)
    if not value:
        raise ConnectorError("secret_not_available", "Referenced secret is not available")
    return value
