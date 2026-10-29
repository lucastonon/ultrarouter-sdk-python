"""Every script in examples/ runs to completion against the mock gateway, as a real process."""

from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import TEST_KEY, MockGateway

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = sorted((ROOT / "examples").glob("*.py"))


def test_examples_exist() -> None:
    assert len(EXAMPLES) >= 23


@pytest.mark.parametrize("script", EXAMPLES, ids=[p.name for p in EXAMPLES])
def test_example_runs(script: Path, mock_gateway: MockGateway) -> None:
    source = script.read_text(encoding="utf-8")
    if importlib.util.find_spec("openai") is None and (
        "as_openai(" in source or "import openai" in source
    ):
        pytest.skip("uses the optional openai package (the [openai] extra)")
    env = {k: v for k, v in os.environ.items() if not k.startswith(("ULTRAROUTER_", "UR_"))}
    env.update(
        {
            "ULTRAROUTER_API_KEY": TEST_KEY,
            "ULTRAROUTER_BASE_URL": mock_gateway.url,
            "PYTHONWARNINGS": "error::DeprecationWarning",
        }
    )
    result = subprocess.run(
        [sys.executable, str(script)],
        env=env,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, f"{script.name} failed:\n{result.stdout}\n{result.stderr}"
    assert result.stdout.strip(), f"{script.name} printed nothing"
    _check_expected_output(source, result.stdout, script.name)


def _expected_output(source: str) -> list[str]:
    """The lines of an ``Expected output (mock gateway...)`` docstring section, if any."""
    lines = source.split('"""', 2)[1].splitlines()
    for index, line in enumerate(lines):
        if line.startswith("Expected output (mock gateway"):
            block = []
            for item in lines[index + 1 :]:
                if not item.startswith("    "):
                    break
                block.append(item[4:])
            return block
    return []


def _check_expected_output(source: str, stdout: str, name: str) -> None:
    """Each expected line (``...`` matches anything) appears in the output, in order."""
    output = stdout.splitlines()
    position = 0
    for expected in _expected_output(source):
        pattern = re.compile(".*".join(re.escape(part) for part in expected.split("...")) + "$")
        while position < len(output) and not pattern.match(output[position]):
            position += 1
        assert position < len(output), f"{name}: expected output line not found: {expected!r}"
        position += 1


def test_every_learning_example_documents_its_expected_output() -> None:
    learning = [p for p in EXAMPLES if p.name.startswith("learning_")]
    assert len(learning) == 8
    for script in learning:
        assert _expected_output(script.read_text(encoding="utf-8")), script.name


def test_examples_have_a_docstring_and_main_guard() -> None:
    for script in EXAMPLES:
        text = script.read_text(encoding="utf-8")
        assert text.startswith('"""'), f"{script.name} needs a module docstring"
        assert 'if __name__ == "__main__":' in text, f"{script.name} needs a main guard"


def test_expected_output_checker() -> None:
    source = '"""Doc.\n\nExpected output (mock gateway):\n    a: ...\n    b: 2\n"""\n'
    _check_expected_output(source, "noise\na: 1\nb: 2\n", "ok.py")
    with pytest.raises(AssertionError, match="not found"):
        _check_expected_output(source, "b: 2\na: 1\n", "order.py")
    with pytest.raises(AssertionError, match="not found"):
        _check_expected_output(source, "a: 1\nb: 3\n", "value.py")
