"""The outcome ledger: durable queue semantics, artifacts, finals and the artifact scope."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

import httpx
import pytest

from conftest import TEST_KEY, MockGateway
from ultrarouter import (
    AsyncUltraRouter,
    FileOutcomeStore,
    InvalidRequestError,
    MemoryOutcomeStore,
    OutcomeStore,
    OutcomeStoreError,
    UltraRouter,
    diff_stats,
)
from ultrarouter._queue import OutcomeQueue, iso_from_ms, new_ulid

EVENT = {"channel": "behavioral", "kind": "accepted"}


def _result_row(event: dict[str, Any], status: str = "accepted") -> dict[str, Any]:
    return {
        "status": status,
        "id": "oev_1",
        "source_event_id": event.get("source_event_id"),
        "canonical_target_id": "art_1",
        "target_kind": "artifact",
        "artifact_version": 1,
        "latency_class": "instant",
        "source": "declared",
        "learning_use": ["rank"],
        "reason": None,
    }


class FlakyGateway:
    """Fails the first ``failures`` outcome posts with ``status``, then accepts."""

    def __init__(self, failures: int, status: int = 503) -> None:
        self.failures = failures
        self.status = status
        self.bodies: list[dict[str, Any]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        self.bodies.append(body)
        if len(self.bodies) <= self.failures:
            return httpx.Response(
                self.status,
                json={
                    "error": {
                        "code": "provider_unavailable" if self.status >= 500 else "invalid_request",
                        "message": "x",
                        "request_id": "r",
                        "retryable": self.status >= 500,
                    }
                },
            )
        if request.url.path.startswith("/v1/requests/"):
            return httpx.Response(202, json=_result_row(body))
        return httpx.Response(
            202, json={"object": "list", "data": [_result_row(e) for e in body["outcomes"]]}
        )


def _client(handler: Any, store: OutcomeStore | None = None) -> UltraRouter:
    return UltraRouter(
        api_key=TEST_KEY,
        base_url="http://gw",
        max_retries=0,
        outcome_store=store,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def test_ulid_and_iso_format() -> None:
    a, b = new_ulid(0), new_ulid(0)
    assert len(a) == 26 and a[:10] == "0000000000" and a != b
    assert iso_from_ms(0) == "1970-01-01T00:00:00.000Z"
    assert iso_from_ms(1_700_000_000_123.9) == "2023-11-14T22:13:20.123Z"


def test_record_finalizes_and_sends_a_provenance_free_event() -> None:
    gateway = FlakyGateway(0)
    with _client(gateway) as client:
        receipt = client.outcomes.record("art_1", {**EVENT, "value": {"edits": 2}})
    assert receipt.status == "delivered" and receipt.result is not None
    sent = gateway.bodies[0]["outcomes"][0]
    assert set(sent) == {"channel", "kind", "value", "observed_at", "source_event_id"}
    assert sent["observed_at"].endswith("Z") and len(sent["source_event_id"]) == 26


def test_caller_supplied_identity_is_preserved() -> None:
    gateway = FlakyGateway(0)
    with _client(gateway) as client:
        client.outcomes.record(
            {"artifact": "art_1"},
            {**EVENT, "observed_at": "2026-01-01T00:00:00.000Z", "source_event_id": "mine"},
        )
    sent = gateway.bodies[0]["outcomes"][0]
    assert (sent["observed_at"], sent["source_event_id"]) == ("2026-01-01T00:00:00.000Z", "mine")


def test_retry_law_persist_before_send_and_replay_verbatim() -> None:
    gateway = FlakyGateway(failures=1)
    store = MemoryOutcomeStore()
    with _client(gateway, store) as client:
        receipt = client.outcomes.record("art_1", EVENT)
        assert receipt.status == "queued" and receipt.error is not None and receipt.error.retryable
        assert len(store.list()) == 1 and store.list()[0]["attempts"] == 1
        report = client.outcomes.flush()
    assert (report.delivered, report.rejected, report.pending) == (1, 0, 0)
    assert gateway.bodies[0] == gateway.bodies[1], "a retry must replay the identical event"


def test_terminal_refusal_is_dropped_not_retried() -> None:
    gateway = FlakyGateway(failures=1, status=400)
    store = MemoryOutcomeStore()
    with _client(gateway, store) as client:
        receipt = client.outcomes.record("art_1", EVENT)
    assert receipt.status == "rejected"
    assert store.list() == []


def test_request_target_uses_the_request_shortcut() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return FlakyGateway(0)(request)

    with _client(handler) as client:
        receipt = client.outcomes.record({"request": "req_9"}, EVENT)
        alias = client.record_outcome({"request": "req_9"}, EVENT)
    assert receipt.status == alias.status == "delivered"
    assert seen[0].url.path == "/v1/requests/req_9/outcomes"
    assert "outcomes" not in json.loads(seen[0].content)


def test_invalid_target_is_refused() -> None:
    with _client(FlakyGateway(0)) as client, pytest.raises(InvalidRequestError):
        client.outcomes.record({"nope": "x"}, EVENT)


def test_file_store_survives_a_restart(tmp_path: Path) -> None:
    path = tmp_path / "queue" / "outcomes.json"
    with _client(FlakyGateway(failures=99), FileOutcomeStore(path)) as client:
        assert client.outcomes.record("art_1", EVENT).status == "queued"
    assert path.exists() and oct(path.stat().st_mode & 0o777) == "0o600"
    persisted = json.loads(path.read_text())
    assert persisted[0]["event"]["kind"] == "accepted"
    gateway = FlakyGateway(0)
    with _client(gateway, FileOutcomeStore(path)) as client:
        report = client.outcomes.flush()
    assert report.delivered == 1
    assert json.loads(path.read_text()) == []
    assert gateway.bodies[0]["outcomes"][0] == persisted[0]["event"]


def test_file_store_starts_empty_only_when_the_file_is_absent(tmp_path: Path) -> None:
    path = tmp_path / "new" / "q.json"
    store = FileOutcomeStore(path)
    assert store.list() == []
    assert not path.exists(), "reading never creates the file"
    store.append({"id": "x", "event": {}})
    assert [e["id"] for e in FileOutcomeStore(path).list()] == ["x"]


@pytest.mark.parametrize(
    "content",
    ["{not json", '{"id": "x"}', '[{"id": "x"}, 3]', '[{"event": {}}]', ""],
    ids=["malformed", "not-a-list", "non-object-entry", "entry-without-id", "empty"],
)
def test_file_store_refuses_damaged_state_and_preserves_the_file(
    tmp_path: Path, content: str
) -> None:
    path = tmp_path / "q.json"
    path.write_text(content)
    store = FileOutcomeStore(path)
    with pytest.raises(OutcomeStoreError) as info:
        store.list()
    assert str(path) in str(info.value)
    with pytest.raises(OutcomeStoreError):
        store.append({"id": "y", "event": {}})
    with pytest.raises(OutcomeStoreError):
        store.remove("x")
    assert path.read_text() == content, "the damaged file is kept for recovery"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["q.json"], "no temporary leftovers"


@pytest.mark.skipif(os.name != "posix" or os.geteuid() == 0, reason="needs a non-root POSIX user")
def test_file_store_read_error_is_raised_not_treated_as_empty(tmp_path: Path) -> None:
    path = tmp_path / "q.json"
    original = json.dumps([{"id": "keep", "event": {"kind": "accepted"}}])
    path.write_text(original)
    path.chmod(0o000)
    try:
        store = FileOutcomeStore(path)
        with pytest.raises(OutcomeStoreError):
            store.append({"id": "new", "event": {}})
    finally:
        path.chmod(0o600)
    assert path.read_text() == original
    assert [e["id"] for e in FileOutcomeStore(path).list()] == ["keep"]


def test_file_store_path_that_is_a_directory_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(OutcomeStoreError):
        FileOutcomeStore(tmp_path).list()


def test_record_with_a_damaged_store_raises_and_sends_nothing(tmp_path: Path) -> None:
    path = tmp_path / "q.json"
    path.write_text("{damaged")
    gateway = FlakyGateway(0)
    with _client(gateway, FileOutcomeStore(path)) as client:
        with pytest.raises(OutcomeStoreError):
            client.outcomes.record("art_1", EVENT)
        with pytest.raises(OutcomeStoreError):
            client.outcomes.flush()
    assert gateway.bodies == []
    assert path.read_text() == "{damaged"


def test_queue_with_injected_clock_and_ids() -> None:
    sent: list[dict[str, Any]] = []
    ids = iter(f"id-{i}" for i in range(10))
    queue = OutcomeQueue(
        MemoryOutcomeStore(),
        lambda e, o: sent.append(e) or {"status": "accepted"},
        now_ms=lambda: 0.0,
        gen_id=lambda: next(ids),
    )
    receipt = queue.enqueue({"artifact": "a"}, EVENT)
    assert receipt.entry_id == "id-0"
    assert sent[0]["event"] == {
        **EVENT,
        "observed_at": "1970-01-01T00:00:00.000Z",
        "source_event_id": "id-1",
    }
    assert queue.size() == 0


def test_queue_never_prints(capsys: pytest.CaptureFixture[str]) -> None:
    with _client(FlakyGateway(failures=1)) as client:
        client.outcomes.record("art_1", {**EVENT, "value": {"note": "should stay private"}})
        client.outcomes.flush()
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""


# ── artifacts, finals, scope (against the mock gateway) ──


def test_artifacts_lifecycle(mock_gateway: MockGateway) -> None:
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        kind = client.artifact_types.upsert(
            name="support-reply",
            archetype="draft",
            objective={
                "metric": "acceptance_rate",
                "unit": "ratio",
                "direction": "higher_is_better",
                "resolution_criteria": "approved",
                "source": "reviewer",
                "window": "P7D",
            },
        )
        artifact = client.artifacts.create(
            key="ticket:1:reply", archetype="draft", request_ids=["req_1"]
        )
        fetched = client.artifacts.get(artifact.id)
        page = client.artifacts.list(limit=5, key="ticket:1:reply")
        stats = diff_stats("Draft reply.", "Final reply, edited.")
        final = client.artifacts.final(
            artifact.id, diff_stats=stats, final_hash=stats["final_hash"]
        )
        batch = client.outcomes.batch(
            [
                {"artifact_key": "ticket:1:reply", **EVENT, "source_event_id": "e1"},
                {"artifact_key": "ticket:1:reply", **EVENT, "source_event_id": "e1"},
            ]
        )
        pending = client.outcomes.pending(state="overdue")
    assert kind.object
    assert artifact.key == "ticket:1:reply" and artifact.id.startswith("art_")
    assert fetched.id == artifact.id
    assert page.object == "list"
    assert final.object
    assert (batch.accepted, batch.duplicate) == (1, 1)
    assert pending.object == "list"
    final_body = mock_gateway.requests[4]["body"]
    assert set(final_body) == {"diff_stats", "final_hash"}, "no text is sent without consent"
    assert mock_gateway.requests[3]["query"] == {"limit": "5", "key": "ticket:1:reply"}


def test_with_artifact_binds_requests_and_flushes(mock_gateway: MockGateway) -> None:
    mock_gateway.fail(
        "/v1/artifacts/" + _artifact_id("ticket:7") + "/outcomes",
        status=503,
        code="provider_unavailable",
    )
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url, max_retries=0) as client:
        with client.with_artifact("ticket:7") as scope:
            reply = scope.chat.completions.create(
                model="m/x", messages=[{"role": "user", "content": "hi"}]
            )
            scope.embeddings.create(model="m/e", input="x")
            receipt = scope.record(EVENT)
            assert receipt.status == "queued"
        assert client._outcome_queue.size() == 0, "the scope flushes on exit"
    assert reply.ur.artifact_id == _artifact_id("ticket:7")
    chat_body = mock_gateway.requests[0]["body"]
    assert chat_body["ur"] == {"artifact": "ticket:7"}
    assert mock_gateway.requests[1]["body"]["ur"] == {"artifact": "ticket:7"}


def test_with_artifact_flushes_even_on_error(mock_gateway: MockGateway) -> None:
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url, max_retries=0) as client:
        mock_gateway.fail(
            "/v1/artifacts/" + _artifact_id("k") + "/outcomes",
            status=503,
            code="provider_unavailable",
        )
        with pytest.raises(RuntimeError), client.with_artifact("k") as scope:
            scope.record(EVENT)
            raise RuntimeError("boom")
        assert client._outcome_queue.size() == 0


async def test_async_ledger_and_scope(mock_gateway: MockGateway) -> None:
    async with AsyncUltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        artifact = await client.artifacts.create(key="k-async")
        receipt = await client.outcomes.record(artifact.id, EVENT)
        async with client.with_artifact("k-scope") as scope:
            await scope.chat.completions.create(
                model="m/x", messages=[{"role": "user", "content": "hi"}]
            )
            scoped = await scope.record(EVENT)
            final = await scope.final(final_hash="0" * 64)
        report = await client.outcomes.flush()
        alias = await client.record_outcome({"request": "req_1"}, EVENT)
    assert receipt.status == scoped.status == alias.status == "delivered"
    assert final.object
    assert report.pending == 0


def _artifact_id(key: str) -> str:
    import hashlib

    return "art_" + hashlib.sha256(key.encode()).hexdigest()[:16]


# ── ambiguous failures keep the event (never "rejected") ──


def _error_response(status: int, code: str, retryable: bool | None = None) -> httpx.Response:
    error: dict[str, Any] = {"code": code, "message": "x", "request_id": "req_x"}
    if retryable is not None:
        error["retryable"] = retryable
    return httpx.Response(status, json={"error": error})


class ScriptedGateway:
    """Answers outcome posts from a script of callables, then accepts; records every request."""

    def __init__(self, *script: Any) -> None:
        self.script = list(script)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.script:
            step = self.script.pop(0)
            return step(request)  # type: ignore[no-any-return]
        return FlakyGateway(0)(request)


def _timeout(request: httpx.Request) -> httpx.Response:
    raise httpx.ReadTimeout("read timed out", request=request)


def _connect_error(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("refused", request=request)


AMBIGUOUS = [
    pytest.param(_timeout, id="transport-timeout"),
    pytest.param(_connect_error, id="connection-error"),
    pytest.param(lambda r: _error_response(503, "provider_unavailable"), id="503"),
    pytest.param(
        lambda r: _error_response(503, "atomic_spend_guard_unavailable", False),
        id="503-non-retryable",
    ),
    pytest.param(lambda r: _error_response(500, "internal", False), id="500-non-retryable"),
    pytest.param(lambda r: _error_response(429, "rate_limited"), id="429"),
    pytest.param(lambda r: _error_response(408, "http_408"), id="408"),
    pytest.param(lambda r: _error_response(401, "authentication"), id="401-credentials"),
    pytest.param(lambda r: _error_response(403, "permission"), id="403-credentials"),
    pytest.param(lambda r: httpx.Response(202, content=b"<html>proxy</html>"), id="garbled-2xx"),
    # 401, 403, 408 and 429 always keep the event, whatever the body, code or flag
    pytest.param(lambda r: httpx.Response(401, json={}), id="401-empty-json"),
    pytest.param(lambda r: httpx.Response(401, content=b""), id="401-no-body"),
    pytest.param(lambda r: _error_response(403, "workspace_suspended", False), id="403-unfamiliar"),
    pytest.param(lambda r: _error_response(403, "model_unpriced"), id="403-taxonomy-code"),
    pytest.param(lambda r: _error_response(408, "http_408", False), id="408-non-retryable"),
    pytest.param(lambda r: _error_response(429, "rate_limited", False), id="429-non-retryable"),
    pytest.param(lambda r: _error_response(429, "invalid_request", False), id="429-event-code"),
    # a 4xx that is not a validated, event-specific gateway refusal keeps the event
    pytest.param(
        lambda r: httpx.Response(
            400,
            content=b"<html><body>Bad Request</body></html>",
            headers={"content-type": "text/html"},
        ),
        id="400-html-from-a-proxy",
    ),
    pytest.param(lambda r: httpx.Response(404, content=b"Not Found"), id="404-plain-text"),
    pytest.param(lambda r: httpx.Response(400, content=b""), id="400-empty-body"),
    pytest.param(lambda r: httpx.Response(400, json=["not", "an", "envelope"]), id="400-json-list"),
    pytest.param(lambda r: httpx.Response(400, json={"error": "flat"}), id="400-flat-error"),
    pytest.param(
        lambda r: httpx.Response(400, json={"error": {"message": "no code"}}), id="400-no-code"
    ),
    pytest.param(lambda r: _error_response(400, "brand_new_code", False), id="400-unknown-code"),
    pytest.param(lambda r: _error_response(422, "validation_error", False), id="422-unknown-code"),
    pytest.param(
        lambda r: _error_response(400, "invalid_request", True), id="400-contradictory-flag"
    ),
    pytest.param(lambda r: _error_response(400, "not_found", False), id="400-status-code-mismatch"),
    pytest.param(lambda r: _error_response(402, "spend_cap_exceeded"), id="402-not-the-event"),
    pytest.param(lambda r: _error_response(499, "cancelled"), id="499-cancelled"),
    # an event code at its own status, but not a COMPLETE, typed envelope with retryable: false
    pytest.param(
        lambda r: httpx.Response(400, json={"error": {"code": "invalid_request"}}),
        id="400-code-only",
    ),
    pytest.param(lambda r: _incomplete(400, "invalid_request", "message"), id="400-no-message"),
    pytest.param(lambda r: _incomplete(400, "invalid_request", "request_id"), id="400-no-req-id"),
    pytest.param(lambda r: _incomplete(404, "not_found", "retryable"), id="404-no-retryable"),
    pytest.param(lambda r: _with(400, "invalid_request", retryable=None), id="400-retryable-null"),
    pytest.param(
        lambda r: _with(400, "invalid_request", retryable="false"), id="400-retryable-string"
    ),
    pytest.param(lambda r: _with(409, "conflict", retryable=0), id="409-retryable-zero"),
    pytest.param(lambda r: _with(400, "invalid_request", message=7), id="400-message-not-a-string"),
    pytest.param(lambda r: _with(404, "not_found", request_id=None), id="404-request-id-null"),
    pytest.param(lambda r: _with(409, "conflict", provider_code=5), id="409-provider-code-number"),
    pytest.param(lambda r: _with(400, "invalid_request", code=""), id="400-empty-code"),
]


def _complete(status: int, code: str) -> dict[str, Any]:
    return {"code": code, "message": "x", "request_id": "req_x", "retryable": False}


def _incomplete(status: int, code: str, missing: str) -> httpx.Response:
    error = _complete(status, code)
    del error[missing]
    return httpx.Response(status, json={"error": error})


def _with(status: int, code: str, **fields: Any) -> httpx.Response:
    return httpx.Response(status, json={"error": {**_complete(status, code), **fields}})


@pytest.mark.parametrize("failure", AMBIGUOUS)
def test_ambiguous_failure_keeps_the_event_with_the_same_identity(failure: Any) -> None:
    gateway = ScriptedGateway(failure)
    store = MemoryOutcomeStore()
    with _client(gateway, store) as client:
        receipt = client.outcomes.record("art_1", EVENT)
        assert receipt.status == "queued", receipt
        assert receipt.error is not None
        assert client.outcomes.size() == 1 and store.list()[0]["attempts"] == 1
        report = client.outcomes.flush()
    assert (report.delivered, report.rejected, report.pending) == (1, 0, 0)
    first, second = gateway.requests
    assert first.content == second.content, "the replay is byte-identical"
    assert first.headers["idempotency-key"] == second.headers["idempotency-key"]


def test_client_side_deadline_keeps_the_event() -> None:
    gateway = ScriptedGateway()
    store = MemoryOutcomeStore()
    with _client(gateway, store) as client:
        receipt = client.outcomes.record("art_1", EVENT, options={"timeout": 0})
        assert receipt.status == "queued" and receipt.error is not None
        assert receipt.error.code == "timeout"
        assert gateway.requests == []
        assert client.outcomes.flush().delivered == 1


@pytest.mark.parametrize(
    ("status", "code"), [(400, "invalid_request"), (404, "not_found"), (409, "conflict")]
)
def test_definitive_rejection_drops_the_event(status: int, code: str) -> None:
    gateway = ScriptedGateway(lambda r: _error_response(status, code, False))
    store = MemoryOutcomeStore()
    with _client(gateway, store) as client:
        receipt = client.outcomes.record("art_1", EVENT)
        assert receipt.status == "rejected"
        assert receipt.error is not None and receipt.error.status == status
        assert store.list() == []
        assert client.outcomes.flush().delivered == 0
    assert len(gateway.requests) == 1


def test_queued_entries_carry_a_stable_idempotency_key_across_restarts(tmp_path: Path) -> None:
    path = tmp_path / "q.json"
    first = ScriptedGateway(_timeout)
    with _client(first, FileOutcomeStore(path)) as client:
        assert client.outcomes.record("art_1", EVENT).status == "queued"
    stored = json.loads(path.read_text())[0]
    assert stored["idempotency_key"]
    second = ScriptedGateway()
    with _client(second, FileOutcomeStore(path)) as client:
        assert client.outcomes.flush().delivered == 1
    assert first.requests[0].headers["idempotency-key"] == stored["idempotency_key"]
    assert second.requests[0].headers["idempotency-key"] == stored["idempotency_key"]
    assert first.requests[0].content == second.requests[0].content


async def test_async_timeout_and_cancellation_keep_the_event() -> None:
    store = MemoryOutcomeStore()
    gateway = ScriptedGateway(_timeout)
    async with AsyncUltraRouter(
        api_key=TEST_KEY,
        base_url="http://gw",
        max_retries=0,
        outcome_store=store,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(gateway)),
    ) as client:
        receipt = await client.outcomes.record("art_1", EVENT)
        assert receipt.status == "queued" and receipt.error is not None
        assert receipt.error.code == "timeout"

        started = asyncio.Event()

        async def hang(request: httpx.Request) -> httpx.Response:
            started.set()
            await asyncio.sleep(30)
            return httpx.Response(202)

        client._http._transport = httpx.MockTransport(hang)  # type: ignore[attr-defined]
        task = asyncio.create_task(client.outcomes.record("art_2", EVENT))
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert sorted(e["target"]["artifact"] for e in store.list()) == ["art_1", "art_2"]

        client._http._transport = httpx.MockTransport(ScriptedGateway())  # type: ignore[attr-defined]
        report = await client.outcomes.flush()
    assert (report.delivered, report.rejected, report.pending) == (2, 0, 0)


@pytest.mark.parametrize("failure", AMBIGUOUS)
async def test_async_ambiguous_failure_keeps_the_event(failure: Any) -> None:
    gateway = ScriptedGateway(failure)
    store = MemoryOutcomeStore()
    async with AsyncUltraRouter(
        api_key=TEST_KEY,
        base_url="http://gw",
        max_retries=0,
        outcome_store=store,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(gateway)),
    ) as client:
        receipt = await client.outcomes.record("art_1", EVENT)
        assert receipt.status == "queued", receipt
        assert client.outcomes.size() == 1
        report = await client.outcomes.flush()
    assert (report.delivered, report.rejected, report.pending) == (1, 0, 0)


# ── a success the contract does not describe proves nothing ──

MALFORMED_SUCCESS = [
    pytest.param({"request": "req_1"}, {}, id="request-empty-object"),
    pytest.param({"request": "req_1"}, {"status": "weird"}, id="request-unknown-status"),
    pytest.param({"request": "req_1"}, [], id="request-list"),
    pytest.param({"artifact": "art_1"}, {"data": [{}]}, id="artifact-empty-row"),
    pytest.param({"artifact": "art_1"}, {"data": []}, id="artifact-no-rows"),
    pytest.param({"artifact": "art_1"}, {"data": {}}, id="artifact-data-not-a-list"),
    pytest.param({"artifact": "art_1"}, {}, id="artifact-empty-object"),
    pytest.param({"artifact": "art_1"}, {"data": ["accepted"]}, id="artifact-row-not-an-object"),
]


def _answer(body: Any) -> Any:
    return lambda r: httpx.Response(202, json=body)


@pytest.mark.parametrize(("target", "body"), MALFORMED_SUCCESS)
def test_malformed_success_keeps_the_event(target: dict[str, str], body: Any) -> None:
    gateway = ScriptedGateway(_answer(body))
    store = MemoryOutcomeStore()
    with _client(gateway, store) as client:
        receipt = client.outcomes.record(target, EVENT)
        assert receipt.status == "queued", receipt
        assert receipt.error is not None and receipt.error.code == "invalid_response"
        assert len(store.list()) == 1
        assert client.outcomes.flush().delivered == 1


@pytest.mark.parametrize(("target", "body"), MALFORMED_SUCCESS)
async def test_async_malformed_success_keeps_the_event(target: dict[str, str], body: Any) -> None:
    gateway = ScriptedGateway(_answer(body))
    store = MemoryOutcomeStore()
    async with AsyncUltraRouter(
        api_key=TEST_KEY,
        base_url="http://gw",
        max_retries=0,
        outcome_store=store,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(gateway)),
    ) as client:
        receipt = await client.outcomes.record(target, EVENT)
        assert receipt.status == "queued", receipt
        assert len(store.list()) == 1


@pytest.mark.parametrize("status", ["accepted", "duplicate", "conflict", "rejected"])
def test_every_documented_result_status_counts_as_delivered(status: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        row = {**_result_row(body), "status": status}
        return httpx.Response(202, json=row)

    store = MemoryOutcomeStore()
    with _client(handler, store) as client:
        receipt = client.outcomes.record({"request": "req_1"}, EVENT)
    assert receipt.status == "delivered" and receipt.result is not None
    assert receipt.result["status"] == status and store.list() == []
