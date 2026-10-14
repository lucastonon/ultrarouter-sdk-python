# Context runtime (`ultrarouter.context`)

`ultrarouter.context` makes the context a model call sees explicit and hashable. It is a pure
library: no network, clock, environment or randomness, and no dependencies beyond the standard
library. Its manifest bytes and hashes are byte-identical to the TypeScript SDK's runtime and to
what the gateway verifies, which the test suite checks against shared fixtures.

You can adopt it in one file and leave in one file: `to_messages(from_messages(m))` always
returns `m` exactly, and nothing in the gateway requires a manifest.

## Concepts

| Term | Meaning |
| --- | --- |
| `Module` | a typed, versioned, content-hashed unit of context (a policy, a fact, an example) |
| `Envelope` | the identity of one execution: tenant, stage, mode, knowledge cutoff (`asOf`), budgets, pins |
| `Contract` | what a stage may see: required / optional / forbidden kinds, budgets, limits, pin policy |
| `CompatibilityProfile` | how the compiler orders, budgets, refuses and hashes (`ULTRAROUTER_PROFILE` is the default) |
| `Manifest` | the hashable record of what one execution was allowed to see, and what was refused and why |

Structures are plain dicts (`TypedDict`s with camelCase keys) so they serialize to JSON as-is.

## Lift a conversation and leave again

```python
import json

from ultrarouter.context import from_messages, to_messages, to_wire

messages = [
    {"role": "system", "content": "You are a careful assistant."},
    {"role": "user", "content": "<document>Refunds take 14 days.</document>"},
    {"role": "user", "content": "How long do refunds take?"},
]

lifted = from_messages(messages)
for label in lifted["labels"]:
    print(label["messageIndex"], label["kind"], label["eligible"])
# 0 system_instructions False / 1 reference_context True / 2 user_question False

manifest = lifted["manifest"]
print(manifest["manifestHash"])
assert to_messages(json.loads(json.dumps(manifest))) == messages  # the exit guarantee

wire = to_wire(manifest)  # hashes and ranges only, never message text
print(sorted(wire))
```

Segment kinds: `system_instructions`, `user_question`, `reference_context`, `few_shot_examples`,
`tool_schemas`, `tool_results`, `history`, `output_contract`. Pass `ur.segments`-style hints as the
second argument to override the heuristic for a message, optionally for a character span:
`from_messages(messages, [{"index": 1, "kind": "reference_context"}])`.

The wire form can be sent as `ur.manifest` on a chat request; the gateway verifies every hash
against the bytes it receives before doing anything else, and refuses a mismatch
(`ManifestMismatchError`) or a malformed manifest (`ManifestInvalidError`).

## Compile modules under a contract

```python
from ultrarouter.context import ULTRAROUTER_PROFILE, compile, render


def module(id_: str, kind: str, memory: str, trust: str, tokens: int) -> dict:
    return {
        "id": id_,
        "version": "1",
        "kind": kind,
        "memoryClass": memory,  # working, episodic, semantic, procedural
        "trustClass": trust,  # authoritative, approved_derived, untrusted
        "privacyClass": "workspace_private",
        "availability": {"from": None, "to": None},
        "contentHash": f"sha256:{id_}",
        "tokenEstimate": tokens,
        "facets": {},
    }


envelope = {
    "id": "exec-1",
    "tenant": "acme",
    "stage": "answer",
    "mode": "live",
    "asOf": "2026-04-01T00:00:00.000Z",
    "cutoffs": {},
    "budgets": {"tokens": 100},
    "seed": "seed-1",
    "pins": [],
    "releases": {},
    "permissionEpoch": "epoch-1",
}
contract = {
    "stage": "answer",
    "requiredKinds": [],
    "optionalKinds": ["policy", "fact", "history"],
    "forbiddenKinds": ["scratchpad"],
    "budgets": {"tokens": 30},
    "limits": [],
    "pinPolicy": "none",
    "slots": ["instruction", "reference", "exemplar"],
}
candidates = [
    {"module": module("refund-policy", "policy", "procedural", "authoritative", 12)},
    {"module": module("order-facts", "fact", "semantic", "approved_derived", 10)},
    {"module": module("old-thread", "history", "episodic", "approved_derived", 20)},
    {"module": module("notes", "scratchpad", "working", "approved_derived", 5)},
]

result = compile(envelope, contract, candidates, ULTRAROUTER_PROFILE)
print(result.ok)
print(
    [entry["moduleId"] for entry in result.manifest["entries"]]
)  # admitted, ordered stable to volatile
print([(r["code"], r.get("moduleId")) for r in result.refusals])  # why the others were refused

messages_out = render(
    result.manifest,
    {
        "refund-policy": "Refunds are issued within 14 days.",
        "order-facts": "Order 1001 shipped Monday.",
    },
)
print(messages_out)
```

`compile` never raises on an inadmissible module; it records a typed refusal
(`BUDGET_EXCEEDED`, `FORBIDDEN_KIND`, `AVAILABILITY_REFUSED`, `UNTRUSTED_IN_INSTRUCTION_SLOT`,
`REQUIRED_CONTEXT_MISSING`, ...). A fatal refusal (for example a required kind missing, or a pin
that does not match) makes `result.ok` false and `result.manifest` `None`.

Under the default profile, admitted modules are ordered stable to volatile (procedural, semantic,
working, episodic), and a token budget sheds the most volatile optional modules first; mandatory
(pinned) modules are never shed. `render` puts instruction-slot modules into one system message
and untrusted reference material into one fenced user message that tells the model not to follow
instructions inside it.

## Custom profiles

A profile parameterises the one compiler: ordering (`selection` keeps candidate order,
`volatility` sorts stable to volatile), the budget strategy (`tokens` or `count`), refusal-code
mapping, availability policy, release bindings, limits and the manifest encoder.

```python
from ultrarouter.context import (
    BudgetStrategy,
    CompatibilityProfile,
    default_render_serializer,
    define_kinds,
    define_memory_classes,
    define_refusals,
    ultrarouter_manifest_encoder,
)

count_profile = CompatibilityProfile(
    name="first-two",
    order_rule="selection",
    memory_classes=define_memory_classes(),
    kinds=define_kinds(["policy", "fact", "history"]),
    refusals=define_refusals(
        ["TOO_MANY"], lambda reason, detail: "TOO_MANY" if reason == "BUDGET_EXCEEDED" else None
    ),
    limits=[],
    budget=BudgetStrategy(kind="count", limit=lambda env, con: 2),
    serializer=default_render_serializer,
    manifest_encoder=ultrarouter_manifest_encoder,
)
picked = compile(envelope, {**contract, "forbiddenKinds": []}, candidates[:3], count_profile)
print([e["moduleId"] for e in picked.manifest["entries"]], [r["code"] for r in picked.refusals])
```

## Also exported here

- [`learned_placement_index` and `apply_learned_context`](learned-placement.md)
- [`render_prompt` and `render_hosted_prompt_result`](prompt-render.md)
- `canonical_json`, `sha256_hex`, `hash_context_value`: the hashing primitives (keys sorted,
  JavaScript number and string formatting; every key is data, including names such as
  `__proto__` or `constructor`, at any depth, so two different values never share a hash)
- `segment`, `pin_never_touch_spans`: the segmentation building blocks

## Not yet available in Python

The TypeScript SDK's context runtime also includes a standard-operating-procedure compiler, a
prompt-surface linter, native delivery planning and portable knowledge packs. They are not part of
this Python release.
