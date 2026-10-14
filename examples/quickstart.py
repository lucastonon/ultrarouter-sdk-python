"""Send one chat completion and print the answer, the served model and the cost.

Run: ULTRAROUTER_API_KEY=... ULTRAROUTER_BASE_URL=... python examples/quickstart.py
"""

from __future__ import annotations

import os

from ultrarouter import UltraRouter

MODEL = os.environ.get("ULTRAROUTER_MODEL", "openai/gpt-5.2-mini")


def main() -> None:
    with UltraRouter() as client:
        reply = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You answer in one short sentence."},
                {"role": "user", "content": "What does an LLM gateway do?"},
            ],
        )
    print(reply.choices[0].message.content)
    print(
        f"request={reply.ur.request_id} model={reply.ur.model_served} cost_usd={reply.ur.cost_usd}"
    )


if __name__ == "__main__":
    main()
