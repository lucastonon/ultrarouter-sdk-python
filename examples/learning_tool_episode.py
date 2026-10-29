"""A multi-step tool episode: every step correlated, one terminal verdict for the whole task.

The agent works the deterministic order desk (`ultrarouter.demo`): each model call is one step of
an episode (`client.episode(key)` sends the key as `X-UR-Artifact` and a request id minted before
each call); tool calls run against the toy environment; at the end its verifier decides and the
verdict is reported once, on the last step. The toy environment is a demonstration, not evidence
that learning improves an agent.

This example resolves or creates order-desk (config:read/write), and sends its slug on every call.
Enable learning separately for its ct_... ID after full workspace learning consent.

Run: ULTRAROUTER_API_KEY=... ULTRAROUTER_BASE_URL=... python examples/learning_tool_episode.py

Expected output (mock gateway; it calls one tool and stops, so the task fails):
    task: Process orders C-300 and C-301.
    step 1: lookup_order -> {"ok": false, "error": "UNKNOWN_ORDER"}
    step 2: answered
    episode order-desk:s3_01... : 2 steps, verdict fail
    reported on the last step: fail (teaches: True)
    note: Deterministic demonstration environment. ...
"""

from __future__ import annotations

import json
import os
from typing import Any

from ultrarouter import UltraRouter, new_episode_key
from ultrarouter.demo import NOTICE, OrderDesk

MODEL = os.environ.get("ULTRAROUTER_MODEL", "openai/gpt-5.2-mini")
MAX_STEPS = 12


def main() -> int:
    desk = OrderDesk("s3")
    print("task:", desk.task)
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": "You run an order desk. Use the tools; reserve or backorder.",
        },
        {"role": "user", "content": desk.task},
    ]
    with UltraRouter() as client, client.episode(new_episode_key("order-desk:s3")) as episode:
        call_type = next(
            (ct for ct in client.call_types.list().data if ct.slug == "order-desk"), None
        )
        if call_type is None:
            call_type = client.call_types.create(slug="order-desk")
        for step in range(1, MAX_STEPS + 1):
            reply = episode.chat.completions.create(
                call_type=call_type.slug, model=MODEL, messages=messages, tools=desk.tools
            )
            message = reply.choices[0].message
            if not message.tool_calls:
                print(f"step {step}: answered")
                break
            messages.append(
                {"role": "assistant", "content": message.content, "tool_calls": message.tool_calls}
            )
            for call in message.tool_calls:
                tool_message = desk.tool_message(call)
                messages.append(tool_message)
                result = json.loads(tool_message["content"])
                print(f"step {step}: {call['function']['name']} -> {json.dumps(result)}")
        verdict = desk.verify()
        steps = len(episode.request_ids)
        print(f"episode {episode.key[:17]}... : {steps} steps, verdict {verdict.verdict}")
        report = episode.report(
            verdict.verdict, source="verifier", evidence_hash=verdict.evidence_hash
        )
    if not report.reported:
        print("reported: nothing (verdict unknown)")
        return 0
    print(f"reported on the last step: {report.verdict} (teaches: {report.teaches})")
    print("note:", NOTICE)
    return 0 if report.status == "delivered" else 1


if __name__ == "__main__":
    raise SystemExit(main())
