"""``client.learning``: every control, sync and async, its request, its typed model, and the
actionable typed errors for the gateway's refusals."""

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
    ConflictError,
    InternalServerError,
    InvalidRequestError,
    LearningBudgetExhaustedError,
    LearningConsentRequiredError,
    LearningError,
    LearningForbiddenError,
    LearningNotEnabledError,
    LearningNotFoundError,
    LearningPolicyInvalidError,
    LearningProviderUnavailableError,
    LearningQuotaExhaustedError,
    LearningVersionConflictError,
    NotFoundError,
    PermissionDeniedError,
    UltraRouterError,
)
from ultrarouter import UltraRouter as Client
from ultrarouter._errors import error_from_response, learning_error, parse_learning_refusal
from ultrarouter.types import (
    LearningControl,
    LearningEvaluationList,
    LearningStatus,
    LearningVersionDetail,
    LearningVersionList,
)

MODEL = "openai/gpt-5.2-mini"
BASE = "/v1/call-types/order-desk/learning"


def _calls(gateway: MockGateway) -> list[tuple[str, str, Any]]:
    return [(r["method"], r["path"], r["body"]) for r in gateway.requests]


def test_the_full_control_cycle(mock_gateway: MockGateway) -> None:
    with Client(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        learning = client.learning
        before = learning.status("order-desk")
        assert isinstance(before, LearningStatus) and before.object == "learning"
        assert (before.state, before.reason, before.enabled) == ("off", "not_enabled", False)
        enabled = learning.enable(
            "order-desk",
            reflection_model=MODEL,
            lessons_mode="with_precedents",
            lessons_k=6,
            promotion="evaluate",
            recipe={"validator": "elv2", "generation": "atomic", "observations": "elo2"},
        )
        assert isinstance(enabled, LearningControl) and enabled.object == "learning_control"
        assert (enabled.action, enabled.changed, enabled.call_type_id) == (
            "enable",
            True,
            "order-desk",
        )
        status = enabled.learning
        assert status.state == "learning" and status.enabled and status.governed
        assert status.promotion is not None and status.promotion.mode == "evaluate"
        assert status.reflection.model == MODEL and status.reflection.provider.available
        assert status.recipe is not None and status.recipe.validator == "elv2"
        assert status.active_version is not None and status.active_version.id == "epb_2"
        assert status.latest_candidate is not None and status.latest_candidate.id == "epb_3"
        assert status.evaluation is not None and status.evaluation.decision == "running"
        assert status.evidence.verified == 9 and status.budget.state == "ok"
        again = learning.enable("order-desk", reflection_model=MODEL)
        assert again.changed is False  # idempotent
        paused = learning.pause("order-desk")
        assert (paused.action, paused.learning.state, paused.learning.paused) == (
            "pause",
            "paused",
            True,
        )
        assert learning.resume("order-desk").learning.state == "learning"
        versions = learning.versions("order-desk")
        assert isinstance(versions, LearningVersionList)
        assert [(v.id, v.state) for v in versions.data] == [
            ("epb_3", "evaluating"),
            ("epb_2", "active"),
            ("epb_1", "retired"),
        ]
        assert versions.data[0].cohort.pass_ == 9
        detail = learning.version("order-desk", "epb_3")
        assert isinstance(detail, LearningVersionDetail) and detail.active_lessons == 3
        assert [lesson.id for lesson in detail.lessons] == ["lsn_1", "lsn_2", "lsn_3"]
        assert detail.transitions[0].reason == "published"
        evaluations = learning.evaluations("order-desk")
        assert isinstance(evaluations, LearningEvaluationList)
        (evaluation,) = evaluations.data
        assert evaluation.arms.candidate.pass_ == 5 and evaluation.arms.incumbent.verified == 6
        assert evaluation.difference is not None and evaluation.difference.lower == -0.125
        promoted = learning.promote("order-desk", "epb_3")
        assert (promoted.action, promoted.version_id, promoted.stopped_evaluation_id) == (
            "promote",
            "epb_3",
            "lev_1",
        )
        assert promoted.learning.active_version is not None
        assert promoted.learning.active_version.id == "epb_3"
        rolled = learning.rollback("order-desk", version_id="epb_1")
        assert rolled.version_id == "epb_1"
        assert rolled.learning.active_version is not None
        assert rolled.learning.active_version.id == "epb_1"
        rejected = learning.reject("order-desk", "epb_3")
        assert rejected.action == "reject"
        disabled = learning.disable("order-desk")
        assert (disabled.learning.state, disabled.learning.reason) == ("disabled", "disabled")
    calls = _calls(mock_gateway)
    assert calls[1] == (
        "POST",
        f"{BASE}/enable",
        {
            "reflection_model": MODEL,
            "lessons_mode": "with_precedents",
            "lessons_k": 6,
            "promotion": {"mode": "evaluate"},
            "recipe": {"validator": "elv2", "generation": "atomic", "observations": "elo2"},
        },
    )
    assert ("POST", f"{BASE}/pause", None) in calls  # no body
    assert ("GET", f"{BASE}/versions/epb_3", None) in calls
    assert ("POST", f"{BASE}/versions/epb_3/promote", None) in calls
    assert ("POST", f"{BASE}/rollback", {"version_id": "epb_1"}) in calls
    assert ("POST", f"{BASE}/versions/epb_3/reject", None) in calls
    for request in mock_gateway.requests:
        if request["method"] == "POST":
            assert request["headers"].get("idempotency-key")


async def test_the_full_control_cycle_async(mock_gateway: MockGateway) -> None:
    async with AsyncUltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        learning = client.learning
        assert (await learning.status("ct-a")).state == "off"
        enabled = await learning.enable(
            "ct-a", reflection_model=MODEL, promotion={"mode": "manual", "objective": "success"}
        )
        assert enabled.learning.promotion is not None
        assert enabled.learning.promotion.mode == "manual"
        assert (await learning.pause("ct-a")).learning.state == "paused"
        assert (await learning.resume("ct-a")).learning.state == "learning"
        assert len((await learning.versions("ct-a")).data) == 3
        assert (await learning.version("ct-a", "epb_1")).state == "retired"
        assert len((await learning.evaluations("ct-a")).data) == 1
        assert (await learning.promote("ct-a", "epb_3")).version_id == "epb_3"
        rolled = await learning.rollback("ct-a")  # the version active before the current one
        assert rolled.version_id == "epb_2"
        assert (await learning.reject("ct-a", "epb_3")).action == "reject"
        assert (await learning.disable("ct-a")).learning.state == "disabled"
    enable = next(r for r in mock_gateway.requests if r["path"].endswith("/enable"))
    assert enable["body"]["promotion"] == {"mode": "manual", "objective": "success"}
    rollback = next(r for r in mock_gateway.requests if r["path"].endswith("/rollback"))
    assert rollback["body"] == {}


def test_enable_requires_a_reflection_model(mock_gateway: MockGateway) -> None:
    with Client(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        with pytest.raises(InvalidRequestError, match="reflection_model"):
            client.learning.enable("ct-o", reflection_model="")
    assert mock_gateway.requests == []


def test_call_type_ids_are_path_encoded(mock_gateway: MockGateway) -> None:
    with Client(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        client.learning.status("a/b c")
    assert mock_gateway.requests[0]["path"] == "/v1/call-types/a%2Fb%20c/learning"


def _enable(client: Client, call_type: str, **kwargs: Any) -> Any:
    return client.learning.enable(call_type, reflection_model=MODEL, **kwargs)


@pytest.mark.parametrize(
    ("call", "cls", "reason", "refusal", "detail"),
    [
        (
            lambda c: _enable(c, "no-consent"),
            LearningConsentRequiredError,
            "missing_consent",
            "corrections_consent_required",
            None,
        ),
        (
            lambda c: _enable(c, "no-provider"),
            LearningProviderUnavailableError,
            "provider_unavailable",
            "reflection_model_not_workspace_owned",
            "no_workspace_key",
        ),
        (
            lambda c: _enable(c, "bad-policy", promotion={"min_verified_per_arm": 0}),
            LearningPolicyInvalidError,
            "invalid_promotion",
            "promotion_invalid",
            "min_verified_per_arm_range",
        ),
        (
            lambda c: c.learning.pause("never-enabled"),
            LearningNotEnabledError,
            "not_enabled",
            "learning_not_enabled",
            None,
        ),
        (
            lambda c: c.learning.rollback("support-reply", version_id="epb_3"),
            LearningVersionConflictError,
            "version_conflict",
            "rollback_target_not_earlier",
            None,
        ),
        (
            lambda c: c.learning.promote("support-reply", "epb_2"),
            LearningVersionConflictError,
            "version_conflict",
            "version_already_active",
            None,
        ),
        (
            lambda c: c.learning.reject("support-reply", "epb_2"),
            LearningVersionConflictError,
            "version_conflict",
            "version_active",
            None,
        ),
        (
            lambda c: c.learning.status("ct_missing"),
            LearningNotFoundError,
            "not_found",
            "not_found",
            None,
        ),
        (
            lambda c: c.learning.version("support-reply", "epb_404"),
            LearningNotFoundError,
            "not_found",
            "not_found",
            None,
        ),
        (
            lambda c: c.learning.pause("read-only"),
            LearningForbiddenError,
            "forbidden",
            "permission",
            None,
        ),
    ],
    ids=[
        "consent",
        "provider",
        "promotion",
        "not-enabled",
        "rollback-not-earlier",
        "promote-active",
        "reject-active",
        "unknown-call-type",
        "unknown-version",
        "forbidden",
    ],
)
def test_refusals_are_actionable_typed_errors(
    call: Any,
    cls: type[LearningError],
    reason: str,
    refusal: str,
    detail: str | None,
    mock_gateway: MockGateway,
) -> None:
    with Client(api_key=TEST_KEY, base_url=mock_gateway.url, max_retries=0) as client:
        with pytest.raises(cls) as info:
            call(client)
    error = info.value
    assert (error.reason, error.refusal, error.detail) == (reason, refusal, detail)
    assert error.action == LEARNING_ERROR_ACTIONS[reason] and error.action in error.message
    assert error.status >= 400 and error.request_id
    assert isinstance(error.__cause__, UltraRouterError)
    if reason == "not_found":
        assert isinstance(error, NotFoundError)
    if reason == "forbidden":
        assert isinstance(error, PermissionDeniedError)
    if reason in ("not_enabled", "version_conflict"):
        assert isinstance(error, ConflictError) and error.status == 409
    if reason == "invalid_promotion":
        assert isinstance(error, InvalidRequestError) and error.status == 400


def test_no_rollback_target(mock_gateway: MockGateway) -> None:
    with Client(api_key=TEST_KEY, base_url=mock_gateway.url, max_retries=0) as client:
        client.learning.rollback("support-reply", version_id="epb_1")
        with pytest.raises(LearningVersionConflictError) as info:
            client.learning.rollback("support-reply")  # nothing earlier than epb_1
    assert info.value.refusal == "no_rollback_target"


@pytest.mark.parametrize(
    ("call_type", "state"), [("quota-out", "quota_exhausted"), ("budget-out", "budget_exhausted")]
)
def test_stopped_states_are_explicit_in_the_status(
    call_type: str, state: str, mock_gateway: MockGateway
) -> None:
    with Client(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        status = _enable(client, call_type).learning
    assert status.state == state and status.budget.state == state and status.reason


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
        as_code = learning_error(_envelope(409, code))
        assert isinstance(as_code, LearningError), code
        assert as_code.reason == reason and as_code.code == code
        if "_" in code:  # a named refusal is a snake_case token
            as_refusal = learning_error(_envelope(409, "conflict", f"{code}: because"))
            assert isinstance(as_refusal, LearningError) and as_refusal.reason == reason
            assert as_refusal.refusal == code


def test_the_refusal_is_the_first_token_of_the_message() -> None:
    owned = learning_error(
        _envelope(
            400,
            "invalid_request",
            "reflection_model_not_workspace_owned (workspace_funding_frozen): 'x' must resolve",
        )
    )
    assert isinstance(owned, LearningProviderUnavailableError)
    assert (owned.refusal, owned.detail) == (
        "reflection_model_not_workspace_owned",
        "workspace_funding_frozen",
    )
    policy = learning_error(_envelope(400, "invalid_request", "promotion_invalid (alpha_range)"))
    assert isinstance(policy, LearningPolicyInvalidError) and policy.detail == "alpha_range"
    not_enabled = learning_error(_envelope(409, "conflict", "learning_not_enabled"))
    assert isinstance(not_enabled, LearningNotEnabledError) and not_enabled.detail is None
    plain = learning_error(_envelope(403, "permission", "Forbidden: no"))
    assert isinstance(plain, LearningForbiddenError) and plain.refusal == "permission"
    assert parse_learning_refusal("call type 'x' not found") is None
    assert parse_learning_refusal("single: word") is None  # a named refusal has an underscore
    assert parse_learning_refusal("no_rollback_target") == ("no_rollback_target", None)
    budget = learning_error(_envelope(402, "spend_cap_exceeded"))
    assert isinstance(budget, LearningBudgetExhaustedError)
    quota = learning_error(_envelope(429, "rate_limited", "quota_exhausted: provider said no"))
    assert isinstance(quota, LearningQuotaExhaustedError)


def test_unrecognised_and_transport_errors_pass_through() -> None:
    unknown = _envelope(400, "invalid_request", "bad body")
    assert learning_error(unknown) is unknown
    sentence = _envelope(400, "invalid_request", "request body must be valid JSON")
    assert learning_error(sentence) is sentence
    server = _envelope(500, "internal")
    assert isinstance(server, InternalServerError) and learning_error(server) is server
    transport = APIConnectionError("down", retryable=True)
    assert learning_error(transport) is transport
    already = learning_error(_envelope(404, "not_found"))
    assert learning_error(already) is already


def test_an_unrecognised_refusal_is_raised_unchanged() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={
                "error": {
                    "code": "invalid_request",
                    "message": "request body must be valid JSON",
                    "request_id": "r",
                    "retryable": False,
                }
            },
        )

    client = Client(
        api_key=TEST_KEY,
        base_url="http://gateway.test",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(InvalidRequestError) as info:
        client.learning.enable("x", reflection_model=MODEL)
    assert not isinstance(info.value, LearningError)


def test_unknown_status_fields_are_kept(mock_gateway: MockGateway) -> None:
    with Client(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        status = client.learning.status("support-reply")
    assert status.state == "learning" and status.model_extra == {}
    extra = LearningStatus.model_validate({**status.to_dict(), "future_field": 1})
    assert extra.model_extra == {"future_field": 1}
