"""Handle typed errors: an unpriced model, an unknown model and retry settings.

Run: ULTRAROUTER_API_KEY=... ULTRAROUTER_BASE_URL=... python examples/errors_and_retries.py
"""

from __future__ import annotations

import os

from ultrarouter import (
    ModelUnpricedError,
    NotFoundError,
    RateLimitError,
    UltraRouter,
    UltraRouterError,
)

UNPRICED_MODEL = os.environ.get("ULTRAROUTER_UNPRICED_MODEL", "acme/unpriced-model")
MISSING_MODEL = os.environ.get("ULTRAROUTER_MISSING_MODEL", "acme/missing-model")


def ask(client: UltraRouter, model: str) -> None:
    """Send one request and explain what happened."""
    try:
        reply = client.chat.completions.create(
            model=model, messages=[{"role": "user", "content": "Hi"}]
        )
        print(f"{model}: {reply.choices[0].message.content}")
    except ModelUnpricedError as exc:
        print(f"{model}: not priced; nothing was called or billed (HTTP {exc.status})")
        print(f"{model}: retryable={exc.retryable}")
    except NotFoundError as exc:
        print(f"{model}: unknown model ({exc.request_id})")
    except RateLimitError:
        print(f"{model}: still rate limited after automatic retries")
    except UltraRouterError as exc:
        print(f"{model}: {exc.code} ({exc.status})")


def main() -> None:
    # 20 s total budget per call, up to 3 retries for transient failures.
    with UltraRouter(timeout=20, max_retries=3) as client:
        ask(client, UNPRICED_MODEL)
        ask(client, MISSING_MODEL)


if __name__ == "__main__":
    main()
