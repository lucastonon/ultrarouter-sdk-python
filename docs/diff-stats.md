# Diff statistics

`diff_stats(draft, final)` measures how much a person changed a draft before approving it,
without sending either text anywhere. Use it for the human-approved final of an artifact (and in
reviewer events) when the workspace has not consented to storing corrections.

```python
from ultrarouter import diff_stats

stats = diff_stats(
    "Your order ships Monday.",
    "Your order ships Tuesday. Sorry for the delay!",
)
print(stats)
# {'edit_ratio': ..., 'changed_spans': ..., 'lengths': {'draft': 24, 'final': 46}, 'final_hash': '...'}
```

| Field | Meaning |
| --- | --- |
| `edit_ratio` | normalized character edit ratio in `[0, 1]`; `0` means identical, `1` means nothing shared |
| `changed_spans` | number of contiguous changed regions (`0` when identical) |
| `lengths` | `{"draft": n, "final": m}` in UTF-16 code units |
| `final_hash` | SHA-256 hex of the final text's UTF-8 bytes |

Details:

- Deterministic and pure: no network, no clock, no randomness.
- Lengths are counted in UTF-16 code units, the unit the gateway and the TypeScript SDK use, so
  the numbers agree across languages (an emoji usually counts as 2).
- The diff trims the common prefix and suffix, then runs a character LCS on the middle. Very large
  middles (over 4,000,000 comparison cells) are reported as one fully changed region: the result
  can over-report change, never under-report it.

Sending it:

```python
from ultrarouter import UltraRouter

client = UltraRouter()
artifact = client.artifacts.create(key="ticket:4812:reply")
client.artifacts.final(artifact.id, diff_stats=stats, final_hash=stats["final_hash"])
```
