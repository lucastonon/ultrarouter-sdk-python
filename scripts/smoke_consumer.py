"""Smoke test for an *installed* ultrarouter distribution (run by scripts/smoke.sh).

It must type-check with ``mypy --strict`` against the installed package (proving ``py.typed``
ships) and run against the mock gateway: sync and async chat, streaming, embeddings, typed errors,
the learning loop (correlation, verdict reports, receipts, learning controls, the packaged
fixtures, adapters and the demonstration environment) and the offline context runtime.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import ultrarouter
from ultrarouter import (
    AsyncUltraRouter,
    ChatCompletion,
    CreateEmbeddingResponse,
    LearningNotFoundError,
    ModelUnpricedError,
    NotReportedOutcome,
    ProxyOutcomeReport,
    Stream,
    TeachingOutcomeReport,
    UltraRouter,
    new_request_id,
)
from ultrarouter.adapters import WebhookOutcomeHandler, WebhookVerifier, sign_webhook
from ultrarouter.context import from_messages, to_messages
from ultrarouter.demo import OrderDesk
from ultrarouter.types import LearningControl, LearningStatus, OutcomeReceiptRecord

#: The shared fixtures the wheel must ship unchanged.
FIXTURE_SHA256 = {
    "outcome_verdicts.json": "e55e452d5e5374ad07ac13ab7e9b44978425151d902a620edc2586a4e9633e1e",
    "toy_env.json": "c868940d540331a66d0120ee54f071e6f0c1f9728bf43cf51445ba429c0a51d5",
}

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


def check_learning() -> None:
    """Correlation, verdict reports, receipts, controls, adapters and the demo, installed."""
    data = Path(ultrarouter.__file__).resolve().parent / "_data"
    for name, digest in FIXTURE_SHA256.items():
        assert hashlib.sha256((data / name).read_bytes()).hexdigest() == digest, name
    with UltraRouter() as client:
        request_id = new_request_id()
        reply = client.chat.completions.create(
            model=MODEL, messages=MESSAGES, request_id=request_id, episode_key="smoke:1"
        )
        assert reply.ur.request_id == request_id
        report: TeachingOutcomeReport = client.outcomes.report(
            request_id, "pass", source="verifier"
        )
        assert report.teaches
        assert report.status == "delivered"
        proxy: ProxyOutcomeReport = client.outcomes.report(request_id, "fail", source="self_rating")
        assert not proxy.teaches
        silent: NotReportedOutcome = client.outcomes.report(request_id, "unknown", source="webhook")
        assert silent.status == "not_reported"
        final: OutcomeReceiptRecord = client.outcomes.wait_for_receipt(report, timeout=10)
        assert final.status == "applied"
        # One mock gateway serves every smoke environment: a fresh call type per run.
        call_type = f"smoke-{new_request_id()}"
        control: LearningControl = client.learning.enable(call_type, reflection_model=MODEL)
        status: LearningStatus = control.learning
        assert control.changed
        assert status.state == "learning"
        refusal: LearningNotFoundError | None = None
        try:
            client.learning.status("ct_missing")
        except LearningNotFoundError as exc:
            refusal = exc
        assert refusal is not None, "expected LearningNotFoundError"
        assert refusal.reason == "not_found"
        body = json.dumps({"event_id": "evt_smoke", "request_id": request_id, "verdict": "pass"})
        secret = "smoke-only-" + request_id  # a throwaway value for this run
        handler = WebhookOutcomeHandler(WebhookVerifier(secret))
        headers = sign_webhook(body, secret=secret, now_s=time.time())
        assert handler.handle(client, body, headers).status == "reported"
        assert handler.handle(client, body, headers).status == "duplicate"
    desk = OrderDesk("s6")
    desk.solve()
    assert desk.verify().verdict == "pass"


async def check_learning_async() -> None:
    """The async learning surface, installed."""
    async with AsyncUltraRouter() as client:
        async with client.episode() as episode:
            await episode.chat.completions.create(model=MODEL, messages=MESSAGES)
            report = await episode.report("fail", source="business_rule")
        assert report.reported
        assert (await client.learning.status("smoke-async")).state == "off"


def check_context() -> None:
    """The pure context runtime round-trips a conversation."""
    lifted = from_messages(MESSAGES)
    assert to_messages(lifted["manifest"]) == MESSAGES


def main() -> int:
    """Run every check and report the interpreter."""
    check_installation()
    check_sync()
    asyncio.run(check_async())
    check_learning()
    asyncio.run(check_learning_async())
    check_context()
    print(f"smoke ok: ultrarouter {ultrarouter.__version__} on Python {sys.version.split()[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
