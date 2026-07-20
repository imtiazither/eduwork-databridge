import asyncio

import httpx
import pytest
from eduwork_databridge.connectors.base import ConnectorError
from eduwork_databridge.connectors.rest import RESTConnector
from eduwork_databridge.schemas.config import RetryPolicy, SourceObjectConfig


def test_rest_connector_handles_pagination_and_retry() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503, request=request)
        if request.url.path.endswith("page2"):
            return httpx.Response(200, json={"items": [{"id": "2"}], "next": None}, request=request)
        return httpx.Response(200, json={"items": [{"id": "1"}], "next": "/page2"}, request=request)

    connector = RESTConnector(
        base_url="http://testserver/",
        timeout_seconds=2,
        retry=RetryPolicy(attempts=2, initial_seconds=0.001, maximum_seconds=0.001),
        allow_private_network=True,
        transport=httpx.MockTransport(handler),
    )
    source_object = SourceObjectConfig(
        key="items",
        object_type="api_resource",
        location="items",
        contract_version="1.0",
        options={"records_path": "items", "next_path": "next", "max_pages": 5},
    )
    batch = asyncio.run(connector.extract(source_object))
    assert [item["id"] for item in batch.records] == ["1", "2"]
    assert batch.metadata["page_count"] == 2
    assert calls == 3


def test_rest_connector_rejects_non_retryable_status() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, request=request)

    connector = RESTConnector(
        base_url="http://testserver/",
        timeout_seconds=2,
        retry=RetryPolicy(attempts=2, initial_seconds=0.001, maximum_seconds=0.001),
        allow_private_network=True,
        transport=httpx.MockTransport(handler),
    )
    source_object = SourceObjectConfig(
        key="items", object_type="api_resource", location="items", contract_version="1.0"
    )
    with pytest.raises(ConnectorError, match="status 401"):
        asyncio.run(connector.extract(source_object))


def test_rest_connection_test_performs_safe_request() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(204, request=request)

    connector = RESTConnector(
        base_url="http://testserver/",
        timeout_seconds=2,
        retry=RetryPolicy(attempts=1),
        allow_private_network=True,
        transport=httpx.MockTransport(handler),
    )
    result = asyncio.run(connector.test_connection())
    assert result.ok is True
    assert result.details["status_code"] == 204
