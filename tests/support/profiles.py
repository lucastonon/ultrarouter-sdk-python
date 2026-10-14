"""The custom ``selection_count`` compatibility profile used by the compile parity goldens.

It mirrors ``SELECTION_COUNT_PROFILE`` in ``scripts/gen_parity_goldens.mjs`` field for field:
selection order, a count budget, a refusal-code mapping, an availability policy, an
authoritative kind, a release binding, a profile limit, a default kind limit and a result ceiling.
"""

from __future__ import annotations

from typing import Any

from ultrarouter.context import (
    BudgetStrategy,
    CompatibilityProfile,
    default_render_serializer,
    define_kinds,
    define_memory_classes,
    define_refusals,
    ultrarouter_manifest_encoder,
)


def _map(reason: str, detail: str | None) -> str | None:
    if reason == "BUDGET_EXCEEDED":
        return "ACME_TOO_MANY"
    if reason == "AVAILABILITY_REFUSED" and detail == "unknown":
        return "ACME_UNDATED"
    return None


def _count_limit(envelope: dict[str, Any], contract: dict[str, Any]) -> int | None:
    value = contract.get("budgets", {}).get("tokens")
    if value is None:
        value = envelope.get("budgets", {}).get("tokens")
    return value


SELECTION_COUNT_PROFILE = CompatibilityProfile(
    name="selection_count",
    order_rule="selection",
    memory_classes=define_memory_classes(["archival"]),
    kinds=define_kinds(["policy", "fact", "note", "example"]),
    refusals=define_refusals(["ACME_TOO_MANY", "ACME_UNDATED"], _map),
    limits=[{"kind": "example", "max": 1, "label": "one example"}],
    budget=BudgetStrategy(kind="count", limit=_count_limit),
    serializer=default_render_serializer,
    manifest_encoder=ultrarouter_manifest_encoder,
    authoritative_kinds=("policy",),
    release_binding={"kinds": ["policy"], "facet": "release", "releaseKey": "policy"},
    availability={"refuseUndated": True, "strictModes": ["audit"]},
    default_kind_limit=2,
    result_ceiling=6,
)
