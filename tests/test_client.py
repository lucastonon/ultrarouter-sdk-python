"""Client construction, configuration, request shaping, OpenAI interop and path encoding."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

import ultrarouter
from conftest import TEST_KEY, MockGateway
from ultrarouter import (
    DEFAULT_BASE_URL,
    AsyncUltraRouter,
    UltraRouter,
    UltraRouterError,
)

MESSAGES = [{"role": "user", "content": "hi"}]


def test_missing_api_key_raises_a_clear_error() -> None:
    with pytest.raises(UltraRouterError) as info:
        UltraRouter()
    assert info.value.code == "missing_api_key"
    assert "ULTRAROUTER_API_KEY" in str(info.value)


def test_api_key_and_base_url_from_environment(
    monkeypatch: pytest.MonkeyPatch, mock_gateway: MockGateway
) -> None:
    monkeypatch.setenv("ULTRAROUTER_API_KEY", "ur_sk_test_from_env")
    monkeypatch.setenv("ULTRAROUTER_BASE_URL", mock_gateway.url + "/")
    with UltraRouter() as client:
        assert client.base_url == mock_gateway.url
        client.models.list()
    assert mock_gateway.requests[-1]["headers"]["authorization"] == "Bearer ur_sk_test_from_env"


def test_alias_environment_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UR_API_KEY", "ur_sk_test_alias")
    monkeypatch.setenv("UR_BASE_URL", "http://alias.example")
    with UltraRouter() as client:
        assert client.api_key == "ur_sk_test_alias"
        assert client.base_url == "http://alias.example"


def test_explicit_values_beat_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ULTRAROUTER_API_KEY", "ur_sk_test_env")
    monkeypatch.setenv("ULTRAROUTER_BASE_URL", "http://env.example")
    with UltraRouter(api_key="ur_sk_test_explicit", base_url="http://explicit.example") as client:
        assert (client.api_key, client.base_url) == (
            "ur_sk_test_explicit",
            "http://explicit.example",
        )


def test_default_base_url_and_v1_suffix_normalization() -> None:
    with UltraRouter(api_key="k") as client:
        assert client.base_url == DEFAULT_BASE_URL
    with UltraRouter(api_key="k", base_url="https://gw.example.com/v1/") as client:
        assert client.base_url == "https://gw.example.com"


def test_default_headers_and_user_agent(mock_gateway: MockGateway) -> None:
    with UltraRouter(
        api_key=TEST_KEY, base_url=mock_gateway.url, default_headers={"X-Team": "search"}
    ) as client:
        client.key.get()
    headers = mock_gateway.requests[-1]["headers"]
    assert headers["x-team"] == "search"
    assert headers["user-agent"] == f"ultrarouter-python/{ultrarouter.__version__}"
    assert headers["accept"] == "application/json"


def test_chat_round_trip_with_defaults(mock_gateway: MockGateway) -> None:
    with UltraRouter(
        api_key=TEST_KEY,
        base_url=mock_gateway.url,
        default_model="openai/gpt-5.2-mini",
        defaults={"compression": "semantic_safe", "max_cost_usd": 0.02},
    ) as client:
        reply = client.chat.completions.create(messages=MESSAGES, temperature=0.2)
    assert reply.choices[0].message.content == "Hello from the mock gateway."
    assert reply.ur.model_served == "openai/gpt-5.2-mini"
    assert reply.usage.total_tokens == 19
    body = mock_gateway.requests[-1]["body"]
    assert body == {
        "messages": MESSAGES,
        "temperature": 0.2,
        "model": "openai/gpt-5.2-mini",
        "compression": "semantic_safe",
        "ur": {"max_cost_usd": 0.02},
    }


def test_extra_body_query_headers_and_per_call_options(mock_gateway: MockGateway) -> None:
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        client.chat.completions.create(
            model="m/x",
            messages=MESSAGES,
            extra_body={"vendor_flag": True},
            extra_query={"debug": "1"},
            extra_headers={"X-Trace": "abc"},
            idempotency_key="idem-1",
            timeout=30,
            max_retries=0,
        )
    request = mock_gateway.requests[-1]
    assert request["body"]["vendor_flag"] is True
    assert request["query"] == {"debug": "1"}
    assert request["headers"]["x-trace"] == "abc"
    assert request["headers"]["idempotency-key"] == "idem-1"


def test_structured_output_and_tools(mock_gateway: MockGateway) -> None:
    schema = {
        "type": "json_schema",
        "json_schema": {
            "name": "answer",
            "schema": {
                "type": "object",
                "properties": {"answer": {"type": "string"}, "valid": {"type": "boolean"}},
                "required": ["answer", "valid"],
            },
        },
    }
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "parameters": {"type": "object", "properties": {"city": {"type": "string"}}},
            },
        }
    ]
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        structured = client.chat.completions.create(
            model="m/x", messages=MESSAGES, response_format=schema
        )
        assert json.loads(structured.choices[0].message.content or "") == {
            "answer": "sample-answer",
            "valid": True,
        }
        called = client.chat.completions.create(
            model="m/x", messages=MESSAGES, tools=tools, tool_choice="auto"
        )
    assert called.choices[0].finish_reason == "tool_calls"
    tool_call = (called.choices[0].message.tool_calls or [])[0]
    assert tool_call["function"]["name"] == "get_weather"


def test_embeddings_float_and_base64(mock_gateway: MockGateway) -> None:
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        floats = client.embeddings.create(
            model="openai/text-embedding-3-small", input=["a", "b"], dimensions=4
        )
        assert [len(e.embedding) for e in floats.data] == [4, 4]  # type: ignore[arg-type]
        b64 = client.embeddings.create(
            model="openai/text-embedding-3-small", input="a", encoding_format="base64"
        )
        assert isinstance(b64.data[0].embedding, str)
    assert floats.ur.request_id.startswith("req_")


def test_models_list_and_retrieve(mock_gateway: MockGateway) -> None:
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        models = client.models.list(provider="openai", capability="tools")
        detail = client.models.retrieve("openai/gpt-5.2")
    assert models.object == "list" and len(models.data) == 3
    assert mock_gateway.requests[0]["query"] == {"provider": "openai", "capability": "tools"}
    assert detail.id == "openai/gpt-5.2"
    # the slash in a model id is percent-encoded into one path segment
    assert mock_gateway.requests[1]["path"] == "/v1/models/openai%2Fgpt-5.2"


def test_as_openai_with_injected_class() -> None:
    class FakeOpenAI:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

    with UltraRouter(api_key="ur_sk_test_k", base_url="http://gw") as client:
        made = client.as_openai(FakeOpenAI)
    assert made.kwargs == {"base_url": "http://gw/v1", "api_key": "ur_sk_test_k"}


def test_as_openai_with_the_real_openai_package(sandbox_network: MockGateway) -> None:
    openai = pytest.importorskip("openai")
    with UltraRouter() as client:
        oai = client.as_openai()
        assert isinstance(oai, openai.OpenAI)
        assert str(oai.base_url).rstrip("/") == f"{sandbox_network.url}/v1"
        reply = oai.chat.completions.create(
            model="openai/gpt-5.2-mini", messages=[{"role": "user", "content": "hi"}]
        )
        assert reply.choices[0].message.content == "Hello from the mock gateway."
        oai.close()


async def test_async_as_openai_returns_async_client() -> None:
    openai = pytest.importorskip("openai")
    async with AsyncUltraRouter(api_key="ur_sk_test_k", base_url="http://gw") as client:
        oai = client.as_openai()
        assert isinstance(oai, openai.AsyncOpenAI)
        await oai.close()


def test_with_options_shares_the_pool_and_overrides_defaults(mock_gateway: MockGateway) -> None:
    with UltraRouter(
        api_key=TEST_KEY, base_url=mock_gateway.url, timeout=600, max_retries=2
    ) as client:
        quick = client.with_options(timeout=5, max_retries=0, default_headers={"X-Mode": "quick"})
        assert (quick.timeout, quick.max_retries) == (5.0, 0)
        assert (client.timeout, client.max_retries) == (600.0, 2)
        assert quick._http is client._http
        quick.models.list()
        quick.close()  # does not close the shared pool
        client.models.list()
    assert mock_gateway.requests[0]["headers"]["x-mode"] == "quick"
    assert "x-mode" not in mock_gateway.requests[1]["headers"]


class _Recorder:
    """A MockTransport handler that records requests and answers outcome/reviewer posts."""

    def __init__(self, fail_first: int = 0) -> None:
        self.requests: list[httpx.Request] = []
        self.fail_first = fail_first

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if len(self.requests) <= self.fail_first:
            return httpx.Response(503, json={"error": {"code": "provider_unavailable"}})
        body = json.loads(request.content) if request.content else {}
        if request.url.path.endswith("/reviewer/events"):
            rows = [
                {"event_id": e["event_id"], "status": "accepted", "repairable": False}
                for e in body["events"]
            ]
            return httpx.Response(200, json={"object": "reviewer_events", "data": rows})
        rows = [
            {"status": "accepted", "source_event_id": o["source_event_id"]}
            for o in body["outcomes"]
        ]
        return httpx.Response(202, json={"object": "list", "data": rows})


REVIEW_EVENT = {
    "event_id": "ev1",
    "artifact_key": "a:1",
    "artifact_version": 1,
    "decision": "approved",
    "effective_at": "2026-01-01T00:00:00Z",
}


def test_with_options_clone_delivers_queues_with_its_own_options() -> None:
    recorder = _Recorder(fail_first=1)
    with UltraRouter(
        api_key=TEST_KEY,
        base_url="http://gw",
        max_retries=2,
        _sleep=lambda _: None,
        http_client=httpx.Client(transport=httpx.MockTransport(recorder)),
    ) as client:
        clone = client.with_options(timeout=7, max_retries=0, default_headers={"X-Clone": "1"})
        receipt = clone.outcomes.record("art_1", {"channel": "behavioral", "kind": "accepted"})
        assert receipt.status == "queued", "max_retries=0 on the clone: one attempt, no retry"
        assert len(recorder.requests) == 1
        assert recorder.requests[0].headers["x-clone"] == "1"
        read_timeout = recorder.requests[0].extensions["timeout"]["read"]
        assert 6 < read_timeout <= 7, "the clone's timeout bounds the attempt"
        # shared store: the parent sees the clone's queued event and delivers it with ITS options
        assert client.outcomes.size() == clone.outcomes.size() == 1
        assert client.outcomes.flush().delivered == 1
        assert "x-clone" not in recorder.requests[1].headers
        assert clone.outcomes.size() == 0

        clone.reviewer.record(REVIEW_EVENT)
        assert clone.reviewer.flush().accepted == 1
        assert recorder.requests[2].headers["x-clone"] == "1"
        assert recorder.requests[2].url.path == "/v1/flywheel/reviewer/events"


async def test_async_with_options_clone_delivers_queues_with_its_own_options() -> None:
    recorder = _Recorder(fail_first=1)

    async def no_sleep(_: float) -> None:
        return None

    async with AsyncUltraRouter(
        api_key=TEST_KEY,
        base_url="http://gw",
        max_retries=2,
        _sleep=no_sleep,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(recorder)),
    ) as client:
        clone = client.with_options(timeout=7, max_retries=0, default_headers={"X-Clone": "1"})
        receipt = await clone.outcomes.record(
            "art_1", {"channel": "behavioral", "kind": "accepted"}
        )
        assert receipt.status == "queued"
        assert len(recorder.requests) == 1
        assert recorder.requests[0].headers["x-clone"] == "1"
        assert 6 < recorder.requests[0].extensions["timeout"]["read"] <= 7
        assert (await client.outcomes.flush()).delivered == 1
        assert "x-clone" not in recorder.requests[1].headers
        clone.reviewer.record(REVIEW_EVENT)
        assert (await clone.reviewer.flush()).accepted == 1
        assert recorder.requests[2].headers["x-clone"] == "1"


def test_user_supplied_http_client_is_not_closed() -> None:
    http = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={})))
    client = UltraRouter(api_key="k", base_url="http://gw", http_client=http)
    client.close()
    assert not http.is_closed
    http.close()


def test_sdk_created_http_client_is_closed() -> None:
    client = UltraRouter(api_key="k", base_url="http://gw")
    client.close()
    assert client._http.is_closed


def test_repr_hides_the_key() -> None:
    with UltraRouter(api_key="ur_sk_test_secret", base_url="http://gw") as client:
        assert "secret" not in repr(client)


def test_response_validation_error_on_unexpected_shape() -> None:
    http = httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"unexpected": True}))
    )
    with UltraRouter(api_key="k", base_url="http://gw", http_client=http) as client:
        with pytest.raises(ultrarouter.APIResponseValidationError) as info:
            client.key.get()
    assert info.value.body == {"unexpected": True}
    http.close()


def test_unknown_response_fields_are_kept(mock_gateway: MockGateway) -> None:
    http = httpx.Client(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(
                200, json={"object": "list", "data": [], "brand_new_field": {"x": 1}}
            )
        )
    )
    with UltraRouter(api_key="k", base_url="http://gw", http_client=http) as client:
        models = client.models.list()
    assert models.model_extra == {"brand_new_field": {"x": 1}}
    assert models.to_dict()["brand_new_field"] == {"x": 1}
    http.close()


PATH_CASES = [
    ("call_types.get", lambda c, v: c.call_types.get(v), "/v1/call-types/{}"),
    ("call_types.update", lambda c, v: c.call_types.update(v, model_pin=None), "/v1/call-types/{}"),
    (
        "call_types.enqueue_eval",
        lambda c, v: c.call_types.enqueue_eval(v),
        "/v1/call-types/{}/evals",
    ),
    ("call_types.list_evals", lambda c, v: c.call_types.list_evals(v), "/v1/call-types/{}/evals"),
    (
        "call_types.prompts.list",
        lambda c, v: c.call_types.prompts.list(v),
        "/v1/call-types/{}/prompts",
    ),
    (
        "call_types.verified_memory.get",
        lambda c, v: c.call_types.verified_memory.get(v),
        "/v1/call-types/{}/verified-memory",
    ),
    (
        "requests.feedback",
        lambda c, v: c.requests.feedback(v, rating=-1),
        "/v1/requests/{}/feedback",
    ),
    ("artifacts.get", lambda c, v: c.artifacts.get(v), "/v1/artifacts/{}"),
    (
        "artifacts.final",
        lambda c, v: c.artifacts.final(v, final_hash="0" * 64),
        "/v1/artifacts/{}/final",
    ),
    ("imports.get", lambda c, v: c.imports.get(v), "/v1/imports/{}"),
    ("imports.cancel", lambda c, v: c.imports.cancel(v), "/v1/imports/{}/cancel"),
    ("bench.status", lambda c, v: c.bench.status(v), "/v1/bench/suites/{}/status"),
    ("bench.get", lambda c, v: c.bench.get(v), "/v1/bench/runs/{}"),
    ("bench.gate", lambda c, v: c.bench.gate(v), "/v1/bench/runs/{}/gate"),
    ("flywheel.oracles.get", lambda c, v: c.flywheel.oracles.get(v), "/v1/flywheel/oracles/{}"),
    (
        "flywheel.candidates.confirmation",
        lambda c, v: c.flywheel.candidates.confirmation(v),
        "/v1/flywheel/candidates/{}/confirmation",
    ),
]


@pytest.mark.parametrize(("name", "call", "template"), PATH_CASES, ids=[c[0] for c in PATH_CASES])
def test_ids_are_percent_encoded_into_one_segment(name: str, call: Any, template: str) -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            404,
            json={
                "error": {
                    "code": "not_found",
                    "message": "x",
                    "request_id": "r",
                    "retryable": False,
                }
            },
        )

    hostile = "a/../b?c=d#e f"
    http = httpx.Client(transport=httpx.MockTransport(handler))
    with UltraRouter(api_key="k", base_url="http://gw", http_client=http) as client:
        with pytest.raises(ultrarouter.NotFoundError):
            call(client, hostile)
    http.close()
    assert seen[0].url.raw_path.decode().split("?")[0] == template.format(
        "a%2F..%2Fb%3Fc%3Dd%23e%20f"
    )


def test_generation_id_is_a_query_parameter() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            404,
            json={
                "error": {
                    "code": "not_found",
                    "message": "x",
                    "request_id": "r",
                    "retryable": False,
                }
            },
        )

    http = httpx.Client(transport=httpx.MockTransport(handler))
    with UltraRouter(api_key="k", base_url="http://gw", http_client=http) as client:
        with pytest.raises(ultrarouter.NotFoundError):
            client.generation.get("req_a&b=c")
    http.close()
    assert seen[0].url.params["id"] == "req_a&b=c"
