"""Every script in examples/ runs to completion against the mock gateway, as a real process."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import TEST_KEY, MockGateway

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = sorted((ROOT / "examples").glob("*.py"))


def test_examples_exist() -> None:
    assert len(EXAMPLES) >= 12


@pytest.mark.parametrize("script", EXAMPLES, ids=[p.name for p in EXAMPLES])
def test_example_runs(script: Path, mock_gateway: MockGateway) -> None:
    source = script.read_text(encoding="utf-8")
    if importlib.util.find_spec("openai") is None and (
        "as_openai(" in source or "import openai" in source
    ):
        pytest.skip("uses the optional openai package (pip install 'ultrarouter[openai]')")
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


def test_examples_have_a_docstring_and_main_guard() -> None:
    for script in EXAMPLES:
        text = script.read_text(encoding="utf-8")
        assert text.startswith('"""'), f"{script.name} needs a module docstring"
        assert 'if __name__ == "__main__":' in text, f"{script.name} needs a main guard"
