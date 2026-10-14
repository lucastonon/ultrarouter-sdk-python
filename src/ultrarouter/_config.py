"""Client defaults and per-call precedence (pure helpers).

Every client-level default (``default_model`` and the ``defaults`` mapping: ``router``,
``compression``, ``call_type``, ``provider``, ``max_cost_usd``) can be overridden per call: an
explicit per-call value always wins, an omitted one falls back to the client default.

Two client-level options shape requests further:

* ``autopilot`` (``"audit"`` | ``"recommend"`` | ``"auto"``) sets the routing ``router`` mode and
  acts as a ceiling: a per-call ``router`` may lower autonomy but never raise it above the
  ceiling (the SDK clamps it; the gateway enforces the same rule).
* ``bench`` tags every request for a Bench suite through ``X-UR-Bench-*`` headers; a per-call
  ``bench=`` is sent as ``ur.bench`` in the body and wins over the headers.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal, TypedDict

__all__ = [
    "AUTOPILOT_ROUTER",
    "AutopilotMode",
    "BenchTag",
    "Defaults",
    "ResolvedBench",
    "apply_chat_defaults",
    "apply_embedding_defaults",
    "clamp_router_downgrade",
    "resolve_bench",
]

AutopilotMode = Literal["audit", "recommend", "auto"]

#: How each Autopilot intent maps onto the routing ``router`` mode.
AUTOPILOT_ROUTER: Mapping[str, str] = {
    "audit": "off",
    "recommend": "candidates",
    "auto": "auto",
}

# Autonomy rank per router mode (higher = more autonomy).
_AUTONOMY_RANK: Mapping[str, int] = {"off": 0, "candidates": 1, "auto": 2}


class BenchTag(TypedDict, total=False):
    """A structured Bench tag: the suite slug plus optional run and trace labels."""

    suite: str
    run: str
    trace: str | Callable[[], str]


class Defaults(TypedDict, total=False):
    """Client-level request defaults; each one can be overridden per call."""

    router: Literal["off", "auto", "candidates"]
    compression: str | Mapping[str, Any]
    call_type: str
    provider: Mapping[str, Any]
    max_cost_usd: float


def clamp_router_downgrade(requested: str, ceiling: str) -> str:
    """Clamp a per-call ``router`` to the Autopilot ceiling (downgrades only).

    A request asking for more autonomy than the ceiling allows gets the ceiling; an equal or
    lower request passes through unchanged. Unknown modes rank as ``off``.
    """
    req = _AUTONOMY_RANK.get(requested, 0)
    ceil = _AUTONOMY_RANK.get(ceiling, 0)
    return ceiling if req > ceil else requested


def _merge_ur(
    call_ur: Mapping[str, Any] | None, max_cost_usd: float | None
) -> dict[str, Any] | None:
    if max_cost_usd is None:
        return dict(call_ur) if call_ur is not None else None
    merged: dict[str, Any] = {"max_cost_usd": max_cost_usd}
    if call_ur:
        merged.update(call_ur)  # a per-call ur.max_cost_usd wins
    return merged


def _fold_bench(body: dict[str, Any]) -> dict[str, Any]:
    """Move a per-call top-level ``bench`` into ``ur.bench`` (where the gateway reads it)."""
    bench = body.pop("bench", None)
    if bench is None:
        return body
    ur = dict(body.get("ur") or {})
    ur["bench"] = bench  # an explicit per-call bench wins over an ur.bench already present
    body["ur"] = ur
    return body


@dataclass(frozen=True)
class ResolvedBench:
    """The resolved client-level Bench tag: static headers plus an optional trace factory."""

    suite: str
    headers: dict[str, str] = field(default_factory=dict)
    trace_factory: Callable[[], str] | None = None


def resolve_bench(
    bench: str | BenchTag | Mapping[str, Any] | None,
    env: Mapping[str, str | None],
) -> ResolvedBench | None:
    """Resolve the client-level Bench tag.

    An explicit ``bench`` wins; otherwise ``UR_BENCH`` (plus optional ``UR_BENCH_RUN`` and
    ``UR_BENCH_TRACE``) from ``env`` is used. Returns ``None`` when no suite applies. Pure: the
    environment is passed in.
    """
    tag: Mapping[str, Any]
    if bench is None:
        suite_env = (env.get("UR_BENCH") or "").strip()
        if not suite_env:
            return None
        built: dict[str, Any] = {"suite": suite_env}
        run_env = env.get("UR_BENCH_RUN")
        trace_env = env.get("UR_BENCH_TRACE")
        if run_env:
            built["run"] = run_env
        if trace_env:
            built["trace"] = trace_env
        tag = built
    elif isinstance(bench, str):
        tag = {"suite": bench}
    else:
        tag = bench
    suite = str(tag.get("suite", "")).strip()
    if not suite:
        return None
    headers = {"x-ur-bench-suite": suite}
    run = tag.get("run")
    if run:
        headers["x-ur-bench-run"] = str(run)
    trace = tag.get("trace")
    if callable(trace):
        return ResolvedBench(suite=suite, headers=headers, trace_factory=trace)
    if isinstance(trace, str) and trace:
        headers["x-ur-bench-trace"] = trace
    return ResolvedBench(suite=suite, headers=headers)


def apply_chat_defaults(
    params: Mapping[str, Any],
    default_model: str | None,
    defaults: Mapping[str, Any],
    autopilot_router: str | None = None,
) -> dict[str, Any]:
    """Build the chat request body: per-call params override client defaults.

    ``None`` values in ``params`` mean "not given". With an Autopilot ceiling, the ceiling is
    the default ``router`` and a per-call ``router`` is clamped to it; without one, a per-call
    ``router`` wins and ``defaults["router"]`` is the fallback.
    """
    body = {k: v for k, v in params.items() if v is not None}
    model = body.get("model") or default_model
    if model is not None:
        body["model"] = model
    if "router" in body:
        if autopilot_router is not None:
            body["router"] = clamp_router_downgrade(str(body["router"]), autopilot_router)
    elif autopilot_router is not None:
        body["router"] = autopilot_router
    elif defaults.get("router") is not None:
        body["router"] = defaults["router"]
    for key in ("compression", "call_type", "provider"):
        if key not in body and defaults.get(key) is not None:
            body[key] = defaults[key]
    ur = _merge_ur(body.get("ur"), defaults.get("max_cost_usd"))
    if ur is not None:
        body["ur"] = ur
    return _fold_bench(body)


def apply_embedding_defaults(
    params: Mapping[str, Any],
    default_model: str | None,
    defaults: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the embeddings body (``model``, ``call_type`` and ``max_cost_usd`` defaults)."""
    body = {k: v for k, v in params.items() if v is not None}
    model = body.get("model") or default_model
    if model is not None:
        body["model"] = model
    if "call_type" not in body and defaults.get("call_type") is not None:
        body["call_type"] = defaults["call_type"]
    ur = _merge_ur(body.get("ur"), defaults.get("max_cost_usd"))
    if ur is not None:
        body["ur"] = ur
    return _fold_bench(body)
