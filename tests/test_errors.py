"""Typed errors: the taxonomy, class selection, retry decisions and the ``model_unpriced`` case."""

from __future__ import annotations

import httpx
import pytest

from conftest import TEST_KEY, MockGateway
from ultrarouter import (
    GATEWAY_ERROR_CODES,
    GATEWAY_ERROR_TAXONOMY,
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncUltraRouter,
    AuthenticationError,
    InternalServerError,
    InvalidRequestError,
    ModelDeniedByPolicyError,
    ModelUnpricedError,
    NotFoundError,
    PermissionDeniedError,
    PromptVariablesMissingError,
    RateLimitError,
    SpendGuardUnavailableError,
    UltraRouter,
    UltraRouterError,
    error_class_for,
    is_gateway_error_code,
    is_retryable_status,
)
from ultrarouter._errors import error_from_response

MESSAGES = [{"role": "user", "content": "hi"}]


def _envelope(
    code: str, *, retryable: bool | None = None, message: str = "boom"
) -> dict[str, object]:
    err: dict[str, object] = {"code": code, "message": message, "request_id": "req_1"}
    if retryable is not None:
        err["retryable"] = retryable
    return {"error": err}


def test_taxonomy_lists_every_code_with_status_and_retryability() -> None:
    assert tuple(GATEWAY_ERROR_TAXONOMY) == GATEWAY_ERROR_CODES
    assert GATEWAY_ERROR_TAXONOMY["model_unpriced"] == (403, False)
    assert GATEWAY_ERROR_TAXONOMY["model_denied_by_policy"] == (403, False)
    assert GATEWAY_ERROR_TAXONOMY["rate_limited"] == (429, True)
    assert GATEWAY_ERROR_TAXONOMY["atomic_spend_guard_unavailable"] == (503, False)
    for code in GATEWAY_ERROR_CODES:
        assert is_gateway_error_code(code)
    assert not is_gateway_error_code("connection")


@pytest.mark.parametrize("code", GATEWAY_ERROR_CODES)
def test_every_code_maps_to_its_own_class(code: str) -> None:
    status, retryable = GATEWAY_ERROR_TAXONOMY[code]
    err = error_from_response(status, _envelope(code, retryable=retryable))
    assert type(err) is error_class_for(code, status)
    assert type(err).default_code == code
    assert isinstance(err, APIStatusError)
    assert isinstance(err, UltraRouterError)
    assert (err.code, err.status, err.retryable, err.request_id) == (
        code,
        status,
        retryable,
        "req_1",
    )


def test_unknown_code_falls_back_to_the_status_class() -> None:
    assert type(error_from_response(404, _envelope("oracle_not_found"))) is NotFoundError
    assert type(error_from_response(403, _envelope("invalid_signature"))) is PermissionDeniedError
    assert type(error_from_response(400, _envelope("validation_error"))) is InvalidRequestError
    assert type(error_from_response(502, _envelope("something_new"))) is InternalServerError
    assert type(error_from_response(418, _envelope("teapot"))) is APIStatusError


def test_error_without_envelope_uses_http_status() -> None:
    err = error_from_response(503, "<html>bad gateway</html>")
    assert err.code == "http_503"
    assert err.retryable is True
    assert "503" in err.message


def test_retryable_flag_defaults() -> None:
    assert error_from_response(429, _envelope("rate_limited")).retryable is True
    assert error_from_response(503, _envelope("atomic_spend_guard_unavailable")).retryable is False
    # The gateway's explicit flag can lower the taxonomy default (never raise it).
    assert (
        error_from_response(502, _envelope("provider_unavailable", retryable=False)).retryable
        is False
    )


def test_stream_error_frame_uses_the_canonical_status() -> None:
    err = error_from_response(0, _envelope("model_unpriced"))
    assert isinstance(err, ModelUnpricedError)
    assert err.status == 403


def test_retryable_statuses() -> None:
    assert [
        s for s in (200, 400, 403, 404, 408, 429, 500, 502, 503, 504) if is_retryable_status(s)
    ] == [
        408,
        429,
        500,
        502,
        503,
        504,
    ]


def test_prompt_variables_missing_error_lists_names() -> None:
    err = PromptVariablesMissingError(missing=["brand", "role"])
    assert err.code == "prompt_variables_missing"
    assert err.missing == ["brand", "role"]
    assert "brand, role" in str(err)
    assert isinstance(err, UltraRouterError)


def test_repr_is_informative() -> None:
    err = error_from_response(429, _envelope("rate_limited"))
    assert "RateLimitError" in repr(err) and "rate_limited" in repr(err)


# ── model_unpriced end to end (sync + async): typed, never retried ──────────────────────────


def test_model_unpriced_is_typed_and_never_retried_sync(mock_gateway: MockGateway) -> None:
    sleeps: list[float] = []
    with UltraRouter(
        api_key=TEST_KEY, base_url=mock_gateway.url, max_retries=5, _sleep=sleeps.append
    ) as client:
        with pytest.raises(ModelUnpricedError) as info:
            client.chat.completions.create(model="acme/unpriced-model", messages=MESSAGES)
        err = info.value
        assert (err.code, err.status, err.retryable) == ("model_unpriced", 403, False)
        assert err.request_id is not None and err.request_id.startswith("req_")
        assert len(mock_gateway.requests) == 1, "a non-retryable 403 must be sent exactly once"
        assert sleeps == []
        with pytest.raises(ModelUnpricedError):
            client.embeddings.create(model="acme/unpriced-model", input="x")
        assert len(mock_gateway.requests) == 2


async def test_model_unpriced_is_typed_and_never_retried_async(mock_gateway: MockGateway) -> None:
    async def no_sleep(_: float) -> None:
        raise AssertionError("must not back off for a non-retryable error")

    async with AsyncUltraRouter(
        api_key=TEST_KEY, base_url=mock_gateway.url, max_retries=5, _sleep=no_sleep
    ) as client:
        with pytest.raises(ModelUnpricedError) as info:
            await client.chat.completions.create(model="acme/unpriced-model", messages=MESSAGES)
        assert info.value.status == 403 and info.value.retryable is False
        assert len(mock_gateway.requests) == 1
        with pytest.raises(ModelUnpricedError):
            await client.embeddings.create(model="acme/unpriced-model", input="x")
        assert len(mock_gateway.requests) == 2


def test_model_unpriced_in_a_stream_error_frame() -> None:
    sse = (
        'data: {"id":"c","object":"chat.completion.chunk","created":1,"model":"m",'
        '"choices":[{"index":0,"delta":{"content":"partial"}}]}\n\n'
        'event: error\ndata: {"error":{"code":"model_unpriced","message":"no price",'
        '"request_id":"req_s","retryable":false}}\n\n'
    )
    http = httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, content=sse.encode()))
    )
    client = UltraRouter(api_key=TEST_KEY, base_url="http://gw", http_client=http)
    stream = client.chat.completions.create(model="m", messages=MESSAGES, stream=True)
    with pytest.raises(ModelUnpricedError):
        list(stream)


def test_model_denied_by_policy_and_not_found(mock_gateway: MockGateway) -> None:
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        with pytest.raises(ModelDeniedByPolicyError):
            client.chat.completions.create(model="acme/denied-model", messages=MESSAGES)
        with pytest.raises(NotFoundError):
            client.chat.completions.create(model="acme/missing-model", messages=MESSAGES)
        with pytest.raises(InvalidRequestError):
            client.chat.completions.create(messages=MESSAGES)  # no model anywhere
    assert len(mock_gateway.requests) == 3


def test_authentication_error(mock_gateway: MockGateway) -> None:
    with UltraRouter(api_key="ur_sk_test_invalid", base_url=mock_gateway.url) as client:
        with pytest.raises(AuthenticationError) as info:
            client.models.list()
    assert info.value.status == 401


def test_rate_limit_is_retried_then_raised(mock_gateway: MockGateway) -> None:
    sleeps: list[float] = []
    with (
        UltraRouter(
            api_key=TEST_KEY, base_url=mock_gateway.url, max_retries=2, _sleep=sleeps.append
        ) as client,
        pytest.raises(RateLimitError),
    ):
        client.chat.completions.create(model="acme/rate-limited", messages=MESSAGES)
    assert len(mock_gateway.requests) == 3
    assert sleeps == [0.0, 0.0]  # Retry-After: 0 honoured


def test_non_retryable_503_is_not_retried(mock_gateway: MockGateway) -> None:
    mock_gateway.fail("/v1/models", status=503, code="atomic_spend_guard_unavailable", times=5)
    with (
        UltraRouter(
            api_key=TEST_KEY, base_url=mock_gateway.url, max_retries=3, _sleep=lambda _: None
        ) as client,
        pytest.raises(SpendGuardUnavailableError),
    ):
        client.models.list()
    assert len(mock_gateway.requests) == 1


def test_transport_errors_are_typed() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = UltraRouter(
        api_key=TEST_KEY,
        base_url="http://gw",
        max_retries=1,
        http_client=httpx.Client(transport=httpx.MockTransport(refuse)),
        _sleep=lambda _: None,
    )
    with pytest.raises(APIConnectionError) as info:
        client.models.list()
    assert info.value.code == "connection" and info.value.retryable is True

    def slow(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    client = UltraRouter(
        api_key=TEST_KEY,
        base_url="http://gw",
        http_client=httpx.Client(transport=httpx.MockTransport(slow)),
    )
    with pytest.raises(APITimeoutError) as timeout_info:
        client.models.list()
    assert timeout_info.value.code == "timeout"
    assert isinstance(timeout_info.value, APIConnectionError)


@pytest.mark.parametrize(
    "code", sorted(c for c, entry in GATEWAY_ERROR_TAXONOMY.items() if not entry.retryable)
)
def test_an_explicit_retryable_flag_never_makes_a_non_retryable_code_retryable(code: str) -> None:
    status = GATEWAY_ERROR_TAXONOMY[code].status
    body = {"error": {"code": code, "message": "contradictory", "retryable": True}}
    assert error_from_response(status, body).retryable is False
    assert error_from_response(0, body).retryable is False  # an SSE error frame


def test_an_explicit_flag_can_still_mark_a_retryable_code_non_retryable() -> None:
    body = {"error": {"code": "provider_unavailable", "retryable": False}}
    assert error_from_response(502, body).retryable is False
    unknown = {"error": {"code": "brand_new_code", "retryable": True}}
    assert error_from_response(418, unknown).retryable is True  # unknown codes follow the flag


def test_contradictory_model_unpriced_is_not_retried_even_with_a_retryable_status() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        body = {"error": {"code": "model_unpriced", "message": "x", "retryable": True}}
        return httpx.Response(503, json=body)

    with UltraRouter(
        api_key=TEST_KEY,
        base_url="http://gw",
        max_retries=3,
        _sleep=lambda _: None,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    ) as client:
        with pytest.raises(ModelUnpricedError) as info:
            client.chat.completions.create(model="m", messages=[{"role": "user", "content": "x"}])
    assert info.value.retryable is False
    assert len(calls) == 1
