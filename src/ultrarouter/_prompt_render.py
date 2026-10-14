"""Render a hosted prompt template client-side (pure helpers).

A hosted prompt is a versioned template with ``{{name}}`` slots and declared variables (each
``required`` or optional). :meth:`ultrarouter.UltraRouter.get_prompt` returns the active
version; :func:`render_prompt` fills it exactly the way the gateway does:

* every ``{{name}}`` (whitespace inside the braces allowed; names are ``[A-Za-z0-9_]+``) is
  replaced by the supplied value converted with ``str()``;
* a declared **required** variable that is missing (or ``None``) is a refusal that names every
  missing variable, never a silent blank;
* a missing optional or undeclared slot renders as an empty string.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any, Literal, TypedDict

from ._errors import PromptVariablesMissingError

__all__ = [
    "PROMPT_VARIABLES_MISSING_CODE",
    "PromptRenderFailure",
    "PromptRenderResult",
    "PromptRenderSuccess",
    "render_hosted_prompt_result",
    "render_prompt",
]

_VARIABLE_TOKEN_RE = re.compile(r"\{\{\s*([A-Za-z0-9_]+)\s*\}\}")

#: The error code for a missing required hosted-prompt variable.
PROMPT_VARIABLES_MISSING_CODE = "prompt_variables_missing"


class PromptRenderSuccess(TypedDict):
    """A successful render: ``{"ok": True, "text": ...}``."""

    ok: Literal[True]
    text: str


class PromptRenderFailure(TypedDict):
    """A refused render: ``{"ok": False, "missing": [...]}`` (sorted, de-duplicated names)."""

    ok: Literal[False]
    missing: list[str]


PromptRenderResult = PromptRenderSuccess | PromptRenderFailure


def _field(item: Any, name: str, default: Any = None) -> Any:
    if isinstance(item, Mapping):
        return item.get(name, default)
    return getattr(item, name, default)


def render_hosted_prompt_result(
    template: str,
    variables: Sequence[Any],
    values: Mapping[str, Any] | None = None,
) -> PromptRenderResult:
    """Render ``template`` and return a result dict instead of raising.

    ``variables`` items are mappings or objects with ``name`` and ``required``. Returns
    ``{"ok": True, "text": ...}`` or ``{"ok": False, "missing": [...]}``.
    """
    supplied = values or {}
    required = {_field(v, "name") for v in variables if _field(v, "required", False) is True}
    missing = sorted(n for n in required if isinstance(n, str) and supplied.get(n) is None)
    if missing:
        return {"ok": False, "missing": missing}

    def substitute(match: re.Match[str]) -> str:
        value = supplied.get(match.group(1))
        return "" if value is None else str(value)

    return {"ok": True, "text": _VARIABLE_TOKEN_RE.sub(substitute, template)}


def render_prompt(prompt: Any, values: Mapping[str, Any] | None = None) -> str:
    """Render a hosted prompt and return the text.

    ``prompt`` is what :meth:`~ultrarouter.UltraRouter.get_prompt` returns (or any mapping /
    object with ``template`` and ``variables``). Raises
    :class:`~ultrarouter.PromptVariablesMissingError` (``status == 0``) listing every missing
    required variable.
    """
    template = _field(prompt, "template")
    if not isinstance(template, str):
        raise TypeError("prompt must have a string 'template'")
    variables = _field(prompt, "variables", None) or []
    result = render_hosted_prompt_result(template, variables, values)
    if result["ok"]:
        return result["text"]
    raise PromptVariablesMissingError(missing=result["missing"])
