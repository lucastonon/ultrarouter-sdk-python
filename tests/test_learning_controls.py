"""``client.learning``: every control, sync and async, its request, its typed model, and the
actionable typed errors."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from conftest import TEST_KEY, MockGateway
from ultrarouter import (
    LEARNING_ERROR_ACTIONS,
    LEARNING_ERROR_CODES,
    LEARNING_ERROR_REASONS,
    APIConnectionError,
    AsyncUltraRouter,
    InternalServerError,
    InvalidRequestError,
    LearningBudgetExhaustedError,
    LearningConsentRequiredError,
    LearningError,
    LearningForbiddenError,
    LearningNotFoundError,
    LearningProviderUnavailableError,
    LearningQuotaExhaustedError,
    NotFoundError,
    PermissionDeniedError,
    UltraRouter,
)
from ultrarouter._errors import error_from_response, learning_error
from ultrarouter.types import (
    LearningEvaluationList,
    LearningStatus,
    LearningVersion,
    LearningVersionList,
)

MODEL = "openai/gpt-5.2-mini"


def _calls(gateway: MockGateway) -> list[tuple[str, str, Any]]:
    return [(r["method"], r["path"], r["body"]) for r in gateway.requests]


def test_the_full_control_cycle(mock_gateway: MockGateway) -> None:
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        learning = client.learning
        before = learning.status("order-desk")
        assert isinstance(before, LearningStatus) and before.state == "not_enabled"
        enabled = learning.enable(
            "order-desk", reflection_model=MODEL, promotion="evaluate", recipe="default"
        )
        assert enabled.state == "active" and enabled.call_type_id == "order-desk"
        assert enabled.promotion is not None and enabled.promotion.mode == "evaluate"
        assert enabled.provider is not None and enabled.provider.model == MODEL
        assert enabled.active is not None and enabled.active.id == "lv_1"
        assert enabled.candidate is not None and enabled.candidate.state == "evaluating"
        assert enabled.evaluation is not None and enabled.evaluation.decision == "running"
        assert enabled.evidence is not None and enabled.evidence.verified == 9
        assert enabled.backlog == 3
        assert enabled.budget is not None and enabled.budget.state == "ok"
        assert learning.pause("order-desk").state == "paused"
        assert learning.resume("order-desk").state == "active"
        versions = learning.versions("order-desk", limit=10)
        assert isinstance(versions, LearningVersionList)
        assert [(v.id, v.state) for v in versions.data] == [
            ("lv_2", "evaluating"),
            ("lv_1", "active"),
        ]
        detail = learning.version("order-desk", "lv_2")
        assert isinstance(detail, LearningVersion) and detail.lesson_count == 2
        assert detail.lessons is not None and detail.lessons[1].tool == "set_order_status"
        assert detail.provenance is not None and detail.provenance.episodes == 12
        evaluations = learning.evaluations("order-desk")
        assert isinstance(evaluations, LearningEvaluationList)
        (evaluation,) = evaluations.data
        assert evaluation.rule is not None and evaluation.rule["min_effect_pp"] == 3
        assert evaluation.candidate is not None and evaluation.candidate.passed == 5
        assert evaluation.interval is not None and evaluation.interval.lower == -12.5
        promoted = learning.promote("order-desk", "lv_2", reason="clear win")
        assert promoted.state == "active" and promoted.state_reason == "manual_promote"
        rolled = learning.rollback("order-desk", version_id="lv_1", reason="regression")
        assert rolled.active is not None and rolled.active.id == "lv_1"
        rejected = learning.reject("order-desk", "lv_2")
        assert rejected.state == "rejected"
        assert learning.disable("order-desk").state == "disabled"
    calls = _calls(mock_gateway)
    base = "/v1/call-types/order-desk/learning"
    assert calls[1] == (
        "POST",
        f"{base}/enable",
        {"reflection_model": MODEL, "promotion": "evaluate", "recipe": "default"},
    )
    assert ("POST", f"{base}/pause", {}) in calls
    assert ("GET", f"{base}/versions/lv_2", None) in calls
    assert ("POST", f"{base}/versions/lv_2/promote", {"reason": "clear win"}) in calls
    assert ("POST", f"{base}/rollback", {"version_id": "lv_1", "reason": "regression"}) in calls
    assert ("POST", f"{base}/versions/lv_2/reject", {}) in calls
    versions_call = next(r for r in mock_gateway.requests if r["path"] == f"{base}/versions")
    assert versions_call["query"] == {"limit": "10"}
    for request in mock_gateway.requests:
        if request["method"] == "POST":
            assert request["headers"].get("idempotency-key")


async def test_the_full_control_cycle_async(mock_gateway: MockGateway) -> None:
    async with AsyncUltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        learning = client.learning
        assert (await learning.status("ct-a")).state == "not_enabled"
        enabled = await learning.enable(
            "ct-a", reflection_model=MODEL, promotion={"mode": "manual"}, objective="success"
        )
        assert enabled.promotion is not None and enabled.promotion.mode == "manual"
        assert (await learning.pause("ct-a")).state == "paused"
        assert (await learning.resume("ct-a")).state == "active"
        assert len((await learning.versions("ct-a")).data) == 2
        assert (await learning.version("ct-a", "lv_1")).state == "active"
        assert len((await learning.evaluations("ct-a", cursor="c1")).data) == 1
        assert (await learning.promote("ct-a", "lv_2")).state == "active"
        assert (await learning.rollback("ct-a", version_id="lv_1")).active is not None
        assert (await learning.reject("ct-a", "lv_2", reason="no")).state == "rejected"
        assert (await learning.disable("ct-a")).state == "disabled"
    enable = next(r for r in mock_gateway.requests if r["path"].endswith("/enable"))
    assert enable["body"]["promotion"] == {"mode": "manual", "objective": "success"}


def test_objective_without_a_mode_defaults_to_evaluate(mock_gateway: MockGateway) -> None:
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        client.learning.enable("ct-o", reflection_model=MODEL, objective="cost_noninferior")
        with pytest.raises(InvalidRequestError, match="reflection_model"):
            client.learning.enable("ct-o", reflection_model="")
    body = mock_gateway.requests[0]["body"]
    assert body["promotion"] == {"mode": "evaluate", "objective": "cost_noninferior"}


def test_call_type_ids_are_path_encoded(mock_gateway: MockGateway) -> None:
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        client.learning.status("a/b c")
    assert mock_gateway.requests[0]["path"] == "/v1/call-types/a%2Fb%20c/learning"


@pytest.mark.parametrize(
    ("call_type", "action", "cls", "reason"),
    [
        ("no-consent", "enable", LearningConsentRequiredError, "missing_consent"),
        ("no-provider", "enable", LearningProviderUnavailableError, "provider_unavailable"),
        ("quota-out", "resume", LearningQuotaExhaustedError, "quota_exhausted"),
        ("budget-out", "resume", LearningBudgetExhaustedError, "budget_exhausted"),
        ("ct_missing", "status", LearningNotFoundError, "not_found"),
        ("read-only", "pause", LearningForbiddenError, "forbidden"),
    ],
)
def test_refusals_are_actionable_typed_errors(
    call_type: str, action: str, cls: type[LearningError], reason: str, mock_gateway: MockGateway
) -> None:
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url, max_retries=0) as client:
        if action == "resume":
            stopped = client.learning.enable(call_type, reflection_model=MODEL)
            assert stopped.state == reason  # the stopped state is explicit in the status
        with pytest.raises(cls) as info:
            if action == "enable":
                client.learning.enable(call_type, reflection_model=MODEL)
            else:
                getattr(client.learning, action)(call_type)
    error = info.value
    assert isinstance(error, LearningError)
    assert error.reason == reason and error.action == LEARNING_ERROR_ACTIONS[reason]
    assert error.action in error.message
    assert error.status >= 400 and error.request_id
    assert isinstance(error.__cause__, Exception)
    if reason == "not_found":
        assert isinstance(error, NotFoundError)
    if reason == "forbidden":
        assert isinstance(error, PermissionDeniedError)


async def test_async_refusal(mock_gateway: MockGateway) -> None:
    async with AsyncUltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        with pytest.raises(LearningConsentRequiredError):
            await client.learning.enable("no-consent", reflection_model=MODEL)


def _envelope(status: int, code: str, message: str = "x", **extra: Any) -> Any:
    error = {"code": code, "message": message, "request_id": "req_e", "retryable": False, **extra}
    return error_from_response(status, {"error": error})


@pytest.mark.parametrize("reason", LEARNING_ERROR_REASONS)
def test_every_listed_code_maps_to_its_reason(reason: str) -> None:
    for code in LEARNING_ERROR_CODES[reason]:
        mapped = learning_error(_envelope(409, code))
        assert isinstance(mapped, LearningError), code
        assert mapped.reason == reason and mapped.code == code


def test_named_refusals_refine_a_generic_code() -> None:
    by_body = learning_error(_envelope(403, "permission", reason="corrections_consent_required"))
    assert isinstance(by_body, LearningConsentRequiredError)
    by_prefix = learning_error(_envelope(400, "invalid_request", "budget_exhausted: spent"))
    assert isinstance(by_prefix, LearningBudgetExhaustedError)
    plain = learning_error(_envelope(403, "permission", "Forbidden: no"))
    assert isinstance(plain, LearningForbiddenError)


def test_unrecognised_and_transport_errors_pass_through() -> None:
    unknown = _envelope(400, "invalid_request", "bad body")
    assert learning_error(unknown) is unknown
    server = _envelope(500, "internal")
    assert isinstance(server, InternalServerError) and learning_error(server) is server
    transport = APIConnectionError("down", retryable=True)
    assert learning_error(transport) is transport
    already = learning_error(_envelope(404, "not_found"))
    assert learning_error(already) is already


def test_an_unrecognised_refusal_is_raised_unchanged(mock_gateway: MockGateway) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={
                "error": {
                    "code": "invalid_request",
                    "message": "promotion: unknown mode",
                    "request_id": "r",
                    "retryable": False,
                }
            },
        )

    client = UltraRouter(
        api_key=TEST_KEY,
        base_url="http://gateway.test",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(InvalidRequestError) as info:
        client.learning.enable("x", reflection_model=MODEL, promotion="sometimes")  # type: ignore[arg-type]
    assert not isinstance(info.value, LearningError)


@pytest.mark.parametrize(
    "body",
    [
        {"learning": {"call_type_id": "x", "state": "active"}},
        {"call_type_id": "x", "state": "active", "future_field": 1},
    ],
)
def test_status_accepts_an_envelope_and_keeps_unknown_fields(body: Any) -> None:
    client = UltraRouter(
        api_key=TEST_KEY,
        base_url="http://gateway.test",
        http_client=httpx.Client(
            transport=httpx.MockTransport(lambda r: httpx.Response(200, json=body))
        ),
    )
    status = client.learning.status("x")
    assert status.state == "active"
    if "future_field" in body:
        assert status.model_extra == {"future_field": 1}
