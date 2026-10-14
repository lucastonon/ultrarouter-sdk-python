"""Stream a chat completion token by token, then print usage and the ur block.

Run: ULTRAROUTER_API_KEY=... ULTRAROUTER_BASE_URL=... python examples/streaming.py
"""

from __future__ import annotations

import os

from ultrarouter import UltraRouter

MODEL = os.environ.get("ULTRAROUTER_MODEL", "openai/gpt-5.2-mini")


def main() -> None:
    with UltraRouter() as client:
        stream = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "Write a two-line poem about latency."}],
            stream=True,
        )
        with stream:
            for chunk in stream:
                for choice in chunk.choices:
                    if choice.delta.content:
                        print(choice.delta.content, end="", flush=True)
        print()
        if stream.usage is not None:
            print(f"tokens: {stream.usage.total_tokens}")
        if stream.ur is not None:
            print(f"request: {stream.ur.request_id} cost_usd: {stream.ur.cost_usd}")


if __name__ == "__main__":
    main()
