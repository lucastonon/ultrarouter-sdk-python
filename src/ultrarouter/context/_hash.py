"""Hashing for the context runtime.

The default profile hashes canonical JSON (object keys sorted, JavaScript-compatible output)
with SHA-256 over its UTF-8 bytes, byte-identical to the gateway and the TypeScript SDK. A
custom profile may declare its own serializer through ``manifest_encoder``.

Pure: same input, same digest.
"""

from __future__ import annotations

import hashlib
from typing import Any

from .._jscompat import canonical_json, js_string, utf8_bytes

__all__ = ["canonical_json", "hash_context_value", "js_json_string", "sha256_hex"]


def js_json_string(value: str) -> str:
    """Encode a string exactly as JavaScript ``JSON.stringify`` would."""
    return js_string(value)


def sha256_hex(text: str) -> str:
    """SHA-256 hex digest of ``text``'s UTF-8 bytes (unpaired surrogates become U+FFFD)."""
    return hashlib.sha256(utf8_bytes(text)).hexdigest()


def hash_context_value(value: Any) -> str:
    """The default content digest: SHA-256 hex over the canonical JSON of ``value``."""
    return sha256_hex(canonical_json(value))
