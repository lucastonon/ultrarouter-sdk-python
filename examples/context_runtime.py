"""Lift a conversation into a manifest, compile modules under a contract, and exit again.

Runs offline: the context runtime needs no gateway.
Run: python examples/context_runtime.py
"""

from __future__ import annotations

import json
from typing import Any

from ultrarouter.context import (
    ULTRAROUTER_PROFILE,
    compile,
    from_messages,
    render,
    to_messages,
    to_wire,
)


def module(id_: str, kind: str, memory: str, trust: str, tokens: int) -> dict[str, Any]:
    """Build a context module description."""
    return {
        "id": id_,
        "version": "1",
        "kind": kind,
        "memoryClass": memory,
        "trustClass": trust,
        "privacyClass": "workspace_private",
        "availability": {"from": None, "to": None},
        "contentHash": f"sha256:{id_}",
        "tokenEstimate": tokens,
        "facets": {},
    }


def main() -> None:
    messages = [
        {"role": "system", "content": "Answer from the reference only."},
        {"role": "user", "content": "<document>Refunds take 14 days.</document>"},
        {"role": "user", "content": "How long do refunds take?"},
    ]
    lifted = from_messages(messages)
    print("labels:", [label["kind"] for label in lifted["labels"]])
    print("exit is exact:", to_messages(json.loads(json.dumps(lifted["manifest"]))) == messages)
    print("wire keys:", sorted(to_wire(lifted["manifest"])))

    envelope = {
        "id": "exec-1",
        "tenant": "acme",
        "stage": "answer",
        "mode": "live",
        "asOf": "2026-04-01T00:00:00.000Z",
        "cutoffs": {},
        "budgets": {},
        "seed": "seed-1",
        "pins": [],
        "releases": {},
        "permissionEpoch": "epoch-1",
    }
    contract = {
        "stage": "answer",
        "requiredKinds": [],
        "optionalKinds": ["policy", "history"],
        "forbiddenKinds": [],
        "budgets": {"tokens": 25},
        "limits": [],
        "pinPolicy": "none",
        "slots": ["instruction", "reference", "exemplar"],
    }
    result = compile(
        envelope,
        contract,
        [
            {"module": module("policy", "policy", "procedural", "authoritative", 15)},
            {"module": module("thread", "history", "episodic", "approved_derived", 20)},
        ],
        ULTRAROUTER_PROFILE,
    )
    assert result.manifest is not None
    print("admitted:", [e["moduleId"] for e in result.manifest["entries"]])
    print("refused:", [(r["code"], r.get("moduleId")) for r in result.refusals])
    print(render(result.manifest, {"policy": "Refunds are issued within 14 days."}))


if __name__ == "__main__":
    main()
