"""Every Python code block in README.md and docs/*.md runs, in order, against the mock gateway.

All outgoing HTTP is rerouted to the local mock (``sandbox_network``), so snippets can show real
URLs and still run offline. Blocks of one page share a namespace, like a reader following the
page top to bottom. A block is skipped only when the line before it is
``<!-- doctest: skip — <reason> -->``; ``test_skips_are_rare_and_justified`` keeps that honest.
"""

from __future__ import annotations

import asyncio
import contextlib
import gc
import importlib.util
import io
import re
import warnings
from pathlib import Path
from typing import Any

import pytest

from conftest import MockGateway

ROOT = Path(__file__).resolve().parents[1]
GENERATED = {"api-reference.md", "types-reference.md", "api-coverage.md"}
DOC_FILES = [
    ROOT / "README.md",
    ROOT / "AGENTS.md",
    *sorted(p for p in (ROOT / "docs").glob("*.md") if p.name not in GENERATED),
]
FENCE = re.compile(r"^```python\n(.*?)^```", re.DOTALL | re.MULTILINE)
SKIP = re.compile(r"<!--\s*doctest:\s*skip\s*[—-]\s*(.+?)\s*-->\s*$")
MAX_SKIPS = 3


def blocks(path: Path) -> list[tuple[int, str, str | None]]:
    """(line number, code, skip reason) for every ```python block."""
    text = path.read_text(encoding="utf-8")
    found: list[tuple[int, str, str | None]] = []
    for match in FENCE.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        before = text[: match.start()].rstrip("\n").splitlines()
        reason = None
        if before:
            skip = SKIP.search(before[-1])
            reason = skip.group(1) if skip else None
        found.append((line, match.group(1), reason))
    return found


def _close_clients(namespace: dict[str, Any]) -> None:
    from ultrarouter import AsyncUltraRouter, UltraRouter

    for value in list(namespace.values()):
        if isinstance(value, UltraRouter):
            value.close()
        elif isinstance(value, AsyncUltraRouter):
            asyncio.run(value.close())
        elif type(value).__module__.startswith("openai") and hasattr(value, "close"):
            with contextlib.suppress(Exception):
                value.close()


def _needs_openai(code: str) -> bool:
    return (
        "as_openai(" in code or re.search(r"^\s*(?:import|from) openai\b", code, re.M) is not None
    )


@pytest.mark.parametrize("path", DOC_FILES, ids=[str(p.relative_to(ROOT)) for p in DOC_FILES])
def test_python_blocks_run(path: Path, sandbox_network: MockGateway) -> None:
    if importlib.util.find_spec("openai") is None and any(
        _needs_openai(code) for _, code, reason in blocks(path) if reason is None
    ):
        pytest.skip("uses the optional openai package (the [openai] extra)")
    namespace: dict[str, Any] = {"__name__": "__main__"}
    ran = 0
    try:
        for line, code, reason in blocks(path):
            if reason is not None:
                continue
            sandbox_network.reset()
            compiled = compile(code, f"{path.relative_to(ROOT)}:{line}", "exec")
            with contextlib.redirect_stdout(io.StringIO()):
                exec(compiled, namespace)  # noqa: S102 - running our own documentation
            requests = sandbox_network.requests
            assert not any(
                re.match(r"/v1/call-types/(?!ct_)[^/]+/learning(?:/|$)", item["path"])
                for item in requests
            ), f"{path.name}:{line}: learning controls require ct_... IDs"
            if path.relative_to(ROOT).as_posix() == "docs/learning.md":
                assert all(
                    item["body"].get("call_type") == "support-reply"
                    for item in requests
                    if item["path"] == "/v1/chat/completions"
                ), f"{path.name}:{line}: learning traffic must declare its call-type slug"
            ran += 1
    finally:
        _close_clients(namespace)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            gc.collect()
    assert ran > 0 or not blocks(path), f"{path.name}: every block was skipped"


def test_skips_are_rare_and_justified() -> None:
    skipped = [(p.name, line, reason) for p in DOC_FILES for line, _, reason in blocks(p) if reason]
    assert len(skipped) <= MAX_SKIPS, skipped
    for _, _, reason in skipped:
        assert reason and len(reason) > 10, "a skip must say why"


def test_docs_have_python_examples() -> None:
    total = sum(len(blocks(p)) for p in DOC_FILES)
    assert total >= 80, total


def _docstring_examples() -> list[tuple[str, str]]:
    """(owner, code) for every ``::`` literal block in a public docstring of the package."""
    import importlib
    import inspect
    import pkgutil
    import textwrap
    import types

    import ultrarouter

    owners: list[tuple[str, object]] = []
    for info in pkgutil.walk_packages(ultrarouter.__path__, "ultrarouter."):
        if info.name.endswith("_generated"):
            continue
        module = importlib.import_module(info.name)
        owners.append((info.name, module))
        for name, member in vars(module).items():
            # Only the package's own classes and functions: from Python 3.12 TypeVar instances
            # also carry the defining module, and their docstring is the standard library's.
            if not (inspect.isclass(member) or inspect.isfunction(member)):
                continue
            if isinstance(member, types.GenericAlias):
                continue
            if getattr(member, "__module__", None) != info.name:
                continue
            owners.append((f"{info.name}.{name}", member))
            if inspect.isclass(member):
                owners += [
                    (f"{info.name}.{name}.{m}", v)
                    for m, v in vars(member).items()
                    if inspect.isfunction(v)
                ]
    examples: list[tuple[str, str]] = []
    for owner, obj in owners:
        doc = inspect.getdoc(obj) or ""
        lines = doc.splitlines()
        for i, line in enumerate(lines):
            if not line.rstrip().endswith("::"):
                continue
            block: list[str] = []
            for nxt in lines[i + 1 :]:
                if nxt.strip() and not nxt.startswith("    "):
                    break
                block.append(nxt)
            code = textwrap.dedent("\n".join(block)).strip()
            if code:
                examples.append((owner, code))
    return examples


DOCSTRING_EXAMPLES = _docstring_examples()


def test_docstring_examples_exist() -> None:
    assert len(DOCSTRING_EXAMPLES) >= 5


@pytest.mark.parametrize(
    ("owner", "code"), DOCSTRING_EXAMPLES, ids=[o for o, _ in DOCSTRING_EXAMPLES]
)
def test_docstring_examples_run(owner: str, code: str, sandbox_network: MockGateway) -> None:
    namespace: dict[str, Any] = {"__name__": "__main__"}
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(code, owner, "exec"), namespace)  # noqa: S102 - our own docstrings
    finally:
        _close_clients(namespace)
