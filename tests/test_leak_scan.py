"""The leak scanner: generic secret and path rules, extra pattern files, history and artifacts.

Every credential-shaped sample here is assembled at runtime, so this file itself stays clean, and
the extra-pattern mechanism is exercised with synthetic patterns only.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import leak_scan  # noqa: E402

needs_git = pytest.mark.skipif(
    shutil.which("git") is None or not leak_scan.is_git_repository(ROOT),
    reason="needs a git checkout",
)

SYNTHETIC_PATTERNS: list[dict[str, Any]] = [
    {"id": "synthetic-codename", "regex": "zebra-[0-9]{3}", "description": "synthetic codename"},
    {
        "id": "synthetic-word",
        "regex": "quokka|wombat",
        "flags": "i",
        "description": "synthetic words, any case",
    },
]


def write_patterns(tmp_path: Path, patterns: Any = None) -> Path:
    path = tmp_path / "patterns.json"
    path.write_text(json.dumps(SYNTHETIC_PATTERNS if patterns is None else patterns), "utf-8")
    return path


def rule_ids(text: str, rules: Any = leak_scan.BUILTIN_RULES) -> set[str]:
    return {f.rule for f in leak_scan.scan_text("sample.txt", text, (), rules)}


# ── this repository ──


@needs_git
def test_tree_is_clean() -> None:
    count, findings = leak_scan.scan(leak_scan.iter_tree(ROOT), leak_scan.load_allowlist())
    assert count > 100
    assert findings == [], "\n".join(f.render() for f in findings)


@needs_git
def test_history_is_clean() -> None:
    commits, findings = leak_scan.scan_history(
        leak_scan.iter_history(ROOT), leak_scan.load_allowlist()
    )
    assert commits >= 1
    assert findings == [], "\n".join(f.render() for f in findings)


def test_scanner_source_is_generic_and_does_not_match_itself() -> None:
    text = (ROOT / "scripts" / "leak_scan.py").read_text(encoding="utf-8")
    assert leak_scan.scan_text("scripts/leak_scan.py", text) == []
    assert {rule.id for rule in leak_scan.BUILTIN_RULES} == {
        "anthropic-api-key",
        "openai-api-key",
        "ultrarouter-api-key",
        "github-token",
        "github-fine-grained-token",
        "npm-token",
        "pypi-token",
        "slack-token",
        "slack-app-token",
        "slack-webhook",
        "aws-access-key-id",
        "aws-secret-access-key",
        "google-api-key",
        "stripe-live-key",
        "huggingface-token",
        "private-key-block",
        "macos-home-path",
        "linux-home-path",
        "windows-home-path",
        "macos-temp-path",
    }
    assert not any(rule.external for rule in leak_scan.BUILTIN_RULES)


def test_allowlist_is_minimal_and_every_mask_is_used() -> None:
    entries = leak_scan.load_allowlist()
    assert len(entries) <= 2
    corpus = "\n".join(
        path.read_text("utf-8", "replace")
        for path in (ROOT / "src").rglob("*.py")
        if path.is_file()
    )
    for _glob, substring in entries:
        assert substring in corpus, f"stale allowlist entry: {substring}"


# ── built-in rules ──


SECRET_SAMPLES = [
    ("anthropic-api-key", "sk-" + "ant-" + "api03-" + "x" * 20),
    ("openai-api-key", "sk-" + "A1b2C3d4" * 6),
    ("openai-api-key", "sk-" + "proj-" + "Ab1_-" * 10),
    ("openai-api-key", "sk-" + "svcacct-" + "x" * 40),
    ("openai-api-key", "sk-" + "admin-" + "y" * 40),
    ("ultrarouter-api-key", "ur_sk_" + "live_" + "A" * 24),
    ("ultrarouter-api-key", "ur_sk_" + "test_" + "b" * 30),
    ("github-token", "gh" + "p_" + "a" * 36),
    ("github-token", "gh" + "s_" + "B" * 36),
    ("github-fine-grained-token", "github" + "_pat_" + "11ABCDEFG0" + "1" * 12 + "_" + "z" * 59),
    ("npm-token", "npm" + "_" + "A1b2" * 9),
    ("pypi-token", "pypi-" + "AgEIcHlwaS5vcmc" + "x" * 40),
    ("slack-token", "xox" + "b-1234-5678-abcdef"),
    ("slack-app-token", "xa" + "pp-1-A0B1C2D3-1234-abcdef"),
    ("slack-webhook", "hooks.slack.com/" + "services/T0000AAAA/B0000BBBB/" + "x" * 24),
    ("aws-access-key-id", "AK" + "IA" + "ABCDEFGHIJKLMNOP"),
    ("aws-access-key-id", "AS" + "IA" + "QRSTUVWXYZ234567"),
    ("aws-secret-access-key", "aws_secret_" + "access_key = " + "a1B2/c3D+" * 4 + "abcd"),
    ("google-api-key", "AI" + "za" + "S" * 35),
    ("stripe-live-key", "sk_" + "live_" + "x" * 24),
    ("huggingface-token", "hf" + "_" + "q" * 34),
    ("private-key-block", "-----BEGIN " + "RSA PRIVATE KEY-----"),
    ("private-key-block", "-----BEGIN " + "OPENSSH PRIVATE KEY-----"),
    ("private-key-block", "-----BEGIN " + "EC PRIVATE KEY-----"),
    ("private-key-block", "-----BEGIN " + "PRIVATE KEY-----"),
    ("private-key-block", "-----BEGIN " + "ENCRYPTED PRIVATE KEY-----"),
    ("private-key-block", "-----BEGIN " + "PGP PRIVATE KEY BLOCK-----"),
    ("macos-home-path", "/Use" + "rs/someone/project"),
    ("linux-home-path", "/ho" + "me/someone/project"),
    ("windows-home-path", "C:" + "\\" + "Users\\someone\\project"),
    ("macos-temp-path", "/private/" + "var/folders/xy/T/file"),
    ("macos-temp-path", "/private/" + "tmp/session/file"),
]


@pytest.mark.parametrize(("rule", "sample"), SECRET_SAMPLES, ids=[r for r, _ in SECRET_SAMPLES])
def test_builtin_rules_catch_each_format(rule: str, sample: str) -> None:
    assert rule in rule_ids(f"prefix {sample} suffix"), sample


@pytest.mark.parametrize(
    "text",
    [
        "the sk-learn package and a sk-short-id",
        "npm_install and npm_config_cache",
        "github_pat_ is the fine-grained token prefix",
        "ur_sk_test_mock is a short placeholder",
        "a path like /home/ alone, or ~/.config/app",
        "class NotFoundError(APIStatusError): ...",
        "-----BEGIN PUBLIC KEY-----",
    ],
)
def test_builtin_rules_ignore_lookalikes(text: str) -> None:
    assert rule_ids(text) == set()


def test_secret_file_names_are_forbidden() -> None:
    assert leak_scan.check_file_name("x", ".env")
    assert leak_scan.check_file_name("x", "config/.env.production")
    assert leak_scan.check_file_name("x", "deploy/id_ed25519")
    assert leak_scan.check_file_name("x", "certs/server.PEM")
    assert leak_scan.check_file_name("x", ".pypirc")
    assert leak_scan.check_file_name("x", ".env.example") == []
    assert leak_scan.check_file_name("x", "src/environment.py") == []


def test_content_addressed_lockfile_urls_are_neutral(tmp_path: Path) -> None:
    rules = leak_scan.load_patterns_file(
        write_patterns(tmp_path, [{"id": "hex", "regex": "/ab/", "description": "synthetic"}])
    )
    url = "https://files.pythonhosted.org/packages/ab/cd/" + "0" * 60 + "/pkg.whl"
    assert leak_scan.scan_text("uv.lock", url, (), rules) == []
    assert leak_scan.scan_text("uv.lock", "elsewhere/ab/", (), rules)


# ── extra pattern files ──


def test_patterns_file_adds_rules(tmp_path: Path) -> None:
    rules = leak_scan.load_patterns_file(write_patterns(tmp_path))
    assert [rule.id for rule in rules] == ["synthetic-codename", "synthetic-word"]
    assert all(rule.external for rule in rules)
    assert rule_ids("see zebra-123 here", rules) == {"synthetic-codename"}
    assert rule_ids("a WomBat and a quokka", rules) == {"synthetic-word"}
    assert rule_ids("see zebra-12 here", rules) == set()
    assert rule_ids("see zebra-123 here") == set(), "built-in rules alone do not know it"


def test_allowlist_masks_only_the_exact_token(tmp_path: Path) -> None:
    rules = leak_scan.load_patterns_file(write_patterns(tmp_path))
    allow = [("*", "WombatClient")]
    assert leak_scan.scan_text("x.py", "class WombatClient: ...", allow, rules) == []
    assert leak_scan.scan_text("x.py", "WombatClient and a wombat", allow, rules)
    assert leak_scan.scan_text("x.py", "class WombatClient: ...", [], rules)
    assert leak_scan.scan_text("y.py", "WombatClient", [("x.py", "WombatClient")], rules)


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("{not json", "cannot read"),
        ('{"id": "x"}', "JSON array"),
        ('["x"]', "expected an object"),
        ('[{"regex": "a", "description": "d"}]', "'id'"),
        ('[{"id": "a", "description": "d"}]', "'regex'"),
        ('[{"id": "a", "regex": "a"}]', "'description'"),
        ('[{"id": "a", "regex": "(", "description": "d"}]', "invalid regex"),
        ('[{"id": "a", "regex": "a", "flags": "g", "description": "d"}]', "'flags'"),
        ('[{"id": "a", "regex": "a", "description": "d", "extra": 1}]', "unknown key"),
        (
            '[{"id": "a", "regex": "a", "description": "d"}, '
            '{"id": "a", "regex": "b", "description": "d"}]',
            "duplicate id",
        ),
    ],
)
def test_invalid_patterns_files_are_rejected(tmp_path: Path, content: str, message: str) -> None:
    path = tmp_path / "bad.json"
    path.write_text(content, "utf-8")
    with pytest.raises(leak_scan.PatternsFileError, match=message):
        leak_scan.load_patterns_file(path)


def test_missing_patterns_file_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(leak_scan.PatternsFileError, match="not found"):
        leak_scan.load_patterns_file(tmp_path / "absent.json")


def test_patterns_file_resolution(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(leak_scan.PATTERNS_ENV_VAR, raising=False)
    assert leak_scan.resolve_patterns_file(None) is None
    monkeypatch.setenv(leak_scan.PATTERNS_ENV_VAR, str(tmp_path / "from-env.json"))
    assert leak_scan.resolve_patterns_file(None) == tmp_path / "from-env.json"
    assert leak_scan.resolve_patterns_file(str(tmp_path / "cli.json")) == tmp_path / "cli.json"


def _dist_with(tmp_path: Path, text: str) -> Path:
    dist = tmp_path / "dist"
    dist.mkdir()
    with zipfile.ZipFile(dist / "pkg-0.0.1-py3-none-any.whl", "w") as zf:
        zf.writestr("pkg/module.py", text)
    return dist


def test_cli_uses_the_environment_patterns_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    dist = _dist_with(tmp_path, "codename = 'zebra-404'\n")
    argv = ["--no-tree", "--no-history", "--dist", str(dist)]
    monkeypatch.delenv(leak_scan.PATTERNS_ENV_VAR, raising=False)
    assert leak_scan.main(argv) == 0, "generic rules only: clean"
    assert "no extra file" in capsys.readouterr().err
    monkeypatch.setenv(leak_scan.PATTERNS_ENV_VAR, str(write_patterns(tmp_path)))
    assert leak_scan.main(argv) == 1
    captured = capsys.readouterr()
    assert "[synthetic-codename]" in captured.out and "zebra-404" in captured.out
    assert "2 from the extra patterns file" in captured.err


def test_cli_redacts_external_findings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    dist = _dist_with(tmp_path, "codename = 'zebra-404'\nkey = '" + "AK" + "IA" + "B" * 16 + "'\n")
    monkeypatch.setenv(leak_scan.PATTERNS_ENV_VAR, str(write_patterns(tmp_path)))
    argv = ["--no-tree", "--no-history", "--dist", str(dist), "--redact-external"]
    assert leak_scan.main(argv) == 1
    out = capsys.readouterr().out
    assert "[external rule]" in out
    assert "zebra" not in out and "synthetic-codename" not in out
    assert "[aws-access-key-id]" in out, "built-in findings keep their excerpt"


def test_cli_fails_closed_on_a_missing_configured_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    dist = _dist_with(tmp_path, "x = 1\n")
    monkeypatch.setenv(leak_scan.PATTERNS_ENV_VAR, str(tmp_path / "absent.json"))
    assert leak_scan.main(["--no-tree", "--no-history", "--dist", str(dist)]) == 2
    assert "not found" in capsys.readouterr().err
    flag = ["--patterns-file", str(tmp_path / "gone.json")]
    assert leak_scan.main(["--no-tree", "--no-history", "--dist", str(dist), *flag]) == 2


# ── artifacts ──


def test_scanner_reads_wheels_and_sdists(tmp_path: Path) -> None:
    wheel = tmp_path / "pkg-0.0.1-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as zf:
        zf.writestr("pkg/clean.py", "x = 1\n")
        zf.writestr("pkg/dirty.py", "path = '/Use" + "rs/me'\n")
    sdist = tmp_path / "pkg-0.0.1.tar.gz"
    member = tmp_path / "member.txt"
    member.write_text("token = 'gh" + "p_" + "c" * 36 + "'\n")
    env_file = tmp_path / "dotenv"
    env_file.write_text("A=1\n")
    with tarfile.open(sdist, "w:gz") as tf:
        tf.add(member, arcname="pkg-0.0.1/member.txt")
        tf.add(env_file, arcname="pkg-0.0.1/.env")
    _, findings = leak_scan.scan(leak_scan.iter_dist(tmp_path), [])
    assert sorted((f.location, f.rule) for f in findings) == [
        ("pkg-0.0.1-py3-none-any.whl!pkg/dirty.py", "macos-home-path"),
        ("pkg-0.0.1.tar.gz!pkg-0.0.1/.env", "forbidden-file"),
        ("pkg-0.0.1.tar.gz!pkg-0.0.1/member.txt", "github-token"),
    ]


# ── git history ──


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        [
            "git",
            "-c",
            "user.name=Synthetic",
            "-c",
            "user.email=synthetic@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "init.defaultBranch=main",
            *args,
        ],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
def test_history_scan_finds_removed_secrets_messages_and_merges(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "README.md").write_text("clean\n")
    (repo / "config.py").write_text("x = 1\nkey = '" + "AK" + "IA" + "C" * 16 + "'\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "add config\n\nmentions zebra-777 in the body")
    (repo / "config.py").unlink()
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "remove config")
    # an "evil merge": content introduced only by the merge commit itself
    _git(repo, "checkout", "-q", "-b", "side")
    (repo / "side.txt").write_text("side\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "side")
    _git(repo, "checkout", "-q", "main")
    (repo / "main.txt").write_text("main\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "main")
    _git(repo, "merge", "-q", "--no-ff", "--no-commit", "side")
    (repo / "merged.txt").write_text("one\ntwo\nwombat\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "merge side")

    tree_count, tree_findings = leak_scan.scan(leak_scan.iter_tree(repo), [])
    assert tree_count == 4
    assert [f.rule for f in tree_findings] == [], "the working tree no longer has the key"

    rules = [*leak_scan.BUILTIN_RULES, *leak_scan.load_patterns_file(write_patterns(tmp_path))]
    commits, findings = leak_scan.scan_history(leak_scan.iter_history(repo), [], rules)
    assert commits == 5
    found = {(f.location.split(":", 2)[2], f.line, f.rule) for f in findings}
    assert ("config.py", 2, "aws-access-key-id") in found
    assert ("<message>", 3, "synthetic-codename") in found
    assert ("merged.txt", 3, "synthetic-word") in found
    assert all(f.location.startswith("history:") for f in findings)


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
def test_history_scan_flags_committed_secret_files(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / ".env").write_text("TOKEN=placeholder\n")
    _git(repo, "add", "-f", ".env")
    _git(repo, "commit", "-q", "-m", "oops")
    _git(repo, "rm", "-q", "--cached", ".env")
    _git(repo, "commit", "-q", "-m", "untrack")
    _, findings = leak_scan.scan_history(leak_scan.iter_history(repo), [])
    assert {f.rule for f in findings} == {"forbidden-file"}
    assert len(findings) == 2, "reported where it was added and where it was removed"


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
def test_history_scan_enumerates_binary_empty_and_deleted_files(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "README.md").write_text("clean\n")
    (repo / "keystore.p12").write_bytes(b"\x30\x82\x00\x01binary-bundle\x00\xff")
    (repo / ".npmrc").write_bytes(b"")  # an empty file has no patch text at all
    (repo / ".gitattributes").write_text("*.dat -diff\n")
    # git shows "Binary files differ" for -diff files, so a patch never reveals this content
    (repo / "notes.dat").write_text("key = '" + "AK" + "IA" + "D" * 16 + "'\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "add files")
    for name in ("keystore.p12", ".npmrc", "notes.dat"):
        (repo / name).unlink()
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "remove them")

    assert [f.rule for f in leak_scan.scan(leak_scan.iter_tree(repo), [])[1]] == []
    commits, findings = leak_scan.scan_history(leak_scan.iter_history(repo), [])
    assert commits == 2
    found = {(f.location.split(":", 2)[2], f.rule) for f in findings}
    assert ("keystore.p12", "forbidden-file") in found
    assert (".npmrc", "forbidden-file") in found
    assert ("notes.dat", "aws-access-key-id") in found


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
def test_history_scan_reports_where_content_was_introduced(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "app.py").write_text("x = 1\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "one")
    first = _git(repo, "rev-parse", "--short=12", "HEAD").strip()
    (repo / "app.py").write_text("x = 1\ntoken = 'gh" + "p_" + "e" * 36 + "'\n")
    _git(repo, "commit", "-q", "-am", "two")
    second = _git(repo, "rev-parse", "--short=12", "HEAD").strip()
    _, findings = leak_scan.scan_history(leak_scan.iter_history(repo), [])
    assert [(f.location, f.line, f.rule) for f in findings] == [
        (f"history:{second}:app.py", 2, "github-token")
    ]
    assert first != second


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
def test_history_scan_of_a_repository_without_commits(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    assert leak_scan.scan_history(leak_scan.iter_history(repo), []) == (0, [])
