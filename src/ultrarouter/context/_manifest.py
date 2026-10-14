"""``Manifest``: the hashable record of exactly what one execution was allowed to see.

Ordered admitted entries, the refused set, budgets, the envelope hash, the manifest hash and the
``scaffoldHash`` (kinds, slots and ids only; stable across executions of the same call shape).
:func:`to_wire` renders the ``ur.manifest`` request field, which the gateway verifies against the
bytes it receives.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, TypedDict

__all__ = [
    "NATIVE_DELIVERY_STATES",
    "ContextRange",
    "Manifest",
    "ManifestBudgets",
    "ManifestEntry",
    "ScaffoldSubjectEntry",
    "scaffold_subject",
    "to_wire",
]

NATIVE_DELIVERY_STATES: tuple[str, ...] = ("native", "unavailable")


class ContextRange(TypedDict, total=False):
    """Where a lifted entry came from: message index and UTF-16 ``[start, end)`` offsets."""

    messageIndex: int
    partIndex: int
    start: int
    end: int


class ManifestEntry(TypedDict, total=False):
    """One admitted module in a manifest (identity, labels, order, slot, token estimate)."""

    moduleId: str
    version: str
    kind: str
    memoryClass: str
    trustClass: str
    privacyClass: str
    contentHash: str
    order: int
    mandatory: bool
    tokenEstimate: int
    slot: str
    range: ContextRange
    ext: dict[str, Any]


class ManifestBudgets(TypedDict):
    """Budget accounting of a manifest: tokens admitted, the limit, admitted and refused counts."""

    tokensAdmitted: int
    tokenLimit: int | None
    admitted: int
    refused: int


class Manifest(TypedDict, total=False):
    """The hashable record of what one execution was allowed to see, and what was refused."""

    envelopeId: str
    stage: str
    entries: list[ManifestEntry]
    refused: list[dict[str, Any]]
    budgets: ManifestBudgets
    envelopeHash: str
    manifestHash: str
    scaffoldHash: str
    nativeDelivery: str
    ext: dict[str, Any]


class ScaffoldSubjectEntry(TypedDict):
    """The call-shape identity of one entry (id, kind, slot, mandatory, order)."""

    moduleId: str
    kind: str
    slot: str
    mandatory: bool
    order: int


def scaffold_subject(entries: Sequence[Mapping[str, Any]]) -> list[ScaffoldSubjectEntry]:
    """The ordered scaffold subject for a set of entries (kinds/slots/ids + order only)."""
    return [
        {
            "moduleId": entry["moduleId"],
            "kind": entry["kind"],
            "slot": entry["slot"],
            "mandatory": entry["mandatory"],
            "order": entry["order"],
        }
        for entry in entries
    ]


def to_wire(manifest: Manifest) -> dict[str, Any]:
    """Render a manifest as the ``ur.manifest`` request field. Pure; carries no bodies."""
    entries: list[dict[str, Any]] = []
    for entry in manifest["entries"]:
        wire: dict[str, Any] = {
            "kind": entry["kind"],
            "slot": entry["slot"],
            "trust_class": entry["trustClass"],
            "memory_class": entry["memoryClass"],
            "content_hash": entry["contentHash"],
            "mandatory": entry["mandatory"],
            "order": entry["order"],
        }
        rng = entry.get("range")
        if rng is not None:
            range_wire: dict[str, Any] = {"message_index": rng["messageIndex"]}
            if "partIndex" in rng and rng["partIndex"] is not None:
                range_wire["part_index"] = rng["partIndex"]
            range_wire["start"] = rng["start"]
            range_wire["end"] = rng["end"]
            wire["range"] = range_wire
        entries.append(wire)
    return {
        "scaffold_hash": manifest["scaffoldHash"],
        "manifest_hash": manifest["manifestHash"],
        "envelope_hash": manifest["envelopeHash"],
        "entries": entries,
    }
