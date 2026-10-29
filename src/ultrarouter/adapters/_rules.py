"""Structured-output and business-rule validation (pydantic-based) as a verdict.

``validate_output(output, Model, rules={...})`` parses a model's structured output, validates it
with a pydantic model and applies your business rules. A validator always decides, so the verdict
is ``pass`` or ``fail``, never ``unknown``:

* the output is not JSON: ``fail`` with ``invalid_json``;
* it does not validate: ``fail``, one ``"<field path>: <message>"`` reason per problem;
* a rule returns ``False``: ``fail`` with the rule's name; a rule returning a string fails with
  ``"<name>: <string>"``; a rule that raises fails with ``"<name>: <exception class>"``;
* otherwise ``pass``.

Rules run only on a valid value. The evidence hash covers the validated value (the decoded output
when it does not validate, ``{"text": ...}`` when it is not JSON). Reasons name fields and rules;
they never quote the output. The semantics match the TypeScript SDK's ``validateOutput``.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Generic, Literal, TypeVar

import pydantic

from .._verdicts import Verdict
from ._verifier import evidence_hash

__all__ = ["Rule", "ValidationResult", "validate_output"]

ModelT = TypeVar("ModelT", bound=pydantic.BaseModel)

Rule = Callable[[Any], "bool | str | None"]
"""A business rule: takes the validated model; ``True`` or ``None`` when it holds, ``False`` or a
reason string when it does not."""


@dataclass(frozen=True)
class ValidationResult(Generic[ModelT]):
    """The verdict of :func:`validate_output`, and the validated value when it validated."""

    verdict: Verdict
    """``pass`` or ``fail``."""

    reasons: tuple[str, ...] = ()
    """Field problems and failed rules (names and messages, never the output's values)."""

    value: ModelT | None = None
    """The validated model, when the output validated."""

    source: Literal["business_rule"] = "business_rule"
    """The outcome source to report it under (always ``business_rule``)."""

    evidence_hash: str | None = None
    """``sha256:<hex>`` over the canonical JSON of the decoded output."""

    failed_rules: tuple[str, ...] = field(default=())
    """The names of the rules that did not hold."""

    @property
    def passed(self) -> bool:
        """Whether the verdict is ``pass``."""
        return self.verdict == "pass"


def _path(location: tuple[int | str, ...]) -> str:
    return "$" + "".join(f"[{p}]" if isinstance(p, int) else f".{p}" for p in location)


def validate_output(
    output: str | bytes | Mapping[str, Any] | pydantic.BaseModel,
    model: type[ModelT],
    *,
    rules: Mapping[str, Rule] | None = None,
) -> ValidationResult[ModelT]:
    """Validate structured output against ``model`` and the named business ``rules``.

    Example::

        from pydantic import BaseModel

        from ultrarouter.adapters import validate_output

        class Refund(BaseModel):
            order_id: str
            amount: float

        result = validate_output(
            '{"order_id": "A-100", "amount": 12.5}',
            Refund,
            rules={"amount is positive": lambda r: r.amount > 0},
        )
        assert result.verdict == "pass" and result.value is not None

    Args:
        output: The raw JSON text (``str`` / ``bytes``), an already decoded mapping, or a model.
        model: The pydantic model the output must satisfy.
        rules: Business rules by name; each takes the validated model.
    """
    decoded: Any
    if isinstance(output, (str, bytes)):
        text = output.decode("utf-8", "replace") if isinstance(output, bytes) else output
        try:
            decoded = json.loads(text)
        except ValueError:
            return ValidationResult(
                "fail", ("invalid_json",), evidence_hash=evidence_hash({"text": text})
            )
    elif isinstance(output, pydantic.BaseModel):
        decoded = output.model_dump(mode="json")
    else:
        decoded = output
    digest = evidence_hash(decoded)
    try:
        value = model.model_validate(decoded)
    except pydantic.ValidationError as exc:
        reasons = tuple(
            f"{_path(tuple(error.get('loc', ())))}: {error.get('msg', 'invalid')}"
            for error in exc.errors(include_url=False, include_input=False, include_context=False)
        )
        return ValidationResult("fail", reasons, None, evidence_hash=digest)
    digest = evidence_hash(value.model_dump(mode="json", by_alias=True))
    reasons_out: list[str] = []
    failed: list[str] = []
    for name, rule in (rules or {}).items():
        try:
            holds = rule(value)
        except Exception as exc:
            failed.append(name)
            reasons_out.append(f"{name}: {type(exc).__name__}")
            continue
        if holds is False:
            failed.append(name)
            reasons_out.append(name)
        elif isinstance(holds, str):
            failed.append(name)
            reasons_out.append(f"{name}: {holds}")
    return ValidationResult(
        "fail" if failed else "pass",
        tuple(reasons_out),
        value,
        evidence_hash=digest,
        failed_rules=tuple(failed),
    )
