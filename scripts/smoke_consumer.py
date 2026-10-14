"""Smoke test for an *installed* ultrarouter distribution (run by scripts/smoke.sh).

It must type-check with ``mypy --strict`` against the installed package (proving ``py.typed``
ships) and run against the mock gateway: sync and async chat, streaming, embeddings, typed errors
and the offline context runtime.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import ultrarouter
from ultrarouter import (
    AsyncUltraRouter,
    ChatCompletion,
    CreateEmbeddingResponse,
    ModelUnpricedError,
    Stream,
    UltraRouter,
)
from ultrarouter.context import from_messages, to_messages

MODEL = "openai/gpt-5.2-mini"
MESSAGES: list[dict[str, str]] = [{"role": "user", "content": "smoke test"}]


def check_installation() -> None:
    """The package is imported from site-packages, not from a source checkout."""
    location = Path(ultrarouter.__file__).resolve()
    assert "site-packages" in location.parts, f"imported from {location}"
    assert (location.parent / "py.typed").exists(), "py.typed is missing"
    assert ultrarouter.__version__ == os.environ.get("EXPECTED_VERSION", ultrarouter.__version__)


def check_sync() -> None:
    """Sync chat, streaming, embeddings and a typed error."""
    with UltraRouter() as client:
        reply: ChatCompletion = client.chat.completions.create(model=MODEL, messages=MESSAGES)
        assert reply.choices[0].message.content
        assert reply.ur.request_id.startswith("req_")

        stream: Stream = client.chat.completions.create(model=MODEL, messages=MESSAGES, stream=True)
        assert stream.text()
        assert stream.ur is not None

        vectors: CreateEmbeddingResponse = client.embeddings.create(
            model="openai/text-embedding-3-small", input=["a", "b"]
        )
        assert len(vectors.data) == 2

        error: ModelUnpricedError | None = None
        try:
            client.chat.completions.create(model="acme/unpriced-model", messages=MESSAGES)
        except ModelUnpricedError as exc:
            error = exc
        assert error is not None, "expected ModelUnpricedError"
        assert error.status == 403
        assert error.retryable is False


async def check_async() -> None:
    """Async chat, streaming and embeddings."""
    async with AsyncUltraRouter() as client:
        reply = await client.chat.completions.create(model=MODEL, messages=MESSAGES)
        assert reply.ur.model_served == MODEL
        stream = await client.chat.completions.create(model=MODEL, messages=MESSAGES, stream=True)
        assert await stream.text()
        vectors = await client.embeddings.create(model="openai/text-embedding-3-small", input="x")
        assert vectors.data[0].index == 0


def check_context() -> None:
    """The pure context runtime round-trips a conversation."""
    lifted = from_messages(MESSAGES)
    assert to_messages(lifted["manifest"]) == MESSAGES


def main() -> int:
    """Run every check and report the interpreter."""
    check_installation()
    check_sync()
    asyncio.run(check_async())
    check_context()
    print(f"smoke ok: ultrarouter {ultrarouter.__version__} on Python {sys.version.split()[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
