"""The durable-queue retention rules, case by case, from the fixture shared with the TypeScript SDK.

``tests/fixtures/queue_retention_cases.json`` is a byte-for-byte copy of the TypeScript SDK's
``test/fixtures/queue-retention-cases.json``. Each case is one HTTP answer to one delivery attempt
of one queued event; both SDKs must keep or remove the event exactly as the case says. Every case
runs through the synchronous and the asynchronous client.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest

from conftest import TEST_KEY
from ultrarouter import AsyncUltraRouter, MemoryOutcomeStore, UltraRouter, UltraRouterError

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "queue_retention_cases.json"
#: The sha256 of the shared fixture; a new copy from the TypeScript SDK must update it.
FIXTURE_SHA256 = "edf3d641150ea623586536bcd97947c3530742fc88ad532182a6309d1c21da45"

DATA = json.loads(FIXTURE.read_text("utf-8"))
CASES: list[dict[str, Any]] = DATA["cases"]
EVENT = {"channel": "behavioral", "kind": "accepted"}
REVIEW_EVENT = {
    "event_id": DATA["reviewer_event_id"],
    "artifact_key": "ticket:1:reply",
    "artifact_version": 1,
    "decision": "approved",
    "effective_at": "2026-01-15T12:00:00Z",
}


class _Unreadable(httpx.SyncByteStream, httpx.AsyncByteStream):
    """A body whose stream fails after the headers were received."""

    def __iter__(self) -> Iterator[bytes]:
        raise httpx.ReadError("the body stream failed (fixture)")
        yield b""  # pragma: no cover - makes this a generator

    async def __aiter__(self) -> AsyncIterator[bytes]:
        raise httpx.ReadError("the body stream failed (fixture)")
        yield b""  # pragma: no cover - makes this an async generator


def _answer(case: dict[str, Any]) -> Any:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert len(requests) == 1, "each case answers exactly one delivery attempt"
        headers = {"content-type": case["content_type"]}
        if case.get("unreadable"):
            return httpx.Response(case["status"], headers=headers, stream=_Unreadable())
        return httpx.Response(case["status"], headers=headers, content=case["body"].encode())

    return handler


def _target(case: dict[str, Any]) -> dict[str, str]:
    return {"request": "req_fixture"} if case["kind"] == "outcome" else {"artifact": "art_fixture"}


def _check_outcome(case: dict[str, Any], status: str, store: MemoryOutcomeStore) -> None:
    assert status == case["outcome"], f"{case['id']}: receipt {status} ({case['rule']})"
    assert len(store.list()) == (1 if case["expect"] == "retain" else 0), case["id"]


def _check_reviewer(
    case: dict[str, Any], report: Any, raised: bool, store: MemoryOutcomeStore
) -> None:
    entries = store.list()
    assert len(entries) == (1 if case["expect"] == "retain" else 0), case["id"]
    outcome = case["outcome"]
    if outcome == "dead_lettered":
        assert entries[0].get("dead_letter"), case["id"]
    elif outcome == "pending":
        assert not entries[0].get("dead_letter"), case["id"]
    else:
        assert not raised and report is not None, case["id"]
        assert getattr(report, outcome) == 1, f"{case['id']}: {report}"
    if raised:
        assert case["status"] >= 400 and outcome == "pending", case["id"]


def test_fixture_is_the_pinned_shared_copy() -> None:
    data = FIXTURE.read_bytes()
    assert hashlib.sha256(data).hexdigest() == FIXTURE_SHA256
    assert DATA["schema"] == "ultrarouter.queue-retention-cases.v1"
    assert len({case["id"] for case in CASES}) == len(CASES) == 273
    kinds = {case["kind"] for case in CASES}
    assert kinds == {"outcome", "artifact-outcome", "reviewer"}
    for kind in kinds:
        expected = {case["expect"] for case in CASES if case["kind"] == kind}
        assert expected == {"retain", "drop"}, kind


def test_fixture_matches_the_typescript_sdk_copy() -> None:
    reference = (
        Path(os.environ.get("ULTRAROUTER_TS_SDK", ROOT.parent / "ultrarouter-sdk-typescript"))
        / "test"
        / "fixtures"
        / "queue-retention-cases.json"
    )
    if not reference.exists():
        pytest.skip("TypeScript SDK checkout not available (set ULTRAROUTER_TS_SDK)")
    assert reference.read_bytes() == FIXTURE.read_bytes(), "copy the fixture byte-for-byte"


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_case_sync(case: dict[str, Any]) -> None:
    store = MemoryOutcomeStore()
    http = httpx.Client(transport=httpx.MockTransport(_answer(case)))
    with UltraRouter(
        api_key=TEST_KEY,
        base_url="http://gw",
        max_retries=0,
        outcome_store=store,
        reviewer_store=store,
        http_client=http,
    ) as client:
        if case["kind"] == "reviewer":
            client.reviewer.record(REVIEW_EVENT)
            report, raised = None, False
            if 200 <= case["status"] < 300:
                report = client.reviewer.flush()  # a 2xx answer never raises
            else:
                try:
                    report = client.reviewer.flush()
                except UltraRouterError:
                    raised = True  # only a non-2xx answer may raise
            _check_reviewer(case, report, raised, store)
        else:
            receipt = client.outcomes.record(_target(case), EVENT)
            _check_outcome(case, receipt.status, store)
    http.close()


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
async def test_case_async(case: dict[str, Any]) -> None:
    store = MemoryOutcomeStore()
    http = httpx.AsyncClient(transport=httpx.MockTransport(_answer(case)))
    async with AsyncUltraRouter(
        api_key=TEST_KEY,
        base_url="http://gw",
        max_retries=0,
        outcome_store=store,
        reviewer_store=store,
        http_client=http,
    ) as client:
        if case["kind"] == "reviewer":
            client.reviewer.record(REVIEW_EVENT)
            report, raised = None, False
            if 200 <= case["status"] < 300:
                report = await client.reviewer.flush()  # a 2xx answer never raises
            else:
                try:
                    report = await client.reviewer.flush()
                except UltraRouterError:
                    raised = True  # only a non-2xx answer may raise
            _check_reviewer(case, report, raised, store)
        else:
            receipt = await client.outcomes.record(_target(case), EVENT)
            _check_outcome(case, receipt.status, store)
    await http.aclose()
