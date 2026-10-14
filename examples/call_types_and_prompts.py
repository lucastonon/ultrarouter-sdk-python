"""Create a call type, configure it, add and activate a hosted prompt, and trigger an eval.

Needs a key with config:write.
Run: ULTRAROUTER_API_KEY=... ULTRAROUTER_BASE_URL=... python examples/call_types_and_prompts.py
"""

from __future__ import annotations

import os

from ultrarouter import UltraRouter

MODEL = os.environ.get("ULTRAROUTER_MODEL", "openai/gpt-5.2-mini")
SLUG = os.environ.get("ULTRAROUTER_CALL_TYPE", "support-reply")


def main() -> None:
    with UltraRouter() as client:
        call_type = client.call_types.create(slug=SLUG, config={"model_pin": MODEL})
        print("created:", call_type.id, call_type.lifecycle_state)
        client.call_types.update(SLUG, compression_mode="off", fallbacks=["openai/gpt-5.2"])

        version = client.call_types.prompts.create(
            SLUG,
            template="You are a {{tone}} support agent for {{brand}}.",
            variables=[{"name": "tone", "required": False}, {"name": "brand", "required": True}],
        )
        client.call_types.prompts.activate(SLUG, version.version, gateway_apply=True)

        reply = client.chat.completions.create(
            model=MODEL,
            call_type=SLUG,
            ur={"prompt_vars": {"brand": "Northwind", "tone": "friendly"}},
            messages=[{"role": "user", "content": "Where is my order?"}],
        )
        print("served by:", reply.ur.model_served)

        run = client.call_types.enqueue_eval(SLUG)
        print("eval:", run.run_id if run.enqueued else run.reason)


if __name__ == "__main__":
    main()
