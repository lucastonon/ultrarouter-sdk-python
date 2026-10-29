"""The learning loop with the async client: an episode, a report, a cancellable receipt wait.

`AsyncUltraRouter` has the same surface: `async with client.episode(...)`, `await
client.outcomes.report(...)`, and `await client.outcomes.wait_for_receipt(...)`, which stops at once
when its task is cancelled (the outcome is unaffected: the receipt is durable on the gateway).

The verifier requires the trimmed answer to equal OK; a non-empty wrong answer fails.

This example resolves or creates order-desk (config:read/write), and sends its slug on every call.
Enable learning separately for its ct_... ID after full workspace learning consent.

Run: ULTRAROUTER_API_KEY=... ULTRAROUTER_BASE_URL=... python examples/learning_async.py

Expected output (mock gateway):
    episode: 1 step, reported pass (gateway status pending)
    wait cancelled; the outcome is unaffected
    receipt final: applied
    learning state: off
"""

from __future__ import annotations

import asyncio
import os

from ultrarouter import AsyncUltraRouter

MODEL = os.environ.get("ULTRAROUTER_MODEL", "openai/gpt-5.2-mini")


async def main() -> int:
    async with AsyncUltraRouter() as client:
        call_type = next(
            (ct for ct in (await client.call_types.list()).data if ct.slug == "order-desk"), None
        )
        if call_type is None:
            call_type = await client.call_types.create(slug="order-desk")
        async with client.episode() as episode:
            reply = await episode.chat.completions.create(
                call_type=call_type.slug,
                model=MODEL,
                messages=[{"role": "user", "content": "Say OK."}],
            )
            ok = (reply.choices[0].message.content or "").strip() == "OK"
            report = await episode.report("pass" if ok else "fail", source="verifier")
        if not report.reported or report.status != "delivered":
            print("not delivered:", report.status)
            return 1
        print(
            f"episode: {len(episode.request_ids)} step, reported {report.verdict} "
            f"(gateway status {report.outcome_status})"
        )
        if report.receipt_id is None:
            return 0

        waiting = asyncio.ensure_future(client.outcomes.wait_for_receipt(report, timeout=30))
        await asyncio.sleep(0)  # let it start, then change our mind
        waiting.cancel()
        try:
            await waiting
        except asyncio.CancelledError:
            print("wait cancelled; the outcome is unaffected")

        final = await asyncio.wait_for(client.outcomes.wait_for_receipt(report), timeout=35)
        print("receipt final:", final.status)
        status = await client.learning.status(call_type.id)
        print("learning state:", status.state)
    return 0 if final.status == "applied" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
