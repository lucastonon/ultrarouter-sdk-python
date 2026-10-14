"""``client.bench``: Bench suites, paired runs, reports and the baseline compare gate."""

from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
from typing import Any, Literal, overload

from .._base_client import RequestOptions
from .._errors import APITimeoutError, InvalidRequestError
from .._types import compact
from ..types import (
    BenchBaseline,
    BenchCompareGate,
    BenchDatasetFreeze,
    BenchExpectationParams,
    BenchExpectations,
    BenchOutcomeParams,
    BenchOutcomes,
    BenchReport,
    BenchRun,
    BenchRunTrigger,
    BenchSuiteStatus,
)
from ._base import AsyncAPIResource, SyncAPIResource, build, seg

__all__ = ["DEFAULT_POLL_INTERVAL_S", "DEFAULT_WAIT_TIMEOUT_S", "AsyncBench", "Bench"]

#: Default seconds between polls when ``run(wait=True)``.
DEFAULT_POLL_INTERVAL_S = 1.0
#: Default seconds ``run(wait=True)`` waits for a terminal status.
DEFAULT_WAIT_TIMEOUT_S = 120.0
_TERMINAL = frozenset({"complete", "failed"})

ReportFormat = Literal["json", "md", "bundle"]


def _run_body(
    *,
    max_cost_usd: float,
    mode: str | None,
    selection_mode: str | None,
    require_power: bool | None,
    dry_run: bool | None,
    force: bool | None,
    call_types: Sequence[str] | None,
    candidates: Sequence[str] | None,
    compare: bool | None,
    baseline_run_id: str | None,
    cost_ceiling_usd: float | None,
    max_output_tokens: int | None,
) -> dict[str, Any]:
    return compact(
        max_cost_usd=max_cost_usd,
        mode=mode,
        selection_mode=selection_mode,
        require_power=require_power,
        dry_run=dry_run,
        force=force,
        call_types=list(call_types) if call_types is not None else None,
        candidates=list(candidates) if candidates is not None else None,
        compare=compare,
        baseline_run_id=baseline_run_id,
        cost_ceiling_usd=cost_ceiling_usd,
        max_output_tokens=max_output_tokens,
    )


def _outcomes_path(suite: str | None, run: str | None) -> str:
    if run is not None:
        return f"/v1/bench/runs/{seg(run)}/outcomes"
    if suite is not None:
        return f"/v1/bench/suites/{seg(suite)}/outcomes"
    raise InvalidRequestError("bench.record requires suite= or run=", status=0)


def _timeout_error(run_id: str, wait_timeout: float, status: str) -> APITimeoutError:
    return APITimeoutError(
        f"bench run {run_id} did not reach a terminal status within {wait_timeout}s "
        f"(last status {status!r})"
    )


class Bench(SyncAPIResource):
    """``client.bench``: capture traffic into a suite, freeze it, run paired comparisons.

    Tag traffic with ``UltraRouter(bench="suite")`` or a per-call ``bench=``, then ``freeze`` the
    suite, ``run`` candidates against your current model, and read the ``report``.
    """

    def status(self, suite: str, *, options: RequestOptions | None = None) -> BenchSuiteStatus:
        """Suite readiness: captured items per call type and capture health."""
        return self._client.request_model(
            build("GET", f"/v1/bench/suites/{seg(suite)}/status", options=options),
            BenchSuiteStatus,
        )

    def freeze(
        self, suite: str, *, max_items: int | None = None, options: RequestOptions | None = None
    ) -> BenchDatasetFreeze:
        """Freeze the suite's captures into immutable, weighted datasets.

        Args:
            suite: The suite slug.
            max_items: Optional cap on frozen items per call type (1..5000).
            options: Per-call request options.
        """
        return self._client.request_model(
            build(
                "POST",
                f"/v1/bench/suites/{seg(suite)}/freeze",
                body=compact(max_items=max_items),
                options=options,
            ),
            BenchDatasetFreeze,
        )

    @overload
    def run(
        self,
        *,
        suite: str,
        max_cost_usd: float,
        wait: Literal[False] = False,
        mode: Literal["request", "task"] | None = None,
        selection_mode: Literal["selection", "noninferiority"] | None = None,
        require_power: bool | None = None,
        dry_run: bool | None = None,
        force: bool | None = None,
        call_types: Sequence[str] | None = None,
        candidates: Sequence[str] | None = None,
        compare: bool | None = None,
        baseline_run_id: str | None = None,
        cost_ceiling_usd: float | None = None,
        max_output_tokens: int | None = None,
        poll_interval: float = DEFAULT_POLL_INTERVAL_S,
        wait_timeout: float = DEFAULT_WAIT_TIMEOUT_S,
        options: RequestOptions | None = None,
    ) -> BenchRunTrigger: ...

    @overload
    def run(
        self,
        *,
        suite: str,
        max_cost_usd: float,
        wait: Literal[True],
        mode: Literal["request", "task"] | None = None,
        selection_mode: Literal["selection", "noninferiority"] | None = None,
        require_power: bool | None = None,
        dry_run: bool | None = None,
        force: bool | None = None,
        call_types: Sequence[str] | None = None,
        candidates: Sequence[str] | None = None,
        compare: bool | None = None,
        baseline_run_id: str | None = None,
        cost_ceiling_usd: float | None = None,
        max_output_tokens: int | None = None,
        poll_interval: float = DEFAULT_POLL_INTERVAL_S,
        wait_timeout: float = DEFAULT_WAIT_TIMEOUT_S,
        options: RequestOptions | None = None,
    ) -> BenchRunTrigger | BenchRun: ...

    def run(
        self,
        *,
        suite: str,
        max_cost_usd: float,
        wait: bool = False,
        mode: Literal["request", "task"] | None = None,
        selection_mode: Literal["selection", "noninferiority"] | None = None,
        require_power: bool | None = None,
        dry_run: bool | None = None,
        force: bool | None = None,
        call_types: Sequence[str] | None = None,
        candidates: Sequence[str] | None = None,
        compare: bool | None = None,
        baseline_run_id: str | None = None,
        cost_ceiling_usd: float | None = None,
        max_output_tokens: int | None = None,
        poll_interval: float = DEFAULT_POLL_INTERVAL_S,
        wait_timeout: float = DEFAULT_WAIT_TIMEOUT_S,
        options: RequestOptions | None = None,
    ) -> BenchRunTrigger | BenchRun:
        """Trigger a Bench run (``POST /v1/bench/suites/{slug}/runs``).

        Args:
            suite: The suite slug.
            max_cost_usd: Hard budget for the run, in USD.
            wait: Poll until the run is ``complete`` or ``failed`` and return the
                :class:`~ultrarouter.types.BenchRun` (a dry run, or a trigger without a run id,
                returns the trigger immediately).
            mode: ``request`` (per request) or ``task`` (per multi-call task).
            selection_mode: ``selection`` or ``noninferiority``.
            require_power: Refuse to run when the dataset is underpowered for the margin.
            dry_run: Estimate cost and dispositions without spending anything.
            force: Re-run even if an identical run exists.
            call_types: Restrict the run to these call types.
            candidates: Candidate model ids to compare against the current model.
            compare: Run as a baseline comparison (with ``baseline_run_id``).
            baseline_run_id: The pinned baseline run to compare with.
            cost_ceiling_usd: Per-item cost ceiling the compare gate enforces.
            max_output_tokens: Cap on output tokens per replayed item.
            poll_interval: Seconds between polls when ``wait=True``.
            wait_timeout: Seconds to wait before raising :class:`~ultrarouter.APITimeoutError`.
            options: Per-call request options.
        """
        body = _run_body(
            max_cost_usd=max_cost_usd,
            mode=mode,
            selection_mode=selection_mode,
            require_power=require_power,
            dry_run=dry_run,
            force=force,
            call_types=call_types,
            candidates=candidates,
            compare=compare,
            baseline_run_id=baseline_run_id,
            cost_ceiling_usd=cost_ceiling_usd,
            max_output_tokens=max_output_tokens,
        )
        trigger = self._client.request_model(
            build("POST", f"/v1/bench/suites/{seg(suite)}/runs", body=body, options=options),
            BenchRunTrigger,
        )
        if not wait or trigger.bench_run_id is None:
            return trigger
        return self.wait(
            trigger.bench_run_id, poll_interval=poll_interval, wait_timeout=wait_timeout
        )

    def wait(
        self,
        run_id: str,
        *,
        poll_interval: float = DEFAULT_POLL_INTERVAL_S,
        wait_timeout: float = DEFAULT_WAIT_TIMEOUT_S,
        options: RequestOptions | None = None,
    ) -> BenchRun:
        """Poll a run until it is ``complete`` or ``failed`` and return it."""
        deadline = time.monotonic() + wait_timeout
        while True:
            run = self.get(run_id, options=options)
            if run.status in _TERMINAL:
                return run
            if time.monotonic() + poll_interval > deadline:
                raise _timeout_error(run_id, wait_timeout, run.status)
            self._client._sleep(poll_interval)

    def get(self, run_id: str, *, options: RequestOptions | None = None) -> BenchRun:
        """Get a run (``GET /v1/bench/runs/{id}``)."""
        return self._client.request_model(
            build("GET", f"/v1/bench/runs/{seg(run_id)}", options=options), BenchRun
        )

    @overload
    def report(
        self,
        run_id: str,
        *,
        format: Literal["json"] = "json",
        options: RequestOptions | None = None,
    ) -> BenchReport: ...

    @overload
    def report(
        self, run_id: str, *, format: Literal["md", "bundle"], options: RequestOptions | None = None
    ) -> str: ...

    def report(
        self, run_id: str, *, format: ReportFormat = "json", options: RequestOptions | None = None
    ) -> BenchReport | str:
        """Get the immutable report of a completed run.

        ``format="json"`` (default) returns a :class:`~ultrarouter.types.BenchReport`;
        ``"md"`` returns a Markdown export and ``"bundle"`` an offline-verifiable evidence
        bundle, both as text.
        """
        req = build(
            "GET", f"/v1/bench/runs/{seg(run_id)}/report", query={"format": format}, options=options
        )
        if format == "json":
            return self._client.request_model(req, BenchReport)
        return self._client.request_text(req)

    def expect(
        self,
        suite: str,
        expectations: Sequence[BenchExpectationParams | Mapping[str, Any]],
        *,
        options: RequestOptions | None = None,
    ) -> BenchExpectations:
        """Attach your own assertions (e.g. JSON-schema checks) to a suite."""
        return self._client.request_model(
            build(
                "POST",
                f"/v1/bench/suites/{seg(suite)}/expectations",
                body={"expectations": list(expectations)},
                options=options,
            ),
            BenchExpectations,
        )

    def record(
        self,
        outcomes: Sequence[BenchOutcomeParams | Mapping[str, Any]],
        *,
        suite: str | None = None,
        run: str | None = None,
        options: RequestOptions | None = None,
    ) -> BenchOutcomes:
        """Record per-trace pass/fail outcomes on a suite (``suite=``) or a run (``run=``)."""
        return self._client.request_model(
            build(
                "POST",
                _outcomes_path(suite, run),
                body={"outcomes": list(outcomes)},
                options=options,
            ),
            BenchOutcomes,
        )

    def baseline(self, run_id: str, *, options: RequestOptions | None = None) -> BenchBaseline:
        """Pin a completed run as the suite baseline (``POST /v1/bench/runs/{id}/baseline``)."""
        return self._client.request_model(
            build("POST", f"/v1/bench/runs/{seg(run_id)}/baseline", options=options), BenchBaseline
        )

    def gate(self, run_id: str, *, options: RequestOptions | None = None) -> BenchCompareGate:
        """Read a compare run's gate: ``verdict`` is ``pass``, ``fail`` or ``inconclusive``."""
        return self._client.request_model(
            build("GET", f"/v1/bench/runs/{seg(run_id)}/gate", options=options), BenchCompareGate
        )


class AsyncBench(AsyncAPIResource):
    """``client.bench`` on :class:`~ultrarouter.AsyncUltraRouter`."""

    async def status(
        self, suite: str, *, options: RequestOptions | None = None
    ) -> BenchSuiteStatus:
        """Suite readiness; async twin of :meth:`Bench.status`."""
        return await self._client.request_model(
            build("GET", f"/v1/bench/suites/{seg(suite)}/status", options=options),
            BenchSuiteStatus,
        )

    async def freeze(
        self, suite: str, *, max_items: int | None = None, options: RequestOptions | None = None
    ) -> BenchDatasetFreeze:
        """Freeze a suite; async twin of :meth:`Bench.freeze`."""
        return await self._client.request_model(
            build(
                "POST",
                f"/v1/bench/suites/{seg(suite)}/freeze",
                body=compact(max_items=max_items),
                options=options,
            ),
            BenchDatasetFreeze,
        )

    @overload
    async def run(
        self,
        *,
        suite: str,
        max_cost_usd: float,
        wait: Literal[False] = False,
        mode: Literal["request", "task"] | None = None,
        selection_mode: Literal["selection", "noninferiority"] | None = None,
        require_power: bool | None = None,
        dry_run: bool | None = None,
        force: bool | None = None,
        call_types: Sequence[str] | None = None,
        candidates: Sequence[str] | None = None,
        compare: bool | None = None,
        baseline_run_id: str | None = None,
        cost_ceiling_usd: float | None = None,
        max_output_tokens: int | None = None,
        poll_interval: float = DEFAULT_POLL_INTERVAL_S,
        wait_timeout: float = DEFAULT_WAIT_TIMEOUT_S,
        options: RequestOptions | None = None,
    ) -> BenchRunTrigger: ...

    @overload
    async def run(
        self,
        *,
        suite: str,
        max_cost_usd: float,
        wait: Literal[True],
        mode: Literal["request", "task"] | None = None,
        selection_mode: Literal["selection", "noninferiority"] | None = None,
        require_power: bool | None = None,
        dry_run: bool | None = None,
        force: bool | None = None,
        call_types: Sequence[str] | None = None,
        candidates: Sequence[str] | None = None,
        compare: bool | None = None,
        baseline_run_id: str | None = None,
        cost_ceiling_usd: float | None = None,
        max_output_tokens: int | None = None,
        poll_interval: float = DEFAULT_POLL_INTERVAL_S,
        wait_timeout: float = DEFAULT_WAIT_TIMEOUT_S,
        options: RequestOptions | None = None,
    ) -> BenchRunTrigger | BenchRun: ...

    async def run(
        self,
        *,
        suite: str,
        max_cost_usd: float,
        wait: bool = False,
        mode: Literal["request", "task"] | None = None,
        selection_mode: Literal["selection", "noninferiority"] | None = None,
        require_power: bool | None = None,
        dry_run: bool | None = None,
        force: bool | None = None,
        call_types: Sequence[str] | None = None,
        candidates: Sequence[str] | None = None,
        compare: bool | None = None,
        baseline_run_id: str | None = None,
        cost_ceiling_usd: float | None = None,
        max_output_tokens: int | None = None,
        poll_interval: float = DEFAULT_POLL_INTERVAL_S,
        wait_timeout: float = DEFAULT_WAIT_TIMEOUT_S,
        options: RequestOptions | None = None,
    ) -> BenchRunTrigger | BenchRun:
        """Trigger a Bench run; async twin of :meth:`Bench.run`."""
        body = _run_body(
            max_cost_usd=max_cost_usd,
            mode=mode,
            selection_mode=selection_mode,
            require_power=require_power,
            dry_run=dry_run,
            force=force,
            call_types=call_types,
            candidates=candidates,
            compare=compare,
            baseline_run_id=baseline_run_id,
            cost_ceiling_usd=cost_ceiling_usd,
            max_output_tokens=max_output_tokens,
        )
        trigger = await self._client.request_model(
            build("POST", f"/v1/bench/suites/{seg(suite)}/runs", body=body, options=options),
            BenchRunTrigger,
        )
        if not wait or trigger.bench_run_id is None:
            return trigger
        return await self.wait(
            trigger.bench_run_id, poll_interval=poll_interval, wait_timeout=wait_timeout
        )

    async def wait(
        self,
        run_id: str,
        *,
        poll_interval: float = DEFAULT_POLL_INTERVAL_S,
        wait_timeout: float = DEFAULT_WAIT_TIMEOUT_S,
        options: RequestOptions | None = None,
    ) -> BenchRun:
        """Poll a run to a terminal status; async twin of :meth:`Bench.wait`."""
        deadline = time.monotonic() + wait_timeout
        while True:
            run = await self.get(run_id, options=options)
            if run.status in _TERMINAL:
                return run
            if time.monotonic() + poll_interval > deadline:
                raise _timeout_error(run_id, wait_timeout, run.status)
            await self._client._sleep(poll_interval)

    async def get(self, run_id: str, *, options: RequestOptions | None = None) -> BenchRun:
        """Get a run; async twin of :meth:`Bench.get`."""
        return await self._client.request_model(
            build("GET", f"/v1/bench/runs/{seg(run_id)}", options=options), BenchRun
        )

    @overload
    async def report(
        self,
        run_id: str,
        *,
        format: Literal["json"] = "json",
        options: RequestOptions | None = None,
    ) -> BenchReport: ...

    @overload
    async def report(
        self, run_id: str, *, format: Literal["md", "bundle"], options: RequestOptions | None = None
    ) -> str: ...

    async def report(
        self, run_id: str, *, format: ReportFormat = "json", options: RequestOptions | None = None
    ) -> BenchReport | str:
        """Get a run report; async twin of :meth:`Bench.report`."""
        req = build(
            "GET", f"/v1/bench/runs/{seg(run_id)}/report", query={"format": format}, options=options
        )
        if format == "json":
            return await self._client.request_model(req, BenchReport)
        return await self._client.request_text(req)

    async def expect(
        self,
        suite: str,
        expectations: Sequence[BenchExpectationParams | Mapping[str, Any]],
        *,
        options: RequestOptions | None = None,
    ) -> BenchExpectations:
        """Attach assertions; async twin of :meth:`Bench.expect`."""
        return await self._client.request_model(
            build(
                "POST",
                f"/v1/bench/suites/{seg(suite)}/expectations",
                body={"expectations": list(expectations)},
                options=options,
            ),
            BenchExpectations,
        )

    async def record(
        self,
        outcomes: Sequence[BenchOutcomeParams | Mapping[str, Any]],
        *,
        suite: str | None = None,
        run: str | None = None,
        options: RequestOptions | None = None,
    ) -> BenchOutcomes:
        """Record per-trace outcomes; async twin of :meth:`Bench.record`."""
        return await self._client.request_model(
            build(
                "POST",
                _outcomes_path(suite, run),
                body={"outcomes": list(outcomes)},
                options=options,
            ),
            BenchOutcomes,
        )

    async def baseline(
        self, run_id: str, *, options: RequestOptions | None = None
    ) -> BenchBaseline:
        """Pin a baseline; async twin of :meth:`Bench.baseline`."""
        return await self._client.request_model(
            build("POST", f"/v1/bench/runs/{seg(run_id)}/baseline", options=options), BenchBaseline
        )

    async def gate(self, run_id: str, *, options: RequestOptions | None = None) -> BenchCompareGate:
        """Read a compare gate; async twin of :meth:`Bench.gate`."""
        return await self._client.request_model(
            build("GET", f"/v1/bench/runs/{seg(run_id)}/gate", options=options), BenchCompareGate
        )
