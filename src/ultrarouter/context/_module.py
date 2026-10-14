"""``Module``: a typed, versioned, content-hashed unit of context.

``kind``, ``memoryClass`` and ``privacyClass`` are labels the compiler carries but never branches
on. ``trustClass`` is the one field with core meaning: ``untrusted`` content is admissible only in
a reference or exemplar slot. ``ext`` round-trips application-specific fields and is never a
source of authority.

Structural types are ``TypedDict`` with camelCase keys, byte-compatible with the TypeScript
runtime and the shared fixtures.
"""

from __future__ import annotations

from typing import Any, TypedDict

__all__ = ["TRUST_CLASSES", "Availability", "Module"]

TRUST_CLASSES: tuple[str, ...] = ("authoritative", "approved_derived", "untrusted")

# ``from`` is a Python keyword, so ``Availability`` uses the functional TypedDict form to keep both
# keys. The compiler reads them via ``dict`` access (``availability["from"]`` / ``["to"]``);
# ISO-8601
# instants or ``None`` (a null ``from`` = "no availability of its own").
Availability = TypedDict("Availability", {"from": str | None, "to": str | None})
Availability.__doc__ = (
    """When a module is available: ISO-8601 ``from`` / ``to`` instants (``None`` = unbounded)."""
)


class Module(TypedDict, total=False):
    """A typed, versioned, content-hashed unit of context (camelCase keys, JSON-native)."""

    id: str
    version: str
    kind: str
    memoryClass: str
    trustClass: str
    privacyClass: str
    availability: dict[str, Any]  # {"from": str | None, "to": str | None}
    contentHash: str
    tokenEstimate: int
    facets: dict[str, Any]
    slotHint: str
    ext: dict[str, Any]
