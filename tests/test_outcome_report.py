"""``client.outcomes.report``: the shared verdict mapping, stable identity, idempotent delivery
(acknowledgement loss, repeats, concurrency), pending receipts and receipt waiting."""

from __future__ import annotations

import asyncio
import hashlib
import json
import threading
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
import pytest

from conftest import TEST_KEY, MockGateway
from ultrarouter import (
    OUTCOME_SOURCES,
    AsyncUltraRouter,
    InvalidRequestError,
    MemoryOutcomeStore,
    NotFoundError,
    NotReportedOutcome,
    ProxyOutcomeReport,
    ReceiptWaitTimeoutError,
    TeachingOutcomeReport,
    UltraRouter,
    report_source_event_id,
    source_teaches,
    verdict_event,
)
from ultrarouter._queue import is_outcome_result
from ultrarouter._verdicts import outcome_verdicts_document

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "outcome_verdicts.json"
PACKAGED = ROOT / "src" / "ultrarouter" / "_data" / "outcome_verdicts.json"
#: The sha256 of the fixture shared byte for byte with the TypeScript SDK.
FIXTURE_SHA256 = "e55e452d5e5374ad07ac13ab7e9b44978425151d902a620edc2586a4e9633e1e"
DOC = json.loads(FIXTURE.read_text("utf-8"))
CASES = [(source, verdict) for source in DOC["sources"] for verdict in ("pass", "fail")]
MODEL = "openai/gpt-5.2-mini"


# ── the shared fixture ──


def test_fixture_is_the_shared_copy_and_the_package_ships_it_unchanged() -> None:
    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == FIXTURE_SHA256
    assert PACKAGED.read_bytes() == FIXTURE.read_bytes()
    assert outcome_verdicts_document() == DOC
    assert tuple(DOC["sources"]) == OUTCOME_SOURCES
    assert DOC["unknown"] == {"sends": False, "result": "not_reported"}


@pytest.mark.parametrize(("source", "verdict"), CASES)
def test_mapping_is_exactly_the_fixture(source: str, verdict: str) -> None:
    expected = DOC["sources"][source][verdict]
    event = verdict_event(source, verdict)
    assert event is not None
    assert (event.channel, event.kind) == (expected["channel"], expected["kind"])
    assert event.value == expected.get("value")
    assert event.teaches is DOC["sources"][source]["teaches"] is source_teaches(source)
    assert event.label == DOC["sources"][source]["label"]


def test_unknown_and_invalid_inputs() -> None:
    for source in OUTCOME_SOURCES:
        assert verdict_event(source, "unknown") is None
    with pytest.raises(InvalidRequestError, match="source"):
        verdict_event("thumbs", "pass")
    with pytest.raises(InvalidRequestError, match="verdict"):
        verdict_event("verifier", "maybe")


def test_source_event_id_vectors_shared_with_the_typescript_sdk() -> None:
    assert (
        report_source_event_id("req_01HZX", "pass", "verifier", "suite-a")
        == "rpt_f71bac648bc0837828dff7b6e243a78283cfe82f08616f03d22235a78cd0410d"
    )
    assert (
        report_source_event_id("req_01HZX", "fail", "webhook")
        == "rpt_061f7a76e66ffc1f5ba4ba61a90fbca1740e509f979b3367002c72366090d75f"
    )


def test_source_event_id_matches_the_typescript_derivation() -> None:
    # Vectors computed independently with node's crypto (the TypeScript SDK's reportSourceEventId).
    assert (
        report_source_event_id("req_1", "pass", "verifier")
        == "rpt_c7b6e2c7c27f2b7ce45a0f8d9704bfc8ed22c2996acc7dc688efac34ff98bf29"
    )
    material = "ur-outcome-report/v1\nreq_c_X\nfail\nwebhook\nevt_9"
    assert report_source_event_id("req_c_X", "fail", "webhook", "evt_9") == (
        "rpt_" + hashlib.sha256(material.encode()).hexdigest()
    )
    assert report_source_event_id("r", "pass", "verifier", None) == report_source_event_id(
        "r", "pass", "verifier", ""
    )
    assert len({report_source_event_id("r", v, s) for s, v in CASES}) == len(CASES)


# ── on the wire, sync and async, every source and verdict ──


def _outcome_posts(gateway: MockGateway, request_id: str) -> list[dict[str, Any]]:
    path = f"/v1/requests/{request_id}/outcomes"
    return [r for r in gateway.requests if r["path"] == path and r["method"] == "POST"]


@pytest.mark.parametrize(("source", "verdict"), CASES)
def test_report_sends_the_mapped_event(
    source: str, verdict: str, mock_gateway: MockGateway
) -> None:
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        report = client.outcomes.report("req_c_1", verdict, source=source)  # type: ignore[call-overload]
    (sent,) = _outcome_posts(mock_gateway, "req_c_1")
    expected = DOC["sources"][source][verdict]
    body = sent["body"]
    assert body["channel"] == expected["channel"] and body["kind"] == expected["kind"]
    assert body.get("value") == expected.get("value")
    assert body["source_event_id"] == report_source_event_id("req_c_1", verdict, source)
    assert body["observed_at"].endswith("Z")
    assert set(body) <= {"channel", "kind", "value", "source_event_id", "observed_at"}
    assert sent["headers"]["idempotency-key"] == f"ur-outcome-{body['source_event_id']}"
    teaches = DOC["sources"][source]["teaches"]
    assert isinstance(report, TeachingOutcomeReport if teaches else ProxyOutcomeReport)
    assert report.teaches is teaches and report.reported is True
    assert report.status == "delivered" and report.outcome_status == "pending"
    assert report.channel == expected["channel"] and report.kind == expected["kind"]
    assert report.entry_id == report.source_event_id == body["source_event_id"]
    assert report.receipt is not None and report.receipt_id == report.receipt.id
    assert report.is_pending


@pytest.mark.parametrize(("source", "verdict"), CASES)
async def test_async_report_sends_the_mapped_event(
    source: str, verdict: str, mock_gateway: MockGateway
) -> None:
    async with AsyncUltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        report = await client.outcomes.report("req_c_2", verdict, source=source)  # type: ignore[call-overload]
    (sent,) = _outcome_posts(mock_gateway, "req_c_2")
    expected = DOC["sources"][source][verdict]
    assert (sent["body"]["channel"], sent["body"]["kind"]) == (
        expected["channel"],
        expected["kind"],
    )
    assert report.teaches is DOC["sources"][source]["teaches"]


@pytest.mark.parametrize("source", OUTCOME_SOURCES)
def test_unknown_sends_nothing(source: str, mock_gateway: MockGateway) -> None:
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        report = client.outcomes.report("req_c_3", "unknown", source=source)  # type: ignore[arg-type]
        assert client.outcomes.size() == 0
    assert isinstance(report, NotReportedOutcome)
    assert (report.status, report.reported, report.teaches, report.reason) == (
        "not_reported",
        False,
        False,
        "verdict_unknown",
    )
    assert mock_gateway.requests == []


async def test_async_unknown_sends_nothing(mock_gateway: MockGateway) -> None:
    async with AsyncUltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        report = await client.outcomes.report("req_c_3", "unknown", source="webhook")
    assert isinstance(report, NotReportedOutcome)
    assert mock_gateway.requests == []


def test_report_options_reach_the_event(mock_gateway: MockGateway) -> None:
    when = datetime(2026, 10, 29, 12, 30, 15, 123456, tzinfo=timezone(timedelta(hours=-3)))
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        report = client.outcomes.report(
            "req_c_4",
            "fail",
            source="human_review",
            idempotency_key="review-7",
            observed_at=when,
            evidence_hash="ab" * 32,
            supersedes="rpt_earlier",
        )
    body = _outcome_posts(mock_gateway, "req_c_4")[0]["body"]
    assert body["observed_at"] == "2026-10-29T15:30:15.123Z"
    assert body["evidence_hash"] == "ab" * 32
    assert body["supersedes_event_id"] == "rpt_earlier"
    assert body["source_event_id"] == report_source_event_id(
        "req_c_4", "fail", "human_review", "review-7"
    )
    assert report.source_event_id == body["source_event_id"]


@pytest.mark.parametrize(
    ("given", "sent"),
    [
        ("2026-10-29T15:30:15Z", "2026-10-29T15:30:15.000Z"),
        ("2026-10-29T15:30:15.987654+00:00", "2026-10-29T15:30:15.987Z"),
        ("2026-10-29T12:30:15-03:00", "2026-10-29T15:30:15.000Z"),
        ("2026-10-29", "2026-10-29T00:00:00.000Z"),
    ],
)
def test_observed_at_strings_are_normalized(
    given: str, sent: str, mock_gateway: MockGateway
) -> None:
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        client.outcomes.report("req_c_5", "pass", source="verifier", observed_at=given)
    assert _outcome_posts(mock_gateway, "req_c_5")[0]["body"]["observed_at"] == sent


@pytest.mark.parametrize(
    "kwargs",
    [
        {"request_id": "bad id"},
        {"request_id": ""},
        {"verdict": "maybe"},
        {"source": "thumbs"},
        {"idempotency_key": ""},
        {"observed_at": "yesterday"},
        {"observed_at": ""},
    ],
)
def test_invalid_reports_are_refused_before_any_network(
    kwargs: dict[str, Any], mock_gateway: MockGateway
) -> None:
    args: dict[str, Any] = {"request_id": "req_c_6", "verdict": "pass", "source": "verifier"}
    args.update(kwargs)
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        with pytest.raises(InvalidRequestError) as info:
            client.outcomes.report(
                args.pop("request_id"), args.pop("verdict"), source=args.pop("source"), **args
            )
        assert client.outcomes.size() == 0
    assert info.value.status == 0
    assert mock_gateway.requests == []


# ── idempotency: repeats, acknowledgement loss, concurrency, conflicts ──


def test_a_repeated_report_replays_the_identical_event(mock_gateway: MockGateway) -> None:
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        first = client.outcomes.report("req_c_7", "pass", source="verifier")
        second = client.outcomes.report("req_c_7", "pass", source="verifier")
        receipts = client.outcomes.receipts_for_request("req_c_7").data
    posts = _outcome_posts(mock_gateway, "req_c_7")
    assert len(posts) == 2
    assert posts[0]["body"] == posts[1]["body"]  # observed_at included
    assert posts[0]["headers"]["idempotency-key"] == posts[1]["headers"]["idempotency-key"]
    assert first.outcome_status == "pending" and second.outcome_status == "duplicate"
    assert second.receipt_id == first.receipt_id
    assert len(receipts) == 1


def test_a_different_payload_under_the_same_identity_is_a_conflict(
    mock_gateway: MockGateway,
) -> None:
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        client.outcomes.report("req_c_8", "pass", source="verifier", evidence_hash="aa")
        clash = client.outcomes.report("req_c_8", "pass", source="verifier", evidence_hash="bb")
        assert client.outcomes.size() == 0
    posts = _outcome_posts(mock_gateway, "req_c_8")
    assert posts[0]["body"]["source_event_id"] == posts[1]["body"]["source_event_id"]
    assert posts[0]["headers"]["idempotency-key"] != posts[1]["headers"]["idempotency-key"]
    assert clash.status == "rejected"
    assert clash.error is not None and clash.error.code == "conflict"


class _LedgerTransport(httpx.BaseTransport):
    """A gateway double for the outcome route: idempotent on the event identity, able to lose the
    acknowledgement of the first attempt *after* recording the event."""

    def __init__(self, *, lose_first_ack: bool = False, fail_first: int = 0) -> None:
        self.events: dict[str, str] = {}
        self.attempts: list[httpx.Request] = []
        self.lose_first_ack = lose_first_ack
        self.fail_first = fail_first
        self.lock = threading.Lock()

    def answer(self, request: httpx.Request) -> httpx.Response:
        with self.lock:
            self.attempts.append(request)
            if self.fail_first > 0:
                self.fail_first -= 1
                return httpx.Response(
                    503,
                    json={
                        "error": {
                            "code": "provider_unavailable",
                            "message": "x",
                            "request_id": "req_x",
                            "retryable": True,
                        }
                    },
                )
            body = json.loads(request.content)
            key = body["source_event_id"]
            known = self.events.get(key)
            if known is not None and known != request.content.decode():
                return httpx.Response(
                    409,
                    json={
                        "error": {
                            "code": "conflict",
                            "message": "x",
                            "request_id": "req_x",
                            "retryable": False,
                        }
                    },
                )
            status = "duplicate" if known is not None else "accepted"
            self.events[key] = request.content.decode()
            response = httpx.Response(
                202,
                json={"id": "oev_1", "status": status, "source_event_id": key, "receipt": None},
            )
            if self.lose_first_ack:
                self.lose_first_ack = False
                raise httpx.ReadError("the acknowledgement was lost after processing")
            return response

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        return self.answer(request)


class _AsyncLedgerTransport(httpx.AsyncBaseTransport):
    def __init__(self, inner: _LedgerTransport, delay: float = 0.0) -> None:
        self.inner = inner
        self.delay = delay

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        await request.aread()
        if self.delay:
            await asyncio.sleep(self.delay)
        return self.inner.answer(request)


def _client(transport: httpx.BaseTransport, **kwargs: Any) -> UltraRouter:
    return UltraRouter(
        api_key=TEST_KEY,
        base_url="http://gateway.test",
        http_client=httpx.Client(transport=transport),
        _sleep=lambda _s: None,
        **kwargs,
    )


def test_ack_loss_and_retry_never_double_report() -> None:
    ledger = _LedgerTransport(lose_first_ack=True)
    client = _client(ledger)
    report = client.outcomes.report("req_c_9", "pass", source="verifier")
    assert len(ledger.attempts) == 2  # the transport retried the lost acknowledgement
    first, second = ledger.attempts
    assert first.content == second.content
    assert first.headers["idempotency-key"] == second.headers["idempotency-key"]
    assert len(ledger.events) == 1
    assert report.status == "delivered" and report.outcome_status == "duplicate"
    assert client.outcomes.size() == 0


def test_ack_loss_with_no_retries_left_queues_then_flush_replays_once() -> None:
    ledger = _LedgerTransport(lose_first_ack=True)
    client = _client(ledger, max_retries=0)
    report = client.outcomes.report("req_c_10", "fail", source="webhook", idempotency_key="evt_1")
    assert report.status == "queued" and report.error is not None
    assert client.outcomes.size() == 1
    flushed = client.outcomes.flush()
    assert flushed.delivered == 1 and flushed.pending == 0
    again = client.outcomes.report("req_c_10", "fail", source="webhook", idempotency_key="evt_1")
    assert again.outcome_status == "duplicate"
    bodies = {a.content for a in ledger.attempts}
    assert len(bodies) == 1 and len(ledger.events) == 1
    assert len({a.headers["idempotency-key"] for a in ledger.attempts}) == 1


def test_a_queued_report_is_replayed_verbatim_by_a_repeat_call() -> None:
    ledger = _LedgerTransport(fail_first=1)
    client = _client(ledger, max_retries=0)
    queued = client.outcomes.report("req_c_11", "pass", source="verifier")
    assert queued.status == "queued"
    replay = client.outcomes.report("req_c_11", "pass", source="verifier")
    assert replay.status == "delivered" and replay.entry_id == queued.entry_id
    assert ledger.attempts[0].content == ledger.attempts[1].content
    assert client.outcomes.size() == 0


def test_concurrent_repeats_share_one_send() -> None:
    gate = threading.Event()
    ledger = _LedgerTransport()

    class Slow(httpx.BaseTransport):
        def handle_request(self, request: httpx.Request) -> httpx.Response:
            gate.wait(5)
            return ledger.answer(request)

    client = _client(Slow())
    results: list[Any] = []
    threads = [
        threading.Thread(
            target=lambda: results.append(
                client.outcomes.report("req_c_12", "pass", source="verifier")
            )
        )
        for _ in range(5)
    ]
    for thread in threads:
        thread.start()
    gate.set()
    for thread in threads:
        thread.join(5)
    assert len(results) == 5
    assert len(ledger.attempts) == 1
    assert {r.outcome_status for r in results} == {"accepted"}


async def test_async_concurrent_repeats_share_one_send_and_survive_a_cancelled_caller() -> None:
    ledger = _LedgerTransport()
    client = AsyncUltraRouter(
        api_key=TEST_KEY,
        base_url="http://gateway.test",
        http_client=httpx.AsyncClient(transport=_AsyncLedgerTransport(ledger, delay=0.05)),
    )
    first = asyncio.ensure_future(client.outcomes.report("req_c_13", "pass", source="verifier"))
    await asyncio.sleep(0)
    first.cancel()  # the caller gives up; the shared send must not be cancelled for the others
    others = await asyncio.gather(
        *(client.outcomes.report("req_c_13", "pass", source="verifier") for _ in range(3))
    )
    with pytest.raises(asyncio.CancelledError):
        await first
    assert len(ledger.attempts) == 1
    assert {r.outcome_status for r in others} == {"accepted"}
    await client.close()


async def test_async_ack_loss_retry() -> None:
    ledger = _LedgerTransport(lose_first_ack=True)

    async def no_sleep(_s: float) -> None:
        return None

    async with AsyncUltraRouter(
        api_key=TEST_KEY,
        base_url="http://gateway.test",
        http_client=httpx.AsyncClient(transport=_AsyncLedgerTransport(ledger)),
        _sleep=no_sleep,
    ) as client:
        report = await client.outcomes.report("req_c_14", "fail", source="verifier")
    assert len(ledger.attempts) == 2 and len(ledger.events) == 1
    assert report.outcome_status == "duplicate"


def test_ack_loss_over_real_http(mock_gateway: MockGateway) -> None:
    import urllib.request

    request = urllib.request.Request(  # noqa: S310 - the local mock gateway
        f"{mock_gateway.url}/__mock__/drop",
        data=json.dumps({"path": "/v1/requests/req_c_15/outcomes", "times": 1}).encode(),
        headers={"content-type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(request).close()  # noqa: S310
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url, _sleep=lambda _s: None) as client:
        report = client.outcomes.report("req_c_15", "pass", source="business_rule")
        receipts = client.outcomes.receipts_for_request("req_c_15").data
    assert len(_outcome_posts(mock_gateway, "req_c_15")) == 2
    assert report.outcome_status == "duplicate"
    assert len(receipts) == 1


# ── pending receipts in the queue ──


@pytest.mark.parametrize(
    ("answer", "is_result"),
    [
        ({"status": "pending", "receipt": {"id": "ork_1", "status": "pending"}}, True),
        ({"status": "pending"}, True),
        ({"status": "accepted"}, True),
        ({"status": "PENDING", "receipt": {"id": "ork_1"}}, False),
        ({"status": "waiting"}, False),
        (["pending"], False),
    ],
)
def test_pending_is_a_delivered_result(answer: Any, is_result: bool) -> None:
    """The shared retention fixture's rule: ``pending`` is the request shortcut's durable
    acceptance, a delivered result like ``accepted``."""
    assert is_outcome_result(answer) is is_result


def test_a_pending_answer_is_delivered_and_leaves_the_queue() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(202, json={"status": "pending"})

    store = MemoryOutcomeStore()
    client = UltraRouter(
        api_key=TEST_KEY,
        base_url="http://gateway.test",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        outcome_store=store,
    )
    report = client.outcomes.report("req_c_16", "pass", source="verifier")
    assert report.status == "delivered" and report.is_pending and store.list() == []
    assert report.receipt is None and report.receipt_id is None  # an answer without a receipt


# ── receipts ──


def test_receipt_reads_and_wait_until_applied(mock_gateway: MockGateway) -> None:
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        reply = client.chat.completions.create(
            model=MODEL, messages=[{"role": "user", "content": "Hi"}], episode_key="ep_w"
        )
        report = client.outcomes.report(reply.ur.request_id, "pass", source="verifier")
        assert report.is_pending and report.receipt is not None
        assert report.receipt.status == "pending" and not report.receipt.is_terminal
        read = client.outcomes.receipt(report.receipt.id)
        assert read.id == report.receipt.id and read.request_id == reply.ur.request_id
        final = client.outcomes.wait_for_receipt(report, timeout=10, poll_interval=0.05)
        assert final.status == "applied" and final.is_terminal
        assert final.episode == "associated" and final.outcome_event_id
        listed = client.outcomes.receipts_for_request(reply.ur.request_id)
        assert [r.id for r in listed.data] == [final.id]
        late = client.outcomes.report(reply.ur.request_id, "fail", source="verifier")
        assert late.outcome_status == "accepted" and late.receipt is not None
        assert late.receipt.status == "applied"
        proxy = client.outcomes.report(reply.ur.request_id, "pass", source="self_rating")
        assert proxy.receipt is not None and proxy.receipt.episode == "not_applicable"


async def test_async_receipts(mock_gateway: MockGateway) -> None:
    async with AsyncUltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        reply = await client.chat.completions.create(
            model=MODEL, messages=[{"role": "user", "content": "Hi"}]
        )
        report = await client.outcomes.report(reply.ur.request_id, "fail", source="webhook")
        assert report.receipt_id is not None
        assert (await client.outcomes.receipt(report.receipt_id)).status == "pending"
        final = await client.outcomes.wait_for_receipt(
            report.receipt_id, timeout=10, poll_interval=0.05
        )
        assert final.status == "applied"
        listed = await client.outcomes.receipts_for_request(reply.ur.request_id)
        assert len(listed.data) == 1


def test_an_unknown_request_expires_and_a_refused_id_is_404(mock_gateway: MockGateway) -> None:
    import urllib.request

    request = urllib.request.Request(  # noqa: S310 - the local mock gateway
        f"{mock_gateway.url}/__mock__/learning",
        data=json.dumps({"pending_ttl_s": 0.1}).encode(),
        headers={"content-type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(request).close()  # noqa: S310
    try:
        with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url, max_retries=0) as client:
            report = client.outcomes.report("req_c_never", "pass", source="verifier")
            final = client.outcomes.wait_for_receipt(report, timeout=5, poll_interval=0.05)
            assert (final.status, final.reason, final.episode) == (
                "expired",
                "request_not_found",
                "not_recorded",
            )
            refused = client.outcomes.report("req_missing", "pass", source="verifier")
            assert refused.status == "rejected" and isinstance(refused.error, NotFoundError)
            with pytest.raises(NotFoundError):
                client.outcomes.receipt("ork_unknown")
    finally:
        mock_gateway.reset()


class _Clock:
    def __init__(self) -> None:
        self.now = 1_000.0
        self.sleeps: list[float] = []

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def _receipt_client(
    answers: Callable[[int], httpx.Response], clock: _Clock, **kwargs: Any
) -> tuple[UltraRouter, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return answers(len(seen))

    client = UltraRouter(
        api_key=TEST_KEY,
        base_url="http://gateway.test",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        max_retries=0,
        _sleep=clock.sleep,
        _clock=clock.time,
        **kwargs,
    )
    return client, seen


def _receipt(status: str, **extra: Any) -> httpx.Response:
    return httpx.Response(200, json={"id": "ork_1", "status": status, **extra})


def test_wait_backs_off_and_times_out_with_the_last_receipt() -> None:
    clock = _Clock()
    client, seen = _receipt_client(lambda _n: _receipt("pending", request_id="req_1"), clock)
    with pytest.raises(ReceiptWaitTimeoutError) as info:
        client.outcomes.wait_for_receipt("ork_1", timeout=10, poll_interval=0.25)
    error = info.value
    assert error.receipt_id == "ork_1" and error.code == "timeout"
    assert error.last_receipt is not None and error.last_receipt.status == "pending"
    assert error.request_id == "req_1"
    assert clock.sleeps[:5] == [0.25, 0.5, 1.0, 2.0, 4.0]
    assert max(clock.sleeps) <= 4.0 and sum(clock.sleeps) <= 10.0
    assert all(r.url.path == "/v1/outcome-receipts/ork_1" for r in seen)


def test_wait_returns_the_terminal_receipt_and_accepts_wrapped_bodies() -> None:
    clock = _Clock()
    states = {
        1: _receipt("pending"),
        2: httpx.Response(
            200, json={"receipt": {"id": "ork_1", "status": "rejected", "reason": "x"}}
        ),
    }
    client, seen = _receipt_client(lambda n: states[n], clock)
    final = client.outcomes.wait_for_receipt("ork_1")
    assert final.status == "rejected" and final.reason == "x" and len(seen) == 2


def test_wait_keeps_polling_through_transient_failures_but_raises_refusals() -> None:
    clock = _Clock()
    answers = {
        1: httpx.Response(
            503,
            json={
                "error": {
                    "code": "provider_unavailable",
                    "message": "x",
                    "request_id": "r",
                    "retryable": True,
                }
            },
        ),
        2: _receipt("applied"),
    }
    client, _ = _receipt_client(lambda n: answers[n], clock)
    assert client.outcomes.wait_for_receipt("ork_1").status == "applied"
    refused, _ = _receipt_client(
        lambda _n: httpx.Response(
            404,
            json={
                "error": {
                    "code": "not_found",
                    "message": "x",
                    "request_id": "r",
                    "retryable": False,
                }
            },
        ),
        _Clock(),
    )
    with pytest.raises(NotFoundError):
        refused.outcomes.wait_for_receipt("ork_1")


def test_wait_needs_a_receipt() -> None:
    client, _ = _receipt_client(lambda _n: _receipt("applied"), _Clock())
    queued = TeachingOutcomeReport(
        request_id="r",
        verdict="pass",
        source="verifier",
        status="queued",
        channel="computable",
        kind="oracle_pass",
        source_event_id="rpt_1",
        entry_id="rpt_1",
    )
    with pytest.raises(InvalidRequestError, match="no gateway receipt"):
        client.outcomes.wait_for_receipt(queued)
    with pytest.raises(InvalidRequestError):
        client.outcomes.wait_for_receipt("")


@pytest.mark.parametrize(
    "body",
    [
        {"object": "list", "data": [{"id": "ork_1", "status": "pending"}]},
        {"receipts": [{"id": "ork_1", "status": "pending"}]},
        [{"id": "ork_1", "status": "pending"}],
    ],
)
def test_receipt_list_shapes(body: Any) -> None:
    client, _ = _receipt_client(lambda _n: httpx.Response(200, json=body), _Clock())
    listed = client.outcomes.receipts_for_request("req_1")
    assert [r.id for r in listed.data] == ["ork_1"]


async def test_async_wait_is_cancellable_and_times_out() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _receipt("pending")

    async with AsyncUltraRouter(
        api_key=TEST_KEY,
        base_url="http://gateway.test",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    ) as client:
        task = asyncio.ensure_future(
            client.outcomes.wait_for_receipt("ork_1", timeout=30, poll_interval=0.05)
        )
        await asyncio.sleep(0.12)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(client.outcomes.wait_for_receipt("ork_1", timeout=30), 0.1)
        with pytest.raises(ReceiptWaitTimeoutError):
            await client.outcomes.wait_for_receipt("ork_1", timeout=0.15, poll_interval=0.05)


def test_wait_ends_on_a_non_retryable_server_error_and_survives_a_read_timeout() -> None:
    from ultrarouter import InternalServerError

    clock = _Clock()
    broken, _ = _receipt_client(
        lambda _n: httpx.Response(
            500,
            json={
                "error": {"code": "internal", "message": "x", "request_id": "r", "retryable": False}
            },
        ),
        clock,
    )
    with pytest.raises(InternalServerError):
        broken.outcomes.wait_for_receipt("ork_1")

    calls = {"n": 0}

    def slow_then_applied(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ReadTimeout("slow read", request=request)
        return _receipt("applied")

    client = UltraRouter(
        api_key=TEST_KEY,
        base_url="http://gateway.test",
        http_client=httpx.Client(transport=httpx.MockTransport(slow_then_applied)),
        max_retries=0,
        _sleep=clock.sleep,
        _clock=clock.time,
    )
    assert client.outcomes.wait_for_receipt("ork_1").status == "applied"
    assert calls["n"] == 2  # the timed-out read was one missed poll
