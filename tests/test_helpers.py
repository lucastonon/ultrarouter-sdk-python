"""Pure helpers: JavaScript-compatible JSON, diff stats, prompt rendering, learned placement."""

from __future__ import annotations

import math

import pytest

from ultrarouter import (
    LEARNED_MESSAGE_ROLE,
    PROMPT_VARIABLES_MISSING_CODE,
    PromptVariablesMissingError,
    apply_learned_context,
    diff_stats,
    learned_placement_index,
    render_hosted_prompt_result,
    render_prompt,
)
from ultrarouter._jscompat import (
    canonical_json,
    js_number,
    js_sorted_keys,
    js_string,
    utf8_bytes,
    utf16_units,
)
from ultrarouter.types import PreflightPrompt


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, "0"),
        (-0.0, "0"),
        (1.0, "1"),
        (0.1, "0.1"),
        (1e-7, "1e-7"),
        (1.5e-7, "1.5e-7"),
        (0.000001, "0.000001"),
        (123.456, "123.456"),
        (1e21, "1e+21"),
        (1.5e22, "1.5e+22"),
        (1e20, "100000000000000000000"),
        (2**53, "9007199254740992"),
        (2**53 + 1, "9007199254740992"),
        (-2.5, "-2.5"),
        (math.nan, "null"),
        (math.inf, "null"),
    ],
)
def test_js_number(value: float, expected: str) -> None:
    assert js_number(value) == expected


def test_js_string_and_surrogates() -> None:
    assert js_string('a"b\\c\n\u0001é') == '"a\\"b\\\\c\\nu0001é"'.replace("nu0001", "n\\u0001")
    assert js_string("\ud83d") == '"\\ud83d"'
    assert js_string("😀") == '"😀"'
    assert utf16_units("a😀") == [0x61, 0xD83D, 0xDE00]
    assert utf8_bytes("\ud800x") == "�x".encode()


def test_key_order_matches_json_stringify() -> None:
    assert js_sorted_keys(["b", "10", "2", "a", "01", "-1"]) == ["2", "10", "-1", "01", "a", "b"]
    assert js_sorted_keys(["￿", "😀"]) == ["😀", "￿"]  # UTF-16 order, not code-point order


def test_canonical_json_rejects_non_json_values() -> None:
    assert canonical_json({"t": (1, 2), 3: "int key"}) == '{"3":"int key","t":[1,2]}'
    with pytest.raises(TypeError):
        canonical_json({"x": object()})


def test_diff_stats_identity_and_change() -> None:
    same = diff_stats("abc", "abc")
    assert same == {
        "edit_ratio": 0,
        "changed_spans": 0,
        "lengths": {"draft": 3, "final": 3},
        "final_hash": same["final_hash"],
    }
    changed = diff_stats("The quick brown fox", "The quick red fox")
    assert 0 < changed["edit_ratio"] < 1 and changed["changed_spans"] >= 1
    assert diff_stats("", "new")["edit_ratio"] == 1.0
    assert diff_stats("👋", "")["lengths"] == {"draft": 2, "final": 0}


def test_diff_stats_degrades_conservatively_on_huge_inputs() -> None:
    a = "x" + "a" * 2_500 + "y"
    b = "x" + "b" * 2_500 + "y"
    stats = diff_stats(a, b)
    assert stats["changed_spans"] == 1 and stats["edit_ratio"] == pytest.approx(5_000 / 5_004)


def test_render_prompt_from_model_mapping_and_object() -> None:
    prompt = PreflightPrompt(
        version=1,
        template="Hi {{name}}, {{ tone }}!",
        variables=[{"name": "name", "required": True}],
        sha256="x",
    )
    assert render_prompt(prompt, {"name": "Ana", "tone": "welcome"}) == "Hi Ana, welcome!"
    assert render_prompt({"template": "{{a}}", "variables": []}) == ""
    with pytest.raises(PromptVariablesMissingError) as info:
        render_prompt(prompt, {})
    assert info.value.missing == ["name"] and info.value.code == PROMPT_VARIABLES_MISSING_CODE
    assert info.value.status == 0
    with pytest.raises(TypeError):
        render_prompt({"variables": []})


def test_render_result_form() -> None:
    assert render_hosted_prompt_result("{{x}}", [{"name": "x", "required": True}], {"x": 1}) == {
        "ok": True,
        "text": "1",
    }
    assert render_hosted_prompt_result("{{x}}", [{"name": "x", "required": True}]) == {
        "ok": False,
        "missing": ["x"],
    }


def test_learned_placement() -> None:
    assert learned_placement_index([]) == 0
    assert learned_placement_index([{"role": "system"}, {"role": "system"}, {"role": "user"}]) == 2

    class Msg:
        def __init__(self, role: str) -> None:
            self.role = role

    assert learned_placement_index([Msg("system"), Msg("user")]) == 1
    messages = [{"role": "system", "content": "s"}, {"role": "user", "content": "q"}]
    applied = apply_learned_context(messages, "LEARNED")
    assert applied[1] == {"role": LEARNED_MESSAGE_ROLE, "content": "LEARNED"}
    assert apply_learned_context(messages, None) == messages
    assert apply_learned_context(messages, "") == messages
    assert len(messages) == 2
