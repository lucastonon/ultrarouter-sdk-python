"""Send chat completions concurrently with the async client.

Run: ULTRAROUTER_API_KEY=... ULTRAROUTER_BASE_URL=... python examples/async_quickstart.py
"""

from __future__ import annotations

import asyncio
import os

from ultrarouter import AsyncUltraRouter

MODEL = os.environ.get("ULTRAROUTER_MODEL", "openai/gpt-5.2-mini")
QUESTIONS = ["What is a fallback model?", "What is a call type?", "What is an idempotency key?"]


async def main() -> None:
    async with AsyncUltraRouter(default_model=MODEL) as client:
        replies = await asyncio.gather(
            *(
                client.chat.completions.create(messages=[{"role": "user", "content": question}])
                for question in QUESTIONS
            )
        )
    for question, reply in zip(QUESTIONS, replies, strict=True):
        print(f"{question} -> {reply.choices[0].message.content} ({reply.ur.request_id})")


if __name__ == "__main__":
    asyncio.run(main())
