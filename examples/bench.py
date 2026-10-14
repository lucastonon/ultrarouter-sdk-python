"""Capture traffic into a Bench suite, freeze it and run a dry-run comparison.

Use a test key.
Run: ULTRAROUTER_API_KEY=ur_sk_test_... ULTRAROUTER_BASE_URL=... python examples/bench.py
"""

from __future__ import annotations

import os

from ultrarouter import UltraRouter

MODEL = os.environ.get("ULTRAROUTER_MODEL", "openai/gpt-5.2-mini")
CANDIDATE = os.environ.get("ULTRAROUTER_CANDIDATE_MODEL", "openai/gpt-5.2")
SUITE = os.environ.get("ULTRAROUTER_BENCH_SUITE", "examples-suite")


def main() -> None:
    with UltraRouter(bench=SUITE) as client:
        for question in (
            "Can I return a gift?",
            "Do you ship abroad?",
            "How do I reset my password?",
        ):
            client.chat.completions.create(
                model=MODEL,
                call_type="support-reply",
                messages=[{"role": "user", "content": question}],
            )
        print("captured:", client.bench.status(SUITE).total_captured)
        frozen = client.bench.freeze(SUITE)
        print("datasets:", len(frozen.datasets))
        estimate = client.bench.run(
            suite=SUITE, max_cost_usd=2, candidates=[CANDIDATE], dry_run=True
        )
        print(f"estimate_usd={estimate.estimate_usd}")
        for disposition in estimate.dispositions:
            print(disposition.call_type_id, disposition.disposition, disposition.reason)


if __name__ == "__main__":
    main()
