"""Server-sent events: chunk assembly, heartbeats, the final ``ur`` chunk, errors, Stream objects."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterator

import httpx
import pytest

from conftest import TEST_KEY, MockGateway
from ultrarouter import (
    APIResponseValidationError,
    AsyncStream,
    AsyncUltraRouter,
    ProviderUnavailableError,
    Stream,
    UltraRouter,
)
from ultrarouter._streaming import SSEDecoder, aiter_chunks, iter_chunks

MESSAGES = [{"role": "user", "content": "hi"}]


def chunk_frame(delta: str) -> str:
    payload = {
        "id": "chatcmpl-1",
        "object": "chat.completion.chunk",
        "created": 1,
        "model": "m",
        "choices": [{"index": 0, "delta": {"content": delta}}],
    }
    return f"data: {json.dumps(payload)}\n\n"


FINAL = (
    "data: "
    + json.dumps(
        {
            "id": "chatcmpl-1",
            "object": "chat.completion.chunk",
            "created": 1,
            "model": "m",
            "choices": [],
            "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
            "ur": {
                "request_id": "req_abc",
                "call_type": None,
                "model_served": "m",
                "provider": "p",
                "routing": {"mode": "off", "fallback_used": False},
                "compression": {"applied": "off"},
                "cost_usd": 0.0001,
                "byok": False,
            },
        }
    )
    + "\n\n"
)


def lines(sse: str) -> Iterator[str]:
    return iter(sse.split("\n"))


def text_of(chunks: list) -> str:  # type: ignore[type-arg]
    return "".join(c.choices[0].delta.content or "" for c in chunks if c.choices)


def test_assembles_content_and_final_ur() -> None:
    sse = chunk_frame("Hello") + ": ping\n\n" + chunk_frame(" world") + FINAL + "data: [DONE]\n\n"
    chunks = list(iter_chunks(lines(sse)))
    assert text_of(chunks) == "Hello world"
    assert chunks[-1].ur is not None and chunks[-1].ur.request_id == "req_abc"
    assert chunks[-1].usage is not None and chunks[-1].usage.total_tokens == 5


def test_stops_at_done_even_with_trailing_frames() -> None:
    sse = chunk_frame("A") + "data: [DONE]\n\n" + chunk_frame("B")
    assert text_of(list(iter_chunks(lines(sse)))) == "A"


def test_trailing_frame_without_blank_line() -> None:
    sse = chunk_frame("A") + chunk_frame("B").rstrip("\n")
    assert text_of(list(iter_chunks(lines(sse)))) == "AB"


def test_crlf_and_multiline_data() -> None:
    decoder = SSEDecoder()
    assert decoder.push("event: custom\r\n") is None
    assert decoder.push("data: line1\r\n") is None
    assert decoder.push("data: line2\r\n") is None
    assert decoder.push("\r\n") == ("custom", "line1\nline2")
    assert decoder.push("\n") is None


def test_error_frame_raises_typed_error() -> None:
    err = 'event: error\ndata: {"error": {"code": "provider_unavailable", "message": "boom", "request_id": "req_err", "retryable": true}}\n\n'
    with pytest.raises(ProviderUnavailableError) as info:
        list(iter_chunks(lines(chunk_frame("x") + err)))
    assert info.value.request_id == "req_err"


def test_malformed_frame_raises() -> None:
    with pytest.raises(APIResponseValidationError):
        list(iter_chunks(lines(chunk_frame("x") + "data: {bad}\n\n")))


def test_chunk_with_wrong_shape_raises() -> None:
    with pytest.raises(APIResponseValidationError):
        list(iter_chunks(lines('data: {"choices": "nope"}\n\n')))


async def test_async_iterator() -> None:
    async def gen() -> AsyncIterator[str]:
        for line in (chunk_frame("A") + chunk_frame("B") + "data: [DONE]\n\n").split("\n"):
            yield line

    chunks = [c async for c in aiter_chunks(gen())]
    assert text_of(chunks) == "AB"


def test_stream_object_against_the_mock(mock_gateway: MockGateway) -> None:
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        stream = client.chat.completions.create(
            model="openai/gpt-5.2-mini", messages=MESSAGES, stream=True
        )
        assert isinstance(stream, Stream)
        with stream:
            pieces = [
                c.choices[0].delta.content
                for c in stream
                if c.choices and c.choices[0].delta.content
            ]
        assert "".join(pieces) == "Hello from the mock gateway."
        assert stream.ur is not None and stream.ur.request_id.startswith("req_")
        assert stream.usage is not None and stream.usage.total_tokens == 19
        request = mock_gateway.requests[-1]
        assert request["body"]["stream"] is True
        assert request["headers"]["accept"] == "text/event-stream"
        assert "idempotency-key" not in request["headers"]


def test_stream_text_helper_and_tool_call_fragments(mock_gateway: MockGateway) -> None:
    tools = [
        {
            "type": "function",
            "function": {
                "name": "lookup",
                "parameters": {"type": "object", "properties": {"q": {"type": "string"}}},
            },
        }
    ]
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        assert (
            client.chat.completions.create(model="m/x", messages=MESSAGES, stream=True).text()
            == "Hello from the mock gateway."
        )
        stream = client.chat.completions.create(
            model="m/x", messages=MESSAGES, tools=tools, stream=True
        )
        fragments = [
            call
            for chunk in stream
            for choice in chunk.choices
            for call in (choice.delta.tool_calls or [])
        ]
        assert fragments[0].function is not None and fragments[0].function.name == "lookup"
        arguments = "".join(f.function.arguments or "" for f in fragments if f.function)
        assert json.loads(arguments) == {"q": "sample-q"}


def test_stream_close_is_idempotent(mock_gateway: MockGateway) -> None:
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        stream = client.chat.completions.create(model="m/x", messages=MESSAGES, stream=True)
        first = next(stream)
        assert first.choices[0].delta.role == "assistant"
        stream.close()
        stream.close()
        assert stream.response.is_closed


def test_stream_http_error_before_body_raises_typed(mock_gateway: MockGateway) -> None:
    mock_gateway.fail("/v1/chat/completions", status=502, code="provider_unavailable")
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url, max_retries=3) as client:
        with pytest.raises(ProviderUnavailableError):
            client.chat.completions.create(model="m/x", messages=MESSAGES, stream=True)
    assert len(mock_gateway.requests) == 1  # streams are never retried


async def test_async_stream_against_the_mock(mock_gateway: MockGateway) -> None:
    async with AsyncUltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        stream = await client.chat.completions.create(model="m/x", messages=MESSAGES, stream=True)
        assert isinstance(stream, AsyncStream)
        async with stream:
            text = await stream.text()
        assert text == "Hello from the mock gateway."
        assert stream.ur is not None
        again = await client.chat.completions.create(model="m/x", messages=MESSAGES, stream=True)
        first = await again.__anext__()
        assert first.choices[0].delta.role == "assistant"
        await again.close()


def test_mocktransport_stream_round_trip() -> None:
    sse = chunk_frame("hey") + FINAL + "data: [DONE]\n\n"
    http = httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, content=sse.encode()))
    )
    with UltraRouter(api_key=TEST_KEY, base_url="http://gw", http_client=http) as client:
        stream = client.chat.completions.create(model="m", messages=MESSAGES, stream=True)
        assert stream.text() == "hey"
        assert stream.ur is not None and stream.ur.cost_usd == 0.0001
    http.close()
