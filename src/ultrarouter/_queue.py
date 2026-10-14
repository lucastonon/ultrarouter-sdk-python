"""Durable local queues for outcome events and reviewer decisions.

**Outcomes.** :meth:`~ultrarouter.UltraRouter.outcomes` ``record`` first *finalizes* an event
(fixes ``observed_at`` and a client-generated ``source_event_id``), *persists* it to a store, and
only then sends it. A failed send leaves the identical event queued; :meth:`OutcomeQueue.flush`
replays it byte-for-byte later with the same ``Idempotency-Key``. Because the event never changes
between attempts, a retry the server already saw is recorded as a ``duplicate``, never as a
conflicting second event.

Only a *validated, event-specific* refusal drops an event (:func:`is_definitive_rejection`): a 4xx
other than 401, 403, 408 and 429 whose body is a complete gateway error envelope (string ``code``,
``message`` and ``request_id``, ``retryable: false``) with ``invalid_request``, ``not_found`` or
``conflict`` at that code's own status. Everything else keeps the event queued, including a 2xx
answer that is not an outcome result. The reviewer queue removes an event only on a validated
per-event verdict (:func:`reviewer_verdict_action`). These are the TypeScript SDK's rules, checked
against a shared fixture of cases.

**Reviewer decisions.** The reviewer queue works the same way and additionally keeps a refusal the
server marks *repairable* as a local dead letter, so a human decision is never silently dropped;
:meth:`~ultrarouter.UltraRouter.reviewer` ``repair`` re-sends it.

Stores are pluggable: :class:`MemoryOutcomeStore` (default, lives as long as the client) or
:class:`FileOutcomeStore` (a JSON file, survives restarts). Events carry ids, hashes and values,
never prompt or completion text.
"""

from __future__ import annotations

import copy
import json
import os
import secrets
import tempfile
import threading
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Protocol, runtime_checkable

from ._errors import (
    GATEWAY_ERROR_TAXONOMY,
    APIConnectionError,
    OutcomeStoreError,
    UltraRouterError,
)

__all__ = [
    "AsyncOutcomeQueue",
    "AsyncReviewerQueue",
    "FileOutcomeStore",
    "MemoryOutcomeStore",
    "OutcomeFlushReport",
    "OutcomeQueue",
    "OutcomeReceipt",
    "OutcomeStore",
    "ReviewerFlushReport",
    "ReviewerQueue",
    "is_definitive_rejection",
    "is_outcome_result",
    "iso_from_ms",
    "new_ulid",
    "reviewer_verdict_action",
]

QueuedEntry = dict[str, Any]

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def new_ulid(now_ms: float | None = None) -> str:
    """A lexicographically sortable ULID (48-bit time + 80 random bits, Crockford base32)."""
    ts = int(now_ms if now_ms is not None else time.time() * 1000)
    time_part = ""
    for _ in range(10):
        time_part = _CROCKFORD[ts % 32] + time_part
        ts //= 32
    rand_part = "".join(_CROCKFORD[b % 32] for b in secrets.token_bytes(16))
    return time_part + rand_part


def iso_from_ms(ms: float) -> str:
    """Format epoch milliseconds as ``YYYY-MM-DDTHH:MM:SS.mmmZ`` (JavaScript ``toISOString``)."""
    whole = int(ms)
    seconds, millis = divmod(whole, 1000)
    moment = datetime.fromtimestamp(seconds, tz=timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%S") + f".{millis:03d}Z"


@runtime_checkable
class OutcomeStore(Protocol):
    """The durability port both queues persist through.

    An implementation must persist the whole entry before returning from :meth:`append`, so a
    crash after ``append`` and before delivery loses nothing. Entries are JSON-serializable dicts
    with a unique ``"id"``.
    """

    def append(self, entry: QueuedEntry) -> None:
        """Persist a new entry."""

    def update(self, entry: QueuedEntry) -> None:
        """Replace the stored entry with the same ``id``."""

    def remove(self, entry_id: str) -> None:
        """Delete the entry with ``entry_id`` (no error if it is absent)."""

    def list(self) -> list[QueuedEntry]:
        """Return every stored entry, oldest first."""


class MemoryOutcomeStore:
    """The default in-process store: durable for the lifetime of the client, FIFO order."""

    def __init__(self) -> None:
        self._entries: dict[str, QueuedEntry] = {}
        self._lock = threading.Lock()

    def append(self, entry: QueuedEntry) -> None:
        """Persist a new entry."""
        with self._lock:
            self._entries[entry["id"]] = entry

    def update(self, entry: QueuedEntry) -> None:
        """Replace the stored entry with the same ``id``."""
        with self._lock:
            if entry["id"] in self._entries:
                self._entries[entry["id"]] = entry

    def remove(self, entry_id: str) -> None:
        """Delete the entry with ``entry_id``."""
        with self._lock:
            self._entries.pop(entry_id, None)

    def list(self) -> list[QueuedEntry]:
        """Return every stored entry, oldest first."""
        with self._lock:
            return list(self._entries.values())


class FileOutcomeStore:
    """A JSON-file store that survives process restarts.

    The whole queue is rewritten atomically (temporary file + rename, mode ``0600``) on every
    change and read back on first use. Point two clients at two different files.

    The store starts empty only when the file does not exist. A file that cannot be read, is
    not valid JSON, or does not hold a list of entries raises
    :class:`~ultrarouter.OutcomeStoreError` on every operation and is never overwritten, so its
    events can be recovered by hand.
    """

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self.path = Path(path)
        self._loaded = False
        self._cache: list[QueuedEntry] = []
        self._lock = threading.Lock()

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        try:
            raw = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            self._cache = []
            self._loaded = True
            return
        except (OSError, UnicodeDecodeError) as exc:
            raise OutcomeStoreError(
                f"cannot read the queue file {self.path}: {exc}; it was left untouched"
            ) from exc
        try:
            parsed = json.loads(raw)
        except ValueError as exc:
            raise OutcomeStoreError(
                f"the queue file {self.path} is not valid JSON ({exc}); it was left untouched "
                "so its events can be recovered"
            ) from exc
        if not isinstance(parsed, list) or not all(
            isinstance(entry, dict) and isinstance(entry.get("id"), str) for entry in parsed
        ):
            raise OutcomeStoreError(
                f"the queue file {self.path} does not hold a list of queue entries; it was "
                "left untouched so its events can be recovered"
            )
        self._cache = parsed
        self._loaded = True

    def _persist(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(
                prefix=self.path.name + ".", suffix=".tmp", dir=self.path.parent
            )
        except OSError as exc:
            raise OutcomeStoreError(f"cannot write the queue file {self.path}: {exc}") from exc
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(self._cache, handle)
            os.chmod(tmp, 0o600)
            os.replace(tmp, self.path)
        except BaseException as exc:
            Path(tmp).unlink(missing_ok=True)
            if isinstance(exc, OSError):
                raise OutcomeStoreError(f"cannot write the queue file {self.path}: {exc}") from exc
            raise

    def append(self, entry: QueuedEntry) -> None:
        """Persist a new entry."""
        with self._lock:
            self._ensure_loaded()
            self._cache.append(entry)
            self._persist()

    def update(self, entry: QueuedEntry) -> None:
        """Replace the stored entry with the same ``id``."""
        with self._lock:
            self._ensure_loaded()
            for index, item in enumerate(self._cache):
                if item.get("id") == entry["id"]:
                    self._cache[index] = entry
                    break
            self._persist()

    def remove(self, entry_id: str) -> None:
        """Delete the entry with ``entry_id``."""
        with self._lock:
            self._ensure_loaded()
            self._cache = [item for item in self._cache if item.get("id") != entry_id]
            self._persist()

    def list(self) -> list[QueuedEntry]:
        """Return every stored entry, oldest first (copies)."""
        with self._lock:
            self._ensure_loaded()
            return [dict(item) for item in self._cache]


def _classify(err: Exception) -> UltraRouterError:
    if isinstance(err, UltraRouterError):
        return err
    return APIConnectionError(str(err), retryable=True)


#: Statuses that never drop an event, whatever the body, code or flag says: the credentials (401,
#: 403) or the timing (408, 429) were refused, or an intermediary answered.
_ALWAYS_RETAIN_STATUSES = frozenset({401, 403, 408, 429})

#: Gateway codes that refuse the event itself (malformed, unknown target, conflicting replay).
EVENT_REJECTION_CODES = ("invalid_request", "not_found", "conflict")


def is_definitive_rejection(err: BaseException) -> bool:
    """Whether ``err`` is the gateway definitively refusing the *event*, so it may be dropped.

    All of these must hold (the same rule as the TypeScript SDK):

    1. the status is a 4xx other than 401, 403, 408 and 429 (those four always keep the event);
    2. the body was a complete gateway error envelope
       (:attr:`~ultrarouter.UltraRouterError.envelope`: string ``code``, ``message`` and
       ``request_id``, boolean ``retryable``) whose code is the error's code;
    3. the code is ``invalid_request``, ``not_found`` or ``conflict``, non-retryable in the
       taxonomy, at exactly the status the taxonomy gives it (400, 404, 409);
    4. the envelope says ``retryable: false`` (and so does the error).

    Everything else keeps the event queued: timeouts, cancellation, connection failures, 5xx
    answers, an answer without a complete envelope (an HTML 400 from a proxy, an empty body, a
    missing field, ``retryable: null`` or ``"false"``), an unknown or contradictory code, and a
    malformed success.
    """
    if not isinstance(err, UltraRouterError):
        return False
    if err.status in _ALWAYS_RETAIN_STATUSES or not 400 <= err.status < 500:
        return False
    envelope = err.envelope
    if envelope is None or envelope.get("code") != err.code:
        return False
    if envelope.get("retryable") is not False or err.retryable:
        return False
    code = err.code
    entry = GATEWAY_ERROR_TAXONOMY.get(code)
    return (
        code in EVENT_REJECTION_CODES
        and entry is not None
        and not entry.retryable
        and entry.status == err.status
    )


#: The statuses the contract defines for one recorded outcome.
_OUTCOME_RESULT_STATUSES = frozenset({"accepted", "duplicate", "conflict", "rejected"})


def is_outcome_result(value: Any) -> bool:
    """Whether a 2xx answer is an outcome result: an object with a known ``status``."""
    return isinstance(value, Mapping) and value.get("status") in _OUTCOME_RESULT_STATUSES


def _malformed_success() -> UltraRouterError:
    return UltraRouterError(
        "the outcome route answered without a recognisable result",
        code="invalid_response",
        status=0,
        retryable=False,
    )


def _is_client_error_answer(err: BaseException) -> bool:
    """A reviewer batch refusal to raise: a non-retryable 4xx other than 408/429 (a bad signature,
    a revoked key, an invalid batch, an HTML error page from a proxy). The batch stays queued."""
    return (
        isinstance(err, UltraRouterError)
        and 400 <= err.status < 500
        and err.status not in (408, 429)
        and not err.retryable
    )


def reviewer_verdict_action(verdict: Any) -> Literal["remove", "dead_letter", "drop", "keep"]:
    """What one per-event reviewer verdict allows the queue to do (the TypeScript SDK's rule).

    Only an object with a string ``event_id`` moves an event: ``accepted`` / ``duplicate`` remove
    it; ``rejected`` / ``unsupported`` with a string ``reason`` and a boolean ``repairable`` drop it
    (``false``) or keep it as a dead letter (``true``). Anything else keeps it queued.
    """
    if not isinstance(verdict, Mapping) or not isinstance(verdict.get("event_id"), str):
        return "keep"
    status = verdict.get("status")
    if status in ("accepted", "duplicate"):
        return "remove"
    if status not in ("rejected", "unsupported"):
        return "keep"
    reason, repairable = verdict.get("reason"), verdict.get("repairable")
    if not isinstance(reason, str) or not isinstance(repairable, bool):
        return "keep"
    return "dead_letter" if repairable else "drop"


# ─────────────────────────────── outcome queue ───────────────────────────────


@dataclass
class OutcomeReceipt:
    """What ``outcomes.record(...)`` returns. It never raises for a delivery failure.

    ``status`` is ``"delivered"`` (the server answered; ``result`` holds its per-event verdict),
    ``"queued"`` (the delivery failed or its outcome is unknown, for example a timeout; the
    event stays in the store, unchanged, for :meth:`flush`) or ``"rejected"`` (the server
    definitively refused the event with a non-retryable 4xx; it was dropped and ``error`` says
    why).
    """

    status: Literal["delivered", "queued", "rejected"]
    entry_id: str
    result: dict[str, Any] | None = None
    error: UltraRouterError | None = None


@dataclass
class OutcomeFlushReport:
    """What ``outcomes.flush()`` returns."""

    delivered: int = 0
    rejected: int = 0
    pending: int = 0
    results: list[dict[str, Any]] = field(default_factory=list)


def _finalize_event(
    outcome: Mapping[str, Any], now_ms: Callable[[], float], gen_id: Callable[[], str]
) -> dict[str, Any]:
    event = dict(outcome)
    if event.get("observed_at") is None:
        event["observed_at"] = iso_from_ms(now_ms())
    if event.get("source_event_id") is None:
        event["source_event_id"] = gen_id()
    return event


OutcomeSender = Callable[[QueuedEntry, Mapping[str, Any]], Any]
AsyncOutcomeSender = Callable[[QueuedEntry, Mapping[str, Any]], Awaitable[Any]]


class _OutcomeQueueBase:
    def __init__(
        self,
        store: OutcomeStore,
        now_ms: Callable[[], float] | None = None,
        gen_id: Callable[[], str] | None = None,
    ) -> None:
        self.store = store
        self._now_ms = now_ms or (lambda: time.time() * 1000)
        self._gen_id = gen_id or new_ulid

    def _new_entry(self, target: Mapping[str, str], outcome: Mapping[str, Any]) -> QueuedEntry:
        entry_id = self._gen_id()
        return {
            "id": entry_id,
            "idempotency_key": f"ur-outcome-{entry_id}",
            "target": dict(target),
            "event": _finalize_event(outcome, self._now_ms, self._gen_id),
            "enqueued_at": iso_from_ms(self._now_ms()),
            "attempts": 0,
        }

    def _on_failure(self, entry: QueuedEntry, err: Exception) -> OutcomeReceipt:
        error = _classify(err)
        if is_definitive_rejection(err):
            self.store.remove(entry["id"])
            return OutcomeReceipt(status="rejected", entry_id=entry["id"], error=error)
        entry["attempts"] = int(entry.get("attempts", 0)) + 1
        entry["last_error"] = error.code
        self.store.update(entry)
        return OutcomeReceipt(status="queued", entry_id=entry["id"], error=error)

    def size(self) -> int:
        """Number of events still queued."""
        return len(self.store.list())


class OutcomeQueue(_OutcomeQueueBase):
    """The synchronous durable outcome queue (one per :class:`~ultrarouter.UltraRouter`)."""

    def __init__(
        self,
        store: OutcomeStore,
        send: OutcomeSender,
        now_ms: Callable[[], float] | None = None,
        gen_id: Callable[[], str] | None = None,
    ) -> None:
        super().__init__(store, now_ms, gen_id)
        self._send = send

    def with_sender(self, send: OutcomeSender) -> OutcomeQueue:
        """A queue over the same store (and clock and id source) that delivers through ``send``."""
        clone = copy.copy(self)
        clone._send = send
        return clone

    def enqueue(
        self,
        target: Mapping[str, str],
        outcome: Mapping[str, Any],
        options: Mapping[str, Any] | None = None,
    ) -> OutcomeReceipt:
        """Finalize, persist, then try to deliver one event."""
        entry = self._new_entry(target, outcome)
        self.store.append(entry)
        return self._deliver(entry, options or {})

    def flush(self, options: Mapping[str, Any] | None = None) -> OutcomeFlushReport:
        """Try to deliver every queued event (oldest first)."""
        report = OutcomeFlushReport()
        for entry in self.store.list():
            receipt = self._deliver(entry, options or {})
            if receipt.status == "delivered" and receipt.result is not None:
                report.delivered += 1
                report.results.append(receipt.result)
            elif receipt.status == "rejected":
                report.rejected += 1
        report.pending = self.size()
        return report

    def _deliver(self, entry: QueuedEntry, options: Mapping[str, Any]) -> OutcomeReceipt:
        try:
            result = self._send(entry, options)
            if not is_outcome_result(result):
                raise _malformed_success()  # a success the contract does not describe
        except Exception as err:
            return self._on_failure(entry, err)
        self.store.remove(entry["id"])
        return OutcomeReceipt(status="delivered", entry_id=entry["id"], result=dict(result))


class AsyncOutcomeQueue(_OutcomeQueueBase):
    """The asynchronous durable outcome queue (one per :class:`~ultrarouter.AsyncUltraRouter`)."""

    def __init__(
        self,
        store: OutcomeStore,
        send: AsyncOutcomeSender,
        now_ms: Callable[[], float] | None = None,
        gen_id: Callable[[], str] | None = None,
    ) -> None:
        super().__init__(store, now_ms, gen_id)
        self._send = send

    def with_sender(self, send: AsyncOutcomeSender) -> AsyncOutcomeQueue:
        """A queue over the same store (and clock and id source) that delivers through ``send``."""
        clone = copy.copy(self)
        clone._send = send
        return clone

    async def enqueue(
        self,
        target: Mapping[str, str],
        outcome: Mapping[str, Any],
        options: Mapping[str, Any] | None = None,
    ) -> OutcomeReceipt:
        """Finalize, persist, then try to deliver one event."""
        entry = self._new_entry(target, outcome)
        self.store.append(entry)
        return await self._deliver(entry, options or {})

    async def flush(self, options: Mapping[str, Any] | None = None) -> OutcomeFlushReport:
        """Try to deliver every queued event (oldest first)."""
        report = OutcomeFlushReport()
        for entry in self.store.list():
            receipt = await self._deliver(entry, options or {})
            if receipt.status == "delivered" and receipt.result is not None:
                report.delivered += 1
                report.results.append(receipt.result)
            elif receipt.status == "rejected":
                report.rejected += 1
        report.pending = self.size()
        return report

    async def _deliver(self, entry: QueuedEntry, options: Mapping[str, Any]) -> OutcomeReceipt:
        try:
            result = await self._send(entry, options)
            if not is_outcome_result(result):
                raise _malformed_success()  # a success the contract does not describe
        except Exception as err:
            return self._on_failure(entry, err)
        self.store.remove(entry["id"])
        return OutcomeReceipt(status="delivered", entry_id=entry["id"], result=dict(result))


# ─────────────────────────────── reviewer queue ───────────────────────────────

DEFAULT_REVIEWER_BATCH_SIZE = 200
MAX_REVIEWER_BATCH_SIZE = 500


@dataclass
class ReviewerFlushReport:
    """What ``reviewer.flush()`` returns."""

    accepted: int = 0
    """Events the server recorded."""

    duplicate: int = 0
    """Re-sent events the server had already recorded (visible no-ops)."""

    dead_lettered: int = 0
    """Events refused with a repairable reason; kept locally for ``reviewer.repair``."""

    dropped: int = 0
    """Events refused with a terminal reason and removed."""

    pending: int = 0
    """Events still queued after a retryable failure."""

    results: list[dict[str, Any]] = field(default_factory=list)
    """Per-event verdicts in flush order."""


ReviewerSender = Callable[[list[QueuedEntry], Any, Any, Mapping[str, Any]], dict[str, Any]]
AsyncReviewerSender = Callable[
    [list[QueuedEntry], Any, Any, Mapping[str, Any]], Awaitable[dict[str, Any]]
]


def _group(entries: list[QueuedEntry]) -> list[tuple[Any, Any, list[QueuedEntry]]]:
    groups: dict[str, tuple[Any, Any, list[QueuedEntry]]] = {}
    for entry in entries:
        backfill = entry.get("backfill")
        system = entry.get("reviewer_system")
        key = json.dumps([backfill.get("id") if isinstance(backfill, dict) else None, system])
        if key not in groups:
            groups[key] = (backfill, system, [])
        groups[key][2].append(entry)
    return list(groups.values())


class _ReviewerQueueBase:
    def __init__(
        self,
        store: OutcomeStore,
        now_ms: Callable[[], float] | None = None,
        gen_id: Callable[[], str] | None = None,
        batch_size: int = DEFAULT_REVIEWER_BATCH_SIZE,
    ) -> None:
        self.store = store
        self._now_ms = now_ms or (lambda: time.time() * 1000)
        self._gen_id = gen_id or new_ulid
        self.batch_size = max(1, min(batch_size, MAX_REVIEWER_BATCH_SIZE))

    def enqueue(
        self,
        event: Mapping[str, Any],
        *,
        backfill: Mapping[str, Any] | None = None,
        reviewer_system: str | None = None,
    ) -> str:
        """Persist one reviewer event (no network) and return its queue-entry id."""
        entry: QueuedEntry = {
            "id": self._gen_id(),
            "event": dict(event),
            "enqueued_at": iso_from_ms(self._now_ms()),
            "attempts": 0,
        }
        if backfill is not None:
            entry["backfill"] = dict(backfill)
        if reviewer_system is not None:
            entry["reviewer_system"] = reviewer_system
        self.store.append(entry)
        return str(entry["id"])

    def pending(self) -> list[QueuedEntry]:
        """Entries awaiting delivery (dead letters excluded)."""
        return [e for e in self.store.list() if not e.get("dead_letter")]

    def dead_letters(self) -> list[QueuedEntry]:
        """Entries the server refused with a repairable reason."""
        return [e for e in self.store.list() if e.get("dead_letter")]

    def clear_dead_letter(self, entry_id: str) -> None:
        """Remove a dead letter after a successful repair."""
        self.store.remove(entry_id)

    def _apply(self, batch: list[QueuedEntry], response: Any, report: ReviewerFlushReport) -> bool:
        """Apply per-event verdicts; False (batch untouched but counted) when there are none."""
        rows = response.get("data") if isinstance(response, Mapping) else None
        if not isinstance(rows, list):
            self._mark_failed(batch)  # a success without a list of verdicts proves nothing
            return False
        by_id: dict[str, Any] = {}
        for row in rows:
            # Only a string event_id can name a queued event; any other value (a number, null,
            # a list, an object) is skipped before it is used as a key, so the event is kept.
            if isinstance(row, Mapping) and isinstance(row.get("event_id"), str):
                by_id[row["event_id"]] = row
        for entry in batch:
            verdict = by_id.get(entry["event"].get("event_id"))
            action = reviewer_verdict_action(verdict)
            if action == "keep":  # no verdict, or one that does not validate
                entry["attempts"] = int(entry.get("attempts", 0)) + 1
                self.store.update(entry)
                continue
            assert isinstance(verdict, Mapping)  # reviewer_verdict_action validated it
            report.results.append(dict(verdict))
            if action == "remove":
                if verdict["status"] == "accepted":
                    report.accepted += 1
                else:
                    report.duplicate += 1
                self.store.remove(entry["id"])
            elif action == "dead_letter":
                entry["dead_letter"] = {
                    "reason": verdict["reason"],
                    "at": iso_from_ms(self._now_ms()),
                }
                entry["attempts"] = int(entry.get("attempts", 0)) + 1
                self.store.update(entry)
                report.dead_lettered += 1
            else:
                self.store.remove(entry["id"])  # a validated, terminal refusal of this event
                report.dropped += 1
        return True

    def _mark_failed(self, batch: list[QueuedEntry]) -> None:
        for entry in batch:
            entry["attempts"] = int(entry.get("attempts", 0)) + 1
            self.store.update(entry)


class ReviewerQueue(_ReviewerQueueBase):
    """The synchronous durable reviewer-event queue."""

    def __init__(
        self,
        store: OutcomeStore,
        send: ReviewerSender,
        now_ms: Callable[[], float] | None = None,
        gen_id: Callable[[], str] | None = None,
        batch_size: int = DEFAULT_REVIEWER_BATCH_SIZE,
    ) -> None:
        super().__init__(store, now_ms, gen_id, batch_size)
        self._send = send

    def with_sender(self, send: ReviewerSender) -> ReviewerQueue:
        """A queue over the same store (and settings) that delivers through ``send``."""
        clone = copy.copy(self)
        clone._send = send
        return clone

    def flush(self, options: Mapping[str, Any] | None = None) -> ReviewerFlushReport:
        """Send every queued event in signed batches (grouped by backfill and reviewer system).

        Events are only ever removed by validated per-event verdicts (see
        :func:`reviewer_verdict_action`). A failed delivery never removes one: a failure whose
        outcome is unknown (timeout, cancellation, connection failure, 408/429/5xx, a success whose
        ``data`` is not a list) leaves the batch queued and ends this flush, and any other
        non-retryable 4xx answer (401/403, a bad signature, an invalid batch, an HTML 400 from a
        proxy) also leaves it queued and is raised.
        """
        report = ReviewerFlushReport()
        for backfill, system, entries in _group(self.pending()):
            for start in range(0, len(entries), self.batch_size):
                batch = entries[start : start + self.batch_size]
                try:
                    response = self._send(batch, backfill, system, options or {})
                except Exception as err:
                    self._mark_failed(batch)
                    if _is_client_error_answer(err):
                        raise
                    break
                if not self._apply(batch, response, report):
                    break
        report.pending = len(self.pending())
        return report


class AsyncReviewerQueue(_ReviewerQueueBase):
    """The asynchronous durable reviewer-event queue."""

    def __init__(
        self,
        store: OutcomeStore,
        send: AsyncReviewerSender,
        now_ms: Callable[[], float] | None = None,
        gen_id: Callable[[], str] | None = None,
        batch_size: int = DEFAULT_REVIEWER_BATCH_SIZE,
    ) -> None:
        super().__init__(store, now_ms, gen_id, batch_size)
        self._send = send

    def with_sender(self, send: AsyncReviewerSender) -> AsyncReviewerQueue:
        """A queue over the same store (and settings) that delivers through ``send``."""
        clone = copy.copy(self)
        clone._send = send
        return clone

    async def flush(self, options: Mapping[str, Any] | None = None) -> ReviewerFlushReport:
        """Async twin of :meth:`ReviewerQueue.flush`."""
        report = ReviewerFlushReport()
        for backfill, system, entries in _group(self.pending()):
            for start in range(0, len(entries), self.batch_size):
                batch = entries[start : start + self.batch_size]
                try:
                    response = await self._send(batch, backfill, system, options or {})
                except Exception as err:
                    self._mark_failed(batch)
                    if _is_client_error_answer(err):
                        raise
                    break
                if not self._apply(batch, response, report):
                    break
        report.pending = len(self.pending())
        return report
