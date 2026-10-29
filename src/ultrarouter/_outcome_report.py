"""What ``client.outcomes.report(...)`` returns, and how a report becomes an outcome event.

A report is a verdict (``pass``, ``fail`` or ``unknown``) on one request, from one source
(``verifier``, ``business_rule``, ``webhook``, ``human_review`` or ``self_rating``). The shared
verdict fixture maps it to an outcome channel and kind (see :mod:`ultrarouter._verdicts`).

The return type says what happened and whether the report can teach:

* :class:`NotReportedOutcome` for ``unknown``: nothing was sent;
* :class:`TeachingOutcomeReport` (``teaches`` is ``True``) for a teaching source;
* :class:`ProxyOutcomeReport` (``teaches`` is ``False``) for ``self_rating``, which only ranks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from ._correlation import validate_request_id
from ._errors import InvalidRequestError, UltraRouterError
from ._queue import OutcomeReceipt
from ._verdicts import VerdictEvent, report_source_event_id, verdict_event
from .types._learning import OutcomeReceiptRecord

__all__ = [
    "NotReportedOutcome",
    "OutcomeReport",
    "ProxyOutcomeReport",
    "ReportDeliveryStatus",
    "TeachingOutcomeReport",
    "build_report_event",
    "report_from_receipt",
]

ReportDeliveryStatus = Literal["delivered", "queued", "rejected"]
"""Local delivery: ``delivered`` (the gateway answered), ``queued`` (kept in the durable queue
for ``flush()``), ``rejected`` (the gateway definitively refused the event; ``error`` says why)."""


@dataclass(frozen=True)
class NotReportedOutcome:
    """A verdict of ``unknown``: nothing was sent, and nothing is ever inferred from silence."""

    request_id: str
    """The request the verdict was about."""

    source: str
    """The source that had no trustworthy verdict."""

    verdict: Literal["unknown"] = "unknown"
    """Always ``unknown``."""

    status: Literal["not_reported"] = "not_reported"
    """Always ``not_reported``."""

    reported: Literal[False] = False
    """Always ``False``: no event exists."""

    teaches: Literal[False] = False
    """Always ``False``: an unknown verdict carries no signal."""

    reason: Literal["verdict_unknown"] = "verdict_unknown"
    """Always ``verdict_unknown``."""


@dataclass(frozen=True)
class _ReportedOutcome:
    request_id: str
    """The request the outcome was reported on."""

    verdict: Literal["pass", "fail"]
    """The verdict reported."""

    source: str
    """Where the verdict came from."""

    status: ReportDeliveryStatus
    """Local delivery status (see :data:`ReportDeliveryStatus`)."""

    channel: str
    """The outcome channel the verdict mapped to."""

    kind: str
    """The channel kind the verdict mapped to."""

    source_event_id: str
    """The stable event id: reporting the same verdict again names the same event. Pass it as
    ``supersedes`` to revise this report."""

    entry_id: str
    """The durable-queue entry id (the ``source_event_id``, unless a different payload under the
    same identity had to be sent as its own entry)."""

    result: dict[str, Any] | None = None
    """The gateway's answer for this event, when it answered."""

    error: UltraRouterError | None = None
    """Why delivery failed (``queued``) or the event was refused (``rejected``)."""

    reported: Literal[True] = field(default=True, init=False)
    """Always ``True``: the event exists locally or on the gateway."""

    @property
    def outcome_status(self) -> str | None:
        """The gateway's status for the event: ``accepted``, ``duplicate``, ``pending`` (accepted
        before the request was persisted; see ``receipt``), ``conflict`` or ``rejected``."""
        status = (self.result or {}).get("status")
        return status if isinstance(status, str) else None

    @property
    def receipt(self) -> OutcomeReceiptRecord | None:
        """The durable receipt the gateway returned, when it returned one."""
        raw = (self.result or {}).get("receipt")
        if not isinstance(raw, dict):
            return None
        return OutcomeReceiptRecord.model_validate(raw)

    @property
    def receipt_id(self) -> str | None:
        """The receipt id, for ``outcomes.receipt`` / ``outcomes.wait_for_receipt``."""
        receipt = self.receipt
        return receipt.id if receipt is not None else None

    @property
    def outcome_event_id(self) -> str | None:
        """The recorded outcome event id, once known."""
        value = (self.result or {}).get("id")
        if isinstance(value, str) and value:
            return value
        receipt = self.receipt
        return receipt.outcome_event_id if receipt is not None else None

    @property
    def is_pending(self) -> bool:
        """Whether the gateway holds the outcome as a pending receipt (request not yet stored)."""
        return self.outcome_status == "pending"


@dataclass(frozen=True)
class TeachingOutcomeReport(_ReportedOutcome):
    """A reported verdict from a source that teaches (verifier, business rule, webhook, human)."""

    teaches: Literal[True] = field(default=True, init=False)
    """Always ``True``: this outcome can reach learning as evidence."""


@dataclass(frozen=True)
class ProxyOutcomeReport(_ReportedOutcome):
    """A reported self-rating: recorded as a weak proxy that may rank but never teaches."""

    teaches: Literal[False] = field(default=False, init=False)
    """Always ``False``: a proxy never teaches."""


OutcomeReport = TeachingOutcomeReport | ProxyOutcomeReport | NotReportedOutcome
"""Everything ``client.outcomes.report(...)`` can return."""


def _iso(value: str | datetime) -> str:
    """Normalize to ``YYYY-MM-DDTHH:MM:SS.mmmZ`` (JavaScript ``toISOString``).

    A value without an offset is local time, as JavaScript reads a date-time string; a bare date
    is midnight UTC.
    """
    if isinstance(value, str):
        text = value.strip()
        try:
            if len(text) == 10:  # a bare date
                moment = datetime.fromisoformat(text).replace(tzinfo=timezone.utc)
            else:
                moment = datetime.fromisoformat(text[:-1] + "+00:00" if text[-1:] in "Zz" else text)
        except (ValueError, IndexError):
            raise InvalidRequestError(
                "observed_at must be an ISO-8601 instant or a datetime", status=0
            ) from None
    else:
        moment = value
    moment = moment.astimezone(timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%S") + f".{moment.microsecond // 1000:03d}Z"


@dataclass(frozen=True)
class ReportEvent:
    """A report turned into the outcome event to send (internal)."""

    mapped: VerdictEvent
    event: dict[str, Any]
    source_event_id: str


def build_report_event(
    request_id: str,
    verdict: str,
    source: str,
    *,
    idempotency_key: str | None,
    observed_at: str | datetime | None,
    evidence_hash: str | None,
    supersedes: str | None,
) -> ReportEvent | None:
    """Validate a report and build its event; ``None`` for ``unknown`` (nothing to send)."""
    validate_request_id(request_id)
    mapped = verdict_event(source, verdict)
    if mapped is None:
        return None
    if idempotency_key is not None and not idempotency_key:
        raise InvalidRequestError("idempotency_key must not be empty", status=0)
    source_event_id = report_source_event_id(request_id, verdict, source, idempotency_key)
    event: dict[str, Any] = {
        "channel": mapped.channel,
        "kind": mapped.kind,
        "source_event_id": source_event_id,
    }
    if mapped.value is not None:
        event["value"] = dict(mapped.value)
    if observed_at is not None:
        event["observed_at"] = _iso(observed_at)
    if evidence_hash is not None:
        event["evidence_hash"] = evidence_hash
    if supersedes is not None:
        event["supersedes_event_id"] = supersedes
    return ReportEvent(mapped, event, source_event_id)


def report_from_receipt(
    request_id: str,
    verdict: Literal["pass", "fail"],
    source: str,
    built: ReportEvent,
    receipt: OutcomeReceipt,
) -> TeachingOutcomeReport | ProxyOutcomeReport:
    """Wrap the queue's delivery receipt as the typed report."""
    cls = TeachingOutcomeReport if built.mapped.teaches else ProxyOutcomeReport
    return cls(
        request_id=request_id,
        verdict=verdict,
        source=source,
        status=receipt.status,
        channel=built.mapped.channel,
        kind=built.mapped.kind,
        source_event_id=built.source_event_id,
        entry_id=receipt.entry_id,
        result=receipt.result,
        error=receipt.error,
    )
