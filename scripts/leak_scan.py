#!/usr/bin/env python3
"""Fail if the repository, its git history or its built distributions contain secrets.

Three sources are scanned:

* **tree**: every file git would ship (tracked files plus untracked, non-ignored files);
* **history** (on by default inside a git repository): every commit reachable from any ref: its
  message, the name of every path it changes (listed from git's raw output against each parent,
  so binary, empty and deleted files and merges are covered) and the content of every distinct
  blob it introduces (read from the object store, independent of diff settings);
* **dist** (``--dist DIR``): every member of each wheel (``.whl``) and sdist (``.tar.gz``).

The built-in rules are generic: credential formats (API keys and tokens of common providers,
private-key blocks), absolute local paths (macOS, Linux and Windows home directories, macOS
temporary directories) and committed secret files (``.env``, private keys, package-registry
credentials). The rules are written so that this file never matches itself (``sk-(?:ant)-``).

Organisation-specific rules are not part of this repository. Supply them as a JSON file with
``--patterns-file PATH`` or the ``ULTRAROUTER_LEAK_PATTERNS_FILE`` environment variable: a JSON
array of ``{"id": str, "regex": str, "flags"?: str, "description": str}`` objects. ``flags`` may
contain ``i`` (ignore case), ``m`` (multi-line), ``s`` (dot matches newline) and ``u`` (no-op);
regexes should use the syntax Python and JavaScript share. A configured file that is missing or
invalid is an error (exit 2), never a silent fallback. With ``--redact-external`` (for public CI
logs), findings of those rules print only their location.

Usage::

    python scripts/leak_scan.py                       # tree + history
    python scripts/leak_scan.py --dist dist           # tree + history + built artifacts
    python scripts/leak_scan.py --no-tree --no-history --dist dist

The allowlist file (``scripts/leak_scan_allowlist.txt``) holds exact masks, one per line:
``<path glob>:<exact substring>  # justification``. Inside files matching the glob, that exact
substring is blanked out before the rules run, so a mask can never hide anything else on the
same line.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
import tarfile
import zipfile
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST_PATH = ROOT / "scripts" / "leak_scan_allowlist.txt"
PATTERNS_ENV_VAR = "ULTRAROUTER_LEAK_PATTERNS_FILE"


@dataclass(frozen=True)
class Rule:
    """One scanning rule: an id, a compiled regex, a description and where it came from."""

    id: str
    pattern: re.Pattern[str]
    description: str
    external: bool = False


def _rule(rule_id: str, regex: str, description: str, flags: int = 0) -> Rule:
    return Rule(rule_id, re.compile(regex, flags), description)


#: The generic, built-in rules.
BUILTIN_RULES: tuple[Rule, ...] = (
    # ── credentials ──
    _rule("anthropic-api-key", r"sk-(?:ant)-", "Anthropic API key prefix"),
    _rule(
        "openai-api-key",
        r"\bsk-(?!ant-)(?:proj-|svcacct-|admin-)?[A-Za-z0-9_-]{32,}",
        "OpenAI API key (sk-, sk-proj-, sk-svcacct-, sk-admin-)",
    ),
    _rule("ultrarouter-api-key", r"ur_sk_(?:live|test)_[A-Za-z0-9]{24,}", "ultrarouter API key"),
    _rule("github-token", r"\bgh[pousr]_[A-Za-z0-9]{30,}", "GitHub classic or app token"),
    _rule("github-fine-grained-token", r"\bgithub_pat_[A-Za-z0-9_]{40,}", "GitHub fine-grained"),
    _rule("npm-token", r"\bnpm_[A-Za-z0-9]{36}\b", "npm access token"),
    _rule("pypi-token", r"\bpypi-AgEIcHlwaS5vcmc[A-Za-z0-9_-]{16,}", "PyPI API token"),
    _rule("slack-token", r"\bxox[abposr]-", "Slack token"),
    _rule("slack-app-token", r"\bxapp-[0-9]+-[A-Za-z0-9-]+", "Slack app-level token"),
    _rule(
        "slack-webhook",
        r"hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[A-Za-z0-9]+",
        "Slack incoming-webhook URL",
    ),
    _rule(
        "aws-access-key-id",
        r"\b(?:AKIA|ASIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA)[0-9A-Z]{16}\b",
        "AWS access key id",
    ),
    _rule(
        "aws-secret-access-key",
        r"aws_?secret_?access_?key[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9/+]{40}\b",
        "AWS secret access key assignment",
        re.IGNORECASE,
    ),
    _rule("google-api-key", r"\bAIza[0-9A-Za-z_-]{35}\b", "Google API key"),
    _rule("stripe-live-key", r"\b(?:sk|rk)_live_[0-9A-Za-z]{24,}", "Stripe live secret key"),
    _rule("huggingface-token", r"\bhf_[A-Za-z0-9]{34,}", "Hugging Face access token"),
    _rule(
        "private-key-block",
        r"-----BEGIN [A-Z ]*PRIVATE KEY(?: BLOCK)?-----",
        "PEM / OpenSSH / PGP private key block",
    ),
    # ── absolute local paths ──
    _rule("macos-home-path", r"/(?:Users)/", "absolute macOS home path"),
    _rule("linux-home-path", r"/home/[a-z_][a-z0-9_.-]*/", "absolute Linux home path"),
    _rule("windows-home-path", r"\b[A-Za-z]:\\{1,2}Users\\{1,2}", "absolute Windows home path"),
    _rule("macos-temp-path", r"/private/(?:var/folders|tmp)/", "macOS temporary directory"),
)

#: Committed files that should never ship, matched against the basename (fnmatch, any case).
FORBIDDEN_FILES: tuple[tuple[str, str], ...] = (
    (".env", "environment file"),
    (".env.*", "environment file"),
    ("*.pem", "PEM file"),
    ("*.p12", "PKCS #12 bundle"),
    ("*.pfx", "PKCS #12 bundle"),
    ("id_rsa", "SSH private key"),
    ("id_dsa", "SSH private key"),
    ("id_ecdsa", "SSH private key"),
    ("id_ed25519", "SSH private key"),
    (".npmrc", "npm credentials file"),
    (".pypirc", "PyPI credentials file"),
)
_FORBIDDEN_FILE_EXCEPTIONS = frozenset({".env.example", ".env.sample", ".env.template"})

#: Content-addressed download URLs in lockfiles: the hex path segments are hashes, not text.
_NEUTRAL = (re.compile(r"files\.pythonhosted\.org/packages/[0-9a-f]{2}/[0-9a-f]{2}/[0-9a-f]{60}/"),)

_BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".pyc"}
_ALLOWED_FLAGS = {"i": re.IGNORECASE, "m": re.MULTILINE, "s": re.DOTALL, "u": 0}
_PATTERN_KEYS = {"id", "regex", "flags", "description"}


class PatternsFileError(ValueError):
    """The extra patterns file is missing, unreadable or invalid."""


@dataclass(frozen=True)
class Finding:
    """One forbidden match."""

    location: str
    line: int
    rule: str
    excerpt: str
    external: bool = False

    def render(self, *, redact_external: bool = False) -> str:
        """Human-readable form: ``location:line: [rule] excerpt``."""
        if self.external and redact_external:
            return f"{self.location}:{self.line}: [external rule]"
        return f"{self.location}:{self.line}: [{self.rule}] {self.excerpt}"


# ─────────────────────────────── rules and masks ───────────────────────────────


def load_patterns_file(path: str | os.PathLike[str]) -> list[Rule]:
    """Load extra rules from a JSON patterns file (see the module docstring for the format)."""
    file = Path(path)
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PatternsFileError(f"patterns file not found: {file}") from exc
    except (OSError, ValueError) as exc:
        raise PatternsFileError(f"cannot read patterns file {file}: {exc}") from exc
    if not isinstance(data, list):
        raise PatternsFileError(f"{file}: expected a JSON array of pattern objects")
    rules: list[Rule] = []
    seen: set[str] = set()
    for index, item in enumerate(data):
        where = f"{file}: entry {index}"
        if not isinstance(item, dict):
            raise PatternsFileError(f"{where}: expected an object")
        unknown = set(item) - _PATTERN_KEYS
        if unknown:
            raise PatternsFileError(f"{where}: unknown key(s) {sorted(unknown)}")
        rule_id, regex = item.get("id"), item.get("regex")
        description, flags = item.get("description"), item.get("flags", "")
        if not isinstance(rule_id, str) or not rule_id:
            raise PatternsFileError(f"{where}: 'id' must be a non-empty string")
        if rule_id in seen:
            raise PatternsFileError(f"{where}: duplicate id {rule_id!r}")
        if not isinstance(regex, str) or not regex:
            raise PatternsFileError(f"{where} ({rule_id}): 'regex' must be a non-empty string")
        if not isinstance(description, str) or not description:
            raise PatternsFileError(f"{where} ({rule_id}): 'description' must be a string")
        if not isinstance(flags, str) or set(flags) - set(_ALLOWED_FLAGS):
            raise PatternsFileError(f"{where} ({rule_id}): 'flags' may contain only i, m, s, u")
        compiled_flags = 0
        for flag in flags:
            compiled_flags |= _ALLOWED_FLAGS[flag]
        try:
            pattern = re.compile(regex, compiled_flags)
        except re.error as exc:
            raise PatternsFileError(f"{where} ({rule_id}): invalid regex: {exc}") from exc
        seen.add(rule_id)
        rules.append(Rule(rule_id, pattern, description, external=True))
    return rules


def resolve_patterns_file(cli_value: str | None) -> Path | None:
    """The configured patterns file: ``--patterns-file`` first, then the environment variable."""
    value = cli_value or os.environ.get(PATTERNS_ENV_VAR)
    return Path(value).expanduser() if value else None


def load_allowlist(path: Path = ALLOWLIST_PATH) -> list[tuple[str, str]]:
    """Read ``<path glob>:<substring>  # reason`` masks (blank lines and comments ignored)."""
    entries: list[tuple[str, str]] = []
    if not path.exists():
        return entries
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        spec, _, reason = line.partition("  #")
        if not reason.strip():
            raise ValueError(f"allowlist entry without a '  # reason': {raw!r}")
        glob, sep, substring = spec.strip().partition(":")
        if not sep or not substring:
            raise ValueError(f"allowlist entry must be '<path glob>:<substring>': {raw!r}")
        entries.append((glob, substring))
    return entries


def _masks_for(path: str, allowlist: Iterable[tuple[str, str]]) -> list[str]:
    if path.endswith(ALLOWLIST_PATH.relative_to(ROOT).as_posix()):
        # The allowlist file necessarily contains every allowed substring.
        return [sub for _, sub in allowlist]
    return [sub for glob, sub in allowlist if fnmatch.fnmatch(path, glob)]


def _member_path(location: str) -> str:
    return location.split("!")[-1]


def scan_text(
    location: str,
    text: str,
    allowlist: Iterable[tuple[str, str]] = (),
    rules: Sequence[Rule] = BUILTIN_RULES,
    *,
    path: str | None = None,
    first_line: int = 1,
) -> list[Finding]:
    """Return every forbidden match in ``text`` after the allowlist and neutral masks.

    ``path`` is the file path the allowlist globs are matched against (default: the location's
    member path); ``first_line`` numbers the first line of ``text``.
    """
    return scan_lines(
        location,
        list(enumerate(text.splitlines(), start=first_line)),
        allowlist,
        rules,
        path=path,
    )


def scan_lines(
    location: str,
    lines: Sequence[tuple[int, str]],
    allowlist: Iterable[tuple[str, str]] = (),
    rules: Sequence[Rule] = BUILTIN_RULES,
    *,
    path: str | None = None,
) -> list[Finding]:
    """Like :func:`scan_text` for ``(line number, line)`` pairs (for example one blob's lines)."""
    masks = _masks_for(path if path is not None else _member_path(location), allowlist)
    masked = _mask("\n".join(line for _, line in lines), masks)
    # Only rules that match somewhere in the (masked) text need the line-by-line pass.
    candidates = [rule for rule in rules if _prefilter(rule.pattern).search(masked) is not None]
    findings: list[Finding] = []
    if not candidates:
        return findings
    for number, original in lines:
        line = _mask(original, masks)
        for rule in candidates:
            match = rule.pattern.search(line)
            if match is not None:
                start = max(0, match.start() - 30)
                excerpt = original[start : match.end() + 30].strip()
                findings.append(Finding(location, number, rule.id, excerpt, rule.external))
    return findings


def _mask(text: str, masks: Sequence[str]) -> str:
    for sub in masks:
        text = text.replace(sub, " " * len(sub))
    for neutral in _NEUTRAL:
        text = neutral.sub(lambda m: " " * len(m.group(0)), text)
    return text


_PREFILTERS: dict[re.Pattern[str], re.Pattern[str]] = {}


def _prefilter(pattern: re.Pattern[str]) -> re.Pattern[str]:
    # The same rule over a whole text, with ``^``/``$`` at line boundaries as in the line pass.
    compiled = _PREFILTERS.get(pattern)
    if compiled is None:
        compiled = re.compile(pattern.pattern, pattern.flags | re.MULTILINE)
        _PREFILTERS[pattern] = compiled
    return compiled


def check_file_name(location: str, path: str) -> list[Finding]:
    """Findings for a committed file whose name marks it as a secret (``.env``, keys, ...)."""
    name = PurePosixPath(path).name
    if name.lower() in _FORBIDDEN_FILE_EXCEPTIONS:
        return []
    for glob, what in FORBIDDEN_FILES:
        if fnmatch.fnmatch(name.lower(), glob):
            return [Finding(location, 0, "forbidden-file", f"{what}: {path}")]
    return []


def _decode(data: bytes) -> str | None:
    if b"\x00" in data[:8192]:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1")


# ─────────────────────────────── sources ───────────────────────────────


def is_git_repository(root: Path = ROOT) -> bool:
    """Whether ``root`` is inside a git work tree."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False
    return result.returncode == 0 and result.stdout.strip() == "true"


def tree_files(root: Path = ROOT) -> list[Path]:
    """Files git would ship: tracked plus untracked-but-not-ignored."""
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout
    paths = [root / p for p in out.decode("utf-8").split("\0") if p]
    return sorted(p for p in paths if p.is_file())


def iter_tree(root: Path = ROOT) -> Iterator[tuple[str, bytes]]:
    """Yield ``(relative path, bytes)`` for every shippable file in the working tree."""
    for path in tree_files(root):
        yield path.relative_to(root).as_posix(), path.read_bytes()


def iter_dist(dist: Path) -> Iterator[tuple[str, bytes]]:
    """Yield ``(archive!member, bytes)`` for every member of each wheel and sdist in ``dist``."""
    for archive in sorted(dist.iterdir()):
        if archive.suffix == ".whl":
            with zipfile.ZipFile(archive) as zf:
                for name in zf.namelist():
                    if not name.endswith("/"):
                        yield f"{archive.name}!{name}", zf.read(name)
        elif archive.name.endswith(".tar.gz"):
            with tarfile.open(archive, "r:gz") as tf:
                for member in tf.getmembers():
                    if member.isfile():
                        handle = tf.extractfile(member)
                        if handle is not None:
                            yield f"{archive.name}!{member.name}", handle.read()


@dataclass
class HistoryChunk:
    """Text from git history to scan: a commit message, a changed path, or a blob's content.

    ``path`` is ``None`` for a commit message. A changed-path chunk (``lines`` empty) is checked
    for a forbidden file name; a content chunk carries the lines of one blob version.
    """

    location: str
    path: str | None
    lines: list[tuple[int, str]]


_NO_BLOB = "0" * 40
_SUBMODULE_MODE = "160000"


def _git_output(root: Path, *args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True).stdout


def _changed_paths(root: Path) -> list[tuple[str, str, str, str]]:
    """Every path every reachable commit changes: ``(commit, status, path, new blob, new mode)``.

    Uses git's own raw output (``--raw -z``), so binary files, empty files and deletions are all
    listed (a patch shows none of their names as text). Root commits and every parent of a merge
    are included, newest commit first.
    """
    out = _git_output(
        root,
        "log",
        "--all",
        "--root",
        "-m",
        "--raw",
        "-z",
        "--no-abbrev",
        "--no-renames",
        "--no-ext-diff",
        "--format=%x01%H",
    )
    changes: list[tuple[str, str, str, str]] = []
    for block in out.split(b"\x01")[1:]:
        sha, _, rest = block.partition(b"\0")
        tokens = rest.split(b"\0")
        index = 0
        while index + 1 < len(tokens):
            meta = tokens[index].lstrip(b"\n")
            if not meta.startswith(b":"):
                index += 1
                continue
            fields = meta[1:].decode("ascii", "replace").split(" ")
            path = tokens[index + 1].decode("utf-8", "replace")
            if len(fields) >= 5:
                _, new_mode, _, new_blob, status = fields[:5]
                changes.append(
                    (sha.decode("ascii")[:12], status[:1], path, f"{new_blob} {new_mode}")
                )
            index += 2
    return changes


def _blobs(root: Path, shas: Iterable[str]) -> Iterator[tuple[str, bytes]]:
    """Yield ``(sha, content)`` for each blob, read through one ``git cat-file --batch``."""
    process = subprocess.Popen(
        ["git", "cat-file", "--batch"], cwd=root, stdin=subprocess.PIPE, stdout=subprocess.PIPE
    )
    if process.stdin is None or process.stdout is None:  # pragma: no cover - PIPE always set
        raise RuntimeError("git cat-file pipes are unavailable")
    try:
        for sha in shas:
            process.stdin.write(sha.encode("ascii") + b"\n")
            process.stdin.flush()
            header = process.stdout.readline().split()
            if len(header) != 3 or header[1] != b"blob":
                continue  # "<sha> missing" or not a blob
            content = process.stdout.read(int(header[2]))
            process.stdout.read(1)  # the newline after the content
            yield sha, content
    finally:
        process.stdin.close()
        process.wait()


def iter_history(root: Path = ROOT) -> Iterator[HistoryChunk]:
    """Yield what every commit reachable from any ref contributed: its message, every path it
    changed (for the file-name check, including binary, empty and deleted files) and, once per
    distinct blob, the content it introduced (whatever git's diff settings would show)."""
    if not _git_output(root, "for-each-ref", "--count=1").strip():
        return  # no commits yet
    log = _git_output(root, "log", "--all", "--format=%x01%H%x00%B")
    for block in log.split(b"\x01")[1:]:
        sha, _, body = block.partition(b"\0")
        lines = body.decode("utf-8", "replace").splitlines()
        yield HistoryChunk(
            f"history:{sha.decode('ascii')[:12]}:<message>",
            None,
            list(enumerate(lines, start=1)),
        )
    first_seen: dict[str, tuple[str, str]] = {}
    for commit, _status, path, blob in _changed_paths(root):
        yield HistoryChunk(f"history:{commit}:{path}", path, [])
        sha, mode = blob.split(" ")
        if sha != _NO_BLOB and mode != _SUBMODULE_MODE:
            first_seen[sha] = (commit, path)  # newest first: the last write is the oldest commit
    for sha, content in _blobs(root, list(first_seen)):
        commit, path = first_seen[sha]
        text = _decode(content)
        if text is None or PurePosixPath(path).suffix.lower() in _BINARY_SUFFIXES:
            continue
        yield HistoryChunk(
            f"history:{commit}:{path}", path, list(enumerate(text.splitlines(), start=1))
        )


# ─────────────────────────────── scanning ───────────────────────────────


def scan(
    sources: Iterable[tuple[str, bytes]],
    allowlist: list[tuple[str, str]],
    rules: Sequence[Rule] = BUILTIN_RULES,
) -> tuple[int, list[Finding]]:
    """Scan ``sources`` (``(location, bytes)`` pairs); return (files scanned, findings)."""
    count = 0
    findings: list[Finding] = []
    for location, data in sources:
        path = _member_path(location)
        findings.extend(check_file_name(location, path))
        if PurePosixPath(path).suffix.lower() in _BINARY_SUFFIXES:
            continue
        text = _decode(data)
        if text is None:
            continue
        count += 1
        findings.extend(scan_text(location, text, allowlist, rules))
    return count, findings


def scan_history(
    chunks: Iterable[HistoryChunk],
    allowlist: list[tuple[str, str]],
    rules: Sequence[Rule] = BUILTIN_RULES,
) -> tuple[int, list[Finding]]:
    """Scan git history chunks; return (commits scanned, findings)."""
    commits: set[str] = set()
    findings: list[Finding] = []
    for chunk in chunks:
        commits.add(chunk.location.split(":")[1])
        if chunk.path is not None and not chunk.lines:
            findings.extend(check_file_name(chunk.location, chunk.path))
            continue
        findings.extend(
            scan_lines(
                chunk.location,
                chunk.lines,
                allowlist,
                rules,
                path=chunk.path if chunk.path is not None else "<commit message>",
            )
        )
    return len(commits), findings


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point; exit 0 when clean, 1 on findings, 2 on a usage error."""
    parser = argparse.ArgumentParser(description="Scan for secrets and internal references.")
    parser.add_argument("--dist", type=Path, help="also scan wheels/sdists in this directory")
    parser.add_argument("--no-tree", action="store_true", help="skip the working tree")
    parser.add_argument("--no-history", action="store_true", help="skip the git history")
    parser.add_argument(
        "--patterns-file",
        help=f"extra rules (JSON); default: the {PATTERNS_ENV_VAR} environment variable",
    )
    parser.add_argument(
        "--redact-external",
        action="store_true",
        help="print only the location of findings from the extra rules (for public logs)",
    )
    args = parser.parse_args(argv)

    rules: list[Rule] = list(BUILTIN_RULES)
    patterns_file = resolve_patterns_file(args.patterns_file)
    external = 0
    if patterns_file is not None:
        try:
            extra = load_patterns_file(patterns_file)
        except PatternsFileError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        external = len(extra)
        rules += extra
    allowlist = load_allowlist()
    in_git = is_git_repository(ROOT)

    findings: list[Finding] = []
    summary: list[str] = []
    if not args.no_tree:
        if not in_git:
            print("error: the working-tree scan needs a git checkout", file=sys.stderr)
            return 2
        n, f = scan(iter_tree(), allowlist, rules)
        findings += f
        summary.append(f"{n} tree file(s)")
    if not args.no_history and in_git:
        n, f = scan_history(iter_history(), allowlist, rules)
        findings += f
        summary.append(f"{n} commit(s)")
    if args.dist is not None:
        if not args.dist.is_dir():
            print(f"error: --dist {args.dist} is not a directory", file=sys.stderr)
            return 2
        n, f = scan(iter_dist(args.dist), allowlist, rules)
        findings += f
        summary.append(f"{n} distribution member(s)")

    findings = list(dict.fromkeys(findings))  # a merge commit is diffed against each parent
    for finding in findings:
        print(finding.render(redact_external=args.redact_external))
    source = f"{external} from the extra patterns file" if patterns_file else "no extra file"
    status = "FAIL" if findings else "OK"
    print(
        f"leak scan {status}: {len(findings)} finding(s) in {', '.join(summary) or 'nothing'}; "
        f"rules: {len(BUILTIN_RULES)} built-in, {source}",
        file=sys.stderr,
    )
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
