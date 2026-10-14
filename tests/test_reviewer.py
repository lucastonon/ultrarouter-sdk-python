"""The reviewer adapter: signatures over the exact bytes sent, the durable queue, dead letters."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

import httpx
import pytest

from conftest import TEST_KEY, MockGateway
from ultrarouter import (
    REVIEWER_SIGNATURE_HEADER,
    REVIEWER_TIMESTAMP_HEADER,
    AsyncUltraRouter,
    PermissionDeniedError,
    UltraRouter,
    UltraRouterError,
    reviewer_signature_headers,
    reviewer_signed_payload,
    sign_payload,
)


def event(event_id: str, version: int = 1, **extra: Any) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "artifact_key": "ticket:1:reply",
        "artifact_version": version,
        "decision": "approved_with_edits",
        "effective_at": "2026-01-15T12:00:00Z",
        **extra,
    }


def test_signature_recipe_matches_a_reference_hmac() -> None:
    raw = b'{"events":[]}'
    expected = (
        "sha256=" + hmac.new(b"ur_sk_test_k", b"1700000000." + raw, hashlib.sha256).hexdigest()
    )
    assert sign_payload("ur_sk_test_k", "1700000000", raw) == expected
    assert sign_payload("ur_sk_test_k", "1700000000", raw.decode()) == expected
    assert reviewer_signed_payload("1", "x") == b"1.x"
    headers = reviewer_signature_headers("ur_sk_test_k", raw, now_s=1700000000.9)
    assert headers == {REVIEWER_TIMESTAMP_HEADER: "1700000000", REVIEWER_SIGNATURE_HEADER: expected}


def test_send_signs_the_exact_bytes_it_sends() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        timestamp = request.headers[REVIEWER_TIMESTAMP_HEADER]
        assert request.headers[REVIEWER_SIGNATURE_HEADER] == sign_payload(
            TEST_KEY, timestamp, request.content
        )
        body = json.loads(request.content)
        rows = [
            {
                "event_id": e["event_id"],
                "status": "accepted",
                "reason": "",
                "repairable": False,
                "learning_use": [],
                "artifact_id": None,
                "artifact_version": None,
                "channel": None,
                "final_version": None,
                "kind": None,
                "latency_class": None,
                "outcome_event_id": None,
            }
            for e in body["events"]
        ]
        return httpx.Response(
            200,
            json={
                "object": "reviewer_events",
                "adapter": "standard",
                "data": rows,
                "accepted": len(rows),
                "duplicate": 0,
                "rejected": 0,
                "unsupported": 0,
            },
        )

    with UltraRouter(
        api_key=TEST_KEY,
        base_url="http://gw",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    ) as client:
        result = client.reviewer.send(
            [event("e1"), event("e2")],
            reviewer_system="docs-review",
            backfill={"id": "bf1", "total": 2},
        )
    assert result.accepted == 2
    body = json.loads(captured[0].content)
    assert list(body) == ["reviewer_system", "backfill", "events"]
    assert captured[0].headers["content-type"] == "application/json"


def test_a_retry_replays_identical_bytes_and_signature() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        if len(captured) == 1:
            return httpx.Response(
                503,
                json={"error": {"code": "provider_unavailable", "message": "x", "request_id": "r"}},
            )
        return httpx.Response(
            200,
            json={
                "object": "reviewer_events",
                "adapter": "standard",
                "data": [],
                "accepted": 0,
                "duplicate": 0,
                "rejected": 0,
                "unsupported": 0,
            },
        )

    with UltraRouter(
        api_key=TEST_KEY,
        base_url="http://gw",
        _sleep=lambda _: None,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    ) as client:
        client.reviewer.send([event("e1")])
    assert captured[0].content == captured[1].content
    assert (
        captured[0].headers[REVIEWER_SIGNATURE_HEADER]
        == captured[1].headers[REVIEWER_SIGNATURE_HEADER]
    )


def test_queue_flush_duplicates_dead_letters_and_repair(mock_gateway: MockGateway) -> None:
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        client.reviewer.record(event("e1"))
        client.reviewer.record(event("e2", version=999))  # the mock refuses it as repairable
        assert mock_gateway.requests == [], "record() never touches the network"
        report = client.reviewer.flush()
        assert (report.accepted, report.dead_lettered, report.pending) == (1, 1, 0)
        letters = client.reviewer.dead_letters()
        assert [letter["event"]["event_id"] for letter in letters] == ["e2"]
        assert letters[0]["dead_letter"]["reason"].startswith("version_mismatch")
        client.reviewer.record(event("e1"))  # a replay of an accepted event
        assert client.reviewer.flush().duplicate == 1
        repaired = client.reviewer.repair(letters[0], repin_to_current_version=True)
        assert repaired.object
        if repaired.result is not None and repaired.result.status in ("accepted", "duplicate"):
            assert client.reviewer.dead_letters() == []
        setup = client.reviewer.setup()
        health = client.reviewer.health()
        tested = client.reviewer.test("replay")
    assert setup.object and health.object and tested.object
    repair_body = mock_gateway.requests[2]["body"]
    assert (
        repair_body["event"]["event_id"] == "e2" and repair_body["repin_to_current_version"] is True
    )


def test_flush_groups_by_backfill_and_batches() -> None:
    batches: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        batches.append(body)
        rows = [
            {
                "event_id": e["event_id"],
                "status": "accepted",
                "reason": "",
                "repairable": False,
                "learning_use": [],
                "artifact_id": None,
                "artifact_version": None,
                "channel": None,
                "final_version": None,
                "kind": None,
                "latency_class": None,
                "outcome_event_id": None,
            }
            for e in body["events"]
        ]
        return httpx.Response(
            200,
            json={
                "object": "reviewer_events",
                "adapter": "standard",
                "data": rows,
                "accepted": len(rows),
                "duplicate": 0,
                "rejected": 0,
                "unsupported": 0,
            },
        )

    with UltraRouter(
        api_key=TEST_KEY,
        base_url="http://gw",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    ) as client:
        client._reviewer_queue.batch_size = 2
        for i in range(3):
            client.reviewer.record(event(f"a{i}"), backfill={"id": "bf-a"})
        client.reviewer.record(event("b0"), reviewer_system="other")
        report = client.reviewer.flush()
    assert report.accepted == 4
    assert [len(b["events"]) for b in batches] == [2, 1, 1]
    assert batches[0]["backfill"] == {"id": "bf-a"} and "backfill" not in batches[2]
    assert batches[2]["reviewer_system"] == "other"


def test_bad_signature_is_raised_not_swallowed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            json={
                "error": {
                    "code": "permission",
                    "message": "invalid_signature",
                    "request_id": "r",
                    "retryable": False,
                }
            },
        )

    with UltraRouter(
        api_key=TEST_KEY,
        base_url="http://gw",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    ) as client:
        client.reviewer.record(event("e1"))
        with pytest.raises(PermissionDeniedError):
            client.reviewer.flush()
        assert len(client._reviewer_queue.pending()) == 1, "the event is kept for a later flush"


def test_retryable_failure_keeps_the_batch_queued() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    with UltraRouter(
        api_key=TEST_KEY,
        base_url="http://gw",
        max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    ) as client:
        client.reviewer.record(event("e1"))
        report = client.reviewer.flush()
    assert report.pending == 1 and report.accepted == 0


async def test_async_reviewer(mock_gateway: MockGateway) -> None:
    async with AsyncUltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        client.reviewer.record(event("x1"))
        report = await client.reviewer.flush()
        sent = await client.reviewer.send([event("x2")])
        health = await client.reviewer.health()
        setup = await client.reviewer.setup()
        tested = await client.reviewer.test()
        assert client.reviewer.dead_letters() == []
    assert report.accepted == 1 and sent.accepted == 1
    assert health.object and setup.object and tested.object


@pytest.mark.parametrize("kind", ["timeout", "deadline", "503-non-retryable"])
def test_ambiguous_failure_keeps_the_batch_queued_without_raising(kind: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if kind == "timeout":
            raise httpx.ReadTimeout("slow", request=request)
        return httpx.Response(
            503,
            json={"error": {"code": "atomic_spend_guard_unavailable", "retryable": False}},
        )

    with UltraRouter(
        api_key=TEST_KEY,
        base_url="http://gw",
        max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    ) as client:
        client.reviewer.record(event("e1"))
        options = {"timeout": 0} if kind == "deadline" else None
        report = client.reviewer.flush(options=options)  # type: ignore[arg-type]
        assert (report.accepted, report.pending, report.dropped) == (0, 1, 0)
        assert client._reviewer_queue.pending()[0]["attempts"] == 1


# ── the same retention rules as outcomes ──


def _row(event_id: str, **over: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "event_id": event_id,
        "status": "accepted",
        "reason": "",
        "repairable": False,
        "learning_use": [],
        "artifact_id": None,
        "artifact_version": None,
        "channel": None,
        "final_version": None,
        "kind": None,
        "latency_class": None,
        "outcome_event_id": None,
    }
    row.update(over)
    return row


def _verdicts(rows: list[dict[str, Any]]) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "object": "reviewer_events",
            "adapter": "standard",
            "data": rows,
            "accepted": 0,
            "duplicate": 0,
            "rejected": 0,
            "unsupported": 0,
        },
    )


def test_only_well_formed_terminal_verdicts_drop_an_event() -> None:
    rows = [
        _row("dropped-rejected", status="rejected", reason="artifact_unknown"),
        _row("dropped-unsupported", status="unsupported", reason="decision_unknown"),
        _row("kept-unknown-status", status="mystery"),
        _row("kept-missing-status", status=None),
        _row("kept-repairable-missing", status="rejected", repairable=None),
        _row("kept-reason-missing", status="rejected", reason=None),
        _row("kept-reason-not-a-string", status="unsupported", reason=3),
        _row("kept-repairable-string", status="rejected", repairable="false"),
        _row("dead-lettered", status="rejected", repairable=True, reason="version_mismatch"),
    ]

    with UltraRouter(
        api_key=TEST_KEY,
        base_url="http://gw",
        http_client=httpx.Client(transport=httpx.MockTransport(lambda r: _verdicts(rows))),
    ) as client:
        for row in rows:
            client.reviewer.record(event(row["event_id"]))
        report = client.reviewer.flush()
        pending = sorted(e["event"]["event_id"] for e in client._reviewer_queue.pending())
        letters = [e["event"]["event_id"] for e in client.reviewer.dead_letters()]
    assert (report.dropped, report.dead_lettered, report.pending) == (2, 1, 6)
    assert pending == [
        "kept-missing-status",
        "kept-reason-missing",
        "kept-reason-not-a-string",
        "kept-repairable-missing",
        "kept-repairable-string",
        "kept-unknown-status",
    ]
    assert letters == ["dead-lettered"]
    assert len(report.results) == 3, "only validated verdicts are reported"


NON_STRING_EVENT_IDS = [
    pytest.param(7, id="int"),
    pytest.param(1.5, id="float"),
    pytest.param(None, id="null"),
    pytest.param(True, id="true"),
    pytest.param(False, id="false"),
    pytest.param(["e1"], id="list"),
    pytest.param({"event_id": "e1"}, id="object"),
]


@pytest.mark.parametrize("event_id", NON_STRING_EVENT_IDS)
def test_a_verdict_without_a_string_event_id_keeps_the_event(event_id: Any) -> None:
    rows = [{"event_id": event_id, "status": "accepted"}]
    with UltraRouter(
        api_key=TEST_KEY,
        base_url="http://gw",
        http_client=httpx.Client(transport=httpx.MockTransport(lambda r: _verdicts(rows))),
    ) as client:
        client.reviewer.record(event("e1"))
        report = client.reviewer.flush()  # never raises on a 2xx answer
        assert (report.accepted, report.pending) == (0, 1)
        assert [e["event"]["event_id"] for e in client._reviewer_queue.pending()] == ["e1"]


@pytest.mark.parametrize("event_id", NON_STRING_EVENT_IDS)
async def test_async_a_verdict_without_a_string_event_id_keeps_the_event(event_id: Any) -> None:
    rows = [{"event_id": event_id, "status": "accepted"}]
    async with AsyncUltraRouter(
        api_key=TEST_KEY,
        base_url="http://gw",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(lambda r: _verdicts(rows))),
    ) as client:
        client.reviewer.record(event("e1"))
        report = await client.reviewer.flush()
        assert (report.accepted, report.pending) == (0, 1)


def test_unhashable_event_ids_next_to_a_valid_verdict() -> None:
    rows = [
        {"event_id": ["e1"], "status": "accepted"},
        {"event_id": {"id": "e1"}, "status": "rejected", "reason": "x", "repairable": False},
        _row("e2", status="accepted"),
    ]
    with UltraRouter(
        api_key=TEST_KEY,
        base_url="http://gw",
        http_client=httpx.Client(transport=httpx.MockTransport(lambda r: _verdicts(rows))),
    ) as client:
        client.reviewer.record(event("e1"))
        client.reviewer.record(event("e2"))
        report = client.reviewer.flush()
        assert (report.accepted, report.pending) == (1, 1)
        assert [e["event"]["event_id"] for e in client._reviewer_queue.pending()] == ["e1"]


@pytest.mark.parametrize(
    "body",
    [{"object": "reviewer_events"}, {"data": {}}, {"data": "accepted"}, {}],
    ids=["no-data", "data-object", "data-string", "empty"],
)
def test_a_success_without_a_verdict_list_keeps_the_batch(body: dict[str, Any]) -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=body)

    with UltraRouter(
        api_key=TEST_KEY,
        base_url="http://gw",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    ) as client:
        client._reviewer_queue.batch_size = 1
        client.reviewer.record(event("e1"))
        client.reviewer.record(event("e2"))
        report = client.reviewer.flush()
        assert (report.accepted, report.dropped, report.pending) == (0, 0, 2)
        assert len(calls) == 1, "the flush ends at the first batch that proves nothing"
        assert [e["attempts"] for e in client._reviewer_queue.pending()] == [1, 0]


async def test_async_reviewer_validates_verdicts() -> None:
    rows = [
        _row("dropped", status="rejected", reason="artifact_unknown"),
        _row("kept", status="rejected", reason=None),
    ]
    async with AsyncUltraRouter(
        api_key=TEST_KEY,
        base_url="http://gw",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(lambda r: _verdicts(rows))),
    ) as client:
        for row in rows:
            client.reviewer.record(event(row["event_id"]))
        report = await client.reviewer.flush()
        assert (report.dropped, report.pending) == (1, 1)
        assert [e["event"]["event_id"] for e in client._reviewer_queue.pending()] == ["kept"]


@pytest.mark.parametrize(
    ("response", "raises"),
    [
        pytest.param(lambda: httpx.Response(401, json={}), True, id="401-empty-json"),
        pytest.param(
            lambda: httpx.Response(
                403, json={"error": {"code": "workspace_suspended", "retryable": False}}
            ),
            True,
            id="403-unfamiliar-code",
        ),
        pytest.param(
            lambda: httpx.Response(408, json={"error": {"code": "http_408", "retryable": False}}),
            False,
            id="408-non-retryable",
        ),
        pytest.param(
            lambda: httpx.Response(
                429, json={"error": {"code": "rate_limited", "retryable": False}}
            ),
            False,
            id="429-non-retryable",
        ),
        pytest.param(
            lambda: httpx.Response(400, content=b"<html>Bad Request</html>"),
            True,
            id="400-html-from-a-proxy",
        ),
        pytest.param(
            lambda: httpx.Response(503, content=b"<html>Service Unavailable</html>"),
            False,
            id="503-html",
        ),
        pytest.param(
            lambda: httpx.Response(400, json={"error": {"code": "invalid_request"}}),
            True,
            id="400-invalid-batch",
        ),
    ],
)
def test_batch_failures_never_drop_events(response: Any, raises: bool) -> None:
    with UltraRouter(
        api_key=TEST_KEY,
        base_url="http://gw",
        max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(lambda r: response())),
    ) as client:
        client.reviewer.record(event("e1"))
        if raises:
            with pytest.raises(UltraRouterError):
                client.reviewer.flush()
        else:
            assert client.reviewer.flush().pending == 1
        assert [e["event"]["event_id"] for e in client._reviewer_queue.pending()] == ["e1"]
        assert client._reviewer_queue.pending()[0]["attempts"] == 1
