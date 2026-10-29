"""Request and episode correlation: client-minted request ids, episode keys, request ids on every
result shape (non-streaming, streaming, the ``openai`` package via ``as_openai()``), and on errors."""

from __future__ import annotations

import importlib.util
import re
from typing import Any

import httpx
import pytest

import ultrarouter
from conftest import TEST_KEY, MockGateway
from ultrarouter import (
    EPISODE_HEADER,
    REQUEST_ID_HEADER,
    APITimeoutError,
    AsyncUltraRouter,
    InvalidRequestError,
    UltraRouter,
    correlation_headers,
    is_valid_request_id,
    new_episode_key,
    new_request_id,
    request_id_of,
)
from ultrarouter._correlation import validate_episode_key

MESSAGES = [{"role": "user", "content": "Hi"}]
MODEL = "openai/gpt-5.2-mini"


def _sent(gateway: MockGateway, path: str = "/v1/chat/completions") -> list[dict[str, Any]]:
    return [r for r in gateway.requests if r["path"] == path]


# ── pure helpers ──


def test_new_request_id_is_client_prefixed_and_valid() -> None:
    minted = {new_request_id() for _ in range(200)}
    assert len(minted) == 200
    for value in minted:
        assert re.fullmatch(r"req_c_[0-9A-HJKMNP-TV-Z]{26}", value), value
        assert is_valid_request_id(value)


@pytest.mark.parametrize(
    ("value", "valid"),
    [
        ("req_01J", True),
        ("a", True),
        ("A-b_9", True),
        ("x" * 64, True),
        ("x" * 65, False),
        ("", False),
        ("req 1", False),
        ("req.1", False),
        ("réq", False),
        (None, False),
        (7, False),
    ],
)
def test_request_id_pattern(value: Any, valid: bool) -> None:
    assert is_valid_request_id(value) is valid


def test_new_episode_key() -> None:
    key = new_episode_key()
    assert re.fullmatch(r"ep_[0-9A-Z]{26}", key)
    assert new_episode_key("order:A-100").startswith("order:A-100_")


@pytest.mark.parametrize(
    ("key", "valid"),
    [
        ("order:A-100", True),
        ("ticket 4812 reply", True),
        ("x" * 256, True),
        ("x" * 257, False),
        ("", False),
        (" leading", False),
        ("trailing ", False),
        ("tab\there", False),
        ("naïve", False),
        ("line\nbreak", False),
    ],
)
def test_episode_key_validation(key: str, valid: bool) -> None:
    if valid:
        assert validate_episode_key(key) == key
    else:
        with pytest.raises(InvalidRequestError) as info:
            validate_episode_key(key)
        assert info.value.status == 0
        assert "ur.artifact" in info.value.message


def test_correlation_headers() -> None:
    assert correlation_headers() == {}
    assert correlation_headers(request_id="req_c_1") == {REQUEST_ID_HEADER: "req_c_1"}
    assert correlation_headers(episode_key="ep_1") == {EPISODE_HEADER: "ep_1"}
    assert REQUEST_ID_HEADER == "x-ur-request-id" and EPISODE_HEADER == "x-ur-artifact"
    with pytest.raises(InvalidRequestError):
        correlation_headers(request_id="bad id")


def test_request_id_of_shapes() -> None:
    from ultrarouter.types import ChatCompletion

    completion = ChatCompletion.model_validate(
        {
            "id": "c",
            "object": "chat.completion",
            "created": 1,
            "model": MODEL,
            "choices": [],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            "ur": {
                "request_id": "req_body",
                "byok": False,
                "call_type": None,
                "compression": {"applied": "off"},
                "cost_usd": 0,
                "model_served": MODEL,
                "provider": "openai",
                "routing": {"mode": "off", "fallback_used": False},
            },
        }
    )
    assert request_id_of(completion) == "req_body"
    assert request_id_of("req_direct") == "req_direct"
    assert request_id_of({"ur": {"request_id": "req_map"}}) == "req_map"
    response = httpx.Response(200, headers={REQUEST_ID_HEADER: "req_header"})
    assert request_id_of(response) == "req_header"

    class Wrapped:
        """An object holding a response (like the openai raw-response wrapper)."""

        response = httpx.Response(200, headers={REQUEST_ID_HEADER: "req_wrapped"})

    assert request_id_of(Wrapped()) == "req_wrapped"

    class Extra:
        """A pydantic-like object keeping ``ur`` as an extra field."""

        model_extra = {"ur": {"request_id": "req_extra"}}  # noqa: RUF012 - a test double

    assert request_id_of(Extra()) == "req_extra"
    for bad in (object(), {}, "", "bad id", httpx.Response(200)):
        with pytest.raises(InvalidRequestError):
            request_id_of(bad)


# ── on the wire ──


def test_chat_sends_correlation_headers_and_the_gateway_echoes(
    mock_gateway: MockGateway,
) -> None:
    rid = new_request_id()
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        reply = client.chat.completions.create(
            model=MODEL, messages=MESSAGES, request_id=rid, episode_key="order:A-100"
        )
    assert reply.ur.request_id == rid
    (sent,) = _sent(mock_gateway)
    assert sent["headers"][REQUEST_ID_HEADER] == rid
    assert sent["headers"][EPISODE_HEADER] == "order:A-100"
    assert request_id_of(reply) == rid


def test_without_options_no_correlation_headers_are_sent(mock_gateway: MockGateway) -> None:
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        reply = client.chat.completions.create(model=MODEL, messages=MESSAGES)
    (sent,) = _sent(mock_gateway)
    assert REQUEST_ID_HEADER not in sent["headers"]
    assert EPISODE_HEADER not in sent["headers"]
    assert reply.ur.request_id.startswith("req_")  # gateway-minted


def test_client_mode_mints_a_request_id_for_every_call(mock_gateway: MockGateway) -> None:
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url, request_ids="client") as client:
        first = client.chat.completions.create(model=MODEL, messages=MESSAGES)
        second = client.embeddings.create(model="openai/text-embedding-3-small", input="a")
        explicit = client.chat.completions.create(
            model=MODEL, messages=MESSAGES, request_id="req_mine"
        )
    assert first.ur.request_id.startswith("req_c_")
    assert second.ur.request_id.startswith("req_c_")
    assert first.ur.request_id != second.ur.request_id
    assert explicit.ur.request_id == "req_mine"
    assert client.with_options(timeout=5).request_ids == "client"


def test_request_ids_mode_is_validated() -> None:
    with pytest.raises(ValueError, match="request_ids"):
        UltraRouter(api_key=TEST_KEY, base_url="http://x", request_ids="sometimes")  # type: ignore[arg-type]


def test_invalid_request_id_is_refused_before_any_network(mock_gateway: MockGateway) -> None:
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        with pytest.raises(InvalidRequestError):
            client.chat.completions.create(model=MODEL, messages=MESSAGES, request_id="no spaces")
        with pytest.raises(InvalidRequestError):
            client.chat.completions.create(model=MODEL, messages=MESSAGES, episode_key=" x")
    assert mock_gateway.requests == []


def test_every_retry_carries_the_same_request_id(mock_gateway: MockGateway) -> None:
    mock_gateway.fail("/v1/chat/completions", status=503, times=2)
    rid = new_request_id()
    with UltraRouter(
        api_key=TEST_KEY, base_url=mock_gateway.url, max_retries=2, _sleep=lambda _s: None
    ) as client:
        reply = client.chat.completions.create(model=MODEL, messages=MESSAGES, request_id=rid)
    sent = _sent(mock_gateway)
    assert len(sent) == 3
    assert {r["headers"][REQUEST_ID_HEADER] for r in sent} == {rid}
    assert reply.ur.request_id == rid


def test_an_error_without_an_answer_reports_the_minted_id(mock_gateway: MockGateway) -> None:
    mock_gateway.slow("/v1/chat/completions", header_delay=1.0)
    rid = new_request_id()
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url, timeout=0.2) as client:
        with pytest.raises(APITimeoutError) as info:
            client.chat.completions.create(model=MODEL, messages=MESSAGES, request_id=rid)
    assert info.value.request_id == rid


def test_a_gateway_error_keeps_the_gateways_request_id(mock_gateway: MockGateway) -> None:
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        with pytest.raises(ultrarouter.ModelUnpricedError) as info:
            client.chat.completions.create(
                model="acme/unpriced-model", messages=MESSAGES, request_id="req_c_mine"
            )
    assert info.value.request_id is not None and info.value.request_id != "req_c_mine"


def test_stream_request_id_is_known_before_the_first_chunk(mock_gateway: MockGateway) -> None:
    rid = new_request_id()
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        with client.chat.completions.create(
            model=MODEL, messages=MESSAGES, stream=True, request_id=rid, episode_key="ep_s"
        ) as stream:
            assert stream.request_id == rid  # from the header, nothing iterated yet
            assert stream.ur is None
            stream.text()
            assert stream.ur is not None and stream.ur.request_id == rid
        gateway_minted = client.chat.completions.create(model=MODEL, messages=MESSAGES, stream=True)
        with gateway_minted:
            assert gateway_minted.request_id is not None
            assert gateway_minted.request_id.startswith("req_")
            gateway_minted.text()
    assert request_id_of(stream) == rid
    assert _sent(mock_gateway)[0]["headers"][EPISODE_HEADER] == "ep_s"


def test_stream_request_id_falls_back_to_the_ur_block_and_the_sent_id() -> None:
    from ultrarouter import Stream

    frames = (
        b'data: {"id":"c","object":"chat.completion.chunk","created":1,"model":"m","choices":[],'
        b'"ur":{"request_id":"req_from_body","byok":false,"call_type":null,'
        b'"compression":{"applied":"off"},"cost_usd":0,"model_served":"m","provider":"p",'
        b'"routing":{"mode":"off","fallback_used":false}}}\n\ndata: [DONE]\n\n'
    )
    request = httpx.Request("POST", "http://x/v1/chat/completions", headers={})
    stream = Stream(httpx.Response(200, content=frames, request=request))
    assert stream.request_id is None
    stream.text()
    assert stream.request_id == "req_from_body"
    sent = httpx.Request("POST", "http://x", headers={REQUEST_ID_HEADER: "req_sent"})
    assert Stream(httpx.Response(200, content=b"", request=sent)).request_id == "req_sent"
    assert Stream(httpx.Response(200, content=b"")).request_id is None


async def test_async_correlation_and_stream(mock_gateway: MockGateway) -> None:
    rid = new_request_id()
    async with AsyncUltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        reply = await client.chat.completions.create(
            model=MODEL, messages=MESSAGES, request_id=rid, episode_key="ep_a"
        )
        assert reply.ur.request_id == rid
        stream_id = new_request_id()
        stream = await client.chat.completions.create(
            model=MODEL, messages=MESSAGES, stream=True, request_id=stream_id
        )
        async with stream:
            assert stream.request_id == stream_id
            await stream.text()
        vectors = await client.embeddings.create(
            model="openai/text-embedding-3-small", input="a", request_id="req_c_emb"
        )
    assert vectors.ur is not None and vectors.ur.request_id == "req_c_emb"
    sent = _sent(mock_gateway)
    assert sent[0]["headers"][EPISODE_HEADER] == "ep_a"
    assert sent[1]["headers"][REQUEST_ID_HEADER] == stream_id


async def test_async_client_mode_and_error_attachment(mock_gateway: MockGateway) -> None:
    mock_gateway.slow("/v1/chat/completions", header_delay=1.0)
    async with AsyncUltraRouter(
        api_key=TEST_KEY, base_url=mock_gateway.url, request_ids="client", timeout=0.2
    ) as client:
        with pytest.raises(APITimeoutError) as info:
            await client.chat.completions.create(model=MODEL, messages=MESSAGES)
    assert info.value.request_id is not None and info.value.request_id.startswith("req_c_")


@pytest.mark.skipif(importlib.util.find_spec("openai") is None, reason="needs the openai package")
def test_as_openai_path_carries_and_reads_the_request_id(mock_gateway: MockGateway) -> None:
    rid = new_request_id()
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        chat = client.as_openai()
        reply = chat.chat.completions.create(
            model=MODEL,
            messages=MESSAGES,
            extra_headers=correlation_headers(request_id=rid, episode_key="ep_openai"),
        )
        assert request_id_of(reply) == rid
        raw = chat.chat.completions.with_raw_response.create(
            model=MODEL,
            messages=MESSAGES,
            extra_headers=correlation_headers(request_id="req_c_raw"),
        )
        assert request_id_of(raw) == "req_c_raw"
        streamed = chat.chat.completions.create(
            model=MODEL,
            messages=MESSAGES,
            stream=True,
            extra_headers=correlation_headers(request_id="req_c_stream"),
        )
        assert request_id_of(streamed) == "req_c_stream"  # from the response headers
        last = None
        for chunk in streamed:
            last = chunk
        assert last is not None and request_id_of(last) == "req_c_stream"  # the final ur block
        chat.close()
    first = _sent(mock_gateway)[0]
    assert first["headers"][REQUEST_ID_HEADER] == rid
    assert first["headers"][EPISODE_HEADER] == "ep_openai"
