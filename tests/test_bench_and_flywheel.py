"""Bench runs (wait polling, report formats, outcome routing) and flywheel signed endpoints."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

import httpx
import pytest

from conftest import TEST_KEY, MockGateway
from ultrarouter import (
    APITimeoutError,
    AsyncUltraRouter,
    InvalidRequestError,
    PermissionDeniedError,
    UltraRouter,
    candidate_decision_callback_id,
)
from ultrarouter._resources.flywheel import APPCI_SIGNATURE_HEADER, ORACLE_SIGNATURE_HEADER
from ultrarouter.types import BenchReport, BenchRun, BenchRunTrigger

ORACLE_SECRET = "orsec_mock_signing_secret"


def test_bench_run_dry_run_returns_the_trigger(mock_gateway: MockGateway) -> None:
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        trigger = client.bench.run(
            suite="s", max_cost_usd=5, dry_run=True, wait=True, require_power=True
        )
    assert isinstance(trigger, BenchRunTrigger) and trigger.bench_run_id is None
    assert len(mock_gateway.requests) == 1, "a dry run never polls"
    assert mock_gateway.requests[0]["body"] == {
        "max_cost_usd": 5,
        "dry_run": True,
        "require_power": True,
    }


def test_bench_run_wait_polls_to_a_terminal_status() -> None:
    statuses = iter(["queued", "running", "complete"])
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, json=_trigger("bench_run_9"))
        return httpx.Response(200, json=_run(next(statuses)))

    with UltraRouter(
        api_key=TEST_KEY,
        base_url="http://gw",
        _sleep=sleeps.append,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    ) as client:
        run = client.bench.run(suite="s", max_cost_usd=5, wait=True, poll_interval=0.25)
    assert isinstance(run, BenchRun) and run.status == "complete"
    assert sleeps == [0.25, 0.25]


def test_bench_wait_times_out() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_run("running"))

    with (
        UltraRouter(
            api_key=TEST_KEY,
            base_url="http://gw",
            _sleep=lambda _: None,
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        ) as client,
        pytest.raises(APITimeoutError, match="running"),
    ):
        client.bench.wait("bench_run_9", poll_interval=1.0, wait_timeout=0.0)


def test_bench_report_formats_and_outcome_routing(mock_gateway: MockGateway) -> None:
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        report = client.bench.report("bench_run_1")
        markdown = client.bench.report("bench_run_1", format="md")
        bundle = client.bench.report("bench_run_1", format="bundle")
        client.bench.record([{"trace": "t", "passed": True}], suite="s")
        client.bench.record([{"trace": "t", "passed": True}], run="bench_run_1")
        with pytest.raises(InvalidRequestError):
            client.bench.record([{"trace": "t", "passed": True}])
        frozen = client.bench.freeze("s")
    assert isinstance(report, BenchReport)
    assert markdown.startswith("# Bench report") and isinstance(bundle, str)
    assert [r["query"].get("format") for r in mock_gateway.requests[:3]] == ["json", "md", "bundle"]
    assert mock_gateway.requests[3]["path"] == "/v1/bench/suites/s/outcomes"
    assert mock_gateway.requests[4]["path"] == "/v1/bench/runs/bench_run_1/outcomes"
    assert mock_gateway.requests[5]["body"] == {}, "freeze without max_items sends an empty object"
    assert frozen.object


async def test_async_bench(mock_gateway: MockGateway) -> None:
    async with AsyncUltraRouter(
        api_key=TEST_KEY, base_url=mock_gateway.url, bench="suite-a"
    ) as client:
        run = await client.bench.run(suite="suite-a", max_cost_usd=1, wait=True)
        gate = await client.bench.gate("bench_run_000001")
        baseline = await client.bench.baseline("bench_run_000001")
        md = await client.bench.report("bench_run_000001", format="md")
        status = await client.bench.status("suite-a")
    assert isinstance(run, BenchRun) and run.status == "complete"
    assert gate.verdict == "pass" and baseline.object and isinstance(md, str) and status.object
    assert all(r["headers"]["x-ur-bench-suite"] == "suite-a" for r in mock_gateway.requests)


# ── flywheel signed endpoints ──


def test_candidate_decision_is_signed_and_deterministic(mock_gateway: MockGateway) -> None:
    kwargs: dict[str, Any] = {
        "decision": "accept",
        "actor_id": "alice",
        "reason": "looked good",
        "evidence_hash": "e" * 64,
        "workspace_id": "ws_1",
    }
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        first = client.flywheel.candidates.decide("cand_1", **kwargs)
        second = client.flywheel.candidates.decide("cand_1", **kwargs)
        with pytest.raises(InvalidRequestError):
            client.flywheel.candidates.decide("cand_1", **{**kwargs, "reason": "  "})
    assert (first.status, second.status) == ("accepted", "duplicate")
    body = mock_gateway.requests[0]["body"]
    assert body["callback_id"] == candidate_decision_callback_id(
        workspace_id="ws_1",
        candidate_ref="cand_1",
        evidence_hash="e" * 64,
        decision="accept",
        actor_id="alice",
    )
    assert body["schema"] == "ur.appci.callback.v1" and body["kind"] == "decision"
    assert mock_gateway.requests[0]["headers"][APPCI_SIGNATURE_HEADER].startswith("sha256=")


def test_callback_id_shape() -> None:
    callback = candidate_decision_callback_id(
        workspace_id="w", candidate_ref="c", evidence_hash="h", decision="reject", actor_id="a"
    )
    assert callback.startswith("urcb1_") and len(callback) == 6 + 32
    assert callback != candidate_decision_callback_id(
        workspace_id="w", candidate_ref="c", evidence_hash="h", decision="accept", actor_id="a"
    )


def test_oracle_pull_transport_is_signed_with_the_oracle_secret(mock_gateway: MockGateway) -> None:
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        registration = client.flywheel.oracles.register(
            kind="customer_ci", transport="pull", spec={"description": "ci"}
        )
        assert registration.secret == ORACLE_SECRET
        jobs = client.flywheel.oracles.claim_jobs("orc_1", secret=ORACLE_SECRET, max=2)
        verdicts = client.flywheel.oracles.submit_verdicts(
            "orc_1",
            secret=ORACLE_SECRET,
            verdicts=[
                {
                    "job_id": "job_1",
                    "oracle_version": "v1",
                    "candidate_sha256": "0" * 64,
                    "verdict": "fail",
                    "reasons": ["wrong_value"],
                }
            ],
        )
        with pytest.raises(PermissionDeniedError):
            client.flywheel.oracles.claim_jobs("orc_1", secret="wrong-secret")
    assert jobs.object and verdicts.object
    claim = mock_gateway.requests[1]
    raw = json.dumps(claim["body"], separators=(",", ":")).encode()
    timestamp = claim["headers"]["x-ur-oracle-timestamp"]
    expected = (
        "sha256="
        + hmac.new(
            ORACLE_SECRET.encode(), timestamp.encode() + b"." + raw, hashlib.sha256
        ).hexdigest()
    )
    assert claim["headers"][ORACLE_SIGNATURE_HEADER] == expected


def test_grant_requires_a_cluster_key(mock_gateway: MockGateway) -> None:
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        with pytest.raises(InvalidRequestError):
            client.flywheel.grant(call_type="c")
        grant = client.flywheel.grant(trace_id="trace-1")
        status = client.flywheel.status()
        learning = client.flywheel.calibration()
    assert grant.object and status.learning == learning
    assert mock_gateway.requests[0]["body"] == {"trace_id": "trace-1"}


async def test_async_flywheel_reads(mock_gateway: MockGateway) -> None:
    async with AsyncUltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        results = [
            await client.flywheel.status(),
            await client.flywheel.calibration(),
            await client.flywheel.confirmations(),
            await client.flywheel.moat_next(lever_family="learned_context"),
            await client.flywheel.plan("support"),
            await client.flywheel.plans(),
            await client.flywheel.prompt_candidates(),
            await client.flywheel.sources(),
            await client.flywheel.candidates.list(),
            await client.improvement_reads.list(),
        ]
    assert all(r is not None for r in results)
    assert mock_gateway.requests[3]["query"] == {"lever_family": "learned_context"}
    assert mock_gateway.requests[4]["query"] == {"workflow": "support"}


def _allowance() -> dict[str, Any]:
    return {"grant_usd": None, "reserved_usd": 0.0, "spent_usd": 0.0, "available_usd": 5.0}


def _trigger(run_id: str | None) -> dict[str, Any]:
    return {
        "object": "bench_run_trigger",
        "bench_run_id": run_id,
        "suite": "s",
        "dry_run": run_id is None,
        "mode": "request",
        "selection_mode": "selection",
        "estimate_usd": 0.1,
        "judge_worst_case_usd": 0.0,
        "allowance": _allowance(),
        "dispositions": [],
        "entitlement": {
            "gate_entitled": True,
            "max_candidates": None,
            "max_items_per_call_type": None,
            "notice": None,
            "plan": "team",
            "run_count_limit": None,
            "run_count_used": None,
        },
    }


def _run(status: str) -> dict[str, Any]:
    return {
        "object": "bench_run",
        "id": "bench_run_9",
        "suite": "s",
        "mode": "request",
        "selection_mode": "selection",
        "status": status,
        "estimate_usd": 0.1,
        "allowance": _allowance(),
        "dispositions": [],
        "runs": [],
    }
