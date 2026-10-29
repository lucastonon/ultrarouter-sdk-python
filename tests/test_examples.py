"""Every script in examples/ runs to completion against the mock gateway, as a real process."""

from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from mock_gateway import STATE

from conftest import TEST_KEY, MockGateway
from ultrarouter import UltraRouter

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
            "ULTRAROUTER_CALL_TYPE_ID": "ct_example_controls",
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
    if script.name == "learning_controls.py":
        assert mock_gateway.requests
        assert all(
            item["path"].startswith("/v1/call-types/ct_example_controls/learning")
            or item["path"] == "/v1/call-types/ct_missing/learning"
            for item in mock_gateway.requests
        )
    elif script.name.startswith("learning_"):
        requests = mock_gateway.requests
        traffic = [item for item in requests if item["path"] == "/v1/chat/completions"]
        assert traffic, "the example must actually send inference"
        assert all(item["body"]["call_type"] == "order-desk" for item in traffic)
        listed = next(item for item in requests if item["path"] == "/v1/call-types")
        assert requests.index(listed) < requests.index(traffic[0])
        with STATE.lock:
            call_type = STATE.call_types["order-desk"]
        assert call_type["id"].startswith("ct_")
        if script.name == "learning_async.py":
            assert any(
                item["path"] == f"/v1/call-types/{call_type['id']}/learning" for item in requests
            )
            assert not any(
                item["path"] == "/v1/call-types/order-desk/learning" for item in requests
            )


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


@pytest.mark.parametrize("call_type_id", [None, "", "order-desk"])
def test_learning_controls_rejects_missing_id_or_slug_before_requests(
    call_type_id: str | None, mock_gateway: MockGateway
) -> None:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("ULTRAROUTER_", "UR_"))}
    env.update(ULTRAROUTER_API_KEY=TEST_KEY, ULTRAROUTER_BASE_URL=mock_gateway.url)
    if call_type_id is not None:
        env["ULTRAROUTER_CALL_TYPE_ID"] = call_type_id
    result = subprocess.run(
        [sys.executable, str(ROOT / "examples/learning_controls.py")],
        env=env,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 2
    assert "ULTRAROUTER_CALL_TYPE_ID" in result.stderr
    assert mock_gateway.requests == []


def test_async_example_reuses_existing_call_type(mock_gateway: MockGateway) -> None:
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        existing = client.call_types.create(slug="order-desk")
    start = len(mock_gateway.requests)
    test_example_runs(ROOT / "examples/learning_async.py", mock_gateway)
    sent = mock_gateway.requests[start:]
    assert not any(item["method"] == "POST" and item["path"] == "/v1/call-types" for item in sent)
    assert any(item["path"] == f"/v1/call-types/{existing.id}/learning" for item in sent)


@pytest.mark.parametrize(
    "name", ["learning_async.py", "learning_immediate_outcome.py", "learning_ack_loss.py"]
)
@pytest.mark.parametrize("answer", ["NOT OK", ""])
def test_exact_answer_examples_report_failure_for_wrong_answers(
    name: str, answer: str, mock_gateway: MockGateway
) -> None:
    with STATE.lock:
        STATE.say_ok_reply = answer
    env = {k: v for k, v in os.environ.items() if not k.startswith(("ULTRAROUTER_", "UR_"))}
    env.update(ULTRAROUTER_API_KEY=TEST_KEY, ULTRAROUTER_BASE_URL=mock_gateway.url)
    result = subprocess.run(
        [sys.executable, str(ROOT / "examples" / name)],
        env=env,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=40,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    reports = [item for item in mock_gateway.requests if item["path"].endswith("/outcomes")]
    assert reports
    assert all(item["body"]["kind"] == "oracle_fail" for item in reports)
