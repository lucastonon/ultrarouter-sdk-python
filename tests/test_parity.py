"""Cross-language parity: the Python SDK reproduces the TypeScript reference outputs.

The goldens in ``tests/fixtures/parity/goldens/`` were produced by running the synthetic inputs in
``tests/fixtures/parity/inputs/`` through the TypeScript SDK (``scripts/gen_parity_goldens.mjs``).
Every comparison here is exact: manifest bytes, hashes, indexes, lengths and rendered text.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from profiles import SELECTION_COUNT_PROFILE

from ultrarouter import (
    apply_learned_context,
    diff_stats,
    learned_placement_index,
    render_hosted_prompt_result,
)
from ultrarouter.context import (
    ULTRAROUTER_PROFILE,
    canonical_json,
    compile,
    from_messages,
    hash_context_value,
    render,
    to_messages,
    to_wire,
)

PARITY = Path(__file__).resolve().parent / "fixtures" / "parity"
PROFILES = {"ultrarouter": ULTRAROUTER_PROFILE, "selection_count": SELECTION_COUNT_PROFILE}


def _load(name: str) -> tuple[dict[str, Any], list[Any]]:
    golden = json.loads((PARITY / "goldens" / f"{name}.json").read_text("utf-8"))
    inputs = json.loads((PARITY / golden["input_file"]).read_text("utf-8"))
    return inputs, golden["expected"]


def _pairs(name: str, key: str) -> list[tuple[Any, Any]]:
    inputs, expected = _load(name)
    cases = inputs[key]
    assert len(cases) == len(expected), f"{name}: inputs and goldens are out of step; regenerate"
    return list(zip(cases, expected, strict=True))


def _ids(name: str, key: str, label: str | None = None) -> list[str]:
    inputs, _ = _load(name)
    return [str(c.get(label)) if label else str(i) for i, c in enumerate(inputs[key])]


PLACEMENT = _pairs("placement", "cases")
RENDER = _pairs("render", "cases")
DIFF = _pairs("diff_stats", "cases")
CANONICAL = _pairs("canonical", "cases")
COMPILE = _pairs("compile", "cases")
LIFT = _pairs("lift", "samples")


def test_corpora_are_non_trivial() -> None:
    assert len(PLACEMENT) >= 10
    assert len(RENDER) >= 10
    assert len(DIFF) >= 10
    assert len(CANONICAL) >= 20
    assert len(COMPILE) >= 15
    assert len(LIFT) >= 20
    assert len(_load("canonical_proto")[1]) >= 8


@pytest.mark.parametrize(("case", "expected"), PLACEMENT, ids=_ids("placement", "cases"))
def test_placement(case: dict[str, Any], expected: dict[str, Any]) -> None:
    messages = [{"role": role, "content": f"message {i}"} for i, role in enumerate(case["roles"])]
    content = _load("placement")[0]["module_content"]
    assert learned_placement_index(messages) == expected["index"]
    assert apply_learned_context(messages, content) == expected["applied"]


@pytest.mark.parametrize(("case", "expected"), RENDER, ids=_ids("render", "cases"))
def test_render(case: dict[str, Any], expected: dict[str, Any]) -> None:
    assert (
        render_hosted_prompt_result(case["template"], case["variables"], case["vars"]) == expected
    )


@pytest.mark.parametrize(("case", "expected"), DIFF, ids=_ids("diff_stats", "cases"))
def test_diff_stats(case: dict[str, Any], expected: dict[str, Any]) -> None:
    actual = diff_stats(case["draft"], case["final"])
    assert actual["lengths"] == expected["lengths"]
    assert actual["changed_spans"] == expected["changed_spans"]
    assert actual["final_hash"] == expected["final_hash"]
    assert actual["edit_ratio"] == pytest.approx(expected["edit_ratio"], abs=0, rel=1e-15)


@pytest.mark.parametrize(("case", "expected"), CANONICAL, ids=_ids("canonical", "cases"))
def test_canonical_json(case: dict[str, Any], expected: dict[str, Any]) -> None:
    assert canonical_json(case["value"]) == expected["json"]
    assert hash_context_value(case["value"]) == expected["sha256"]


@pytest.mark.parametrize(("case", "expected"), COMPILE, ids=_ids("compile", "cases", "name"))
def test_compile(case: dict[str, Any], expected: dict[str, Any]) -> None:
    profile = PROFILES[case["profile"]]
    result = compile(case["envelope"], case["contract"], case["candidates"], profile)
    assert result.ok is expected["ok"]
    assert [r["code"] for r in result.refusals] == [r["code"] for r in expected["refusals"]]
    assert result.refusals == expected["refusals"]
    if not expected["ok"]:
        assert result.manifest is None
        return
    manifest = result.manifest
    assert manifest is not None
    encoded = profile.manifest_encoder(
        {k: v for k, v in manifest.items() if k != "manifestHash"},
        {"envelope": case["envelope"], "contract": case["contract"]},
    )
    assert encoded["bytes"] == expected["bytes"]
    assert encoded["hash"] == expected["hash"]
    assert manifest["manifestHash"] == expected["manifest"]["manifestHash"]
    assert json.loads(json.dumps(manifest)) == expected["manifest"]
    assert to_wire(manifest) == expected["wire"]
    if "rendered" in expected:
        assert render(manifest, case["bodies"]) == expected["rendered"]


@pytest.mark.parametrize(("sample", "expected"), LIFT, ids=_ids("lift", "samples", "name"))
def test_lift_and_exit(sample: dict[str, Any], expected: dict[str, Any]) -> None:
    lifted = from_messages(sample["messages"], sample.get("hints"))
    assert json.loads(json.dumps(lifted)) == expected["lifted"]
    # Leaving is exact, also after a JSON round trip of the manifest.
    manifest = json.loads(json.dumps(lifted["manifest"]))
    assert to_messages(manifest) == expected["exited"] == sample["messages"]


# ── prototype-named keys: ordinary data keys, kept at every depth by both implementations ──

_PROTO_INPUTS = json.loads((PARITY / "inputs" / "canonical_proto.json").read_text("utf-8"))["cases"]
_PROTO_EXPECTED_JSON = [
    '{"__proto__":{"review":"different"}}',
    '{"a":{"__proto__":{"x":1}},"b":2}',
    '{"__proto__":null}',
    '{"__proto__":[1,{"__proto__":"deep"}]}',
    '{"__proto__":2,"constructor":1,"prototype":3,"toString":4}',
    '[{"__proto__":{}},{}]',
    '{"Z":1,"__proto__":2,"a":3}',
    '{"outer":{"__proto__":{"__proto__":{"leaf":true}}}}',
]


@pytest.mark.parametrize(
    ("case", "expected"), list(zip(_PROTO_INPUTS, _PROTO_EXPECTED_JSON, strict=True))
)
def test_canonical_json_keeps_prototype_named_keys(case: dict[str, Any], expected: str) -> None:
    assert canonical_json(case["value"]) == expected
    stripped = json.loads(json.dumps(case["value"]).replace('"__proto__"', '"__gone__"'))
    assert hash_context_value(case["value"]) != hash_context_value(stripped)


def test_a_prototype_key_never_collapses_to_the_empty_object_hash() -> None:
    assert hash_context_value({"__proto__": {"review": "different"}}) != hash_context_value({})


CANONICAL_PROTO = _pairs("canonical_proto", "cases")


@pytest.mark.parametrize(
    ("case", "expected"), CANONICAL_PROTO, ids=_ids("canonical_proto", "cases")
)
def test_canonical_proto_matches_the_reference(
    case: dict[str, Any], expected: dict[str, Any]
) -> None:
    assert canonical_json(case["value"]) == expected["json"]
    assert hash_context_value(case["value"]) == expected["sha256"]


def test_reference_agrees_with_the_hand_written_expectations() -> None:
    assert [golden["json"] for _, golden in CANONICAL_PROTO] == _PROTO_EXPECTED_JSON


PROTO_LIFT = [
    (sample, expected)
    for sample, expected in LIFT
    if any("__proto__" in message for message in sample["messages"])
]


def test_lift_corpus_has_prototype_message_keys() -> None:
    assert [sample["name"] for sample, _ in PROTO_LIFT] == [
        "proto-message-key",
        "proto-keys-in-a-conversation",
    ]


@pytest.mark.parametrize(
    ("sample", "expected"), PROTO_LIFT, ids=[sample["name"] for sample, _ in PROTO_LIFT]
)
def test_lift_keeps_an_own_proto_message_key(
    sample: dict[str, Any], expected: dict[str, Any]
) -> None:
    lifted = from_messages(sample["messages"])
    manifest = lifted["manifest"]
    assert manifest["manifestHash"] == expected["lifted"]["manifest"]["manifestHash"]
    assert json.dumps(lifted).count('"__proto__"') == json.dumps(expected["lifted"]).count(
        '"__proto__"'
    )
    exited = to_messages(json.loads(json.dumps(manifest)))
    assert exited == sample["messages"]
    assert [m.get("__proto__", "absent") for m in exited] == [
        m.get("__proto__", "absent") for m in sample["messages"]
    ]
