"""``Contract``: what one stage of an execution may see.

Per stage: which module kinds are required / optional / forbidden, the budgets, per-kind or
per-facet caps (``limits``), the pin policy and the slot vocabulary. ``orderRule`` round-trips for
compatibility, but the compiler orders by the profile's ``order_rule`` so a contract cannot
silently re-order a workload.
"""

from __future__ import annotations

from typing import Any, TypedDict

__all__ = ["PIN_POLICIES", "Contract", "Limit"]

PIN_POLICIES: tuple[str, ...] = ("strict", "none")


class Limit(TypedDict, total=False):
    """A per-kind or per-facet cap: ``max`` admits at most that many matching modules."""

    kind: str
    facet: str
    facetValue: str
    max: int
    label: str


class Contract(TypedDict, total=False):
    """What one stage may see: required, optional and forbidden kinds, budgets, limits, pins."""

    stage: str
    requiredKinds: list[str]
    optionalKinds: list[str]
    forbiddenKinds: list[str]
    budgets: dict[str, Any]
    limits: list[Limit]
    orderRule: str
    pinPolicy: str
    slots: list[str]
    ext: dict[str, Any]
