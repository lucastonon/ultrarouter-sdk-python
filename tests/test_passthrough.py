"""The native passthrough routes: ``POST /v1/responses`` and ``POST /v1/messages``.

Both forward an opaque body verbatim and come back through the client's raw request surface. These
tests prove the realistic body round-trips, the ``X-UR-Request-Id`` / ``X-UR-Cost-Micro-USD``
response headers arrive, and the ``X-UR-*`` request headers reach the gateway, sync and async.
"""

from __future__ import annotations

from typing import Any

import httpx

from conftest import TEST_KEY, MockGateway
from ultrarouter import APIRequest, AsyncUltraRouter, UltraRouter

_TRACE = '{"run": "r-7", "case": "c-3", "stage": "draft", "attempt": 1}'
_UR_HEADERS = {
    "X-UR-Call-Type": "support-reply",
    "X-UR-Trace": _TRACE,
    "X-UR-Timeout-Ms": "30000",
}


def _responses_request() -> APIRequest:
    return APIRequest(
        "POST",
        "/v1/responses",
        body={"model": "gpt-6-sol", "input": "Summarise the ticket."},
        headers=dict(_UR_HEADERS),
    )


def _messages_request() -> APIRequest:
    return APIRequest(
        "POST",
        "/v1/messages",
        body={
            "model": "claude-opus-5-5",
            "max_tokens": 128,
            "messages": [{"role": "user", "content": "Summarise the ticket."}],
        },
        headers=dict(_UR_HEADERS),
    )


def _assert_ur_response_headers(headers: httpx.Headers) -> None:
    assert headers["X-UR-Request-Id"].startswith("req_")
    assert int(headers["X-UR-Cost-Micro-USD"]) >= 0


def _assert_ur_request_forwarded(request: dict[str, Any], method: str, path: str) -> None:
    assert request["method"] == method and request["path"] == path
    # Request headers are sent (and recorded) lower-cased; the ur extensions ride them verbatim.
    assert request["headers"]["x-ur-call-type"] == "support-reply"
    assert request["headers"]["x-ur-trace"] == _TRACE
    assert request["headers"]["x-ur-timeout-ms"] == "30000"
    assert request["headers"].get("idempotency-key"), (
        "a passthrough POST carries an idempotency key"
    )
    assert request["headers"]["authorization"] == f"Bearer {TEST_KEY}"


def test_responses_passthrough_roundtrips_sync(mock_gateway: MockGateway) -> None:
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url, max_retries=0) as client:
        response = client.request(_responses_request())
        body = response.json()
    _assert_ur_response_headers(response.headers)
    assert body["object"] == "response"
    assert body["model"] == "gpt-6-sol"
    assert body["output"][0]["content"][0]["text"]
    assert body["usage"]["total_tokens"] >= 0
    _assert_ur_request_forwarded(mock_gateway.requests[-1], "POST", "/v1/responses")
    assert mock_gateway.requests[-1]["body"]["model"] == "gpt-6-sol"


def test_messages_passthrough_roundtrips_sync(mock_gateway: MockGateway) -> None:
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url, max_retries=0) as client:
        response = client.request(_messages_request())
        body = response.json()
    _assert_ur_response_headers(response.headers)
    assert body["type"] == "message"
    assert body["model"] == "claude-opus-5-5"
    assert body["content"][0]["text"]
    assert body["stop_reason"] == "end_turn"
    assert "output_tokens" in body["usage"]
    _assert_ur_request_forwarded(mock_gateway.requests[-1], "POST", "/v1/messages")
    assert mock_gateway.requests[-1]["body"]["model"] == "claude-opus-5-5"


async def test_responses_passthrough_roundtrips_async(mock_gateway: MockGateway) -> None:
    async with AsyncUltraRouter(
        api_key=TEST_KEY, base_url=mock_gateway.url, max_retries=0
    ) as client:
        response = await client.request(_responses_request())
        body = response.json()
    _assert_ur_response_headers(response.headers)
    assert body["object"] == "response"
    assert body["output"][0]["content"][0]["text"]
    _assert_ur_request_forwarded(mock_gateway.requests[-1], "POST", "/v1/responses")


async def test_messages_passthrough_roundtrips_async(mock_gateway: MockGateway) -> None:
    async with AsyncUltraRouter(
        api_key=TEST_KEY, base_url=mock_gateway.url, max_retries=0
    ) as client:
        message = await client.request_json(_messages_request())
    assert message["type"] == "message"
    assert message["content"][0]["text"]
    assert message["stop_reason"] == "end_turn"
    _assert_ur_request_forwarded(mock_gateway.requests[-1], "POST", "/v1/messages")


def test_passthrough_body_is_sent_without_has_body(mock_gateway: MockGateway) -> None:
    # A non-None body is sent even though the caller did not pass has_body=True.
    request = APIRequest("POST", "/v1/responses", body={"model": "gpt-6-sol", "input": "Hi"})
    assert request.has_body is True
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url, max_retries=0) as client:
        client.request_json(request)
    assert mock_gateway.requests[-1]["body"] == {"model": "gpt-6-sol", "input": "Hi"}
