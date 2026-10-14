# Embeddings

`client.embeddings.create(...)` sends `POST /v1/embeddings` and returns a
[`CreateEmbeddingResponse`](types-reference.md#createembeddingresponse).

```python
from ultrarouter import UltraRouter

client = UltraRouter()
response = client.embeddings.create(
    model="openai/text-embedding-3-small",
    input=["The quick brown fox", "jumps over the lazy dog"],
)
for item in response.data:
    print(item.index, len(item.embedding))
print(response.usage.total_tokens, response.ur.cost_usd)
```

`input` is a string or a list of strings. Results come back in input order (`item.index`).

## Parameters

| Parameter | Meaning |
| --- | --- |
| `input` | text or list of texts (required) |
| `model` | embedding model id; falls back to `default_model` |
| `dimensions` | shorten vectors, for models that support it |
| `encoding_format` | `"float"` (default, lists of floats) or `"base64"` (packed little-endian float32) |
| `user`, `metadata` | passed through |
| `call_type`, `ur`, `bench` | as for chat completions |

## Base64 vectors

Base64 output is smaller on the wire. Decode it with the standard library:

```python
import base64
import struct

packed = client.embeddings.create(
    model="openai/text-embedding-3-small", input="hello", encoding_format="base64", dimensions=8
)
raw = base64.b64decode(packed.data[0].embedding)  # type: ignore[arg-type]
vector = struct.unpack(f"<{len(raw) // 4}f", raw)
print(len(vector))
```

## Async

```python
import asyncio

from ultrarouter import AsyncUltraRouter


async def embed(texts: list[str]) -> list[list[float]]:
    async with AsyncUltraRouter() as client:
        response = await client.embeddings.create(
            model="openai/text-embedding-3-small", input=texts
        )
    return [list(item.embedding) for item in response.data]  # type: ignore[arg-type]


print(len(asyncio.run(embed(["a", "b", "c"]))))
```

The `ur` block on an embeddings response has the request id, served model, provider, routing,
cost and BYOK flag (no compression block: inputs are never rewritten).
