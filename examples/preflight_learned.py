"""Use learned context on a call you make directly to a provider (no proxying).

Run: ULTRAROUTER_API_KEY=... ULTRAROUTER_BASE_URL=... python examples/preflight_learned.py
"""

from __future__ import annotations

import os

from ultrarouter import UltraRouter

CALL_TYPE = os.environ.get("ULTRAROUTER_CALL_TYPE", "support-reply")
CASE_CALL_TYPE = os.environ.get("ULTRAROUTER_CASE_CALL_TYPE", "ticket-classifier")


def call_provider_directly(model: str, messages: list[dict[str, str]]) -> str:
    """Stand-in for your own provider SDK call."""
    return f"[{model}] answered {len(messages)} messages"


def main() -> None:
    messages = [
        {"role": "system", "content": "You are a support agent."},
        {"role": "user", "content": "Where is my refund?"},
    ]
    with UltraRouter() as client:
        session = client.use_learned(
            call_type=CALL_TYPE, artifact_key="ticket:4812:reply", messages=messages
        )
        placed = session.apply(messages)
        print(
            "learned module:",
            session.knowledge.module.id
            if session.knowledge
            else session.preflight.knowledge_reason,
        )
        print("arm:", session.grant.arm if session.grant else session.preflight.grant_reason)
        print(call_provider_directly(session.model or "openai/gpt-5.2-mini", placed))
        print("outcome:", session.record({"channel": "behavioral", "kind": "accepted"}).status)

        # Case-based modules are rendered for the input: pass the messages.
        missing = client.preflight(call_type=CASE_CALL_TYPE)
        present = client.preflight(call_type=CASE_CALL_TYPE, messages=messages)
        print("without messages:", missing.knowledge_reason)
        print("with messages:", present.knowledge is not None)


if __name__ == "__main__":
    main()
