"""Compile: admit candidate context modules into a manifest under a contract and a profile.

Pure: no clock, environment, randomness or I/O. The same inputs always produce the same
manifest hash.

The algorithm is the same for every profile. Authority checks that only an adopting application
can make (tenant isolation, leases, editorial rights, de-duplication identity) are made by that
application's adapter *before* compile, by attaching an ``adapterRefusal`` to a candidate; the
compiler folds such refusals inline in candidate order and never reads ``ext`` for authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ._envelope import hash_envelope
from ._hash import hash_context_value
from ._manifest import ManifestEntry, scaffold_subject
from ._messages import INSTRUCTION_SLOT
from ._profile import CompatibilityProfile

__all__ = ["AdapterRefusal", "CompileResult", "ContextCandidate", "compile"]

# A parent adapter's authority pre-refusal: {"code", "message", "reason"?, "detail"?}.
AdapterRefusal = dict[str, Any]
# One candidate offered to compile:
# {"module": Module, "slot"?: str, "adapterRefusal"?: AdapterRefusal}.
ContextCandidate = dict[str, Any]

_DEFAULT_REFERENCE_SLOT = "reference"


@dataclass(frozen=True)
class CompileResult:
    """The result of :func:`compile`: ``ok``, the ``manifest`` (or ``None``) and ``refusals``."""

    ok: bool
    manifest: dict[str, Any] | None
    refusals: list[dict[str, Any]]


def _parse_instant(value: str) -> float | None:
    try:
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        return datetime.fromisoformat(normalized).timestamp()
    except (ValueError, TypeError):
        return None


def _instant_cmp(left: str, right: str) -> float | None:
    a = _parse_instant(left)
    b = _parse_instant(right)
    if a is None or b is None:
        return None
    return a - b


def _facet_matches_release(facet: Any, release: Any) -> bool:
    if facet is None or release is None:
        return False
    facet_list = facet if isinstance(facet, list) else [facet]
    release_list = release if isinstance(release, list) else [release]
    return any(value in release_list for value in facet_list)


def _resolve_slot(candidate: ContextCandidate) -> str:
    module = candidate["module"]
    explicit = candidate.get("slot")
    if explicit is None:
        explicit = module.get("slotHint")
    if explicit is not None:
        return str(explicit)
    return _DEFAULT_REFERENCE_SLOT if module["trustClass"] == "untrusted" else INSTRUCTION_SLOT


def _availability_refusal(
    module: dict[str, Any], envelope: dict[str, Any], profile: CompatibilityProfile
) -> dict[str, Any] | None:
    availability = module["availability"]
    frm = availability.get("from")
    to = availability.get("to")
    if frm is None:
        if profile.availability and profile.availability.get("refuseUndated"):
            return {
                "reason": "AVAILABILITY_REFUSED",
                "detail": "unknown",
                "message": (
                    "the module carries no availability and cannot be dated against the cutoff"
                ),
            }
    else:
        cmp = _instant_cmp(frm, envelope["asOf"])
        if cmp is not None and cmp > 0:
            return {
                "reason": "AVAILABILITY_REFUSED",
                "detail": "after_cutoff",
                "message": "the module became available after the knowledge cutoff",
            }
    if to is not None:
        cmp = _instant_cmp(to, envelope["asOf"])
        if cmp is not None and cmp < 0:
            return {
                "reason": "AVAILABILITY_REFUSED",
                "detail": "expired",
                "message": "the module expired before the knowledge cutoff",
            }
    return None


def _eligibility_finding(
    module: dict[str, Any],
    slot: str,
    envelope: dict[str, Any],
    contract: dict[str, Any],
    profile: CompatibilityProfile,
) -> dict[str, Any] | None:
    if module["kind"] in contract["forbiddenKinds"]:
        return {
            "reason": "FORBIDDEN_KIND",
            "message": f"kind {module['kind']} is forbidden for this stage",
        }
    if (
        profile.authoritative_kinds is not None
        and module["kind"] in profile.authoritative_kinds
        and module["trustClass"] != "authoritative"
    ):
        return {
            "reason": "AUTHORITATIVE_CONTEXT_UNTRUSTED",
            "message": f"kind {module['kind']} must be authoritative",
        }
    binding = profile.release_binding
    if (
        binding
        and module["kind"] in binding["kinds"]
        and not _facet_matches_release(
            module["facets"].get(binding["facet"]),
            envelope["releases"].get(binding["releaseKey"]),
        )
    ):
        return {
            "reason": "POLICY_RELEASE_MISMATCH",
            "message": (
                f"kind {module['kind']} is not bound to a pinned {binding['releaseKey']} release"
            ),
        }
    availability_finding = _availability_refusal(module, envelope, profile)
    if availability_finding:
        return availability_finding
    if module["trustClass"] == "untrusted" and slot == INSTRUCTION_SLOT:
        return {
            "reason": "UNTRUSTED_IN_INSTRUCTION_SLOT",
            "message": "untrusted content may not be placed in an instruction slot",
        }
    return None


def _undated_is_fatal(
    finding: dict[str, Any], envelope: dict[str, Any], profile: CompatibilityProfile
) -> bool:
    return finding.get("detail") == "unknown" and (
        envelope["mode"] in (profile.availability or {}).get("strictModes", [])
    )


def _facet_count_key(limit: dict[str, Any]) -> str:
    kind = limit.get("kind", "") or ""
    facet = limit.get("facet", "") or ""
    facet_value = limit.get("facetValue", "") or ""
    return f"{kind}|{facet}|{facet_value}"


def _limit_matches(limit: dict[str, Any], module: dict[str, Any]) -> bool:
    if limit.get("kind") is not None and limit["kind"] != module["kind"]:
        return False
    if limit.get("facet") is not None:
        value = module["facets"].get(limit["facet"])
        if value is None:
            return False
        if limit.get("facetValue") is not None:
            value_list = value if isinstance(value, list) else [value]
            if limit["facetValue"] not in value_list:
                return False
    return True


def _entry_shape(admitted: dict[str, Any]) -> ManifestEntry:
    module = admitted["module"]
    return {
        "moduleId": module["id"],
        "version": module["version"],
        "kind": module["kind"],
        "memoryClass": module["memoryClass"],
        "trustClass": module["trustClass"],
        "privacyClass": module["privacyClass"],
        "contentHash": module["contentHash"],
        "order": admitted["admissionIndex"],
        "mandatory": admitted["mandatory"],
        "tokenEstimate": module["tokenEstimate"],
        "slot": admitted["slot"],
    }


def _order_entries(
    admitted: list[dict[str, Any]], profile: CompatibilityProfile
) -> list[dict[str, Any]]:
    if profile.order_rule == "selection":
        return sorted(admitted, key=lambda entry: entry["admissionIndex"])
    rank = profile.volatility_rank or (lambda _entry: 0)
    return sorted(admitted, key=lambda entry: (rank(_entry_shape(entry)), entry["admissionIndex"]))


def compile(
    envelope: dict[str, Any],
    contract: dict[str, Any],
    candidates: list[ContextCandidate],
    profile: CompatibilityProfile,
) -> CompileResult:
    """Admit ``candidates`` into a manifest under ``contract`` and ``profile`` (pure).

    Returns a :class:`CompileResult`: ``ok`` and the ``manifest`` when the run is admissible, and
    every refusal (non-fatal refusals are also listed in ``manifest["refused"]``). A fatal refusal
    (stage mismatch, a missing or mismatched pin, a required kind not covered, ...) makes ``ok``
    false and ``manifest`` ``None``. Never raises on an inadmissible module.

    Args:
        envelope: The execution identity (see :class:`Envelope`).
        contract: What the stage may see (see :class:`Contract`).
        candidates: ``[{"module": Module, "slot"?: str, "adapterRefusal"?: {...}}, ...]``.
        profile: The compatibility profile (``ULTRAROUTER_PROFILE`` by default).
    """
    refusals: list[dict[str, Any]] = []
    state = {"fatal": False}

    def refuse(reason: str, *, message: str, fatal: bool, **opts: Any) -> None:
        refusal: dict[str, Any] = {
            "reason": reason,
            "code": profile.refusals.encode(reason, opts.get("detail")),
            "message": message,
            "fatal": fatal,
        }
        for key in ("detail", "moduleId", "kind", "path"):
            if opts.get(key) is not None:
                refusal[key] = opts[key]
        refusals.append(refusal)
        if fatal:
            state["fatal"] = True

    def refuse_adapter(
        adapter: AdapterRefusal,
        *,
        fatal: bool,
        moduleId: str | None = None,
        kind: str | None = None,
    ) -> None:
        refusal: dict[str, Any] = {
            "reason": adapter.get("reason") or adapter["code"],
            "code": adapter["code"],
            "message": adapter["message"],
            "fatal": fatal,
        }
        if adapter.get("detail") is not None:
            refusal["detail"] = adapter["detail"]
        if moduleId is not None:
            refusal["moduleId"] = moduleId
        if kind is not None:
            refusal["kind"] = kind
        refusals.append(refusal)
        if fatal:
            state["fatal"] = True

    # 1. Stage / planner-bound validation.
    if contract["stage"] != envelope["stage"]:
        refuse(
            "STAGE_CONTRACT_MISMATCH",
            message="the contract stage does not match the execution stage",
            fatal=True,
            path="contract.stage",
        )
    for key in ("plannerDepth", "plannerPass", "toolCalls"):
        ceiling = contract.get("budgets", {}).get(key)
        requested = envelope.get("budgets", {}).get(key)
        if ceiling is not None and requested is not None and requested > ceiling:
            refuse(
                "PLANNER_BOUND_EXCEEDED",
                message=f"planning {key} {requested} exceeds the contract ceiling {ceiling}",
                fatal=True,
                detail=key,
                path=f"envelope.budgets.{key}",
            )

    by_id = {candidate["module"]["id"]: candidate for candidate in candidates}
    allowed_kinds = set(contract["requiredKinds"]) | set(contract["optionalKinds"])

    # 2. Pins by exact id + kind + hash (only under a strict pin policy).
    pinned_ids: set[str] = set()
    pins = envelope.get("pins", [])
    if contract["pinPolicy"] == "strict":
        required_kinds_pinned: set[str] = set()
        for pin in pins:
            pinned_ids.add(pin["id"])
            required_kinds_pinned.add(pin["kind"])
            if pin["kind"] not in allowed_kinds:
                refuse(
                    "PINNED_CONTEXT_NOT_REQUESTED",
                    message=(
                        f"pin {pin['id']} is a kind ({pin['kind']}) "
                        "the contract neither requires nor allows"
                    ),
                    fatal=True,
                    moduleId=pin["id"],
                    kind=pin["kind"],
                )
                continue
            candidate = by_id.get(pin["id"])
            if candidate is None:
                refuse(
                    "REQUIRED_CONTEXT_MISSING",
                    message=f"pinned module {pin['id']} could not be resolved",
                    fatal=True,
                    moduleId=pin["id"],
                    kind=pin["kind"],
                )
                continue
            module = candidate["module"]
            if module["kind"] != pin["kind"] or module["contentHash"] != pin["contentHash"]:
                refuse(
                    "PINNED_CONTEXT_MISMATCH",
                    message=(
                        f"pinned module {pin['id']} does not match the frozen kind and content hash"
                    ),
                    fatal=True,
                    moduleId=pin["id"],
                    kind=pin["kind"],
                )
        # 3. Required kinds present — each must be covered by a pin.
        for kind in contract["requiredKinds"]:
            if kind not in required_kinds_pinned:
                refuse(
                    "REQUIRED_CONTEXT_NOT_PINNED",
                    message=f"required kind {kind} has no pin",
                    fatal=True,
                    kind=kind,
                )

    admitted: list[dict[str, Any]] = []
    admission = {"index": 0}

    def admit(module: dict[str, Any], slot: str, mandatory: bool) -> None:
        admitted.append(
            {
                "module": module,
                "slot": slot,
                "mandatory": mandatory,
                "admissionIndex": admission["index"],
            }
        )
        admission["index"] += 1

    # Mandatory pass.
    for pin in pins if contract["pinPolicy"] == "strict" else []:
        candidate = by_id.get(pin["id"])
        if (
            candidate is None
            or candidate["module"]["kind"] != pin["kind"]
            or candidate["module"]["contentHash"] != pin["contentHash"]
        ):
            continue
        if pin["kind"] not in allowed_kinds:
            continue
        slot = _resolve_slot(candidate)
        if candidate.get("adapterRefusal"):
            refuse_adapter(
                candidate["adapterRefusal"], fatal=True, moduleId=pin["id"], kind=pin["kind"]
            )
            continue
        finding = _eligibility_finding(candidate["module"], slot, envelope, contract, profile)
        if finding:
            refuse(
                finding["reason"],
                message=finding["message"],
                fatal=True,
                detail=finding.get("detail"),
                moduleId=pin["id"],
                kind=pin["kind"],
            )
            continue
        admit(candidate["module"], slot, True)

    # Optional pass.
    limits: list[dict[str, Any]] = [*profile.limits, *contract.get("limits", [])]
    limit_counts: dict[str, int] = {}
    kind_counts: dict[str, int] = {}
    optional_considered = 0
    budget = profile.budget
    tentative_optional: list[dict[str, Any]] = []

    for candidate in candidates:
        module = candidate["module"]
        if module["id"] in pinned_ids:
            continue
        slot = _resolve_slot(candidate)

        if candidate.get("adapterRefusal"):
            refuse_adapter(
                candidate["adapterRefusal"], fatal=False, moduleId=module["id"], kind=module["kind"]
            )
            continue
        if profile.result_ceiling is not None and optional_considered >= profile.result_ceiling:
            refuse(
                "LIMIT_EXCEEDED",
                message=f"optional result ceiling {profile.result_ceiling} reached",
                fatal=False,
                detail="result_ceiling",
                moduleId=module["id"],
                kind=module["kind"],
            )
            continue
        optional_considered += 1
        if module["kind"] not in allowed_kinds:
            refuse(
                "FORBIDDEN_KIND",
                message=f"kind {module['kind']} is not optional for this stage",
                fatal=False,
                detail="not_optional",
                moduleId=module["id"],
                kind=module["kind"],
            )
            continue
        finding = _eligibility_finding(module, slot, envelope, contract, profile)
        if finding:
            refuse(
                finding["reason"],
                message=finding["message"],
                fatal=_undated_is_fatal(finding, envelope, profile),
                detail=finding.get("detail"),
                moduleId=module["id"],
                kind=module["kind"],
            )
            continue
        matched_limit = next((limit for limit in limits if _limit_matches(limit, module)), None)
        if matched_limit:
            key = _facet_count_key(matched_limit)
            count = limit_counts.get(key, 0)
            if count >= matched_limit["max"]:
                label = (
                    matched_limit.get("label")
                    or matched_limit.get("kind")
                    or matched_limit.get("facet")
                    or "limit"
                )
                refuse(
                    "LIMIT_EXCEEDED",
                    message=f"{label} cap {matched_limit['max']} reached",
                    fatal=False,
                    detail="limit",
                    moduleId=module["id"],
                    kind=module["kind"],
                )
                continue
            limit_counts[key] = count + 1
        elif profile.default_kind_limit is not None:
            count = kind_counts.get(module["kind"], 0)
            if count >= profile.default_kind_limit:
                refuse(
                    "LIMIT_EXCEEDED",
                    message=(
                        f"default kind cap {profile.default_kind_limit} "
                        f"reached for {module['kind']}"
                    ),
                    fatal=False,
                    detail="default_kind_limit",
                    moduleId=module["id"],
                    kind=module["kind"],
                )
                continue
            kind_counts[module["kind"]] = count + 1

        # 6. Budget admission.
        if budget.kind == "count":
            limit = budget.limit(envelope, contract)
            admitted_count = len(admitted) + len(tentative_optional)
            if limit is not None and admitted_count >= limit:
                refuse(
                    "BUDGET_EXCEEDED",
                    message=f"selection budget {limit} reached",
                    fatal=False,
                    detail="count",
                    moduleId=module["id"],
                    kind=module["kind"],
                )
                continue
            admit(module, slot, False)
        else:
            tentative_optional.append(
                {
                    "module": module,
                    "slot": slot,
                    "mandatory": False,
                    "admissionIndex": admission["index"],
                }
            )
            admission["index"] += 1

    # 6 (tokens). Shed by keep-priority to fit the token ceiling; mandatory never shed.
    if budget.kind == "tokens":
        limit = budget.limit(envelope, contract)
        admitted_tokens = sum(entry["module"]["tokenEstimate"] for entry in admitted)
        keep_priority = budget.keep_priority or (lambda _entry: 0)
        keep_order = sorted(
            tentative_optional,
            key=lambda entry: (-keep_priority(_entry_shape(entry)), entry["admissionIndex"]),
        )
        kept: set[int] = set()
        shed_mode = budget.shed_mode
        shedding = False
        for candidate in keep_order:
            fits = limit is None or admitted_tokens + candidate["module"]["tokenEstimate"] <= limit
            if not shedding and fits:
                kept.add(candidate["admissionIndex"])
                admitted_tokens += candidate["module"]["tokenEstimate"]
            else:
                if shed_mode == "prefix":
                    shedding = True
                refuse(
                    "BUDGET_EXCEEDED",
                    message=(
                        "optional module shed to preserve higher-priority context "
                        "within the token budget"
                    ),
                    fatal=False,
                    detail="tokens",
                    moduleId=candidate["module"]["id"],
                    kind=candidate["module"]["kind"],
                )
        for candidate in tentative_optional:
            if candidate["admissionIndex"] in kept:
                admitted.append(candidate)

    # 3 (post-admission). Each required kind must be covered by an admitted MANDATORY module.
    admitted_mandatory_kinds = {entry["module"]["kind"] for entry in admitted if entry["mandatory"]}
    for kind in contract["requiredKinds"]:
        if kind not in admitted_mandatory_kinds:
            refuse(
                "REQUIRED_CONTEXT_MISSING",
                message=f"required kind {kind} is not covered by an admitted module",
                fatal=True,
                detail="kind",
                kind=kind,
            )

    if state["fatal"]:
        return CompileResult(ok=False, manifest=None, refusals=refusals)

    # 7. Ordering.
    ordered = _order_entries(admitted, profile)

    entries: list[dict[str, Any]] = []
    for order, entry in enumerate(ordered):
        module = entry["module"]
        manifest_entry: dict[str, Any] = {
            "moduleId": module["id"],
            "version": module["version"],
            "kind": module["kind"],
            "memoryClass": module["memoryClass"],
            "trustClass": module["trustClass"],
            "privacyClass": module["privacyClass"],
            "contentHash": module["contentHash"],
            "order": order,
            "mandatory": entry["mandatory"],
            "tokenEstimate": module["tokenEstimate"],
            "slot": entry["slot"],
        }
        if module.get("ext") is not None:
            manifest_entry["ext"] = module["ext"]
        entries.append(manifest_entry)

    tokens_admitted = sum(entry["tokenEstimate"] for entry in entries)
    token_limit = budget.limit(envelope, contract) if budget.kind == "tokens" else None
    envelope_hash = (
        profile.hash_envelope(envelope)
        if profile.hash_envelope is not None
        else hash_envelope(envelope)
    )
    scaffold_hash = hash_context_value(scaffold_subject(entries))

    encoder_input: dict[str, Any] = {
        "envelopeId": envelope["id"],
        "stage": envelope["stage"],
        "entries": entries,
        "refused": refusals,
        "budgets": {
            "tokensAdmitted": tokens_admitted,
            "tokenLimit": token_limit,
            "admitted": len(entries),
            "refused": len(refusals),
        },
        "envelopeHash": envelope_hash,
        "scaffoldHash": scaffold_hash,
    }
    encoded = profile.manifest_encoder(encoder_input, {"envelope": envelope, "contract": contract})

    manifest = dict(encoder_input)
    manifest["manifestHash"] = encoded["hash"]

    return CompileResult(ok=True, manifest=manifest, refusals=refusals)
