"""``Envelope``: the immutable identity of one execution.

Tenant, stage, mode, knowledge cutoff (``asOf``), budgets, seed, pins, release bindings and the
permission epoch. ``ext`` round-trips application-specific fields and is never a source of
authority.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypedDict

from ._hash import hash_context_value

__all__ = ["Envelope", "EnvelopeBudgets", "Pin", "SealedEnvelope", "hash_envelope", "seal_envelope"]


class Pin(TypedDict):
    """A module the execution must use, frozen by id, kind and content hash."""

    id: str
    kind: str
    contentHash: str
    purpose: str


class EnvelopeBudgets(TypedDict, total=False):
    """Execution budgets (tokens, tool calls, planner depth and passes, time, micro-USD)."""

    tokens: int
    toolCalls: int
    plannerDepth: int
    plannerPass: int
    timeMs: int
    microUsd: int


class Envelope(TypedDict, total=False):
    """The identity of one execution: tenant, stage, mode, cutoff (``asOf``), budgets, pins."""

    id: str
    tenant: str
    stage: str
    mode: str
    asOf: str
    cutoffs: dict[str, str]
    budgets: dict[str, Any]
    seed: str
    pins: list[Pin]
    releases: dict[str, Any]
    permissionEpoch: str
    ext: dict[str, Any]


class SealedEnvelope(TypedDict):
    """An envelope projected to its known fields, with its content hash."""

    envelope: Envelope
    envelopeHash: str


# The known envelope fields, in schema order (used to project away unknown keys before the
# default hash — mirrors ``EnvelopeSchema.parse`` stripping extras. Key ORDER is irrelevant to
# the hash because ``canonical_json`` sorts, but projection keeps the digest schema-scoped).
_ENVELOPE_KEYS = (
    "id",
    "tenant",
    "stage",
    "mode",
    "asOf",
    "cutoffs",
    "budgets",
    "seed",
    "pins",
    "releases",
    "permissionEpoch",
    "ext",
)


def _projected(envelope: Mapping[str, Any]) -> dict[str, Any]:
    return {key: envelope[key] for key in _ENVELOPE_KEYS if key in envelope}


def hash_envelope(envelope: Mapping[str, Any]) -> str:
    """The ultrarouter-default digest of an envelope's schema-scoped content."""
    return hash_context_value(_projected(envelope))


def seal_envelope(raw: Envelope) -> SealedEnvelope:
    """Project + hash an envelope. The hash is what pins it into the manifest and survives the
    process. (Python has no cheap deep-freeze; callers treat the returned envelope as read-only.)"""
    envelope = _projected(raw)
    return {"envelope": envelope, "envelopeHash": hash_context_value(envelope)}  # type: ignore[typeddict-item]
