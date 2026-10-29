"""How an outcome report (a verdict from a source) maps to the gateway's outcome channels.

The mapping is data, not code: ``ultrarouter/_data/outcome_verdicts.json`` is a byte-for-byte copy
of the fixture the TypeScript SDK ships, so both SDKs send exactly the same events.

* ``verifier`` and ``business_rule``: ``computable`` / ``oracle_pass`` or ``oracle_fail``;
* ``webhook``: ``resolution`` / ``resolved_true`` or ``resolved_false``;
* ``human_review``: ``correction`` / ``accepted_unchanged`` or ``rejected``;
* ``self_rating``: ``proxy`` / ``thumbs`` with value ``+1`` or ``-1``; it never teaches.

A verdict of ``unknown`` sends nothing: missing feedback stays missing, it is never guessed. A
self-rating is a weak proxy: it may rank, but it never teaches.

Pure: no network.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from typing import Any, Literal, get_args

from ._errors import InvalidRequestError
from .context._hash import sha256_hex

__all__ = [
    "OUTCOME_SOURCES",
    "REPORT_IDENTITY_VERSION",
    "TEACHING_SOURCES",
    "OutcomeSource",
    "ProxySource",
    "TeachingSource",
    "Verdict",
    "VerdictEvent",
    "outcome_verdicts_document",
    "report_source_event_id",
    "source_teaches",
    "verdict_event",
]

Verdict = Literal["pass", "fail", "unknown"]
"""A report's verdict. ``unknown`` means "no trustworthy outcome": nothing is sent."""

TeachingSource = Literal["verifier", "business_rule", "webhook", "human_review"]
"""Sources whose verdicts teach (they reach learning as evidence)."""

ProxySource = Literal["self_rating"]
"""Sources that only rank and never teach."""

OutcomeSource = Literal["verifier", "business_rule", "webhook", "human_review", "self_rating"]
"""Where a verdict came from; decides the outcome channel and whether it teaches."""

#: Every source, in the fixture's order.
OUTCOME_SOURCES: tuple[str, ...] = get_args(OutcomeSource)

#: The sources that teach.
TEACHING_SOURCES: tuple[str, ...] = get_args(TeachingSource)


@dataclass(frozen=True)
class VerdictEvent:
    """The outcome event one (source, verdict) pair maps to."""

    channel: str
    """The outcome channel (``computable``, ``resolution``, ``correction`` or ``proxy``)."""

    kind: str
    """The channel kind (for example ``oracle_pass``)."""

    value: dict[str, Any] | None
    """The typed value payload, when the mapping has one (self-rating carries ``{"value": ±1}``)."""

    teaches: bool
    """Whether this event reaches learning as evidence (``False`` for a self-rating)."""

    label: str
    """A human-readable label for the source."""


@lru_cache(maxsize=1)
def _raw_document() -> bytes:
    return (resources.files("ultrarouter") / "_data" / "outcome_verdicts.json").read_bytes()


def outcome_verdicts_document() -> dict[str, Any]:
    """The shared verdict-mapping fixture, parsed (a fresh copy on every call)."""
    parsed: dict[str, Any] = json.loads(_raw_document())
    return parsed


@lru_cache(maxsize=1)
def _table() -> dict[str, dict[str, Any]]:
    document = outcome_verdicts_document()
    if document.get("schema_version") != 1:
        raise RuntimeError("unsupported outcome_verdicts.json schema_version")
    sources = document["sources"]
    if set(sources) != set(OUTCOME_SOURCES):  # the packaged data and the Literal must agree
        raise RuntimeError("outcome_verdicts.json sources do not match OutcomeSource")
    return {name: dict(entry) for name, entry in sources.items()}


def source_teaches(source: str) -> bool:
    """Whether a verdict from ``source`` teaches (``False`` only for ``self_rating``)."""
    return bool(_entry(source)["teaches"])


def _entry(source: str) -> dict[str, Any]:
    entry = _table().get(source)
    if entry is None:
        raise InvalidRequestError(
            f"source must be one of {', '.join(OUTCOME_SOURCES)} (got {source!r})", status=0
        )
    return entry


def verdict_event(source: str, verdict: str) -> VerdictEvent | None:
    """The event a verdict maps to, or ``None`` for ``unknown`` (nothing is sent).

    Raises :class:`~ultrarouter.InvalidRequestError` (status 0) for an unknown source or verdict.
    """
    entry = _entry(source)
    if verdict == "unknown":
        return None
    if verdict not in ("pass", "fail"):
        raise InvalidRequestError(
            f"verdict must be 'pass', 'fail' or 'unknown' (got {verdict!r})", status=0
        )
    mapped = entry[verdict]
    value = mapped.get("value")
    return VerdictEvent(
        channel=str(mapped["channel"]),
        kind=str(mapped["kind"]),
        value=dict(value) if isinstance(value, dict) else None,
        teaches=bool(entry["teaches"]),
        label=str(entry["label"]),
    )


#: The version tag mixed into every derived ``source_event_id``.
REPORT_IDENTITY_VERSION = "ur-outcome-report/v1"


def report_source_event_id(
    request_id: str, verdict: str, source: str, idempotency_key: str | None = None
) -> str:
    """The stable ``source_event_id`` of a report: the same inputs always give the same id.

    ``"rpt_"`` followed by the lowercase hex SHA-256 of the UTF-8 string
    ``"ur-outcome-report/v1\n" + request_id + "\n" + verdict + "\n" + source + "\n" +
    (idempotency_key or "")``, exactly as the TypeScript SDK's ``reportSourceEventId``. Reporting
    the same verdict again (a retry after a lost acknowledgement, a restarted process, a
    redelivered webhook) therefore names the same event, which the gateway records once. To record
    a second, distinct event with the same verdict and source, pass a distinct ``idempotency_key``.
    """
    material = "\n".join(
        (REPORT_IDENTITY_VERSION, request_id, verdict, source, idempotency_key or "")
    )
    return "rpt_" + sha256_hex(material)
