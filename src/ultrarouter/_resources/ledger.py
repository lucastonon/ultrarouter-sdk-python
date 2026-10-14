"""The outcome ledger: ``client.artifact_types``, ``client.artifacts``, ``client.outcomes``,
``client.imports`` and ``client.improvement_reads``.

An *artifact* is the unit of value your application produces (a draft, an answer, a forecast).
*Outcomes* are typed events about it (accepted, corrected, resolved...), recorded instantly or
later. Outcome events carry ids, hashes and values, never prompt or completion text; the source
and learning use of an event are assigned by the server from your API key.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal

from .._base_client import RequestOptions
from .._errors import InvalidRequestError
from .._queue import OutcomeFlushReport, OutcomeReceipt
from .._types import compact
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
