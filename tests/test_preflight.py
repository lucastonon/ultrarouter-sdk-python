"""Preflight: the two-lifetime cache, the never-cached grant, ``messages`` for case modules,
``use_learned`` and ``get_prompt`` (sync and async)."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from conftest import TEST_KEY, MockGateway
from ultrarouter import (
    DEFAULT_PREFLIGHT_CACHE_SIZE,
    AsyncUltraRouter,
    InvalidRequestError,
    PreflightCache,
    PreflightCacheEntry,
    UltraRouter,
    decide_preflight_cache,
    parse_grant_header,
    parse_max_age_seconds,
    preflight_cache_key,
    preflight_has_cluster_key,
    render_prompt,
    with_header_grant,
)
from ultrarouter._preflight import build_cache_entry


def _grant(**over: Any) -> dict[str, Any]:
    grant = {
        "grant_id": "grant_" + "a" * 32,
        "arm": "treated",
        "lever_id": None,
        "epoch": 3,
        "valid_until_epoch_close": "2026-10-01T00:00:00Z",
        "request_id": "req_pf_1",
    }
    grant.update(over)
    return grant


def _body(**over: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "object": "preflight",
        "config_version": 7,
        "routing": {
            "mode": "candidates",
            "model": {"id": "openai/gpt-5.2-mini", "evidence": "none", "score": None},
            "fallbacks": [{"id": "openai/gpt-5.2", "score": None}],
            "why": None,
            "max_age_s": 30,
        },
        "prompt": None,
        "knowledge": {
            "module": {
                "id": "lcm_1",
                "version": "lcm1_x",
                "kind": "ur:learned",
                "slot": "learned",
                "state": "screened",
                "content_hash": "h",
                "tokens": 5,
                "content": "LEARNED-BLOCK",
                "lineage": {
                    "pack_hash": "p",
                    "epoch": 3,
                    "item_ids": ["f1"],
                    "ranker_version": "r",
                    "k": 3,
                    "key_spec": "k",
                    "source_snapshot": "2026-09-01T00:00:00Z",
                },
            },
            "placement": "after_stable_prefix",
            "delivery": "off",
        },
        "knowledge_reason": None,
        "grant": _grant(),
        "grant_reason": None,
        "provisional": True,
        "reason": "not_benchmarkable",
    }
    body.update(over)
    return body


def _headers(etag: str = '"e1"', grant: dict[str, Any] | None = None) -> dict[str, str]:
    headers = {"etag": etag, "cache-control": "private, max-age=5", "x-ur-live-max-age": "30"}
    if grant is not None:
        headers["x-ur-grant"] = json.dumps(grant)
    return headers


class Gateway:
    """A scripted preflight endpoint: ``script(call_number, request) -> (status, headers, body)``."""

    def __init__(
        self, script: Callable[[int, httpx.Request], tuple[int, dict[str, str], Any]]
    ) -> None:
        self.script = script
        self.calls: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        status, headers, body = self.script(len(self.calls), request)
        if status == 304:
            return httpx.Response(304, headers=headers)
        if request.url.path.endswith("/artifacts"):
            return httpx.Response(201, json=body)
        return httpx.Response(status, headers=headers, json=body)


class Clock:
    """A controllable epoch-milliseconds clock."""

    def __init__(self) -> None:
        self.ms = 1_000_000.0

    def __call__(self) -> float:
        return self.ms


def _client(gateway: Gateway) -> UltraRouter:
    return UltraRouter(
        api_key=TEST_KEY,
        base_url="http://gw",
        http_client=httpx.Client(transport=httpx.MockTransport(gateway)),
    )


# ── pure helpers ──


def test_parse_grant_header_fails_closed() -> None:
    assert parse_grant_header(None) is None
    assert parse_grant_header("") is None
    assert parse_grant_header("not json") is None
    assert parse_grant_header("[1, 2]") is None
    assert parse_grant_header(json.dumps({"grant_id": "g"})) == {"grant_id": "g"}


def test_parse_max_age_seconds() -> None:
    assert parse_max_age_seconds(None) is None
    assert parse_max_age_seconds("private, max-age=5") == 5
    assert parse_max_age_seconds("MAX-AGE = 12, private") == 12
    assert parse_max_age_seconds("no-store") is None


def test_cluster_key_and_cache_key() -> None:
    assert not preflight_has_cluster_key({"call_type": "c"})
    assert preflight_has_cluster_key({"call_type": "c", "artifact_key": "a"})
    assert preflight_has_cluster_key({"call_type": "c", "trace_id": "t"})
    a = preflight_cache_key({"call_type": "c", "budget": {"max_usd": 1}})
    assert a == preflight_cache_key({"budget": {"max_usd": 1}, "call_type": "c"})
    m1 = preflight_cache_key({"call_type": "c", "messages": [{"role": "user", "content": "x"}]})
    m2 = preflight_cache_key({"call_type": "c", "messages": [{"role": "user", "content": "y"}]})
    assert len({a, m1, m2}) == 3
    assert "x" not in m1  # the messages themselves are never part of the stored key


def test_decide_preflight_cache_honours_both_lifetimes() -> None:
    entry = PreflightCacheEntry(
        etag='"e"', body={}, stored_at_ms=0, config_max_age_s=5, live_max_age_s=30
    )
    assert decide_preflight_cache(None, 0, False).kind == "fetch"
    assert decide_preflight_cache(entry, 1_000, False).kind == "fresh"
    assert decide_preflight_cache(entry, 1_000, True).kind == "revalidate"
    assert decide_preflight_cache(entry, 6_000, False).if_none_match == '"e"'
    assert decide_preflight_cache(entry, 30_000, False).kind == "fetch"
    assert decide_preflight_cache(entry, 1_000, False, live_max_age_override_s=0.5).kind == "fetch"


def test_with_header_grant_never_reads_the_cached_grant() -> None:
    body = _body(grant=None, grant_reason="no_cluster_key")
    assert with_header_grant(body, None)["grant_reason"] == "no_cluster_key"
    merged = with_header_grant(body, _grant())
    assert merged["grant"] == _grant() and merged["grant_reason"] is None
    assert body["grant"] is None  # input untouched


def test_cache_entry_strips_the_grant_and_reads_lifetimes() -> None:
    entry = build_cache_entry(
        _body(), '"e"', {"cache-control": "private, max-age=7", "x-ur-live-max-age": "20"}, 5.0
    )
    assert entry.body["grant"] is None
    assert (entry.config_max_age_s, entry.live_max_age_s, entry.stored_at_ms) == (7.0, 20.0, 5.0)
    fallback = build_cache_entry(_body(), '"e"', {"x-ur-live-max-age": "garbage"}, 0)
    assert (fallback.config_max_age_s, fallback.live_max_age_s) == (5.0, 30.0)


# ── the cache end to end ──


def test_preflight_returns_the_grant_from_the_header() -> None:
    gateway = Gateway(
        lambda n, r: (
            200,
            _headers(grant=_grant(arm="holdout")),
            _body(grant=_grant(arm="treated")),
        )
    )
    with _client(gateway) as client:
        response = client.preflight(call_type="support", artifact_key="a1")
    assert response.grant is not None and response.grant.arm == "holdout"
    assert json.loads(gateway.calls[0].content) == {"call_type": "support", "artifact_key": "a1"}


def test_config_part_is_cached_then_revalidated() -> None:
    clock = Clock()
    gateway = Gateway(
        lambda n, r: (
            (200, _headers(), _body(grant=None, grant_reason="no_cluster_key"))
            if n == 1
            else (304, _headers(), None)
        )
    )
    with _client(gateway) as client:
        first = client.preflight(call_type="support", now_ms=clock)
        clock.ms += 2_000
        second = client.preflight(call_type="support", now_ms=clock)  # fresh: no network
        assert len(gateway.calls) == 1
        clock.ms += 4_000
        third = client.preflight(call_type="support", now_ms=clock)  # past max-age=5: revalidate
    assert len(gateway.calls) == 2
    assert gateway.calls[1].headers["if-none-match"] == '"e1"'
    assert first.config_version == second.config_version == third.config_version == 7


def test_grant_is_never_cached_and_a_304_carries_a_fresh_one() -> None:
    def script(n: int, request: httpx.Request) -> tuple[int, dict[str, str], Any]:
        if n == 1:
            return 200, _headers(grant=_grant(grant_id="g1")), _body(grant=_grant(grant_id="g1"))
        return 304, _headers(grant=_grant(grant_id="g2")), None

    with _client(Gateway(script)) as client:
        first = client.preflight(call_type="support", artifact_key="a1")
        second = client.preflight(call_type="support", artifact_key="a1")
        cached = client._preflight_cache.get(
            preflight_cache_key({"call_type": "support", "artifact_key": "a1"})
        )
    assert first.grant is not None and first.grant.grant_id == "g1"
    assert second.grant is not None and second.grant.grant_id == "g2"
    assert cached is not None and cached.body["grant"] is None


def test_live_part_expiry_forces_a_full_refetch() -> None:
    clock = Clock()
    gateway = Gateway(lambda n, r: (200, _headers(grant=_grant()), _body()))
    with _client(gateway) as client:
        client.preflight(call_type="support", trace_id="t1", now_ms=clock)
        clock.ms += 31_000
        client.preflight(call_type="support", trace_id="t1", now_ms=clock)
    assert "if-none-match" not in gateway.calls[1].headers


def test_no_cache_bypasses_everything() -> None:
    gateway = Gateway(lambda n, r: (200, _headers(), _body()))
    with _client(gateway) as client:
        client.preflight(call_type="support", no_cache=True)
        client.preflight(call_type="support", no_cache=True)
        assert len(client._preflight_cache) == 0
    assert len(gateway.calls) == 2
    assert all("if-none-match" not in c.headers for c in gateway.calls)


# ── messages for case-based modules ──


def test_messages_are_sent_and_keyed(mock_gateway: MockGateway) -> None:
    msgs_a = [
        {"role": "system", "content": "triage"},
        {"role": "user", "content": "my invoice is wrong"},
    ]
    msgs_b = [{"role": "user", "content": "password reset"}]
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        missing = client.preflight(call_type="ticket-classifier")
        assert missing.knowledge is None
        assert missing.knowledge_reason == "case_query_missing"
        with_a = client.preflight(call_type="ticket-classifier", messages=msgs_a)
        with_b = client.preflight(call_type="ticket-classifier", messages=msgs_b)
        again_a = client.preflight(call_type="ticket-classifier", messages=msgs_a)  # cached
    assert with_a.knowledge is not None and "my invoice is wrong" in with_a.knowledge.module.content
    assert with_b.knowledge is not None and "password reset" in with_b.knowledge.module.content
    assert (
        again_a.knowledge is not None
        and again_a.knowledge.module.content == with_a.knowledge.module.content
    )
    bodies = [r["body"] for r in mock_gateway.requests]
    assert len(bodies) == 3
    assert "messages" not in bodies[0]
    assert bodies[1]["messages"] == msgs_a and bodies[2]["messages"] == msgs_b


async def test_messages_are_sent_async(mock_gateway: MockGateway) -> None:
    async with AsyncUltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        missing = await client.preflight(call_type="ticket-classifier")
        present = await client.preflight(
            call_type="ticket-classifier", messages=[{"role": "user", "content": "refund please"}]
        )
        session = await client.use_learned(
            call_type="ticket-classifier", messages=[{"role": "user", "content": "other"}]
        )
    assert missing.knowledge_reason == "case_query_missing"
    assert present.knowledge is not None
    assert session.knowledge is not None
    assert mock_gateway.requests[1]["body"]["messages"] == [
        {"role": "user", "content": "refund please"}
    ]


# ── use_learned + get_prompt ──


def test_use_learned_apply_places_the_block_after_the_system_run(mock_gateway: MockGateway) -> None:
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        session = client.use_learned(call_type="support-reply")
    messages = [
        {"role": "system", "content": "s1"},
        {"role": "system", "content": "s2"},
        {"role": "user", "content": "q"},
    ]
    applied = session.apply(messages)
    assert applied[2] == {"role": "user", "content": session.knowledge.module.content}  # type: ignore[union-attr]
    assert [m["content"] for m in applied if m is not applied[2]] == ["s1", "s2", "q"]
    assert messages[2] == {"role": "user", "content": "q"}  # input not mutated
    assert session.model == "openai/gpt-5.2-mini"


def test_use_learned_injects_for_both_delivery_values() -> None:
    for delivery in ("off", "gateway_inject_after_stable_prefix"):
        body = _body()
        body["knowledge"]["delivery"] = delivery
        gateway = Gateway(lambda n, r, body=body: (200, _headers(), body))
        with _client(gateway) as client:
            session = client.use_learned(call_type="c")
        assert session.apply([{"role": "user", "content": "q"}])[0]["content"] == "LEARNED-BLOCK"


def test_use_learned_holdout_passes_messages_through() -> None:
    gateway = Gateway(
        lambda n, r: (200, _headers(), _body(knowledge=None, knowledge_reason="holdout"))
    )
    with _client(gateway) as client:
        session = client.use_learned(call_type="c")
    messages = [{"role": "user", "content": "q"}]
    assert session.apply(messages) == messages and session.apply(messages) is not messages


def test_use_learned_record_quotes_the_grant() -> None:
    artifact = {
        "artifact": {
            "object": "artifact",
            "id": "art_1",
            "key": "a1",
            "archetype": "answer",
            "artifact_type_version_id": None,
            "call_type_id": None,
            "claims": [],
            "created_at": "t",
            "current_version": 1,
            "exposure_arm": "treated",
            "exposure_epoch": 3,
            "grant_attestation": "applied",
            "grant_id": "g",
            "lifecycle": "open",
            "occurred_at": "t",
            "request_ids": [],
            "situation_key": None,
            "superseded_claims": [],
            "updated_at": "t",
        }
    }

    def script(n: int, request: httpx.Request) -> tuple[int, dict[str, str], Any]:
        if request.url.path == "/v1/preflight":
            return 200, _headers(grant=_grant()), _body()
        if request.url.path == "/v1/artifacts":
            return 201, {}, artifact
        return (
            202,
            {},
            {
                "object": "list",
                "data": [
                    {
                        "status": "accepted",
                        "id": "o1",
                        "source_event_id": "e",
                        "canonical_target_id": "art_1",
                        "target_kind": "artifact",
                        "artifact_version": 1,
                        "latency_class": "instant",
                        "source": "declared",
                        "learning_use": ["rank"],
                        "reason": None,
                    }
                ],
            },
        )

    gateway = Gateway(script)
    with _client(gateway) as client:
        session = client.use_learned(call_type="c", artifact_key="a1")
        receipt = session.record({"channel": "behavioral", "kind": "accepted"})
    assert receipt.status == "delivered"
    upsert = json.loads(gateway.calls[1].content)
    assert upsert == {
        "key": "a1",
        "archetype": "answer",
        "grant_id": _grant()["grant_id"],
        "attestation": "applied",
    }
    assert gateway.calls[2].url.path == "/v1/artifacts/art_1/outcomes"


def test_use_learned_record_without_artifact_key_fails_closed() -> None:
    gateway = Gateway(lambda n, r: (200, _headers(), _body()))
    with _client(gateway) as client:
        session = client.use_learned(call_type="c")
        with pytest.raises(InvalidRequestError, match="artifact_key"):
            session.record({"channel": "behavioral", "kind": "accepted"})


def test_get_prompt_and_render(mock_gateway: MockGateway) -> None:
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        prompt = client.get_prompt("support-reply")
        assert client.get_prompt("code-owned") is None
    assert prompt is not None and prompt.version == 3
    assert (
        render_prompt(prompt, {"brand": "Northwind", "tone": "friendly"})
        == "You are a friendly support agent for Northwind."
    )
    assert (
        render_prompt(prompt, {"brand": "Northwind"}) == "You are a  support agent for Northwind."
    )


async def test_async_grant_never_cached_on_304() -> None:
    def script(n: int, request: httpx.Request) -> tuple[int, dict[str, str], Any]:
        if "if-none-match" not in request.headers:
            return 200, _headers(grant=_grant(grant_id=f"g{n}")), _body(prompt=None)
        return 304, _headers(grant=_grant(grant_id=f"g{n}")), None

    gateway = Gateway(script)
    async with AsyncUltraRouter(
        api_key=TEST_KEY,
        base_url="http://gw",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(gateway)),
    ) as client:
        first = await client.preflight(call_type="c", artifact_key="a")
        second = await client.preflight(call_type="c", artifact_key="a")
        prompt = await client.get_prompt("c")
    assert first.grant is not None and second.grant is not None
    assert (first.grant.grant_id, second.grant.grant_id) == ("g1", "g2")
    assert prompt is None


async def test_async_use_learned_round_trip(mock_gateway: MockGateway) -> None:
    async with AsyncUltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        session = await client.use_learned(call_type="support-reply", artifact_key="ticket:9")
        applied = session.apply(
            [{"role": "system", "content": "s"}, {"role": "user", "content": "q"}]
        )
        receipt = await session.record({"channel": "behavioral", "kind": "accepted"})
    assert receipt.status == "delivered"
    if session.knowledge is not None:
        assert applied[1]["content"] == session.knowledge.module.content


# ── bounded cache ──


def _entry(stored_at_ms: float = 0.0, live_s: float = 30.0) -> PreflightCacheEntry:
    return PreflightCacheEntry(
        etag='"e"', body={}, stored_at_ms=stored_at_ms, config_max_age_s=5, live_max_age_s=live_s
    )


def test_cache_is_bounded_and_least_recently_used_goes_first() -> None:
    cache = PreflightCache(max_entries=3)
    for key in "abc":
        cache.set(key, _entry())
    assert cache.get("a") is not None  # "a" is now the most recently used
    cache.set("d", _entry())
    assert len(cache) == 3
    assert cache.get("b") is None, "the least recently used entry is evicted"
    assert [k for k in "acd" if cache.get(k) is not None] == ["a", "c", "d"]


def test_cache_evicts_expired_entries() -> None:
    cache = PreflightCache(max_entries=10)
    cache.set("old", _entry(stored_at_ms=0, live_s=30))
    cache.set("young", _entry(stored_at_ms=20_000, live_s=30))
    cache.set("new", _entry(stored_at_ms=31_000, live_s=30))  # "old" expired at 30 000 ms
    assert len(cache) == 2 and cache.get("old") is None
    assert cache.get("young", now_ms=49_999) is not None
    assert cache.get("young", now_ms=50_000) is None, "an expired entry is dropped on read"
    assert len(cache) == 1


def test_cache_size_zero_disables_caching() -> None:
    cache = PreflightCache(max_entries=0)
    cache.set("a", _entry())
    assert len(cache) == 0 and cache.get("a") is None
    with pytest.raises(ValueError, match="max_entries"):
        PreflightCache(max_entries=-1)


def test_default_bound() -> None:
    assert PreflightCache().max_entries == DEFAULT_PREFLIGHT_CACHE_SIZE == 1024
    with UltraRouter(api_key=TEST_KEY, base_url="http://gw") as client:
        assert client._preflight_cache.max_entries == 1024


def test_sustained_unique_traffic_stays_within_the_bound() -> None:
    clock = Clock()
    gateway = Gateway(lambda n, r: (200, _headers(etag=f'"e{n}"', grant=_grant()), _body()))
    with UltraRouter(
        api_key=TEST_KEY,
        base_url="http://gw",
        preflight_cache_size=64,
        http_client=httpx.Client(transport=httpx.MockTransport(gateway)),
    ) as client:
        for i in range(1_000):
            client.preflight(
                call_type="support",
                trace_id=f"trace-{i}",
                messages=[{"role": "user", "content": f"unique {i}"}],
                now_ms=clock,
            )
            clock.ms += 10
            assert len(client._preflight_cache) <= 64
        # the most recent identity is still served from the cache (revalidated, not refetched)
        client.preflight(
            call_type="support",
            trace_id="trace-999",
            messages=[{"role": "user", "content": "unique 999"}],
            now_ms=clock,
        )
    assert len(gateway.calls) == 1_001
    assert gateway.calls[-1].headers.get("if-none-match") == '"e1000"'


async def test_async_client_honours_the_cache_size() -> None:
    gateway = Gateway(lambda n, r: (200, _headers(grant=_grant()), _body()))
    async with AsyncUltraRouter(
        api_key=TEST_KEY,
        base_url="http://gw",
        preflight_cache_size=5,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(gateway)),
    ) as client:
        for i in range(50):
            await client.preflight(call_type="support", artifact_key=f"a{i}")
        assert len(client._preflight_cache) == 5
        clone = client.with_options(timeout=5)
        assert clone._preflight_cache is client._preflight_cache
