"""The outcome ledger: ``client.artifact_types``, ``client.artifacts``, ``client.outcomes``,
``client.imports`` and ``client.improvement_reads``.

An *artifact* is the unit of value your application produces (a draft, an answer, a forecast).
*Outcomes* are typed events about it (accepted, corrected, resolved...), recorded instantly or
later. Outcome events carry ids, hashes and values, never prompt or completion text; the source
and learning use of an event are assigned by the server from your API key.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any, Literal, cast, overload

from .._base_client import RequestOptions, parse_model
from .._errors import (
    InvalidRequestError,
    ReceiptWaitTimeoutError,
    UltraRouterError,
)
from .._outcome_report import (
    NotReportedOutcome,
    OutcomeReport,
    ProxyOutcomeReport,
    TeachingOutcomeReport,
    build_report_event,
    report_from_receipt,
)
from .._queue import OutcomeFlushReport, OutcomeReceipt
from .._types import compact
from .._verdicts import OutcomeSource, ProxySource, TeachingSource, Verdict
from ..types import (
    Artifact,
    ArtifactFinal,
    ArtifactList,
    ArtifactObjectiveParams,
    ArtifactType,
    BatchOutcomeParams,
    BatchOutcomesResponse,
    ClaimParams,
    DiffStatsParams,
    Import,
    ImportList,
    ImprovementReads,
    OutcomeParams,
    PendingClaimList,
)
from ..types._learning import OutcomeReceiptRecord, OutcomeReceiptRecordList
from ._base import AsyncAPIResource, SyncAPIResource, build, seg

__all__ = [
    "Archetype",
    "ArtifactTypes",
    "Artifacts",
    "AsyncArtifactTypes",
    "AsyncArtifacts",
    "AsyncImports",
    "AsyncImprovementReads",
    "AsyncOutcomes",
    "Imports",
    "ImprovementReadsResource",
    "Outcomes",
    "normalize_target",
]

Archetype = Literal["forecast", "recommendation", "draft", "extraction", "answer", "action"]


def normalize_target(target: str | Mapping[str, str]) -> dict[str, str]:
    """Normalize an outcome target: a bare string is an artifact id.

    Accepted forms: ``"art_..."``, ``{"artifact": "art_..."}`` or ``{"request": "req_..."}``.
    """
    if isinstance(target, str):
        return {"artifact": target}
    if "artifact" in target:
        return {"artifact": str(target["artifact"])}
    if "request" in target:
        return {"request": str(target["request"])}
    raise InvalidRequestError(
        "outcome target must be an artifact id, {'artifact': id} or {'request': id}", status=0
    )


def _artifact_body(
    key: str,
    archetype: str | None,
    artifact_type: str | None,
    attestation: str | None,
    claims: Sequence[ClaimParams | Mapping[str, Any]] | None,
    grant_id: str | None,
    occurred_at: str | None,
    request_ids: Sequence[str] | None,
    situation_facets: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return compact(
        key=key,
        archetype=archetype,
        artifact_type=artifact_type,
        attestation=attestation,
        claims=list(claims) if claims is not None else None,
        grant_id=grant_id,
        occurred_at=occurred_at,
        request_ids=list(request_ids) if request_ids is not None else None,
        situation_facets=dict(situation_facets) if situation_facets is not None else None,
    )


#: Default total wait of ``outcomes.wait_for_receipt``, in seconds.
DEFAULT_RECEIPT_WAIT_S = 30.0
#: First and largest poll interval of ``outcomes.wait_for_receipt``, in seconds.
RECEIPT_POLL_INITIAL_S = 0.25
RECEIPT_POLL_MAX_S = 4.0


def _receipt_id_of(receipt: str | TeachingOutcomeReport | ProxyOutcomeReport) -> str:
    if isinstance(receipt, str):
        if not receipt:
            raise InvalidRequestError("receipt id must not be empty", status=0)
        return receipt
    receipt_id = receipt.receipt_id
    if receipt_id is None:
        raise InvalidRequestError(
            f"this report has no gateway receipt (delivery status {receipt.status!r}, gateway "
            f"status {receipt.outcome_status!r}); flush the queue or list "
            "outcomes.receipts_for_request(request_id)",
            status=0,
        )
    return receipt_id


def _receipt_list_body(data: Any) -> Any:
    """Accept ``{"data": [...]}``, ``{"receipts": [...]}`` or a bare list (as the TS SDK does)."""
    if isinstance(data, list):
        return {"object": "list", "data": data}
    if isinstance(data, dict) and "data" not in data and isinstance(data.get("receipts"), list):
        return {**{k: v for k, v in data.items() if k != "receipts"}, "data": data["receipts"]}
    return data


def _keep_polling(error: UltraRouterError) -> bool:
    """A read that timed out against the call's own deadline, or a retryable failure the
    transport gave up on, is one missed poll (the TypeScript SDK's rule); anything else
    (``not_found``, ``permission``, a non-retryable server error) ends the wait."""
    if isinstance(error, ReceiptWaitTimeoutError):
        return False
    return error.code == "timeout" or error.retryable


def _report_kwargs_check(verdict: str) -> None:
    if verdict not in ("pass", "fail", "unknown"):
        raise InvalidRequestError(
            f"verdict must be 'pass', 'fail' or 'unknown' (got {verdict!r})", status=0
        )


def _final_body(
    final: str | None,
    draft: str | None,
    diff_stats: DiffStatsParams | Mapping[str, Any] | None,
    final_hash: str | None,
    artifact_version: int | None,
) -> dict[str, Any]:
    return compact(
        final=final,
        draft=draft,
        diff_stats=dict(diff_stats) if diff_stats is not None else None,
        final_hash=final_hash,
        artifact_version=artifact_version,
    )


class ArtifactTypes(SyncAPIResource):
    """``client.artifact_types``: register what "it worked" means for a kind of artifact."""

    def upsert(
        self,
        *,
        name: str,
        archetype: Archetype,
        objective: ArtifactObjectiveParams | Mapping[str, Any],
        options: RequestOptions | None = None,
    ) -> ArtifactType:
        """Register an artifact type or append an objective version (``POST /v1/artifact-types``).

        Args:
            name: The artifact type name (referenced by ``artifacts.create(artifact_type=...)``).
            archetype: One of ``forecast``, ``recommendation``, ``draft``, ``extraction``,
                ``answer``, ``action``.
            objective: The objective: ``metric``, ``unit``, ``direction``,
                ``resolution_criteria``, ``source`` and ``window`` (see
                :class:`~ultrarouter.types.ArtifactObjectiveParams`).
            options: Per-call request options.
        """
        return self._client.request_model(
            build(
                "POST",
                "/v1/artifact-types",
                body={"name": name, "archetype": archetype, "objective": dict(objective)},
                options=options,
            ),
            ArtifactType,
            unwrap="artifact_type",
        )


class Artifacts(SyncAPIResource):
    """``client.artifacts``: create, read and finalize artifacts (metadata only)."""

    def create(
        self,
        *,
        key: str,
        archetype: Archetype | None = None,
        artifact_type: str | None = None,
        attestation: Literal["served", "applied"] | None = None,
        claims: Sequence[ClaimParams | Mapping[str, Any]] | None = None,
        grant_id: str | None = None,
        occurred_at: str | None = None,
        request_ids: Sequence[str] | None = None,
        situation_facets: Mapping[str, Any] | None = None,
        options: RequestOptions | None = None,
    ) -> Artifact:
        """Create an artifact, or return the existing one with the same ``key`` (upsert).

        Args:
            key: Your stable identifier for the artifact (e.g. ``"ticket:4812:reply"``).
            archetype: The artifact archetype.
            artifact_type: A registered artifact type name.
            attestation: ``served`` or ``applied`` (with ``grant_id``, when the learned context
                from a preflight grant was applied).
            claims: Claims the artifact makes, to be resolved later by outcomes.
            grant_id: The exposure grant this artifact was produced under.
            occurred_at: ISO-8601 time the artifact was produced.
            request_ids: Gateway request ids (``req_...``) that produced it.
            situation_facets: Facets describing the situation (for grouping).
            options: Per-call request options.
        """
        body = _artifact_body(
            key,
            archetype,
            artifact_type,
            attestation,
            claims,
            grant_id,
            occurred_at,
            request_ids,
            situation_facets,
        )
        return self._client.request_model(
            build("POST", "/v1/artifacts", body=body, options=options), Artifact, unwrap="artifact"
        )

    def get(self, artifact_id: str, *, options: RequestOptions | None = None) -> Artifact:
        """Get an artifact by id (``GET /v1/artifacts/{id}``)."""
        return self._client.request_model(
            build("GET", f"/v1/artifacts/{seg(artifact_id)}", options=options),
            Artifact,
            unwrap="artifact",
        )

    def list(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        archetype: Archetype | None = None,
        key: str | None = None,
        options: RequestOptions | None = None,
    ) -> ArtifactList:
        """List artifacts, newest first; pass ``next_cursor`` as ``cursor`` for the next page."""
        return self._client.request_model(
            build(
                "GET",
                "/v1/artifacts",
                query={"limit": limit, "cursor": cursor, "archetype": archetype, "key": key},
                options=options,
            ),
            ArtifactList,
        )

    def final(
        self,
        artifact_id: str,
        *,
        final: str | None = None,
        draft: str | None = None,
        diff_stats: DiffStatsParams | Mapping[str, Any] | None = None,
        final_hash: str | None = None,
        artifact_version: int | None = None,
        options: RequestOptions | None = None,
    ) -> ArtifactFinal:
        """Record the human-approved final version (``POST /v1/artifacts/{id}/final``).

        With the workspace's corrections consent, send ``draft`` and ``final`` and the server
        computes the edit statistics. Without consent, never send text: send
        ``diff_stats=ultrarouter.diff_stats(draft, final)`` and ``final_hash`` instead (stored
        as metadata only).
        """
        return self._client.request_model(
            build(
                "POST",
                f"/v1/artifacts/{seg(artifact_id)}/final",
                body=_final_body(final, draft, diff_stats, final_hash, artifact_version),
                options=options,
            ),
            ArtifactFinal,
        )


class Outcomes(SyncAPIResource):
    """``client.outcomes``: record outcome events durably; batch, list pending, flush."""

    def record(
        self,
        target: str | Mapping[str, str],
        outcome: OutcomeParams | Mapping[str, Any],
        *,
        options: RequestOptions | None = None,
    ) -> OutcomeReceipt:
        """Record one outcome event through the durable queue.

        The event is finalized (``observed_at`` and ``source_event_id`` fixed), persisted, then
        sent. Delivery failures never raise. A failure whose outcome is unknown (timeout,
        cancellation, connection failure, 408/429/5xx) leaves the identical event queued
        (``receipt.status == "queued"``) for :meth:`flush`, which replays it with the same
        ``Idempotency-Key``; only a definitive 4xx refusal of the event drops it
        (``"rejected"``). A store that cannot be written raises
        :class:`~ultrarouter.OutcomeStoreError`.

        Args:
            target: An artifact id, ``{"artifact": id}`` or ``{"request": "req_..."}``.
            outcome: The event: ``channel`` and ``kind`` are required; ``value``,
                ``claim_key``, ``confidence``, ``observed_at``, ``source_event_id``... are
                optional (see :class:`~ultrarouter.types.OutcomeParams`).
            options: Per-call request options for the first delivery attempt.
        """
        return self._client._outcome_queue.enqueue(normalize_target(target), outcome, options)

    @overload
    def report(
        self,
        request_id: str,
        verdict: Literal["unknown"],
        *,
        source: OutcomeSource,
        idempotency_key: str | None = None,
        observed_at: str | datetime | None = None,
        evidence_hash: str | None = None,
        supersedes: str | None = None,
        options: RequestOptions | None = None,
    ) -> NotReportedOutcome: ...

    @overload
    def report(
        self,
        request_id: str,
        verdict: Literal["pass", "fail"],
        *,
        source: ProxySource,
        idempotency_key: str | None = None,
        observed_at: str | datetime | None = None,
        evidence_hash: str | None = None,
        supersedes: str | None = None,
        options: RequestOptions | None = None,
    ) -> ProxyOutcomeReport: ...

    @overload
    def report(
        self,
        request_id: str,
        verdict: Literal["pass", "fail"],
        *,
        source: TeachingSource,
        idempotency_key: str | None = None,
        observed_at: str | datetime | None = None,
        evidence_hash: str | None = None,
        supersedes: str | None = None,
        options: RequestOptions | None = None,
    ) -> TeachingOutcomeReport: ...

    @overload
    def report(
        self,
        request_id: str,
        verdict: Verdict,
        *,
        source: OutcomeSource,
        idempotency_key: str | None = None,
        observed_at: str | datetime | None = None,
        evidence_hash: str | None = None,
        supersedes: str | None = None,
        options: RequestOptions | None = None,
    ) -> OutcomeReport: ...

    def report(
        self,
        request_id: str,
        verdict: Verdict,
        *,
        source: OutcomeSource,
        idempotency_key: str | None = None,
        observed_at: str | datetime | None = None,
        evidence_hash: str | None = None,
        supersedes: str | None = None,
        options: RequestOptions | None = None,
    ) -> OutcomeReport:
        """Report whether one request's task succeeded: a verdict from a named source.

        The verdict maps to an outcome event through the verdict table shared with the
        TypeScript SDK: ``verifier`` and ``business_rule`` become ``computable`` /
        ``oracle_pass|oracle_fail``, ``webhook`` becomes ``resolution`` /
        ``resolved_true|resolved_false``, ``human_review`` becomes ``correction`` /
        ``accepted_unchanged|rejected``, and ``self_rating`` becomes a ``proxy`` thumbs event
        that may rank but never teaches. ``verdict="unknown"`` sends nothing and returns
        :class:`~ultrarouter.NotReportedOutcome`: missing feedback stays missing.

        You may report the moment you have the final response: if the gateway has not persisted
        the request yet it answers ``pending`` with a durable receipt and applies the outcome
        when the request lands (``report.is_pending``, ``report.receipt_id``; follow it with
        :meth:`wait_for_receipt`). Never sleep before reporting.

        Reporting never double-counts. The event's ``source_event_id`` is derived from
        ``(request_id, verdict, source, idempotency_key)`` (see
        :func:`~ultrarouter.report_source_event_id`); the event goes through the durable queue
        under that identity, with an ``Idempotency-Key`` derived from it. A retry after a lost
        acknowledgement, a ``flush()`` or a second ``report`` call with the same arguments
        replays the identical event (same ``observed_at``), which the gateway records once
        (``duplicate``); concurrent repeats share one send. A report repeated from another
        process names the same event too; pass ``observed_at`` explicitly when that can happen,
        so the replay is byte-identical rather than a conflicting payload. A failure whose outcome
        is unknown keeps the event queued for :meth:`flush`.

        Args:
            request_id: The gateway request id (``reply.ur.request_id``, ``stream.request_id``,
                :func:`~ultrarouter.request_id_of`, or the id you minted with
                :func:`~ultrarouter.new_request_id`). For a multi-step episode, the last step's.
            verdict: ``"pass"``, ``"fail"`` or ``"unknown"``.
            source: ``"verifier"``, ``"business_rule"``, ``"webhook"``, ``"human_review"`` or
                ``"self_rating"``.
            idempotency_key: Distinguishes two genuinely different reports with the same
                verdict and source on the same request (for example a webhook's event id).
            observed_at: When the outcome was observed (ISO-8601 string or ``datetime``;
                default: the first time this report is made).
            evidence_hash: A content hash of the supporting evidence (never the evidence).
            supersedes: The ``source_event_id`` of an earlier report this one revises.
            options: Per-call request options for the first delivery attempt.

        Returns:
            :class:`~ultrarouter.TeachingOutcomeReport`, :class:`~ultrarouter.ProxyOutcomeReport`
            or :class:`~ultrarouter.NotReportedOutcome`.
        """
        _report_kwargs_check(verdict)
        built = build_report_event(
            request_id,
            verdict,
            source,
            idempotency_key=idempotency_key,
            observed_at=observed_at,
            evidence_hash=evidence_hash,
            supersedes=supersedes,
        )
        if built is None:
            return NotReportedOutcome(request_id=request_id, source=source)
        receipt = self._client._outcome_queue.enqueue_stable(
            built.source_event_id, {"request": request_id}, built.event, options
        )
        return report_from_receipt(
            request_id, cast(Literal["pass", "fail"], verdict), source, built, receipt
        )

    def receipt(
        self, receipt_id: str, *, options: RequestOptions | None = None
    ) -> OutcomeReceiptRecord:
        """One outcome receipt (``GET /v1/outcome-receipts/{id}``): status, reason, episode."""
        return self._client.request_model(
            build("GET", f"/v1/outcome-receipts/{seg(receipt_id)}", options=options),
            OutcomeReceiptRecord,
            unwrap="receipt",
        )

    def receipts_for_request(
        self, request_id: str, *, options: RequestOptions | None = None
    ) -> OutcomeReceiptRecordList:
        """Every outcome receipt for one request (``GET /v1/requests/{id}/outcome-receipts``)."""
        data = self._client.request_json(
            build("GET", f"/v1/requests/{seg(request_id)}/outcome-receipts", options=options)
        )
        return parse_model(OutcomeReceiptRecordList, _receipt_list_body(data))

    def wait_for_receipt(
        self,
        receipt: str | TeachingOutcomeReport | ProxyOutcomeReport,
        *,
        timeout: float = DEFAULT_RECEIPT_WAIT_S,
        poll_interval: float = RECEIPT_POLL_INITIAL_S,
        max_poll_interval: float = RECEIPT_POLL_MAX_S,
        options: RequestOptions | None = None,
    ) -> OutcomeReceiptRecord:
        """Poll a receipt until it is final (``applied``, ``rejected``, ``failed``, ``expired``).

        Reads the public receipt endpoint with a bounded backoff (``poll_interval`` doubling up to
        ``max_poll_interval``) for at most ``timeout`` seconds in total. A poll that fails for a
        transient reason is retried until the deadline; any other refusal is raised. On the
        deadline it raises :class:`~ultrarouter.ReceiptWaitTimeoutError` carrying the last
        receipt read; the outcome is not lost, the receipt keeps reconciling on the gateway.

        Args:
            receipt: A receipt id, or a report returned by :meth:`report`.
            timeout: Total seconds to wait.
            poll_interval: The first wait between reads.
            max_poll_interval: The longest wait between reads.
            options: Per-call request options for each read.
        """
        receipt_id = _receipt_id_of(receipt)
        clock = self._client._clock
        deadline = clock() + max(0.0, timeout)
        interval = max(0.01, poll_interval)
        last: OutcomeReceiptRecord | None = None
        while True:
            remaining = deadline - clock()
            if remaining <= 0:
                break
            try:
                last = self.receipt(
                    receipt_id,
                    options={**(options or {}), "timeout": min(remaining, self._client.timeout)},
                )
            except UltraRouterError as error:
                if not _keep_polling(error):
                    raise
            else:
                if last.is_terminal:
                    return last
            remaining = deadline - clock()
            if remaining <= 0:
                break
            self._client._sleep(min(interval, remaining))
            interval = min(max(interval, max_poll_interval), interval * 2)
        raise ReceiptWaitTimeoutError(
            f"receipt {receipt_id} was still {last.status if last is not None else 'unread'} "
            f"after {timeout}s",
            receipt_id=receipt_id,
            last_receipt=last,
            request_id=last.request_id if last is not None else None,
        )

    def batch(
        self,
        outcomes: Sequence[BatchOutcomeParams | Mapping[str, Any]],
        *,
        options: RequestOptions | None = None,
    ) -> BatchOutcomesResponse:
        """Record up to 1,000 events in one call (``POST /v1/outcomes/batch``).

        Each row names its own target (``artifact_id``, ``artifact_key`` or ``request_id``).
        """
        return self._client.request_model(
            build("POST", "/v1/outcomes/batch", body={"outcomes": list(outcomes)}, options=options),
            BatchOutcomesResponse,
        )

    def pending(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        since: str | None = None,
        archetype: Archetype | None = None,
        state: Literal["pending", "overdue"] | None = None,
        options: RequestOptions | None = None,
    ) -> PendingClaimList:
        """List claims awaiting resolution (``GET /v1/outcomes/pending``), cursor-paginated."""
        return self._client.request_model(
            build(
                "GET",
                "/v1/outcomes/pending",
                query={
                    "limit": limit,
                    "cursor": cursor,
                    "since": since,
                    "archetype": archetype,
                    "state": state,
                },
                options=options,
            ),
            PendingClaimList,
        )

    def flush(self, *, options: RequestOptions | None = None) -> OutcomeFlushReport:
        """Try to deliver every queued event now; returns delivered/rejected/pending counts."""
        return self._client._outcome_queue.flush(options)

    def size(self) -> int:
        """Number of events waiting in the durable queue (no network)."""
        return self._client._outcome_queue.size()


class Imports(SyncAPIResource):
    """``client.imports``: import historical usage or traces (no proxy needed)."""

    def create(
        self,
        *,
        format: str,
        records: Sequence[Any] | None = None,
        jsonl: str | None = None,
        mode: Literal["preview", "commit"] | None = None,
        call_type_id: str | None = None,
        format_version: str | None = None,
        import_id: str | None = None,
        options: RequestOptions | None = None,
    ) -> Import:
        """Start an import (``POST /v1/imports``). ``mode="preview"`` stores nothing.

        Args:
            format: The export format adapter name (e.g. ``"openai_usage"``).
            records: Parsed records (a list), or
            jsonl: the raw JSON Lines text.
            mode: ``preview`` (dry run, returns the capability report) or ``commit``.
            call_type_id: Bind the imported history to a call type.
            format_version: The export format version, when the adapter needs it.
            import_id: Resume a previous import.
            options: Per-call request options.
        """
        body = compact(
            format=format,
            records=list(records) if records is not None else None,
            jsonl=jsonl,
            mode=mode,
            call_type_id=call_type_id,
            format_version=format_version,
            import_id=import_id,
        )
        return self._client.request_model(
            build("POST", "/v1/imports", body=body, options=options), Import, unwrap="import"
        )

    def get(self, import_id: str, *, options: RequestOptions | None = None) -> Import:
        """Get an import and its capability report."""
        return self._client.request_model(
            build("GET", f"/v1/imports/{seg(import_id)}", options=options), Import, unwrap="import"
        )

    def list(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        options: RequestOptions | None = None,
    ) -> ImportList:
        """List imports, newest first (cursor-paginated)."""
        return self._client.request_model(
            build("GET", "/v1/imports", query={"limit": limit, "cursor": cursor}, options=options),
            ImportList,
        )

    def cancel(self, import_id: str, *, options: RequestOptions | None = None) -> Import:
        """Cancel an import that has not finished."""
        return self._client.request_model(
            build("POST", f"/v1/imports/{seg(import_id)}/cancel", options=options),
            Import,
            unwrap="import",
        )


class ImprovementReadsResource(SyncAPIResource):
    """``client.improvement_reads``: per call type, can it spend less and can it get better."""

    def list(self, *, options: RequestOptions | None = None) -> ImprovementReads:
        """Both reads for every call type (``GET /v1/improvement-reads``).

        Each half resolves to one state (``evidence``, ``collecting``, ``needs_confirmation``,
        ``keep_incumbent`` or ``unavailable``) with the next action.
        """
        return self._client.request_model(
            build("GET", "/v1/improvement-reads", options=options), ImprovementReads
        )


# ─────────────────────────────── async ───────────────────────────────


class AsyncArtifactTypes(AsyncAPIResource):
    """``client.artifact_types`` on :class:`~ultrarouter.AsyncUltraRouter`."""

    async def upsert(
        self,
        *,
        name: str,
        archetype: Archetype,
        objective: ArtifactObjectiveParams | Mapping[str, Any],
        options: RequestOptions | None = None,
    ) -> ArtifactType:
        """Register an artifact type; async twin of :meth:`ArtifactTypes.upsert`."""
        return await self._client.request_model(
            build(
                "POST",
                "/v1/artifact-types",
                body={"name": name, "archetype": archetype, "objective": dict(objective)},
                options=options,
            ),
            ArtifactType,
            unwrap="artifact_type",
        )


class AsyncArtifacts(AsyncAPIResource):
    """``client.artifacts`` on :class:`~ultrarouter.AsyncUltraRouter`."""

    async def create(
        self,
        *,
        key: str,
        archetype: Archetype | None = None,
        artifact_type: str | None = None,
        attestation: Literal["served", "applied"] | None = None,
        claims: Sequence[ClaimParams | Mapping[str, Any]] | None = None,
        grant_id: str | None = None,
        occurred_at: str | None = None,
        request_ids: Sequence[str] | None = None,
        situation_facets: Mapping[str, Any] | None = None,
        options: RequestOptions | None = None,
    ) -> Artifact:
        """Create or upsert an artifact; async twin of :meth:`Artifacts.create`."""
        body = _artifact_body(
            key,
            archetype,
            artifact_type,
            attestation,
            claims,
            grant_id,
            occurred_at,
            request_ids,
            situation_facets,
        )
        return await self._client.request_model(
            build("POST", "/v1/artifacts", body=body, options=options), Artifact, unwrap="artifact"
        )

    async def get(self, artifact_id: str, *, options: RequestOptions | None = None) -> Artifact:
        """Get an artifact; async twin of :meth:`Artifacts.get`."""
        return await self._client.request_model(
            build("GET", f"/v1/artifacts/{seg(artifact_id)}", options=options),
            Artifact,
            unwrap="artifact",
        )

    async def list(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        archetype: Archetype | None = None,
        key: str | None = None,
        options: RequestOptions | None = None,
    ) -> ArtifactList:
        """List artifacts; async twin of :meth:`Artifacts.list`."""
        return await self._client.request_model(
            build(
                "GET",
                "/v1/artifacts",
                query={"limit": limit, "cursor": cursor, "archetype": archetype, "key": key},
                options=options,
            ),
            ArtifactList,
        )

    async def final(
        self,
        artifact_id: str,
        *,
        final: str | None = None,
        draft: str | None = None,
        diff_stats: DiffStatsParams | Mapping[str, Any] | None = None,
        final_hash: str | None = None,
        artifact_version: int | None = None,
        options: RequestOptions | None = None,
    ) -> ArtifactFinal:
        """Record the approved final; async twin of :meth:`Artifacts.final`."""
        return await self._client.request_model(
            build(
                "POST",
                f"/v1/artifacts/{seg(artifact_id)}/final",
                body=_final_body(final, draft, diff_stats, final_hash, artifact_version),
                options=options,
            ),
            ArtifactFinal,
        )


class AsyncOutcomes(AsyncAPIResource):
    """``client.outcomes`` on :class:`~ultrarouter.AsyncUltraRouter`."""

    async def record(
        self,
        target: str | Mapping[str, str],
        outcome: OutcomeParams | Mapping[str, Any],
        *,
        options: RequestOptions | None = None,
    ) -> OutcomeReceipt:
        """Record one outcome durably; async twin of :meth:`Outcomes.record`."""
        return await self._client._outcome_queue.enqueue(normalize_target(target), outcome, options)

    @overload
    async def report(
        self,
        request_id: str,
        verdict: Literal["unknown"],
        *,
        source: OutcomeSource,
        idempotency_key: str | None = None,
        observed_at: str | datetime | None = None,
        evidence_hash: str | None = None,
        supersedes: str | None = None,
        options: RequestOptions | None = None,
    ) -> NotReportedOutcome: ...

    @overload
    async def report(
        self,
        request_id: str,
        verdict: Literal["pass", "fail"],
        *,
        source: ProxySource,
        idempotency_key: str | None = None,
        observed_at: str | datetime | None = None,
        evidence_hash: str | None = None,
        supersedes: str | None = None,
        options: RequestOptions | None = None,
    ) -> ProxyOutcomeReport: ...

    @overload
    async def report(
        self,
        request_id: str,
        verdict: Literal["pass", "fail"],
        *,
        source: TeachingSource,
        idempotency_key: str | None = None,
        observed_at: str | datetime | None = None,
        evidence_hash: str | None = None,
        supersedes: str | None = None,
        options: RequestOptions | None = None,
    ) -> TeachingOutcomeReport: ...

    @overload
    async def report(
        self,
        request_id: str,
        verdict: Verdict,
        *,
        source: OutcomeSource,
        idempotency_key: str | None = None,
        observed_at: str | datetime | None = None,
        evidence_hash: str | None = None,
        supersedes: str | None = None,
        options: RequestOptions | None = None,
    ) -> OutcomeReport: ...

    async def report(
        self,
        request_id: str,
        verdict: Verdict,
        *,
        source: OutcomeSource,
        idempotency_key: str | None = None,
        observed_at: str | datetime | None = None,
        evidence_hash: str | None = None,
        supersedes: str | None = None,
        options: RequestOptions | None = None,
    ) -> OutcomeReport:
        """Report a verdict on one request; async twin of :meth:`Outcomes.report`."""
        _report_kwargs_check(verdict)
        built = build_report_event(
            request_id,
            verdict,
            source,
            idempotency_key=idempotency_key,
            observed_at=observed_at,
            evidence_hash=evidence_hash,
            supersedes=supersedes,
        )
        if built is None:
            return NotReportedOutcome(request_id=request_id, source=source)
        receipt = await self._client._outcome_queue.enqueue_stable(
            built.source_event_id, {"request": request_id}, built.event, options
        )
        return report_from_receipt(
            request_id, cast(Literal["pass", "fail"], verdict), source, built, receipt
        )

    async def receipt(
        self, receipt_id: str, *, options: RequestOptions | None = None
    ) -> OutcomeReceiptRecord:
        """One outcome receipt; async twin of :meth:`Outcomes.receipt`."""
        return await self._client.request_model(
            build("GET", f"/v1/outcome-receipts/{seg(receipt_id)}", options=options),
            OutcomeReceiptRecord,
            unwrap="receipt",
        )

    async def receipts_for_request(
        self, request_id: str, *, options: RequestOptions | None = None
    ) -> OutcomeReceiptRecordList:
        """Every receipt for a request; async twin of :meth:`Outcomes.receipts_for_request`."""
        data = await self._client.request_json(
            build("GET", f"/v1/requests/{seg(request_id)}/outcome-receipts", options=options)
        )
        return parse_model(OutcomeReceiptRecordList, _receipt_list_body(data))

    async def wait_for_receipt(
        self,
        receipt: str | TeachingOutcomeReport | ProxyOutcomeReport,
        *,
        timeout: float = DEFAULT_RECEIPT_WAIT_S,
        poll_interval: float = RECEIPT_POLL_INITIAL_S,
        max_poll_interval: float = RECEIPT_POLL_MAX_S,
        options: RequestOptions | None = None,
    ) -> OutcomeReceiptRecord:
        """Poll a receipt until it is final; async twin of :meth:`Outcomes.wait_for_receipt`.

        Cancellable: cancelling the awaiting task (``task.cancel()``, ``asyncio.timeout``,
        ``asyncio.wait_for``) stops the wait at once with ``asyncio.CancelledError``; the
        outcome is unaffected.
        """
        receipt_id = _receipt_id_of(receipt)
        clock = self._client._clock
        deadline = clock() + max(0.0, timeout)
        interval = max(0.01, poll_interval)
        last: OutcomeReceiptRecord | None = None
        while True:
            remaining = deadline - clock()
            if remaining <= 0:
                break
            try:
                last = await self.receipt(
                    receipt_id,
                    options={**(options or {}), "timeout": min(remaining, self._client.timeout)},
                )
            except UltraRouterError as error:
                if not _keep_polling(error):
                    raise
            else:
                if last.is_terminal:
                    return last
            remaining = deadline - clock()
            if remaining <= 0:
                break
            await self._client._sleep(min(interval, remaining))
            interval = min(max(interval, max_poll_interval), interval * 2)
        raise ReceiptWaitTimeoutError(
            f"receipt {receipt_id} was still {last.status if last is not None else 'unread'} "
            f"after {timeout}s",
            receipt_id=receipt_id,
            last_receipt=last,
            request_id=last.request_id if last is not None else None,
        )

    async def batch(
        self,
        outcomes: Sequence[BatchOutcomeParams | Mapping[str, Any]],
        *,
        options: RequestOptions | None = None,
    ) -> BatchOutcomesResponse:
        """Record a batch; async twin of :meth:`Outcomes.batch`."""
        return await self._client.request_model(
            build("POST", "/v1/outcomes/batch", body={"outcomes": list(outcomes)}, options=options),
            BatchOutcomesResponse,
        )

    async def pending(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        since: str | None = None,
        archetype: Archetype | None = None,
        state: Literal["pending", "overdue"] | None = None,
        options: RequestOptions | None = None,
    ) -> PendingClaimList:
        """List pending claims; async twin of :meth:`Outcomes.pending`."""
        return await self._client.request_model(
            build(
                "GET",
                "/v1/outcomes/pending",
                query={
                    "limit": limit,
                    "cursor": cursor,
                    "since": since,
                    "archetype": archetype,
                    "state": state,
                },
                options=options,
            ),
            PendingClaimList,
        )

    async def flush(self, *, options: RequestOptions | None = None) -> OutcomeFlushReport:
        """Deliver queued events; async twin of :meth:`Outcomes.flush`."""
        return await self._client._outcome_queue.flush(options)

    def size(self) -> int:
        """Number of events waiting in the durable queue (no network; not a coroutine)."""
        return self._client._outcome_queue.size()


class AsyncImports(AsyncAPIResource):
    """``client.imports`` on :class:`~ultrarouter.AsyncUltraRouter`."""

    async def create(
        self,
        *,
        format: str,
        records: Sequence[Any] | None = None,
        jsonl: str | None = None,
        mode: Literal["preview", "commit"] | None = None,
        call_type_id: str | None = None,
        format_version: str | None = None,
        import_id: str | None = None,
        options: RequestOptions | None = None,
    ) -> Import:
        """Start an import; async twin of :meth:`Imports.create`."""
        body = compact(
            format=format,
            records=list(records) if records is not None else None,
            jsonl=jsonl,
            mode=mode,
            call_type_id=call_type_id,
            format_version=format_version,
            import_id=import_id,
        )
        return await self._client.request_model(
            build("POST", "/v1/imports", body=body, options=options), Import, unwrap="import"
        )

    async def get(self, import_id: str, *, options: RequestOptions | None = None) -> Import:
        """Get an import; async twin of :meth:`Imports.get`."""
        return await self._client.request_model(
            build("GET", f"/v1/imports/{seg(import_id)}", options=options), Import, unwrap="import"
        )

    async def list(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        options: RequestOptions | None = None,
    ) -> ImportList:
        """List imports; async twin of :meth:`Imports.list`."""
        return await self._client.request_model(
            build("GET", "/v1/imports", query={"limit": limit, "cursor": cursor}, options=options),
            ImportList,
        )

    async def cancel(self, import_id: str, *, options: RequestOptions | None = None) -> Import:
        """Cancel an import; async twin of :meth:`Imports.cancel`."""
        return await self._client.request_model(
            build("POST", f"/v1/imports/{seg(import_id)}/cancel", options=options),
            Import,
            unwrap="import",
        )


class AsyncImprovementReads(AsyncAPIResource):
    """``client.improvement_reads`` on :class:`~ultrarouter.AsyncUltraRouter`."""

    async def list(self, *, options: RequestOptions | None = None) -> ImprovementReads:
        """Both reads per call type; async twin of :meth:`ImprovementReadsResource.list`."""
        return await self._client.request_model(
            build("GET", "/v1/improvement-reads", options=options), ImprovementReads
        )
