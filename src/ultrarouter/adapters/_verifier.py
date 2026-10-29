"""Verifier adapters: turn a computable check or a test suite into a verdict.

A verifier decides whether a task succeeded from evidence it can compute (a test suite, an
arithmetic check, a function over the final state). Its verdict is ``pass``, ``fail`` or
``unknown``; a verifier that cannot decide (it crashed, timed out, the process was killed) says
``unknown``, which reports nothing: a broken check is never evidence that the task failed. Only the
evidence *hash* is ever sent; the evidence stays in your process.

The semantics, reasons and evidence hash match the TypeScript SDK's ``runVerifier`` and
``verdictFromCommand``.
"""

from __future__ import annotations

import os
import signal
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from .._jscompat import canonical_json
from .._verdicts import OutcomeSource, Verdict
from ..context._hash import sha256_hex

__all__ = [
    "VerifierResult",
    "evidence_hash",
    "run_test_suite",
    "run_verifier",
    "verdict_from_command",
]


def evidence_hash(evidence: Any) -> str:
    """``"sha256:"`` plus the hex SHA-256 of the canonical JSON of ``evidence`` (keys sorted
    recursively, JavaScript-compatible numbers): what an outcome carries as ``evidence_hash``
    instead of the evidence. The same value hashes the same in the TypeScript SDK."""
    return "sha256:" + sha256_hex(canonical_json(evidence))


@dataclass(frozen=True)
class VerifierResult:
    """A verifier's verdict, the hash of its evidence and the local reasons. Report it with::

    from ultrarouter.adapters import run_verifier

    result = run_verifier(lambda: 2 + 2 == 4)
    assert result.verdict == "pass"
    # client.outcomes.report(request_id, result.verdict, source=result.source,
    #                        evidence_hash=result.evidence_hash)
    """

    verdict: Verdict
    """``pass``, ``fail`` or ``unknown`` (``unknown`` reports nothing)."""

    reasons: tuple[str, ...] = ()
    """Why, in short machine-readable phrases (kept locally; never sent)."""

    source: OutcomeSource = "verifier"
    """The outcome source to report it under."""

    evidence_hash: str | None = None
    """``sha256:<hex>`` over the canonical JSON of the evidence, or ``None`` when there is none."""

    details: Mapping[str, Any] = field(default_factory=dict)
    """Anything else the verifier keeps locally, such as a test suite's output (never sent)."""

    @property
    def passed(self) -> bool:
        """Whether the verdict is ``pass``."""
        return self.verdict == "pass"


Check = Callable[[], Any]
"""A check: returns ``True``/``False``, a mapping ``{"pass": bool, "evidence"?: ...,
"reasons"?: [...]}``, or a :class:`VerifierResult`."""


def run_verifier(
    check: Check,
    *,
    on_error: Literal["unknown", "fail"] = "unknown",
    source: Literal["verifier", "business_rule"] = "verifier",
) -> VerifierResult:
    """Run a computable check and turn its answer into a :class:`VerifierResult`.

    ``check`` returns ``True`` (pass) or ``False`` (fail); or a mapping with a boolean ``"pass"``
    and optional ``"evidence"`` (hashed into ``evidence_hash``) and ``"reasons"``; or a full
    :class:`VerifierResult`. Anything else is ``unknown`` (``check_returned_no_verdict``).

    A check that raises is ``unknown`` (``verifier_error``: a crashed verifier is not evidence
    that the task failed), unless ``on_error="fail"`` (``check_threw``). An ``AssertionError`` is
    always a ``fail``: in Python a failing assertion is how a check says no.
    """
    try:
        answer: object = check()
    except Exception as exc:
        if on_error == "fail" or isinstance(exc, AssertionError):
            return VerifierResult(
                "fail", ("check_threw",), source, evidence_hash({"error": type(exc).__name__})
            )
        return VerifierResult("unknown", ("verifier_error",), source)
    if isinstance(answer, VerifierResult):
        return answer
    if isinstance(answer, bool):
        return VerifierResult("pass" if answer else "fail", (), source)
    if isinstance(answer, Mapping) and isinstance(answer.get("pass"), bool):
        reasons = answer.get("reasons") or ()
        return VerifierResult(
            "pass" if answer["pass"] else "fail",
            tuple(str(r) for r in reasons),
            source,
            evidence_hash(answer["evidence"]) if answer.get("evidence") is not None else None,
        )
    return VerifierResult("unknown", ("check_returned_no_verdict",), source)


def verdict_from_command(
    exit_code: int | None,
    *,
    stdout: str = "",
    stderr: str = "",
    signal_name: str | None = None,
    unknown_codes: Sequence[int] = (),
) -> VerifierResult:
    """A command's verdict: exit code ``0`` passes, any other exit code fails, and a process killed
    by a signal (no exit code) is ``unknown``. ``unknown_codes`` marks exit codes that mean "could
    not decide" (for example pytest's ``5``, no tests collected). The evidence hash covers the exit
    code, the signal and both outputs; the outputs are kept locally in ``details``."""
    evidence = {
        "exit_code": exit_code,
        "signal": signal_name,
        "stdout": stdout,
        "stderr": stderr,
    }
    digest = evidence_hash(evidence)
    details = {"exit_code": exit_code, "signal": signal_name, "stdout": stdout, "stderr": stderr}
    if exit_code is None:
        return VerifierResult(
            "unknown", (f"killed_by_{signal_name or 'signal'}",), "verifier", digest, details
        )
    if exit_code == 0:
        return VerifierResult("pass", (), "verifier", digest, details)
    verdict: Verdict = "unknown" if exit_code in unknown_codes else "fail"
    return VerifierResult(verdict, (f"exit_code_{exit_code}",), "verifier", digest, details)


def run_test_suite(
    command: Sequence[str | os.PathLike[str]],
    *,
    cwd: str | os.PathLike[str] | None = None,
    env: Mapping[str, str] | None = None,
    timeout: float = 600.0,
    unknown_codes: Sequence[int] = (),
) -> VerifierResult:
    """Run a test suite as a subprocess and judge it with :func:`verdict_from_command`.

    ``command`` is an argument list (never a shell string), for example
    ``["python", "-m", "pytest", "-q", "tests/test_task.py"]`` (pass ``unknown_codes=(5,)`` so
    "no tests collected" is not a fail). A missing program (``command_not_found``) or a timeout
    (``timed_out``) is ``unknown``.
    """
    argv = [os.fspath(part) for part in command]
    if not argv:
        return VerifierResult("unknown", ("empty_command",))
    try:
        completed = subprocess.run(  # noqa: S603 - an argument list chosen by the caller, no shell
            argv,
            cwd=cwd,
            env=dict(env) if env is not None else None,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return VerifierResult("unknown", ("command_not_found",))
    except subprocess.TimeoutExpired:
        return VerifierResult("unknown", ("timed_out",))
    stdout = completed.stdout.decode("utf-8", "replace")
    stderr = completed.stderr.decode("utf-8", "replace")
    code: int | None = completed.returncode
    name: str | None = None
    if code is not None and code < 0:  # killed by a signal (POSIX)
        try:
            name = signal.Signals(-code).name
        except ValueError:
            name = f"signal_{-code}"
        code = None
    return verdict_from_command(
        code, stdout=stdout, stderr=stderr, signal_name=name, unknown_codes=unknown_codes
    )
