"""``client.reviewer``: send human approve / reject / edit decisions into the outcome ledger.

This is the contract your review tool posts to (no third-party connectors are included).
Every delivery is signed with your API key (``X-UR-Reviewer-Signature`` /
``X-UR-Reviewer-Timestamp``), events are persisted locally before the first send, and a refusal
the server marks repairable is kept as a dead letter for :meth:`Reviewer.repair`. The event
shape has no field for provenance or learning use: the server derives both.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any, Literal

from .._base_client import APIRequest, RequestOptions
from .._queue import QueuedEntry, ReviewerFlushReport
from .._signing import reviewer_signature_headers
from .._types import compact
from ..types import (
    ReviewerEvent,
    ReviewerEventsResponse,
    ReviewerHealth,
    ReviewerRepairResult,
    ReviewerSetup,
    ReviewerTestResult,
)
from ._base import AsyncAPIResource, SyncAPIResource, build

__all__ = ["AsyncReviewer", "Reviewer", "reviewer_events_body"]

Scenario = Literal["happy", "replay", "version_mismatch"]


def reviewer_events_body(
    events: Sequence[ReviewerEvent | Mapping[str, Any]],
    backfill: Mapping[str, Any] | None,
    reviewer_system: str | None,
) -> dict[str, Any]:
    """Build the ``POST /v1/flywheel/reviewer/events`` body."""
    body: dict[str, Any] = {}
    if reviewer_system is not None:
        body["reviewer_system"] = reviewer_system
    if backfill is not None:
        body["backfill"] = dict(backfill)
    body["events"] = [dict(e) for e in events]
    return body


def signed_events_request(
    api_key: str,
    events: Sequence[ReviewerEvent | Mapping[str, Any]],
    backfill: Mapping[str, Any] | None,
    reviewer_system: str | None,
    options: Mapping[str, Any] | None,
) -> APIRequest:
    """Serialize the batch once, sign those bytes, and send the same bytes."""
    raw = json.dumps(
        reviewer_events_body(events, backfill, reviewer_system),
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return build(
        "POST",
        "/v1/flywheel/reviewer/events",
        content=raw,
        headers=reviewer_signature_headers(api_key, raw),
        options=options,
    )


def _repair_body(entry: QueuedEntry, repin_to_current_version: bool | None) -> dict[str, Any]:
    return compact(
        event=entry["event"],
        repin_to_current_version=repin_to_current_version,
        reviewer_system=entry.get("reviewer_system"),
    )


def _repaired(result: ReviewerRepairResult) -> bool:
    return result.result is not None and result.result.status in ("accepted", "duplicate")


class Reviewer(SyncAPIResource):
    """``client.reviewer``: the signed, durable reviewer-decision adapter."""

    def setup(self, *, options: RequestOptions | None = None) -> ReviewerSetup:
        """Guided setup: the decision-to-outcome mapping and the signature recipe."""
        return self._client.request_model(
            build("GET", "/v1/flywheel/reviewer/setup", options=options), ReviewerSetup
        )

    def test(
        self, scenario: Scenario = "happy", *, options: RequestOptions | None = None
    ) -> ReviewerTestResult:
        """Run a guided-setup scenario end to end (test data never enters learning or billing).

        ``happy`` joins a test artifact with an edited final, ``replay`` re-sends the same event
        (a ``duplicate``) and ``version_mismatch`` produces a repairable refusal.
        """
        return self._client.request_model(
            build(
                "POST", "/v1/flywheel/reviewer/test", body={"scenario": scenario}, options=options
            ),
            ReviewerTestResult,
        )

    def record(
        self,
        event: ReviewerEvent | Mapping[str, Any],
        *,
        backfill: Mapping[str, Any] | None = None,
        reviewer_system: str | None = None,
    ) -> str:
        """Persist one decision locally (no network); returns the queue-entry id.

        ``event`` needs ``event_id`` (your stable id), ``artifact_id`` or ``artifact_key``,
        ``artifact_version``, ``decision`` (``approved``, ``approved_with_edits``, ``rejected``,
        ``regenerated``) and ``effective_at``. Call :meth:`flush` to send.
        """
        return self._client._reviewer_queue.enqueue(
            event, backfill=backfill, reviewer_system=reviewer_system
        )

    def send(
        self,
        events: Sequence[ReviewerEvent | Mapping[str, Any]],
        *,
        backfill: Mapping[str, Any] | None = None,
        reviewer_system: str | None = None,
        options: RequestOptions | None = None,
    ) -> ReviewerEventsResponse:
        """Post a signed batch now, bypassing the local queue (at most 500 events)."""
        return self._client.request_model(
            signed_events_request(self._client.api_key, events, backfill, reviewer_system, options),
            ReviewerEventsResponse,
        )

    def flush(self, *, options: RequestOptions | None = None) -> ReviewerFlushReport:
        """Send every queued decision in signed batches; returns per-status counts."""
        return self._client._reviewer_queue.flush(options)

    def dead_letters(self) -> list[QueuedEntry]:
        """Queued decisions the server refused with a repairable reason."""
        return self._client._reviewer_queue.dead_letters()

    def repair(
        self,
        entry: QueuedEntry,
        *,
        repin_to_current_version: bool | None = None,
        options: RequestOptions | None = None,
    ) -> ReviewerRepairResult:
        """Re-send one dead letter (``POST /v1/flywheel/reviewer/repair``).

        On success the local dead letter is removed; otherwise it stays.
        """
        result = self._client.request_model(
            build(
                "POST",
                "/v1/flywheel/reviewer/repair",
                body=_repair_body(entry, repin_to_current_version),
                options=options,
            ),
            ReviewerRepairResult,
        )
        if _repaired(result):
            self._client._reviewer_queue.clear_dead_letter(entry["id"])
        return result

    def health(self, *, options: RequestOptions | None = None) -> ReviewerHealth:
        """Integration health: event counts, dead letters, backfills and the next repair action."""
        return self._client.request_model(
            build("GET", "/v1/flywheel/reviewer/health", options=options), ReviewerHealth
        )


class AsyncReviewer(AsyncAPIResource):
    """``client.reviewer`` on :class:`~ultrarouter.AsyncUltraRouter`."""

    async def setup(self, *, options: RequestOptions | None = None) -> ReviewerSetup:
        """Guided setup; async twin of :meth:`Reviewer.setup`."""
        return await self._client.request_model(
            build("GET", "/v1/flywheel/reviewer/setup", options=options), ReviewerSetup
        )

    async def test(
        self, scenario: Scenario = "happy", *, options: RequestOptions | None = None
    ) -> ReviewerTestResult:
        """Run a scenario; async twin of :meth:`Reviewer.test`."""
        return await self._client.request_model(
            build(
                "POST", "/v1/flywheel/reviewer/test", body={"scenario": scenario}, options=options
            ),
            ReviewerTestResult,
        )

    def record(
        self,
        event: ReviewerEvent | Mapping[str, Any],
        *,
        backfill: Mapping[str, Any] | None = None,
        reviewer_system: str | None = None,
    ) -> str:
        """Persist one decision locally (synchronous; no network); see :meth:`Reviewer.record`."""
        return self._client._reviewer_queue.enqueue(
            event, backfill=backfill, reviewer_system=reviewer_system
        )

    async def send(
        self,
        events: Sequence[ReviewerEvent | Mapping[str, Any]],
        *,
        backfill: Mapping[str, Any] | None = None,
        reviewer_system: str | None = None,
        options: RequestOptions | None = None,
    ) -> ReviewerEventsResponse:
        """Post a signed batch now; async twin of :meth:`Reviewer.send`."""
        return await self._client.request_model(
            signed_events_request(self._client.api_key, events, backfill, reviewer_system, options),
            ReviewerEventsResponse,
        )

    async def flush(self, *, options: RequestOptions | None = None) -> ReviewerFlushReport:
        """Send queued decisions; async twin of :meth:`Reviewer.flush`."""
        return await self._client._reviewer_queue.flush(options)

    def dead_letters(self) -> list[QueuedEntry]:
        """Queued decisions refused with a repairable reason (synchronous)."""
        return self._client._reviewer_queue.dead_letters()

    async def repair(
        self,
        entry: QueuedEntry,
        *,
        repin_to_current_version: bool | None = None,
        options: RequestOptions | None = None,
    ) -> ReviewerRepairResult:
        """Re-send a dead letter; async twin of :meth:`Reviewer.repair`."""
        result = await self._client.request_model(
            build(
                "POST",
                "/v1/flywheel/reviewer/repair",
                body=_repair_body(entry, repin_to_current_version),
                options=options,
            ),
            ReviewerRepairResult,
        )
        if _repaired(result):
            self._client._reviewer_queue.clear_dead_letter(entry["id"])
        return result

    async def health(self, *, options: RequestOptions | None = None) -> ReviewerHealth:
        """Integration health; async twin of :meth:`Reviewer.health`."""
        return await self._client.request_model(
            build("GET", "/v1/flywheel/reviewer/health", options=options), ReviewerHealth
        )
