"""Retries, backoff, Retry-After, the total time budget and idempotency keys."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import datetime, timezone
from email.utils import format_datetime

import httpx
import pytest

from ultrarouter import APITimeoutError, InvalidRequestError, ProviderUnavailableError, UltraRouter
from ultrarouter._base_client import APIRequest
from ultrarouter._retry import (
    BASE_DELAY_S,
    MAX_DELAY_S,
    backoff_seconds,
    capped_backoff,
    parse_retry_after,
    resolve_idempotency_key,
)

Responder = Callable[[], httpx.Response]


def scripted(
    responses: list[Responder],
) -> tuple[Callable[[httpx.Request], httpx.Response], list[httpx.Request]]:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return responses[min(len(calls) - 1, len(responses) - 1)]()

    return handler, calls


@pytest.fixture
def make_client() -> Iterator[Callable[..., UltraRouter]]:
    clients: list[UltraRouter] = []

    def factory(
        handler: Callable[[httpx.Request], httpx.Response],
        sleeps: list[float] | None = None,
        **kw: object,
    ) -> UltraRouter:
        client = UltraRouter(
            api_key="ur_sk_test_1",
            base_url="http://gw",
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
            _sleep=(sleeps.append if sleeps is not None else (lambda _: None)),
            _rand=lambda: 0.5,
            **kw,  # type: ignore[arg-type]
        )
        clients.append(client)
        return client

    yield factory
    for client in clients:
        client._http.close()


def post(client: UltraRouter, **options: object) -> object:
    return client.request_json(
        APIRequest(method="POST", path="/v1/x", body={}, has_body=True, options=options)
    )


def test_retries_429_honouring_retry_after(make_client: Callable[..., UltraRouter]) -> None:
    handler, calls = scripted(
        [
            lambda: httpx.Response(
                429, json={"error": {"code": "rate_limited"}}, headers={"retry-after": "2"}
            ),
            lambda: httpx.Response(200, json={"ok": True}),
        ]
    )
    sleeps: list[float] = []
    assert post(make_client(handler, sleeps)) == {"ok": True}
    assert len(calls) == 2
    assert sleeps == [2.0]


def test_retries_5xx_with_jittered_backoff(make_client: Callable[..., UltraRouter]) -> None:
    handler, calls = scripted(
        [
            lambda: httpx.Response(503, json={"error": {"code": "provider_unavailable"}}),
            lambda: httpx.Response(502, json={"error": {"code": "provider_unavailable"}}),
            lambda: httpx.Response(200, json={"ok": True}),
        ]
    )
    sleeps: list[float] = []
    post(make_client(handler, sleeps))
    assert len(calls) == 3
    assert sleeps == [pytest.approx(0.375), pytest.approx(0.75)]  # window * (0.5 + 0.5 * 0.5)


def test_idempotency_key_is_stable_across_retries(make_client: Callable[..., UltraRouter]) -> None:
    handler, calls = scripted(
        [
            lambda: httpx.Response(500, json={"error": {}}),
            lambda: httpx.Response(500, json={"error": {}}),
            lambda: httpx.Response(200, json={}),
        ]
    )
    post(make_client(handler))
    keys = {r.headers.get("idempotency-key") for r in calls}
    assert len(calls) == 3 and len(keys) == 1 and None not in keys


def test_explicit_idempotency_key_is_used(make_client: Callable[..., UltraRouter]) -> None:
    handler, calls = scripted([lambda: httpx.Response(200, json={})])
    post(make_client(handler), idempotency_key="mine")
    assert calls[0].headers["idempotency-key"] == "mine"


def test_get_never_carries_an_idempotency_key(make_client: Callable[..., UltraRouter]) -> None:
    handler, calls = scripted([lambda: httpx.Response(200, json={"object": "list", "data": []})])
    make_client(handler).models.list()
    assert "idempotency-key" not in calls[0].headers


def test_no_retry_on_4xx(make_client: Callable[..., UltraRouter]) -> None:
    handler, calls = scripted(
        [
            lambda: httpx.Response(
                400,
                json={
                    "error": {"code": "invalid_request", "message": "bad", "request_id": "req_1"}
                },
            )
        ]
    )
    with pytest.raises(InvalidRequestError) as info:
        post(make_client(handler))
    assert (info.value.status, info.value.request_id, len(calls)) == (400, "req_1", 1)


def test_exhausts_retries_then_raises_the_last_error(
    make_client: Callable[..., UltraRouter],
) -> None:
    handler, calls = scripted(
        [lambda: httpx.Response(502, json={"error": {"code": "provider_unavailable"}})]
    )
    with pytest.raises(ProviderUnavailableError):
        post(make_client(handler), max_retries=3)
    assert len(calls) == 4


def test_max_retries_zero_sends_once(make_client: Callable[..., UltraRouter]) -> None:
    handler, calls = scripted(
        [lambda: httpx.Response(503, json={"error": {"code": "provider_unavailable"}})]
    )
    with pytest.raises(ProviderUnavailableError):
        post(make_client(handler, max_retries=0))
    assert len(calls) == 1


def test_connection_errors_are_retried(make_client: Callable[..., UltraRouter]) -> None:
    attempts: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        if len(attempts) < 3:
            raise httpx.ConnectError("refused", request=request)
        return httpx.Response(200, json={"ok": True})

    assert post(make_client(handler)) == {"ok": True}
    assert len(attempts) == 3


def test_total_timeout_budget_stops_retries(make_client: Callable[..., UltraRouter]) -> None:
    handler, calls = scripted(
        [lambda: httpx.Response(503, json={"error": {"code": "provider_unavailable"}})]
    )
    client = make_client(handler, timeout=0.0)
    with pytest.raises(APITimeoutError):
        post(client)
    assert calls == []


def test_streams_are_never_retried(make_client: Callable[..., UltraRouter]) -> None:
    handler, calls = scripted(
        [lambda: httpx.Response(503, json={"error": {"code": "provider_unavailable"}})]
    )
    client = make_client(handler, max_retries=5)
    with pytest.raises(ProviderUnavailableError):
        client.chat.completions.create(
            model="m", messages=[{"role": "user", "content": "x"}], stream=True
        )
    assert len(calls) == 1
    assert "idempotency-key" not in calls[0].headers


# ── pure helpers ──


def test_parse_retry_after_seconds_and_dates() -> None:
    assert parse_retry_after(None, 0) is None
    assert parse_retry_after("3", 0) == 3.0
    assert parse_retry_after("-5", 0) == 0.0
    assert parse_retry_after("garbage", 0) is None
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    later = format_datetime(datetime(2026, 1, 1, 0, 0, 10, tzinfo=timezone.utc), usegmt=True)
    assert parse_retry_after(later, now.timestamp()) == pytest.approx(10.0)


def test_backoff_bounds() -> None:
    assert backoff_seconds(0, None, 0.0) == BASE_DELAY_S * 0.5
    assert backoff_seconds(0, None, 1.0) == BASE_DELAY_S
    assert backoff_seconds(10, None, 1.0) == MAX_DELAY_S
    assert backoff_seconds(0, 100.0, 0.5) == MAX_DELAY_S * 4
    assert capped_backoff(5, None, 1.0, remaining=0.2) == 0.2
    assert capped_backoff(0, None, 1.0, remaining=-1) == 0.0


def test_idempotency_key_resolution() -> None:
    assert resolve_idempotency_key("POST", False, None) is not None
    assert resolve_idempotency_key("POST", True, None) is None
    assert resolve_idempotency_key("GET", False, None) is None
    assert resolve_idempotency_key("PATCH", False, None) is None
    assert resolve_idempotency_key("GET", False, "k") == "k"
