"""Stream a chat completion with the async client.

Run: ULTRAROUTER_API_KEY=... ULTRAROUTER_BASE_URL=... python examples/async_streaming.py
"""

from __future__ import annotations

import asyncio
import os

from ultrarouter import AsyncUltraRouter

MODEL = os.environ.get("ULTRAROUTER_MODEL", "openai/gpt-5.2-mini")


async def main() -> None:
    async with AsyncUltraRouter() as client:
        stream = await client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "Name three uses of embeddings."}],
            stream=True,
        )
        async with stream:
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    print(chunk.choices[0].delta.content, end="", flush=True)
        print()
        print(f"request: {stream.ur.request_id if stream.ur else None}")


if __name__ == "__main__":
    asyncio.run(main())
