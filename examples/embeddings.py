"""Embed a few texts and rank them by cosine similarity to a query.

Run: ULTRAROUTER_API_KEY=... ULTRAROUTER_BASE_URL=... python examples/embeddings.py
"""

from __future__ import annotations

import math
import os

from ultrarouter import UltraRouter

MODEL = os.environ.get("ULTRAROUTER_EMBEDDING_MODEL", "openai/text-embedding-3-small")
DOCUMENTS = ["Refunds take 14 days.", "Shipping is free over 50 dollars.", "We are open 9 to 5."]


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity of two vectors."""
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def main() -> None:
    with UltraRouter() as client:
        response = client.embeddings.create(
            model=MODEL, input=["How long do refunds take?", *DOCUMENTS]
        )
    vectors = [list(item.embedding) for item in response.data]  # type: ignore[arg-type]
    query, docs = vectors[0], vectors[1:]
    ranked = sorted(zip(DOCUMENTS, docs, strict=True), key=lambda pair: -cosine(query, pair[1]))
    for text, vector in ranked:
        print(f"{cosine(query, vector):+.3f}  {text}")


if __name__ == "__main__":
    main()
