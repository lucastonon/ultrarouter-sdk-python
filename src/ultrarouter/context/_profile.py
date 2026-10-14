"""Compatibility profiles: the knobs that parameterise the one compiler.

A profile sets the ``order_rule`` (``selection`` keeps candidate order; ``volatility`` sorts
stable to volatile, the ultrarouter default), the memory-class and kind vocabularies, the
refusal-code registry, profile-level limits, the budget strategy, the render serializer and the
``manifest_encoder`` (the bytes the manifest hash is computed over). A profile never grants
authority.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ._hash import canonical_json, sha256_hex
from ._kinds import KindSet, define_kinds
from ._manifest import ManifestEntry
from ._memory import MemoryClassSet, define_memory_classes
from ._messages import RenderSerializer, default_render_serializer
from ._refusals import RefusalRegistry, define_refusals

__all__ = [
    "ULTRAROUTER_PROFILE",
    "BudgetStrategy",
    "CompatibilityProfile",
    "EncodedManifest",
    "ManifestEncoder",
    "default_volatility_rank",
    "encode_ultrarouter_manifest",
    "ultrarouter_manifest_encoder",
]

# ``{"bytes": str, "hash": str}`` — the profile's manifest serialization + its digest.
EncodedManifest = dict[str, str]
# ``(manifest_input, ctx) -> EncodedManifest`` where ctx = {"envelope":.., "contract":..}.
ManifestEncoder = Callable[[dict[str, Any], dict[str, Any]], EncodedManifest]


@dataclass(frozen=True)
class BudgetStrategy:
    """How the profile admits within budget (shed whole modules, never truncate).

    ``kind='tokens'``: a token ceiling with a keep-priority (shed lowest-keep first).
    ``kind='count'``: a maximum pin count checked inline in selection order.
    ``limit(envelope, contract) -> int | None``
    (a ``None`` limit is unbounded).
    """

    kind: str  # 'tokens' | 'count'
    limit: Callable[[dict[str, Any], dict[str, Any]], int | None]
    keep_priority: Callable[[ManifestEntry], int] | None = None
    shed_mode: str = "prefix"  # 'prefix' (monotone) | 'greedy'


@dataclass(frozen=True)
class CompatibilityProfile:
    name: str
    order_rule: str  # 'selection' | 'volatility'
    memory_classes: MemoryClassSet
    kinds: KindSet
    refusals: RefusalRegistry
    limits: list[dict[str, Any]]
    budget: BudgetStrategy
    serializer: RenderSerializer
    manifest_encoder: ManifestEncoder
    hash_envelope: Callable[[dict[str, Any]], str] | None = None
    volatility_rank: Callable[[ManifestEntry], int] | None = None
    authoritative_kinds: tuple[str, ...] | None = None
    release_binding: dict[str, Any] | None = None
    availability: dict[str, Any] | None = None
    default_kind_limit: int | None = None
    result_ceiling: int | None = None


def default_volatility_rank(entry: ManifestEntry) -> int:
    """Stable (procedural) first, volatile (episodic) last; unknown classes rank in the middle."""
    return {"procedural": 0, "semantic": 1, "working": 2, "episodic": 3}.get(
        entry["memoryClass"], 2
    )


def _default_keep_priority(entry: ManifestEntry) -> int:
    """Shed the most volatile first (episodic), keep the most stable last (procedural)."""
    return 3 - default_volatility_rank(entry)


def encode_ultrarouter_manifest(manifest: dict[str, Any]) -> EncodedManifest:
    """The ultrarouter-default manifest bytes: the repo's canonical JSON over a stable,
    bodies-free subject. Two structurally-equal manifests encode identically. Takes no ``ctx``
    (the default reads only the core manifest) so the lift path can reuse it."""
    subject: dict[str, Any] = {
        "envelopeId": manifest["envelopeId"],
        "stage": manifest["stage"],
        "envelopeHash": manifest["envelopeHash"],
        "scaffoldHash": manifest["scaffoldHash"],
    }
    if manifest.get("nativeDelivery") is not None:
        subject["nativeDelivery"] = manifest["nativeDelivery"]
    subject["budgets"] = manifest["budgets"]
    subject["entries"] = [
        {
            "moduleId": entry["moduleId"],
            "version": entry["version"],
            "kind": entry["kind"],
            "memoryClass": entry["memoryClass"],
            "trustClass": entry["trustClass"],
            "privacyClass": entry["privacyClass"],
            "contentHash": entry["contentHash"],
            "order": entry["order"],
            "mandatory": entry["mandatory"],
            "tokenEstimate": entry["tokenEstimate"],
            "slot": entry["slot"],
            "range": entry.get("range") if entry.get("range") is not None else None,
            "ext": entry.get("ext") if entry.get("ext") is not None else None,
        }
        for entry in manifest["entries"]
    ]
    subject["refused"] = [
        {
            "reason": refusal["reason"],
            "code": refusal["code"],
            "moduleId": refusal.get("moduleId") if refusal.get("moduleId") is not None else None,
            "kind": refusal.get("kind") if refusal.get("kind") is not None else None,
            "detail": refusal.get("detail") if refusal.get("detail") is not None else None,
            "path": refusal.get("path") if refusal.get("path") is not None else None,
            "fatal": refusal["fatal"],
        }
        for refusal in manifest["refused"]
    ]
    subject["ext"] = manifest.get("ext") if manifest.get("ext") is not None else None
    encoded = canonical_json(subject)
    return {"bytes": encoded, "hash": sha256_hex(encoded)}


def ultrarouter_manifest_encoder(manifest: dict[str, Any], _ctx: dict[str, Any]) -> EncodedManifest:
    """The ultrarouter-default manifest encoder (profile form)."""
    return encode_ultrarouter_manifest(manifest)


def _default_token_limit(envelope: dict[str, Any], contract: dict[str, Any]) -> int | None:
    contract_tokens: int | None = contract.get("budgets", {}).get("tokens")
    if contract_tokens is not None:
        return contract_tokens
    envelope_tokens: int | None = envelope.get("budgets", {}).get("tokens")
    return envelope_tokens


ULTRAROUTER_PROFILE = CompatibilityProfile(
    name="ultrarouter",
    order_rule="volatility",
    memory_classes=define_memory_classes(),
    kinds=define_kinds([]),
    refusals=define_refusals(),
    limits=[],
    budget=BudgetStrategy(
        kind="tokens", limit=_default_token_limit, keep_priority=_default_keep_priority
    ),
    serializer=default_render_serializer,
    manifest_encoder=ultrarouter_manifest_encoder,
    volatility_rank=default_volatility_rank,
)
