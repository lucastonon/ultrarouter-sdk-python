"""JavaScript-compatible text and JSON primitives (pure, internal).

Hashes and lengths computed by this SDK must agree byte-for-byte with the gateway and the
TypeScript SDK, which run on JavaScript strings (UTF-16) and ``JSON.stringify``. These helpers
reproduce the observable behaviour:

* strings are measured and compared in UTF-16 code units;
* UTF-8 encoding replaces an unpaired surrogate with U+FFFD (as ``TextEncoder`` does);
* numbers are formatted like ``Number.prototype.toString`` (``1e-7``, ``1e+21``, ``-0`` → ``0``,
  ``NaN``/``Infinity`` → ``null``);
* object keys are emitted the way ``JSON.stringify`` emits a sorted object: array-index keys
  (``"0"``, ``"17"``) first in numeric order, then the rest in UTF-16 code-unit order.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Iterable, Mapping
from typing import Any

__all__ = [
    "canonical_json",
    "js_number",
    "js_sorted_keys",
    "js_string",
    "utf8_bytes",
    "utf16_units",
]

_ARRAY_INDEX_RE = re.compile(r"^(?:0|[1-9][0-9]*)$")
_MAX_ARRAY_INDEX = 2**32 - 2
_SAFE_INTEGER = 2**53
_ESCAPES = {
    '"': '\\"',
    "\\": "\\\\",
    "\b": "\\b",
    "\f": "\\f",
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
}


def utf16_units(text: str) -> list[int]:
    """The UTF-16 code units of ``text`` (lone surrogates kept as-is)."""
    raw = text.encode("utf-16-le", "surrogatepass")
    return [raw[i] | (raw[i + 1] << 8) for i in range(0, len(raw), 2)]


def _has_surrogate(text: str) -> bool:
    return any(0xD800 <= ord(ch) <= 0xDFFF for ch in text)


def utf8_bytes(text: str) -> bytes:
    """UTF-8 bytes of ``text``, replacing unpaired surrogates with U+FFFD (``TextEncoder``)."""
    if not _has_surrogate(text):
        return text.encode("utf-8")
    normalized = text.encode("utf-16-le", "surrogatepass").decode("utf-16-le", "replace")
    return normalized.encode("utf-8")


def js_string(text: str) -> str:
    """Encode ``text`` exactly as ``JSON.stringify`` would."""
    if not _has_surrogate(text):
        return json.dumps(text, ensure_ascii=False)
    out = ['"']
    units = utf16_units(text)
    i = 0
    while i < len(units):
        unit = units[i]
        if 0xD800 <= unit <= 0xDBFF and i + 1 < len(units) and 0xDC00 <= units[i + 1] <= 0xDFFF:
            out.append(chr(0x10000 + ((unit - 0xD800) << 10) + (units[i + 1] - 0xDC00)))
            i += 2
            continue
        if 0xD800 <= unit <= 0xDFFF:
            out.append(f"\\u{unit:04x}")
        else:
            ch = chr(unit)
            if ch in _ESCAPES:
                out.append(_ESCAPES[ch])
            elif unit < 0x20:
                out.append(f"\\u{unit:04x}")
            else:
                out.append(ch)
        i += 1
    out.append('"')
    return "".join(out)


def js_number(value: float | int) -> str:
    """Format a number like JavaScript's ``Number.prototype.toString`` / ``JSON.stringify``."""
    if isinstance(value, int) and not isinstance(value, bool):
        if abs(value) <= _SAFE_INTEGER:
            return str(value)
        value = float(value)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        return "null"
    if number == 0:
        return "0"
    sign = "-" if number < 0 else ""
    text = repr(abs(number))
    mantissa, _, exp_text = text.partition("e")
    exponent = int(exp_text) if exp_text else 0
    int_part, _, frac_part = mantissa.partition(".")
    all_digits = int_part + frac_part
    stripped = all_digits.lstrip("0")
    leading = len(all_digits) - len(stripped)
    digits = stripped.rstrip("0") or "0"
    k = len(digits)
    n = len(int_part) - leading + exponent  # decimal point position relative to digits
    if k <= n <= 21:
        return sign + digits + "0" * (n - k)
    if 0 < n <= 21:
        return sign + digits[:n] + "." + digits[n:]
    if -6 < n <= 0:
        return sign + "0." + "0" * (-n) + digits
    exp = n - 1
    exp_str = f"e+{exp}" if exp >= 0 else f"e-{-exp}"
    if k == 1:
        return sign + digits + exp_str
    return sign + digits[0] + "." + digits[1:] + exp_str


def _key_text(key: Any) -> str:
    if isinstance(key, str):
        return key
    if isinstance(key, bool) or key is None:
        return json.dumps(key)
    if isinstance(key, (int, float)):
        return js_number(key)
    raise TypeError(f"object keys must be strings (got {type(key).__name__})")


def js_sorted_keys(keys: Iterable[str]) -> list[str]:
    """Order keys the way ``JSON.stringify`` emits an object built from ``Object.keys().sort()``."""
    index_keys: list[str] = []
    other_keys: list[str] = []
    for key in keys:
        if _ARRAY_INDEX_RE.match(key) and int(key) <= _MAX_ARRAY_INDEX:
            index_keys.append(key)
        else:
            other_keys.append(key)
    index_keys.sort(key=int)
    other_keys.sort(key=utf16_units)
    return index_keys + other_keys


def canonical_json(value: Any) -> str:
    """Deterministic JSON: object keys sorted recursively, JavaScript-compatible output.

    Matches the gateway's canonical JSON for JSON-shaped values. ``None`` values inside objects
    are kept as ``null`` (Python has no ``undefined``).
    """
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return js_string(value)
    if isinstance(value, (int, float)):
        return js_number(value)
    if isinstance(value, Mapping):
        items = {_key_text(k): v for k, v in value.items()}
        return (
            "{"
            + ",".join(js_string(k) + ":" + canonical_json(items[k]) for k in js_sorted_keys(items))
            + "}"
        )
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(canonical_json(item) for item in value) + "]"
    raise TypeError(f"canonical_json cannot encode {type(value).__name__}")
