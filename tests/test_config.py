"""Client defaults vs per-call precedence, the Autopilot ceiling, and Bench tagging."""

from __future__ import annotations

import json
import warnings
from collections.abc import Iterator
from typing import Any

import httpx
import pytest

from ultrarouter import AsyncUltraRouter, UltraRouter
from ultrarouter._config import (
    AUTOPILOT_ROUTER,
    apply_chat_defaults,
    apply_embedding_defaults,
    clamp_router_downgrade,
    resolve_bench,
)

MESSAGES = [{"role": "user", "content": "hi"}]
CHAT = {
    "id": "c1",
    "object": "chat.completion",
    "created": 1,
    "model": "m",
    "choices": [
        {"index": 0, "message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}
    ],
    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    "ur": {
        "request_id": "req_1",
        "call_type": None,
        "model_served": "m",
        "provider": "p",
        "routing": {"mode": "off", "fallback_used": False},
        "compression": {"applied": "off"},
        "cost_usd": 0.0,
        "byok": False,
    },
}


class Recorder:
    """An httpx MockTransport handler that records requests and answers with ``CHAT``."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(200, json=CHAT)

    @property
    def body(self) -> dict[str, Any]:
        return json.loads(self.requests[-1].content)


@pytest.fixture
def recorder() -> Recorder:
    return Recorder()


@pytest.fixture
def client_factory(recorder: Recorder) -> Iterator[Any]:
    made: list[UltraRouter] = []

    def make(**kwargs: Any) -> UltraRouter:
        kwargs.setdefault("api_key", "ur_sk_test_1")
        client = UltraRouter(
            base_url="http://gw",
            http_client=httpx.Client(transport=httpx.MockTransport(recorder)),
            **kwargs,
        )
        made.append(client)
        return client

    yield make
    for client in made:
        client._http.close()


# ── precedence (pure) ──


def test_default_model_used_when_omitted() -> None:
    assert apply_chat_defaults({"messages": MESSAGES}, "a/b", {})["model"] == "a/b"


def test_per_call_model_wins() -> None:
    assert apply_chat_defaults({"messages": MESSAGES, "model": "c/d"}, "a/b", {})["model"] == "c/d"


def test_no_model_anywhere_omits_the_field() -> None:
    assert "model" not in apply_chat_defaults({"messages": MESSAGES}, None, {})


def test_all_defaults_applied() -> None:
    defaults = {
        "router": "off",
        "compression": "semantic_safe",
        "call_type": "support-reply",
        "provider": {"sort": "price"},
        "max_cost_usd": 0.25,
    }
    body = apply_chat_defaults({"messages": MESSAGES}, None, defaults)
    assert body["router"] == "off"
    assert body["compression"] == "semantic_safe"
    assert body["call_type"] == "support-reply"
    assert body["provider"] == {"sort": "price"}
    assert body["ur"] == {"max_cost_usd": 0.25}


def test_per_call_values_win_over_every_default() -> None:
    defaults = {
        "router": "off",
        "compression": "off",
        "call_type": "a",
        "provider": {"sort": "price"},
        "max_cost_usd": 0.25,
    }
    body = apply_chat_defaults(
        {
            "messages": MESSAGES,
            "router": "auto",
            "compression": {"mode": "adaptive"},
            "call_type": "b",
            "provider": {"sort": "latency"},
            "ur": {"max_cost_usd": 1},
        },
        None,
        defaults,
    )
    assert body["router"] == "auto"
    assert body["compression"] == {"mode": "adaptive"}
    assert body["call_type"] == "b"
    assert body["provider"] == {"sort": "latency"}
    assert body["ur"]["max_cost_usd"] == 1


def test_ur_default_merges_with_per_call_ur() -> None:
    body = apply_chat_defaults(
        {"messages": MESSAGES, "ur": {"trace_id": "t1"}}, None, {"max_cost_usd": 0.5}
    )
    assert body["ur"] == {"max_cost_usd": 0.5, "trace_id": "t1"}


def test_none_values_mean_not_given() -> None:
    body = apply_chat_defaults(
        {"messages": MESSAGES, "temperature": None, "model": None}, "a/b", {}
    )
    assert body == {"messages": MESSAGES, "model": "a/b"}


def test_embedding_defaults() -> None:
    body = apply_embedding_defaults({"input": "x"}, "e/1", {"call_type": "ct", "router": "auto"})
    assert body == {"input": "x", "model": "e/1", "call_type": "ct"}
    override = apply_embedding_defaults(
        {"input": "x", "model": "e/2", "call_type": "o"}, "e/1", {"call_type": "ct"}
    )
    assert (override["model"], override["call_type"]) == ("e/2", "o")


# ── Autopilot ──


def test_autopilot_router_mapping() -> None:
    assert dict(AUTOPILOT_ROUTER) == {"audit": "off", "recommend": "candidates", "auto": "auto"}


def test_clamp_router_downgrade() -> None:
    assert clamp_router_downgrade("auto", "off") == "off"
    assert clamp_router_downgrade("candidates", "off") == "off"
    assert clamp_router_downgrade("off", "auto") == "off"
    assert clamp_router_downgrade("candidates", "auto") == "candidates"
    assert clamp_router_downgrade("unknown", "candidates") == "unknown"


@pytest.mark.parametrize(
    ("mode", "router"), [("audit", "off"), ("recommend", "candidates"), ("auto", "auto")]
)
def test_autopilot_sets_the_default_router(
    client_factory: Any, recorder: Recorder, mode: str, router: str
) -> None:
    client = client_factory(autopilot=mode)
    assert client.autopilot.mode == mode
    client.chat.completions.create(model="m", messages=MESSAGES)
    assert recorder.body["router"] == router


def test_per_call_upgrade_is_clamped_under_audit(client_factory: Any, recorder: Recorder) -> None:
    client_factory(autopilot="audit").chat.completions.create(
        model="m", messages=MESSAGES, router="auto"
    )
    assert recorder.body["router"] == "off"


def test_per_call_downgrade_is_honoured_under_auto(client_factory: Any, recorder: Recorder) -> None:
    client_factory(autopilot="auto").chat.completions.create(
        model="m", messages=MESSAGES, router="off"
    )
    assert recorder.body["router"] == "off"


def test_without_autopilot_per_call_router_wins(client_factory: Any, recorder: Recorder) -> None:
    client_factory(defaults={"router": "off"}).chat.completions.create(
        model="m", messages=MESSAGES, router="auto"
    )
    assert recorder.body["router"] == "auto"


def test_invalid_autopilot_is_rejected() -> None:
    with pytest.raises(ValueError, match="autopilot"):
        UltraRouter(api_key="k", autopilot="yolo")  # type: ignore[arg-type]


# ── Bench tagging ──


def test_resolve_bench_forms() -> None:
    assert resolve_bench(None, {}) is None
    simple = resolve_bench("suite-a", {})
    assert simple is not None and simple.headers == {"x-ur-bench-suite": "suite-a"}
    full = resolve_bench({"suite": "s", "run": "r1", "trace": "t1"}, {})
    assert full is not None and full.headers == {
        "x-ur-bench-suite": "s",
        "x-ur-bench-run": "r1",
        "x-ur-bench-trace": "t1",
    }
    factory = resolve_bench({"suite": "s", "trace": lambda: "fresh"}, {})
    assert (
        factory is not None
        and factory.trace_factory is not None
        and "x-ur-bench-trace" not in factory.headers
    )
    assert resolve_bench({"suite": "  "}, {}) is None


def test_resolve_bench_env_fallback_and_precedence() -> None:
    env = {"UR_BENCH": "env-suite", "UR_BENCH_RUN": "sha1", "UR_BENCH_TRACE": None}
    from_env = resolve_bench(None, env)
    assert from_env is not None and from_env.headers == {
        "x-ur-bench-suite": "env-suite",
        "x-ur-bench-run": "sha1",
    }
    explicit = resolve_bench("explicit", env)
    assert explicit is not None and explicit.suite == "explicit"


def test_bench_headers_ride_every_request_and_retries(recorder: Recorder) -> None:
    calls: list[httpx.Request] = []

    def flaky(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(503, json={"error": {"code": "provider_unavailable"}})
        return httpx.Response(200, json=CHAT)

    with UltraRouter(
        api_key="ur_sk_test_1",
        base_url="http://gw",
        bench={"suite": "s", "run": "r"},
        http_client=httpx.Client(transport=httpx.MockTransport(flaky)),
        _sleep=lambda _: None,
    ) as client:
        client.chat.completions.create(model="m", messages=MESSAGES)
    assert len(calls) == 2
    for request in calls:
        assert request.headers["x-ur-bench-suite"] == "s"
        assert request.headers["x-ur-bench-run"] == "r"


def test_bench_trace_factory_is_fresh_per_request(client_factory: Any, recorder: Recorder) -> None:
    counter = iter(range(100))
    client = client_factory(bench={"suite": "s", "trace": lambda: f"trace-{next(counter)}"})
    client.chat.completions.create(model="m", messages=MESSAGES)
    client.chat.completions.create(model="m", messages=MESSAGES)
    assert [r.headers["x-ur-bench-trace"] for r in recorder.requests] == ["trace-0", "trace-1"]


def test_per_call_bench_goes_into_ur_bench_and_wins(
    client_factory: Any, recorder: Recorder
) -> None:
    client = client_factory(bench="init-suite")
    client.chat.completions.create(
        model="m",
        messages=MESSAGES,
        bench={"suite": "call-suite", "trace": "t"},
        ur={"bench": "ignored"},
    )
    assert recorder.body["ur"]["bench"] == {"suite": "call-suite", "trace": "t"}
    assert "bench" not in recorder.body
    assert recorder.requests[-1].headers["x-ur-bench-suite"] == "init-suite"


def test_env_bench_reaches_requests_and_as_openai(
    monkeypatch: pytest.MonkeyPatch, client_factory: Any, recorder: Recorder
) -> None:
    monkeypatch.setenv("UR_BENCH", "env-suite")
    client = client_factory()
    client.chat.completions.create(model="m", messages=MESSAGES)
    assert recorder.requests[-1].headers["x-ur-bench-suite"] == "env-suite"

    class FakeOpenAI:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

    assert client.as_openai(FakeOpenAI).kwargs["default_headers"] == {
        "x-ur-bench-suite": "env-suite"
    }


def test_live_key_with_bench_warns_once() -> None:
    with pytest.warns(UserWarning, match="live key"):
        client = UltraRouter(api_key="ur_sk_live_abc", base_url="http://gw", bench="s")
    client.close()


def test_no_warning_for_test_keys_or_without_bench() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        UltraRouter(api_key="ur_sk_test_abc", base_url="http://gw", bench="s").close()
        UltraRouter(api_key="ur_sk_live_abc", base_url="http://gw").close()


async def test_async_client_applies_the_same_rules() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=CHAT)

    async with AsyncUltraRouter(
        api_key="ur_sk_test_1",
        base_url="http://gw",
        autopilot="recommend",
        default_model="d/m",
        defaults={"call_type": "ct", "max_cost_usd": 0.1},
        bench="s",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    ) as client:
        await client.chat.completions.create(messages=MESSAGES, router="auto")
    body = json.loads(seen[0].content)
    assert body["model"] == "d/m"
    assert body["router"] == "candidates"
    assert body["call_type"] == "ct"
    assert body["ur"] == {"max_cost_usd": 0.1}
    assert seen[0].headers["x-ur-bench-suite"] == "s"
