"""Repository-level checks: synced and generated files, docstrings, links, claims, workflows."""

from __future__ import annotations

import ast
import importlib
import inspect
import os
import pkgutil
import re
import shutil
import subprocess
import sys
import typing
from pathlib import Path
from typing import Any

import pytest
import yaml

import ultrarouter
import ultrarouter.adapters
import ultrarouter.context
import ultrarouter.demo
import ultrarouter.types

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - Python 3.10
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import sync_openapi  # noqa: E402


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args], cwd=ROOT, capture_output=True, text=True, check=False
    )


# ── synced and generated artifacts ──


def test_openapi_header_and_digest() -> None:
    lines = (ROOT / "openapi" / "openapi.yaml").read_bytes().split(b"\n", 2)
    assert (
        lines[0]
        == b"# ultrarouter public API specification (OpenAPI). Synced artifact: do not hand-edit."
    )
    assert re.fullmatch(rb"# spec-sha256: [0-9a-f]{64}", lines[1])
    sync_openapi.verify()


def test_openapi_tamper_is_detected(tmp_path: Path) -> None:
    copy = tmp_path / "openapi.yaml"
    copy.write_bytes((ROOT / "openapi" / "openapi.yaml").read_bytes() + b"# edited\n")
    with pytest.raises(ValueError, match="mismatch"):
        sync_openapi.verify(copy)


def test_generated_types_are_up_to_date() -> None:
    result = _run("scripts/gen_types.py", "--check")
    assert result.returncode == 0, result.stderr


def test_generated_docs_are_up_to_date() -> None:
    result = _run("scripts/gen_docs.py", "--check")
    assert result.returncode == 0, result.stderr


def test_nullable_values_generate_their_type() -> None:
    """A nullable value in the spec is its type plus ``None`` in the generated types, never ``Any``."""
    from ultrarouter.types import (
        ChatCompletionChoice,
        ChatCompletionMessage,
        ChatContentPartParam,
        ChatMessageParam,
        EvalRun,
        EvalRunSpec,
        PreflightParams,
    )

    assert ChatCompletionChoice.model_fields["finish_reason"].annotation == (str | None)
    assert ChatCompletionMessage.model_fields["content"].annotation == (str | None)
    assert EvalRun.model_fields["run_spec"].annotation == (EvalRunSpec | None)
    content = typing.get_type_hints(ChatMessageParam)["content"]
    assert content == (str | list[ChatContentPartParam] | None)
    assert typing.get_type_hints(PreflightParams)["messages"] == list[ChatMessageParam]


def test_parity_goldens_match_the_typescript_reference() -> None:
    ts_sdk = Path(os.environ.get("ULTRAROUTER_TS_SDK", ROOT.parent / "ultrarouter-sdk-typescript"))
    if shutil.which("node") is None or not (ts_sdk / "dist" / "context.js").exists():
        pytest.skip(
            "TypeScript SDK build not available (set ULTRAROUTER_TS_SDK to a built checkout)"
        )
    result = subprocess.run(
        ["node", "scripts/gen_parity_goldens.mjs", "--ts-sdk", str(ts_sdk), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


# ── public API and docstrings ──

PUBLIC_MODULES = (
    ultrarouter,
    ultrarouter.adapters,
    ultrarouter.context,
    ultrarouter.demo,
    ultrarouter.types,
)


def _public_objects() -> list[tuple[str, Any]]:
    found: list[tuple[str, Any]] = []
    for module in PUBLIC_MODULES:
        for name in module.__all__:
            found.append((f"{module.__name__}.{name}", getattr(module, name)))
    from ultrarouter import UltraRouter

    client = UltraRouter(api_key="ur_sk_test_docstrings", base_url="http://localhost")

    def walk(obj: Any, path: str) -> None:
        for name, value in vars(obj).items():
            if not name.startswith("_") and type(value).__module__.startswith(
                "ultrarouter._resources"
            ):
                found.append((f"{path}.{name}", type(value)))
                walk(value, f"{path}.{name}")

    walk(client, "client")
    client.close()
    return found


def test_every_public_name_resolves() -> None:
    for module in PUBLIC_MODULES:
        assert len(module.__all__) == len(set(module.__all__)), module.__name__
        for name in module.__all__:
            assert hasattr(module, name), f"{module.__name__}.{name}"


def test_every_module_has_a_docstring() -> None:
    for info in pkgutil.walk_packages(ultrarouter.__path__, "ultrarouter."):
        module = importlib.import_module(info.name)
        assert inspect.getdoc(module), f"module {info.name} has no docstring"


def test_every_public_symbol_has_a_docstring() -> None:
    missing: list[str] = []
    for path, obj in _public_objects():
        if not (inspect.isclass(obj) or inspect.isfunction(obj)):
            continue
        if not getattr(obj, "__module__", "").startswith("ultrarouter"):
            continue
        if not (obj.__doc__ or "").strip():
            missing.append(path)
        if inspect.isclass(obj):
            for name, member in vars(obj).items():
                if name.startswith("_") or not (
                    inspect.isfunction(member) or isinstance(member, property)
                ):
                    continue
                if not (member.__doc__ or "").strip():
                    missing.append(f"{path}.{name}")
    assert not missing, f"missing docstrings: {sorted(set(missing))}"


def test_package_is_typed_and_versioned() -> None:
    assert (Path(ultrarouter.__file__).parent / "py.typed").exists()
    assert ultrarouter.__version__ == "0.1.0"
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{ultrarouter.__version__}]" in changelog


def test_pyproject_metadata() -> None:
    meta = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert meta["name"] == "ultrarouter"
    assert meta["license"] == "MIT" and meta["license-files"] == ["LICENSE"]
    assert meta["requires-python"] == ">=3.10"
    classifiers = set(meta["classifiers"])
    assert "Typing :: Typed" in classifiers and "Development Status :: 3 - Alpha" in classifiers
    for minor in range(10, 15):
        assert f"Programming Language :: Python :: 3.{minor}" in classifiers
    assert "openai" in meta["optional-dependencies"]
    assert set(meta["urls"]) == {"Homepage", "Documentation", "Repository", "Issues", "Changelog"}
    assert "MIT License" in (ROOT / "LICENSE").read_text(encoding="utf-8")


# ── continuous integration and release ──


def _workflow(name: str) -> dict[Any, Any]:
    data = yaml.safe_load((ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_ci_covers_every_supported_python_and_gate() -> None:
    ci = _workflow("ci.yml")
    matrix = ci["jobs"]["test"]["strategy"]["matrix"]["python-version"]
    assert matrix == ["3.10", "3.11", "3.12", "3.13", "3.14"]
    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for gate in (
        "ruff check",
        "ruff format --check",
        "mypy",
        "gen_types.py --check",
        "gen_docs.py --check",
        "tests/test_docs.py",
        "tests/test_examples.py",
        "twine check --strict",
        "scripts/smoke.sh",
        "scripts/lowest_deps.sh",
        "leak_scan.py --dist dist --redact-external",
        "fetch-depth: 0",
    ):
        assert gate in text, f"ci.yml does not run {gate}"
    assert ci["jobs"]["lowest"]["env"]["UV_PYTHON"] == "3.10"


_USES = re.compile(r"^\s*(?:-\s*)?uses:\s*(\S+)(.*)$")


@pytest.mark.parametrize("name", ["ci.yml", "publish.yml"])
def test_every_action_is_pinned_to_a_commit_sha(name: str) -> None:
    lines = (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8").splitlines()
    uses = [m for m in (_USES.match(line) for line in lines) if m]
    assert uses, f"{name} uses no actions"
    for match in uses:
        action, comment = match.group(1), match.group(2)
        if action.startswith("./"):
            continue  # a local action needs no pin
        _, _, ref = action.partition("@")
        assert re.fullmatch(r"[0-9a-f]{40}", ref), f"{name}: {action} is not pinned to a commit"
        assert re.fullmatch(r"\s*# v\d+\.\d+\.\d+", comment), f"{name}: {action} lacks '# vX.Y.Z'"


def test_publish_uses_trusted_publishing_only_on_release_or_dispatch() -> None:
    publish = _workflow("publish.yml")
    triggers = publish[True]  # YAML 1.1 reads the bare key `on` as a boolean
    assert set(triggers) == {"release", "workflow_dispatch"}
    assert triggers["release"] == {"types": ["published"]}
    assert publish["permissions"] == {"contents": "read"}
    assert publish["jobs"]["publish"]["permissions"] == {"id-token": "write"}
    text = (ROOT / ".github" / "workflows" / "publish.yml").read_text(encoding="utf-8")
    assert "password" not in text
    assert "leak_scan.py --dist dist --redact-external" in text and "fetch-depth: 0" in text
    assert "LEAK_PATTERNS_JSON" in text, "a release scans with the extra patterns"


# ── documentation hygiene ──

DOC_FILES = [
    ROOT / "README.md",
    ROOT / "AGENTS.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "SECURITY.md",
    *sorted((ROOT / "docs").glob("*.md")),
]
LINK = re.compile(r"\]\((?!https?://|mailto:|#)([^)#\s]+)(#[^)\s]*)?\)")


REPO_LINK = re.compile(
    r"\]\(https://github\.com/lucastonon/ultrarouter-sdk-python/(blob|tree)/"
    r"(?:main|feat/learning-loop)/([^)#\s]+)(#[^)\s]*)?\)"
)


@pytest.mark.parametrize("path", DOC_FILES, ids=[p.name for p in DOC_FILES])
def test_relative_links_resolve(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for match in LINK.finditer(text):
        target = (path.parent / match.group(1)).resolve()
        assert target.exists(), f"{path.name}: broken link {match.group(1)}"


@pytest.mark.parametrize("path", DOC_FILES, ids=[p.name for p in DOC_FILES])
def test_repository_links_resolve(path: Path) -> None:
    """Absolute links into this repository point at files (blob) or directories (tree) that exist."""
    for match in REPO_LINK.finditer(path.read_text(encoding="utf-8")):
        kind, target = match.group(1), ROOT / match.group(2)
        assert target.is_file() if kind == "blob" else target.is_dir(), (
            f"{path.name}: broken repository link {match.group(0)}"
        )


def test_readme_links_are_absolute() -> None:
    """PyPI renders the README outside the repository, so it may not use relative links."""
    relative = [m.group(0) for m in LINK.finditer((ROOT / "README.md").read_text(encoding="utf-8"))]
    assert relative == []
    assert REPO_LINK.search((ROOT / "README.md").read_text(encoding="utf-8"))


def test_every_guide_is_indexed() -> None:
    index = (ROOT / "docs" / "index.md").read_text(encoding="utf-8")
    for page in (ROOT / "docs").glob("*.md"):
        if page.name != "index.md":
            assert f"({page.name})" in index, f"{page.name} is not linked from docs/index.md"


def test_llms_txt_format() -> None:
    text = (ROOT / "llms.txt").read_text(encoding="utf-8")
    lines = text.splitlines()
    assert lines[0].startswith("# ") and lines[2].startswith("> ")
    assert "## Optional" in text
    for name in (p.name for p in (ROOT / "docs").glob("*.md") if p.name not in ("index.md",)):
        if name not in ("api-reference.md", "types-reference.md", "api-coverage.md"):
            assert f"/docs/{name})" in text, f"llms.txt misses {name}"


# Hand-written prose only: the generated references reproduce the API specification and code verbatim.
_GENERATED_DOCS = {"api-reference.md", "types-reference.md", "api-coverage.md"}
_CLAIM_FILES = [
    ROOT / "README.md",
    ROOT / "AGENTS.md",
    ROOT / "llms.txt",
    *sorted(p for p in (ROOT / "docs").glob("*.md") if p.name not in _GENERATED_DOCS),
    *sorted((ROOT / "examples").glob("*.py")),
]


@pytest.mark.parametrize("path", _CLAIM_FILES, ids=[p.name for p in _CLAIM_FILES])
def test_no_forbidden_claims(path: Path) -> None:
    """No savings percentages, no 'lossless' for prompt transforms, no 'measured' savings,
    no blanket no-training promise, no general-availability claim for the hosted service."""
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        lower = line.lower()
        if re.search(r"\blossless\b", lower):
            assert re.search(r"legacy|alias|deprecat", lower), f"{path.name}:{number}: {line}"
        if re.search(r"\d+(?:\.\d+)?\s?%", line):
            assert not re.search(r"sav|cheaper|reduc|cut|lower", lower), (
                f"{path.name}:{number}: {line}"
            )
        if re.search(r"\bmeasured\b", lower):
            assert not re.search(r"sav|cost|cheaper", lower), f"{path.name}:{number}: {line}"
        assert not re.search(r"\b(never|not|don'?t|won'?t)\b.{0,40}\btrain", lower), (
            f"{path.name}:{number}: {line}"
        )
        assert not re.search(r"generally available|\bga\b", lower), f"{path.name}:{number}: {line}"


# ── spec test helpers ──


def test_spec_validator_handles_nullable_compositions() -> None:
    sys.path.insert(0, str(ROOT / "tests" / "support"))
    from spec import validate

    union = {"anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}]}
    assert validate(None, {**union, "nullable": True}) == []
    assert validate("x", {**union, "nullable": True}) == []
    assert validate(["x"], {**union, "nullable": True}) == []
    assert validate(5, {**union, "nullable": True})
    assert validate(None, union)


def test_spec_validator_catches_violations() -> None:
    sys.path.insert(0, str(ROOT / "tests" / "support"))
    from spec import validate

    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["a"],
        "properties": {
            "a": {"type": "string", "enum": ["x"]},
            "b": {"type": "integer", "nullable": True},
        },
    }
    assert validate({"a": "x", "b": None}, schema) == []
    assert validate({"a": "y"}, schema)
    assert validate({"b": 1}, schema)
    assert validate({"a": "x", "c": 1}, schema)
    assert validate({"a": "x", "b": "1"}, schema)
    assert validate([], schema)


def test_ast_parses_every_source_file() -> None:
    for path in (ROOT / "src").rglob("*.py"):
        ast.parse(path.read_text(encoding="utf-8"))
