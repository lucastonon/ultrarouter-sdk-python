#!/usr/bin/env python3
"""Sync (or verify) the vendored OpenAPI specification at ``openapi/openapi.yaml``.

The file is a synced artifact: a two-line header followed by the spec body, byte for byte::

    # ultrarouter public API specification (OpenAPI). Synced artifact: do not hand-edit.
    # spec-sha256: <lowercase hex sha256 of the body bytes that follow this header>

Usage::

    python scripts/sync_openapi.py --from /path/to/openapi.yaml   # replace the body
    python scripts/sync_openapi.py --check                        # verify header + digest

After syncing, regenerate the typed shapes (``python scripts/gen_types.py``) and run the tests.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "openapi" / "openapi.yaml"
HEADER_LINE = (
    b"# ultrarouter public API specification (OpenAPI). Synced artifact: do not hand-edit.\n"
)
DIGEST_PREFIX = b"# spec-sha256: "


def split(data: bytes) -> tuple[bytes, bytes, bytes]:
    """Return (header line 1, digest hex, body) or raise ``ValueError``."""
    first, sep, rest = data.partition(b"\n")
    if not sep or first + b"\n" != HEADER_LINE:
        raise ValueError("line 1 is not the synced-artifact header")
    second, sep, body = rest.partition(b"\n")
    if not sep or not second.startswith(DIGEST_PREFIX):
        raise ValueError("line 2 is not a '# spec-sha256: <hex>' line")
    digest = second[len(DIGEST_PREFIX) :]
    return first, digest, body


def verify(path: Path = SPEC_PATH) -> str:
    """Verify the header and digest; return the body's sha256 hex digest."""
    _, digest, body = split(path.read_bytes())
    actual = hashlib.sha256(body).hexdigest()
    if digest.decode("ascii") != actual:
        raise ValueError(f"spec-sha256 mismatch: header {digest.decode()} != body {actual}")
    return actual


def write(source: Path, path: Path = SPEC_PATH) -> str:
    """Write ``source``'s bytes as the body under a fresh header; return the digest."""
    body = source.read_bytes()
    if body.startswith(HEADER_LINE):
        # Re-syncing from another synced copy: keep only its body.
        _, _, body = split(body)
    digest = hashlib.sha256(body).hexdigest()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(HEADER_LINE + DIGEST_PREFIX + digest.encode("ascii") + b"\n" + body)
    return digest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync or verify openapi/openapi.yaml.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--from", dest="source", type=Path, help="spec file to vendor")
    group.add_argument("--check", action="store_true", help="verify the header and digest")
    args = parser.parse_args(argv)
    try:
        if args.check:
            digest = verify()
            print(f"openapi/openapi.yaml OK (spec-sha256 {digest})")
        else:
            digest = write(args.source)
            print(f"wrote openapi/openapi.yaml (spec-sha256 {digest})")
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
