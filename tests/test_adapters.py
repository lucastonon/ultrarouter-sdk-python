"""Starter outcome adapters: verifiers, test suites, business rules and signed delayed webhooks."""

from __future__ import annotations

import hashlib
import hmac
import json
import sys
from typing import Any

import pytest
from pydantic import BaseModel

from conftest import TEST_KEY, MockGateway
from ultrarouter import (
    AsyncUltraRouter,
    ConfigurationError,
    NotReportedOutcome,
    UltraRouter,
    report_source_event_id,
)
from ultrarouter.adapters import (
    DEFAULT_WEBHOOK_SECRET_ENV,
    WEBHOOK_SIGNATURE_HEADER,
    WEBHOOK_TIMESTAMP_HEADER,
    DedupeStore,
    MemoryDedupeStore,
    VerifierResult,
    WebhookOutcome,
    WebhookOutcomeHandler,
    WebhookPayloadError,
    WebhookSignatureError,
    WebhookTimestampError,
    WebhookVerificationError,
    WebhookVerifier,
    evidence_hash,
    parse_webhook_outcome,
    run_test_suite,
    run_verifier,
    sign_webhook,
    validate_output,
    verdict_from_command,
)

SECRET = "whsec_test_only_value"
NOW = 1_800_000_000.0


# ── evidence hash ──


def test_evidence_hash_is_sorted_compact_utf8_json() -> None:
    # The vector both SDKs pin.
    assert evidence_hash({"b": 1, "a": [2, {"d": 3, "c": "é"}]}) == (
        "sha256:972298aac45a9d1196b4ecbe264713640c223d766f94acafbe26813120efef4b"
    )
    text = '{"a":[2,{"c":"é","d":3}],"b":1}'
    assert evidence_hash({"b": 1, "a": [2, {"d": 3, "c": "é"}]}) == (
        "sha256:" + hashlib.sha256(text.encode()).hexdigest()
    )
    assert evidence_hash({"x": 1.0}) == evidence_hash({"x": 1})  # JavaScript number semantics
    assert evidence_hash("abc").startswith("sha256:")


# ── verifiers ──


def test_run_verifier_answers() -> None:
    assert (run_verifier(lambda: True).verdict, run_verifier(lambda: True).reasons) == ("pass", ())
    assert run_verifier(lambda: True).passed
    failed = run_verifier(lambda: False)
    assert (failed.verdict, failed.reasons, failed.evidence_hash) == ("fail", (), None)
    for odd in (None, 1, "yes", {"pass": "true"}):
        result = run_verifier(lambda odd=odd: odd)
        assert (result.verdict, result.reasons) == ("unknown", ("check_returned_no_verdict",))
    detailed = run_verifier(lambda: {"pass": True, "evidence": {"k": 1}, "reasons": ["ok"]})
    assert detailed.verdict == "pass" and detailed.reasons == ("ok",)
    assert detailed.evidence_hash == evidence_hash({"k": 1})
    custom = VerifierResult("fail", ("mine",), "verifier", "sha256:ab")
    assert run_verifier(lambda: custom) is custom
    assert run_verifier(lambda: True, source="business_rule").source == "business_rule"


def test_run_verifier_errors() -> None:
    def broken() -> bool:
        raise KeyError("the check itself is broken")

    crashed = run_verifier(broken)
    assert (crashed.verdict, crashed.reasons, crashed.evidence_hash) == (
        "unknown",
        ("verifier_error",),
        None,
    )
    forced = run_verifier(broken, on_error="fail")
    assert (forced.verdict, forced.reasons) == ("fail", ("check_threw",))
    assert forced.evidence_hash == evidence_hash({"error": "KeyError"})

    def asserting() -> bool:
        assert 1 + 1 == 3, "arithmetic is off"
        return True

    asserted = run_verifier(asserting)  # a failing assertion is a fail in Python
    assert (asserted.verdict, asserted.reasons) == ("fail", ("check_threw",))
    assert asserted.evidence_hash == evidence_hash({"error": "AssertionError"})


def test_verdict_from_command() -> None:
    assert verdict_from_command(0).verdict == "pass"
    failed = verdict_from_command(2, stdout="out", stderr="err")
    assert (failed.verdict, failed.reasons) == ("fail", ("exit_code_2",))
    assert failed.details["stdout"] == "out" and failed.details["stderr"] == "err"
    assert failed.evidence_hash == evidence_hash(
        {"exit_code": 2, "signal": None, "stdout": "out", "stderr": "err"}
    )
    undecided = verdict_from_command(5, unknown_codes=(5,))
    assert (undecided.verdict, undecided.reasons) == ("unknown", ("exit_code_5",))
    killed = verdict_from_command(None, signal_name="SIGTERM")
    assert (killed.verdict, killed.reasons) == ("unknown", ("killed_by_SIGTERM",))
    assert verdict_from_command(None).reasons == ("killed_by_signal",)


@pytest.mark.parametrize(("code", "verdict"), [(0, "pass"), (1, "fail"), (2, "fail")])
def test_run_test_suite_exit_codes(code: int, verdict: str) -> None:
    result = run_test_suite(
        [sys.executable, "-c", f"print('suite output'); raise SystemExit({code})"]
    )
    assert result.verdict == verdict
    assert result.details["exit_code"] == code
    assert "suite output" in str(result.details["stdout"])
    assert result.evidence_hash is not None and result.evidence_hash.startswith("sha256:")


def test_run_test_suite_unknowns() -> None:
    no_tests = run_test_suite([sys.executable, "-c", "raise SystemExit(5)"], unknown_codes=(5,))
    assert no_tests.verdict == "unknown"
    missing = run_test_suite(["definitely-not-a-real-program-xyz"])
    assert (missing.verdict, missing.reasons) == ("unknown", ("command_not_found",))
    slow = run_test_suite([sys.executable, "-c", "import time; time.sleep(5)"], timeout=0.3)
    assert (slow.verdict, slow.reasons) == ("unknown", ("timed_out",))
    assert run_test_suite([]).reasons == ("empty_command",)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX signals")
def test_run_test_suite_killed_by_a_signal() -> None:
    killed = run_test_suite(
        [sys.executable, "-c", "import os, signal; os.kill(os.getpid(), signal.SIGKILL)"]
    )
    assert (killed.verdict, killed.reasons) == ("unknown", ("killed_by_SIGKILL",))


# ── business rules ──


class Refund(BaseModel):
    """A structured refund decision."""

    order_id: str
    amount: float
    approved: bool


GOOD = '{"order_id": "A-100", "amount": 12.5, "approved": true}'
RULES = {
    "amount is positive": lambda r: r.amount > 0,
    "order id is known": lambda r: r.order_id.startswith("A-"),
}


def test_validate_output_pass_and_inputs() -> None:
    result = validate_output(GOOD, Refund, rules=RULES)
    assert result.verdict == "pass" and result.passed and result.reasons == ()
    assert result.value is not None and result.value.amount == 12.5
    assert result.source == "business_rule"
    assert result.evidence_hash == evidence_hash(json.loads(GOOD))
    assert validate_output(GOOD.encode(), Refund).verdict == "pass"
    assert validate_output(json.loads(GOOD), Refund).verdict == "pass"
    model = Refund(order_id="A-1", amount=1, approved=False)
    assert validate_output(model, Refund).verdict == "pass"


def test_validate_output_failures_name_fields_never_values() -> None:
    bad_json = validate_output("{not json", Refund)
    assert (bad_json.verdict, bad_json.reasons, bad_json.value) == ("fail", ("invalid_json",), None)
    assert bad_json.evidence_hash == evidence_hash({"text": "{not json"})
    wrong = validate_output('{"order_id": "SECRET-VALUE", "amount": "lots"}', Refund)
    assert wrong.verdict == "fail"
    assert {r.split(":")[0] for r in wrong.reasons} == {"$.amount", "$.approved"}
    assert all("SECRET-VALUE" not in r and "lots" not in r for r in wrong.reasons)
    nested = validate_output({"order_id": ["x"], "amount": 1, "approved": True}, Refund)
    assert nested.reasons[0].startswith("$.order_id:")


def test_validate_output_rules() -> None:
    negative = validate_output(
        '{"order_id": "B-1", "amount": -1, "approved": true}', Refund, rules=RULES
    )
    assert negative.verdict == "fail"
    assert negative.failed_rules == ("amount is positive", "order id is known")
    assert negative.reasons == ("amount is positive", "order id is known")
    assert negative.value is not None

    def broken(_refund: Refund) -> bool:
        raise ZeroDivisionError

    raised = validate_output(GOOD, Refund, rules={"broken": broken})
    assert (raised.verdict, raised.reasons) == ("fail", ("broken: ZeroDivisionError",))
    explained = validate_output(GOOD, Refund, rules={"cap": lambda r: "over the cap"})
    assert explained.reasons == ("cap: over the cap",)
    holds = validate_output(GOOD, Refund, rules={"none means holds": lambda r: None})
    assert holds.verdict == "pass"


# ── webhooks ──


def _signed(
    payload: dict[str, Any], *, now: float = NOW, secret: str = SECRET
) -> tuple[str, dict[str, str]]:
    body = json.dumps(payload)
    return body, sign_webhook(body, secret=secret, now_s=now)


PAYLOAD = {"event_id": "evt_1", "request_id": "req_c_1", "verdict": "pass"}


def _verifier(**kwargs: Any) -> WebhookVerifier:
    return WebhookVerifier(SECRET, clock=lambda: NOW, **kwargs)


def test_sign_webhook_uses_the_shared_recipe() -> None:
    body, headers = _signed(PAYLOAD)
    expected = hmac.new(
        SECRET.encode(), f"{int(NOW)}.".encode() + body.encode(), hashlib.sha256
    ).hexdigest()
    assert WEBHOOK_SIGNATURE_HEADER == "x-webhook-signature"
    assert WEBHOOK_TIMESTAMP_HEADER == "x-webhook-timestamp"
    assert headers == {
        WEBHOOK_TIMESTAMP_HEADER: str(int(NOW)),
        WEBHOOK_SIGNATURE_HEADER: "sha256=" + expected,
    }


def test_verify_accepts_a_good_delivery_with_any_header_case() -> None:
    body, headers = _signed(PAYLOAD)
    upper = {k.upper(): v for k, v in headers.items()}
    assert _verifier().verify(body, upper) == PAYLOAD
    assert _verifier().verify(body.encode(), headers) == PAYLOAD
    listed = {k: [v] for k, v in headers.items()}  # a multi-value header mapping
    assert _verifier().verify(body, listed) == PAYLOAD


_ZERO = "sha256=" + "0" * 64


@pytest.mark.parametrize(
    ("mutate", "error", "reason"),
    [
        (
            lambda b, h: (b, {**h, WEBHOOK_SIGNATURE_HEADER: _ZERO}),
            WebhookSignatureError,
            "bad_signature",
        ),
        (lambda b, h: (b.replace("pass", "fail"), h), WebhookSignatureError, "bad_signature"),
        (
            lambda b, h: (b, {WEBHOOK_TIMESTAMP_HEADER: h[WEBHOOK_TIMESTAMP_HEADER]}),
            WebhookSignatureError,
            "missing_signature",
        ),
        (
            lambda b, h: (b, {WEBHOOK_SIGNATURE_HEADER: h[WEBHOOK_SIGNATURE_HEADER]}),
            WebhookTimestampError,
            "missing_timestamp",
        ),
        (
            lambda b, h: (b, {**h, WEBHOOK_SIGNATURE_HEADER: "sha1=abc"}),
            WebhookSignatureError,
            "malformed_signature",
        ),
        (
            lambda b, h: (b, {**h, WEBHOOK_TIMESTAMP_HEADER: "soon"}),
            WebhookTimestampError,
            "malformed_timestamp",
        ),
        (
            lambda b, h: (b, {**h, WEBHOOK_TIMESTAMP_HEADER: str(int(NOW) + 1)}),
            WebhookSignatureError,
            "bad_signature",
        ),
    ],
    ids=[
        "forged",
        "tampered-body",
        "no-signature",
        "no-timestamp",
        "malformed-signature",
        "malformed-timestamp",
        "moved-timestamp",
    ],
)
def test_verify_refuses_bad_deliveries(
    mutate: Any, error: type[WebhookVerificationError], reason: str
) -> None:
    body, headers = mutate(*_signed(PAYLOAD))
    with pytest.raises(error) as info:
        _verifier().verify(body, headers)
    assert info.value.reason == reason and info.value.http_status == 401
    assert SECRET not in str(info.value) and "sha256=" not in str(info.value)
    assert info.value.status == 0


@pytest.mark.parametrize(
    ("offset", "fresh"), [(0, True), (300, True), (-300, True), (301, False), (-301, False)]
)
def test_timestamp_tolerance_both_ways(offset: int, fresh: bool) -> None:
    body, headers = _signed(PAYLOAD, now=NOW + offset)
    if fresh:
        assert _verifier().verify(body, headers)["event_id"] == "evt_1"
    else:
        with pytest.raises(WebhookTimestampError) as info:
            _verifier().verify(body, headers)
        assert info.value.reason == "stale_timestamp"
    body, headers = _signed(PAYLOAD, now=NOW + 60)
    with pytest.raises(WebhookTimestampError):
        _verifier(tolerance_s=30).verify(body, headers)


def test_a_stale_delivery_is_refused_before_its_signature_is_checked() -> None:
    body, headers = _signed(PAYLOAD, now=NOW - 3600, secret="someone-else")
    with pytest.raises(WebhookTimestampError):
        _verifier().verify(body, headers)


def test_custom_header_names() -> None:
    body = json.dumps(PAYLOAD)
    headers = sign_webhook(
        body, secret=SECRET, now_s=NOW, signature_header="x-sig", timestamp_header="x-ts"
    )
    assert set(headers) == {"x-sig", "x-ts"}
    verifier = WebhookVerifier(
        SECRET, signature_header="x-sig", timestamp_header="x-ts", clock=lambda: NOW
    )
    assert verifier.verify(body, headers) == PAYLOAD


def test_secret_rotation_env_and_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    body, headers = _signed(PAYLOAD, secret="old-secret")
    rotating = WebhookVerifier(["new-secret", "old-secret"], clock=lambda: NOW)
    assert rotating.verify(body, headers)["verdict"] == "pass"
    assert "old-secret" not in repr(rotating) and "2 hidden" in repr(rotating)
    monkeypatch.delenv(DEFAULT_WEBHOOK_SECRET_ENV, raising=False)
    with pytest.raises(ConfigurationError) as info:
        WebhookVerifier()
    assert info.value.code == "missing_webhook_secret"
    with pytest.raises(ConfigurationError):
        WebhookVerifier("")
    with pytest.raises(ConfigurationError):
        WebhookVerifier([])
    monkeypatch.setenv(DEFAULT_WEBHOOK_SECRET_ENV, SECRET)
    body, headers = _signed(PAYLOAD)
    assert WebhookVerifier(clock=lambda: NOW).verify(body, headers)["event_id"] == "evt_1"
    assert sign_webhook(body, now_s=NOW) == headers
    monkeypatch.setenv("MY_HOOK_SECRET", "custom")
    custom = WebhookVerifier(secret_env="MY_HOOK_SECRET", clock=lambda: NOW)
    body, headers = _signed(PAYLOAD, secret="custom")
    assert custom.verify(body, headers) == PAYLOAD


@pytest.mark.parametrize("payload", ["[1, 2]", "not json"])
def test_signed_but_malformed_bodies(payload: str) -> None:
    headers = sign_webhook(payload, secret=SECRET, now_s=NOW)
    with pytest.raises(WebhookPayloadError) as info:
        _verifier().verify(payload, headers)
    assert info.value.reason == "malformed_payload" and info.value.http_status == 400


@pytest.mark.parametrize(
    "payload",
    [
        {"request_id": "r", "verdict": "pass"},
        {"event_id": "e", "verdict": "pass"},
        {"event_id": "e", "request_id": "r", "verdict": "maybe"},
        {"event_id": 1, "request_id": "r", "verdict": "pass"},
    ],
)
def test_parse_webhook_outcome_requires_the_fields(payload: dict[str, Any]) -> None:
    with pytest.raises(WebhookPayloadError):
        parse_webhook_outcome(payload)


def test_parse_webhook_outcome_optional_fields() -> None:
    parsed = parse_webhook_outcome(
        {**PAYLOAD, "observed_at": "2026-10-29T00:00:00Z", "evidence_hash": "ab", "extra": 1}
    )
    assert parsed == WebhookOutcome("evt_1", "req_c_1", "pass", "2026-10-29T00:00:00Z", "ab")


def test_memory_dedupe_store() -> None:
    now = [0.0]
    store = MemoryDedupeStore(max_entries=2, clock=lambda: now[0])
    assert isinstance(store, DedupeStore)
    assert store.claim("a", 10) and not store.claim("a", 10)
    store.release("a")
    assert store.claim("a", 10)
    assert store.claim("b", 10) and store.claim("c", 10)  # "a" evicted: at most two remembered
    assert len(store) == 2 and store.claim("a", 10)
    now[0] = 100.0
    assert store.claim("c", 10)  # expired
    store.release("never-claimed")


def _handler(dedupe: DedupeStore | None = None) -> WebhookOutcomeHandler:
    return WebhookOutcomeHandler(_verifier(), dedupe=dedupe)


def test_handler_reports_once_and_ignores_redeliveries(mock_gateway: MockGateway) -> None:
    handler = _handler()
    body, headers = _signed(PAYLOAD)
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        first = handler.handle(client, body, headers)
        again = handler.handle(client, body, headers)
        forged = handler.handle(client, body, {**headers, WEBHOOK_SIGNATURE_HEADER: _ZERO})
    assert (first.status, first.http_status) == ("reported", 200)
    assert first.report is not None and first.report.reported
    assert (again.status, again.http_status, again.report) == ("duplicate", 200, None)
    assert again.outcome == first.outcome
    assert (forged.status, forged.http_status, forged.reason) == ("rejected", 401, "bad_signature")
    posts = [r for r in mock_gateway.requests if r["path"] == "/v1/requests/req_c_1/outcomes"]
    assert len(posts) == 1
    sent = posts[0]["body"]
    assert (sent["channel"], sent["kind"]) == ("resolution", "resolved_true")
    assert sent["observed_at"] == "2027-01-15T08:00:00.000Z"  # the signed timestamp
    assert sent["source_event_id"] == report_source_event_id("req_c_1", "pass", "webhook", "evt_1")


def test_handler_rejects_malformed_payloads(mock_gateway: MockGateway) -> None:
    body, headers = _signed({"event_id": "e"})
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        handled = _handler().handle(client, body, headers)
        bad_request_id = _handler().handle(client, *_signed({**PAYLOAD, "request_id": "a b"}))
    assert (handled.status, handled.http_status, handled.reason) == (
        "rejected",
        400,
        "malformed_payload",
    )
    assert (bad_request_id.status, bad_request_id.http_status) == ("rejected", 400)
    assert mock_gateway.requests == []


def test_two_handlers_racing_still_record_one_outcome(mock_gateway: MockGateway) -> None:
    body, headers = _signed({**PAYLOAD, "event_id": "evt_race", "verdict": "fail"})
    with (
        UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as one,
        UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as two,
    ):
        first = _handler().handle(one, body, headers)  # separate processes, separate stores
        second = _handler().handle(two, body, headers)
    assert first.report is not None and second.report is not None
    assert first.report.reported and second.report.reported
    assert first.report.source_event_id == second.report.source_event_id
    assert second.report.outcome_status == "duplicate"


def test_an_unacknowledged_report_is_deferred_and_the_claim_released(
    mock_gateway: MockGateway,
) -> None:
    store = MemoryDedupeStore()
    handler = _handler(store)
    mock_gateway.fail("/v1/requests/req_c_1/outcomes", status=503, times=1)
    body, headers = _signed(PAYLOAD)
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url, max_retries=0) as client:
        deferred = handler.handle(client, body, headers)
        assert (deferred.status, deferred.http_status) == ("deferred", 503)
        assert deferred.reason == "provider_unavailable"
        retried = handler.handle(client, body, headers)  # the sender redelivers
    assert retried.status == "reported"
    assert retried.report is not None and retried.report.reported
    posts = [r for r in mock_gateway.requests if r["path"] == "/v1/requests/req_c_1/outcomes"]
    assert len(posts) == 2 and posts[0]["body"] == posts[1]["body"]


def test_handler_defers_and_releases_when_reporting_raises() -> None:
    store = MemoryDedupeStore()
    handler = _handler(store)
    body, headers = _signed(PAYLOAD)
    client = UltraRouter(api_key=TEST_KEY, base_url="http://gateway.test")

    def boom(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("the outcome store could not be written")

    client.outcomes.report = boom  # type: ignore[method-assign]
    handled = handler.handle(client, body, headers)
    assert (handled.status, handled.http_status, handled.reason) == (
        "deferred",
        503,
        "RuntimeError",
    )
    assert store.claim("evt_1", 60)  # released, so a redelivery can retry


def test_handler_unknown_verdict_reports_nothing(mock_gateway: MockGateway) -> None:
    body, headers = _signed({**PAYLOAD, "verdict": "unknown"})
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        handled = _handler().handle(client, body, headers)
    assert handled.status == "reported" and isinstance(handled.report, NotReportedOutcome)
    assert mock_gateway.requests == []


def test_handler_custom_parser(mock_gateway: MockGateway) -> None:
    def parse(payload: Any) -> WebhookOutcome:
        return WebhookOutcome(
            event_id=payload["id"],
            request_id=payload["meta"]["ur_request_id"],
            verdict="pass" if payload["status"] == "resolved" else "fail",
        )

    handler = WebhookOutcomeHandler(_verifier(), parse=parse)
    body, headers = _signed(
        {"id": "x1", "status": "reopened", "meta": {"ur_request_id": "req_c_2"}}
    )
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        handled = handler.handle(client, body, headers)
        broken = handler.handle(client, *_signed({"id": "x2"}))
    assert handled.report is not None and handled.report.reported
    assert handled.report.kind == "resolved_false"
    assert (broken.status, broken.reason) == ("rejected", "malformed_payload")


async def test_async_handler(mock_gateway: MockGateway) -> None:
    handler = _handler()
    body, headers = _signed({**PAYLOAD, "event_id": "evt_async"})
    stale = sign_webhook(body, secret=SECRET, now_s=NOW - 3600)
    async with AsyncUltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        first = await handler.ahandle(client, body, headers)
        again = await handler.ahandle(client, body, headers)
        refused = await handler.ahandle(client, body, stale)
    assert (first.status, again.status) == ("reported", "duplicate")
    assert (refused.status, refused.reason) == ("rejected", "stale_timestamp")


async def test_async_handler_defers_on_failure() -> None:
    store = MemoryDedupeStore()
    handler = _handler(store)
    body, headers = _signed(PAYLOAD)
    client = AsyncUltraRouter(api_key=TEST_KEY, base_url="http://gateway.test")

    async def boom(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("down")

    client.outcomes.report = boom  # type: ignore[method-assign]
    handled = await handler.ahandle(client, body, headers)
    assert handled.status == "deferred"
    assert store.claim("evt_1", 60)
    await client.close()
