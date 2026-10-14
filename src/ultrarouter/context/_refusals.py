"""Refusals: the compiler's typed record of why a candidate was not admitted (or why a whole
run is inadmissible). Pure data, never an exception on the admission path. A profile can map the
base reasons onto its own code vocabulary with :func:`define_refusals`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypedDict

__all__ = [
    "CONTEXT_DELIVERY_REFUSAL_REASONS",
    "CONTEXT_REFUSAL_REASONS",
    "Refusal",
    "RefusalRegistry",
    "define_refusals",
    "is_context_delivery_refusal_reason",
    "is_context_refusal_reason",
]

CONTEXT_REFUSAL_REASONS: tuple[str, ...] = (
    "STAGE_CONTRACT_MISMATCH",
    "PLANNER_BOUND_EXCEEDED",
    "PINNED_CONTEXT_NOT_REQUESTED",
    "REQUIRED_CONTEXT_NOT_PINNED",
    "PINNED_CONTEXT_MISMATCH",
    "REQUIRED_CONTEXT_MISSING",
    "AUTHORITATIVE_CONTEXT_UNTRUSTED",
    "POLICY_RELEASE_MISMATCH",
    "FORBIDDEN_KIND",
    "BUDGET_EXCEEDED",
    "UNTRUSTED_IN_INSTRUCTION_SLOT",
    "AVAILABILITY_REFUSED",
    "LIMIT_EXCEEDED",
)

_REFUSAL_SET = frozenset(CONTEXT_REFUSAL_REASONS)

# Delivery refusals — emitted by the native-delivery layer, never by ``compile``.
CONTEXT_DELIVERY_REFUSAL_REASONS: tuple[str, ...] = ("NATIVE_UNAVAILABLE",)
_DELIVERY_REFUSAL_SET = frozenset(CONTEXT_DELIVERY_REFUSAL_REASONS)


def is_context_refusal_reason(value: str) -> bool:
    """Whether ``value`` is one of :data:`CONTEXT_REFUSAL_REASONS`."""
    return value in _REFUSAL_SET


def is_context_delivery_refusal_reason(value: str) -> bool:
    """Whether ``value`` is one of :data:`CONTEXT_DELIVERY_REFUSAL_REASONS`."""
    return value in _DELIVERY_REFUSAL_SET


class Refusal(TypedDict, total=False):
    """A single refusal record. ``code`` is the string the active profile renders."""

    reason: str
    code: str
    message: str
    path: str
    moduleId: str
    kind: str
    detail: str
    fatal: bool


class RefusalRegistry:
    """How a profile renders base reasons as concrete codes. ``codes`` is the profile's full
    vocabulary (base ∪ parent); ``encode`` maps (reason, detail) → the emitted code."""

    def __init__(
        self,
        codes: tuple[str, ...],
        mapper: Callable[[str, str | None], str | None] | None,
    ) -> None:
        self.codes = codes
        self._map = mapper

    def encode(self, reason: str, detail: str | None = None) -> str:
        """The code this registry emits for ``reason`` (and optional ``detail``)."""
        mapped = self._map(reason, detail) if self._map is not None else None
        return mapped if mapped is not None else reason


def define_refusals(
    extra_codes: tuple[str, ...] | list[str] | None = None,
    mapper: Callable[[str, str | None], str | None] | None = None,
) -> RefusalRegistry:
    """Build a refusal registry. No arguments ⇒ the ultrarouter default (base reasons ARE the
    codes). A parent passes ``extra_codes`` + a ``mapper`` from (reason, detail) → code."""
    extra = tuple(extra_codes or ())
    codes = CONTEXT_REFUSAL_REASONS + extra
    return RefusalRegistry(codes, mapper)
