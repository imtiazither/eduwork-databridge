import asyncio
import json
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin

import httpx

from eduwork_databridge.connectors.base import (
    ConnectionTestResult,
    Connector,
    ConnectorError,
    DiscoveryResult,
    ExtractionBatch,
)
from eduwork_databridge.connectors.files import discover_fields
from eduwork_databridge.connectors.security import validate_remote_url
from eduwork_databridge.schemas.config import RetryPolicy, SourceObjectConfig


class RESTConnector(Connector):
    connector_type = "rest"

    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        retry: RetryPolicy,
        allow_private_network: bool = False,
        bearer_token: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout_seconds = timeout_seconds
        self.retry = retry
        self.allow_private_network = allow_private_network
        self.bearer_token = bearer_token
        self.transport = transport

    def _url(self, location: str) -> str:
        url = urljoin(self.base_url, location.lstrip("/"))
        return validate_remote_url(url, self.allow_private_network)

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "User-Agent": "EduWork-DataBridge/0.4.0"}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        return headers

    async def _request(self, client: httpx.AsyncClient, url: str) -> httpx.Response:
        delay = self.retry.initial_seconds
        for attempt in range(1, self.retry.attempts + 1):
            try:
                response = await client.get(url, headers=self._headers())
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt == self.retry.attempts:
                    raise ConnectorError("rest_unavailable", "REST source is unavailable") from exc
            else:
                if response.status_code < 300:
                    return response
                retryable = response.status_code == 429 or response.status_code >= 500
                if not retryable or attempt == self.retry.attempts:
                    raise ConnectorError(
                        "rest_request_failed", f"REST source returned status {response.status_code}"
                    )
            await asyncio.sleep(min(delay, self.retry.maximum_seconds))
            delay = min(delay * 2, self.retry.maximum_seconds)
        raise ConnectorError("rest_unavailable", "REST source is unavailable")

    async def test_connection(self) -> ConnectionTestResult:
        url = validate_remote_url(self.base_url, self.allow_private_network)
        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
            follow_redirects=False,
            transport=self.transport,
        ) as client:
            response = await self._request(client, url)
        return ConnectionTestResult(
            ok=True,
            connector=self.connector_type,
            checked_at=datetime.now(UTC),
            details={"base_url_validated": True, "status_code": response.status_code},
        )

    async def extract(
        self,
        source_object: SourceObjectConfig,
        cursor: dict[str, Any] | None = None,
    ) -> ExtractionBatch:
        url = self._url(source_object.location)
        records_path = str(source_object.options.get("records_path", "items"))
        next_path = str(source_object.options.get("next_path", "next"))
        max_pages = int(source_object.options.get("max_pages", 100))
        page_count = 0
        records: list[dict[str, Any]] = []
        if cursor and cursor.get("next_url"):
            url = validate_remote_url(str(cursor["next_url"]), self.allow_private_network)
        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
            follow_redirects=False,
            transport=self.transport,
        ) as client:
            while url:
                page_count += 1
                if page_count > max_pages:
                    raise ConnectorError("page_limit_exceeded", "REST source exceeded page limit")
                response = await self._request(client, url)
                try:
                    payload: Any = response.json()
                except json.JSONDecodeError as exc:
                    raise ConnectorError(
                        "invalid_json_response", "REST source returned invalid JSON"
                    ) from exc
                if isinstance(payload, list):
                    page_records = payload
                    next_value = None
                elif isinstance(payload, dict):
                    page_records = payload.get(records_path, [])
                    next_value = payload.get(next_path)
                else:
                    raise ConnectorError(
                        "invalid_rest_payload", "REST payload must be an object or list"
                    )
                if not isinstance(page_records, list) or not all(
                    isinstance(item, dict) for item in page_records
                ):
                    raise ConnectorError(
                        "invalid_rest_records", "REST records must be a list of objects"
                    )
                records.extend(dict(item) for item in page_records)
                url = (
                    validate_remote_url(
                        urljoin(str(response.url), str(next_value)), self.allow_private_network
                    )
                    if next_value
                    else ""
                )
        raw = (json.dumps(records, sort_keys=True, separators=(",", ":")) + "\n").encode()
        return ExtractionBatch(
            records=records,
            raw_bytes=raw,
            content_type="application/json",
            cursor={"next_url": None, "pages_completed": page_count},
            metadata={"page_count": page_count, "row_count": len(records)},
        )

    async def discover_schema(self, source_object: SourceObjectConfig) -> DiscoveryResult:
        batch = await self.extract(source_object)
        return discover_fields(batch.records, source_object.key)
