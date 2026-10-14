"""The total time budget: a real deadline across connecting, waiting and reading the body.

HTTPX read timeouts bound each wait for the next chunk, not the response as a whole, so a
server that drips a body slowly could otherwise stretch a call far past ``timeout``. These tests
drip responses from the mock gateway in chunks that each arrive well within the budget while the
whole body takes much longer.

Streams have their own documented semantics (see docs/streaming.md): ``timeout`` is a deadline
for the response to start (connection and headers), then an idle limit between chunks.
"""

from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import Callable

import httpx
import pytest

from conftest import TEST_KEY, MockGateway
from ultrarouter import APITimeoutError, AsyncUltraRouter, InvalidRequestError, UltraRouter

MESSAGES = [{"role": "user", "content": "hi"}]
BUDGET = 0.5
#: 8 chunks x 0.15 s = 1.2 s in total, each gap far below the 0.5 s budget.
DRIP = {"chunk_delay": 0.15, "chunks": 8}


def test_a_dripping_body_cannot_outlive_the_budget(mock_gateway: MockGateway) -> None:
    mock_gateway.slow("/v1/models", **DRIP)
    with UltraRouter(
        api_key=TEST_KEY, base_url=mock_gateway.url, timeout=BUDGET, max_retries=0
    ) as client:
        started = time.monotonic()
        with pytest.raises(APITimeoutError):
            client.models.list()
        elapsed = time.monotonic() - started
    assert elapsed < BUDGET + 0.3, f"took {elapsed:.2f}s for a {BUDGET}s budget"


def test_a_dripping_post_body_cannot_outlive_a_per_call_budget(mock_gateway: MockGateway) -> None:
    mock_gateway.slow("/v1/chat/completions", **DRIP)
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url, max_retries=0) as client:
        started = time.monotonic()
        with pytest.raises(APITimeoutError):
            client.chat.completions.create(model="m/x", messages=MESSAGES, timeout=BUDGET)
        assert time.monotonic() - started < BUDGET + 0.3


async def test_async_dripping_body_cannot_outlive_the_budget(mock_gateway: MockGateway) -> None:
    mock_gateway.slow("/v1/models", **DRIP)
    async with AsyncUltraRouter(
        api_key=TEST_KEY, base_url=mock_gateway.url, timeout=BUDGET, max_retries=0
    ) as client:
        started = time.monotonic()
        with pytest.raises(APITimeoutError):
            await client.models.list()
        assert time.monotonic() - started < BUDGET + 0.3


def test_slow_headers_hit_the_deadline(mock_gateway: MockGateway) -> None:
    mock_gateway.slow("/v1/key", header_delay=1.5)
    with UltraRouter(
        api_key=TEST_KEY, base_url=mock_gateway.url, timeout=BUDGET, max_retries=0
    ) as client:
        started = time.monotonic()
        with pytest.raises(APITimeoutError):
            client.key.get()
        assert time.monotonic() - started < BUDGET + 0.3


def test_a_fast_enough_drip_still_succeeds(mock_gateway: MockGateway) -> None:
    mock_gateway.slow("/v1/models", chunk_delay=0.02, chunks=4)
    with UltraRouter(
        api_key=TEST_KEY, base_url=mock_gateway.url, timeout=2.0, max_retries=0
    ) as client:
        assert client.models.list().data


def test_the_budget_spans_retries(mock_gateway: MockGateway) -> None:
    mock_gateway.fail("/v1/models", status=503, code="provider_unavailable", times=1)
    mock_gateway.slow("/v1/models", **DRIP)
    with UltraRouter(
        api_key=TEST_KEY,
        base_url=mock_gateway.url,
        timeout=BUDGET,
        max_retries=2,
        _sleep=lambda _: None,
    ) as client:
        started = time.monotonic()
        with pytest.raises(APITimeoutError):
            client.models.list()
        assert time.monotonic() - started < BUDGET + 0.3


# ── streams: deadline to start, then an idle limit between chunks ──


def test_stream_that_does_not_start_in_time_raises(mock_gateway: MockGateway) -> None:
    mock_gateway.slow("/v1/chat/completions", header_delay=1.5)
    with UltraRouter(
        api_key=TEST_KEY, base_url=mock_gateway.url, timeout=BUDGET, max_retries=0
    ) as client:
        started = time.monotonic()
        with pytest.raises(APITimeoutError):
            client.chat.completions.create(model="m/x", messages=MESSAGES, stream=True)
        assert time.monotonic() - started < BUDGET + 0.3


def test_stream_longer_than_the_budget_with_short_gaps_completes(
    mock_gateway: MockGateway,
) -> None:
    mock_gateway.slow("/v1/chat/completions", chunk_delay=0.1)
    with UltraRouter(
        api_key=TEST_KEY, base_url=mock_gateway.url, timeout=0.35, max_retries=0
    ) as client:
        started = time.monotonic()
        stream = client.chat.completions.create(model="m/x", messages=MESSAGES, stream=True)
        assert stream.text() == "Hello from the mock gateway."
        assert time.monotonic() - started > 0.35, "the whole stream outlived the budget"


def test_stream_gap_longer_than_the_budget_raises_a_typed_timeout(
    mock_gateway: MockGateway,
) -> None:
    mock_gateway.slow("/v1/chat/completions", chunk_delay=0.6)
    with UltraRouter(
        api_key=TEST_KEY, base_url=mock_gateway.url, timeout=0.3, max_retries=0
    ) as client:
        stream = client.chat.completions.create(model="m/x", messages=MESSAGES, stream=True)
        with pytest.raises(APITimeoutError):
            stream.text()
        assert stream.response.is_closed


async def test_async_stream_semantics(mock_gateway: MockGateway) -> None:
    async with AsyncUltraRouter(
        api_key=TEST_KEY, base_url=mock_gateway.url, timeout=0.3, max_retries=0
    ) as client:
        mock_gateway.slow("/v1/chat/completions", header_delay=1.0)
        with pytest.raises(APITimeoutError):
            await client.chat.completions.create(model="m/x", messages=MESSAGES, stream=True)
        mock_gateway.slow("/v1/chat/completions", chunk_delay=0.6)
        stream = await client.chat.completions.create(model="m/x", messages=MESSAGES, stream=True)
        with pytest.raises(APITimeoutError):
            await stream.text()
        await asyncio.sleep(0)


# ── no abandoned work: a timed-out call stops its transfer and frees its worker ──


def _request_threads() -> list[threading.Thread]:
    return [t for t in threading.enumerate() if t.name == "ultrarouter-request" and t.is_alive()]


def _wait_until(condition: Callable[[], bool], seconds: float = 3.0) -> bool:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if condition():
            return True
        time.sleep(0.02)
    return condition()


def test_timed_out_calls_stop_consuming_and_close_every_response(
    mock_gateway: MockGateway,
) -> None:
    calls = 4
    # each body drips one byte every 50 ms: it would take well over a minute to finish
    mock_gateway.slow("/v1/models", chunk_delay=0.05, chunks=100_000, times=calls)
    responses: list[httpx.Response] = []
    http = httpx.Client(event_hooks={"response": [responses.append]})
    with UltraRouter(
        api_key=TEST_KEY, base_url=mock_gateway.url, timeout=0.3, max_retries=0, http_client=http
    ) as client:
        for _ in range(calls):
            started = time.monotonic()
            with pytest.raises(APITimeoutError):
                client.models.list()
            assert time.monotonic() - started < 0.3 + 0.3
        assert _wait_until(lambda: not _request_threads()), "request threads still running"
        assert len(responses) == calls
        assert all(response.is_closed for response in responses)
        assert client._worker_slots.free() == client._worker_slots.limit
    http.close()


def test_outstanding_request_threads_are_bounded() -> None:
    gate = threading.Event()

    def stall(request: httpx.Request) -> httpx.Response:
        gate.wait(5)
        return httpx.Response(200, json={"object": "list", "data": []})

    with UltraRouter(
        api_key=TEST_KEY,
        base_url="http://gw",
        timeout=0.2,
        max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(stall)),
    ) as client:
        client._worker_slots = type(client._worker_slots)(2)
        for _ in range(2):
            with pytest.raises(APITimeoutError):
                client.models.list()
        assert len(_request_threads()) == 2
        started = time.monotonic()
        with pytest.raises(APITimeoutError, match="in flight"):
            client.models.list()  # no third thread: the bound is reached
        assert time.monotonic() - started < 0.5
        assert len(_request_threads()) == 2
        gate.set()
        assert _wait_until(lambda: not _request_threads())
        assert client._worker_slots.free() == 2
        assert client.models.list().data == []


def test_streaming_error_body_is_read_within_the_deadline(mock_gateway: MockGateway) -> None:
    mock_gateway.fail("/v1/chat/completions", status=400, code="invalid_request")
    mock_gateway.slow("/v1/chat/completions", chunk_delay=0.1, chunks=12)  # 1.2 s error body
    with UltraRouter(
        api_key=TEST_KEY, base_url=mock_gateway.url, timeout=0.4, max_retries=0
    ) as client:
        started = time.monotonic()
        with pytest.raises(APITimeoutError):
            client.chat.completions.create(model="m/x", messages=MESSAGES, stream=True)
        assert time.monotonic() - started < 0.4 + 0.3
    assert _wait_until(lambda: not _request_threads())


async def test_async_streaming_error_body_is_read_within_the_deadline(
    mock_gateway: MockGateway,
) -> None:
    mock_gateway.fail("/v1/chat/completions", status=400, code="invalid_request")
    mock_gateway.slow("/v1/chat/completions", chunk_delay=0.1, chunks=12)
    responses: list[httpx.Response] = []

    async def record(response: httpx.Response) -> None:
        responses.append(response)

    http = httpx.AsyncClient(event_hooks={"response": [record]})
    async with AsyncUltraRouter(
        api_key=TEST_KEY, base_url=mock_gateway.url, timeout=0.4, max_retries=0, http_client=http
    ) as client:
        started = time.monotonic()
        with pytest.raises(APITimeoutError):
            await client.chat.completions.create(model="m/x", messages=MESSAGES, stream=True)
        assert time.monotonic() - started < 0.4 + 0.3
    assert responses and all(r.is_closed for r in responses)
    await http.aclose()


def test_streaming_error_body_within_the_budget_is_still_typed(mock_gateway: MockGateway) -> None:
    mock_gateway.fail("/v1/chat/completions", status=400, code="invalid_request")
    mock_gateway.slow("/v1/chat/completions", chunk_delay=0.02, chunks=4)
    with UltraRouter(
        api_key=TEST_KEY, base_url=mock_gateway.url, timeout=2.0, max_retries=0
    ) as client:
        with pytest.raises(InvalidRequestError):
            client.chat.completions.create(model="m/x", messages=MESSAGES, stream=True)
