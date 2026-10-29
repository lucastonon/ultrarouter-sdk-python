# Outcomes and artifacts

The outcome ledger records what happened **after** a model answered. Your application produces
*artifacts* (a draft reply, an answer, a forecast, an extraction); *outcome events* say what
became of them: accepted, edited, resolved correctly, clicked, and so on, instantly or days
later. Events carry ids, hashes and values, never prompt or completion text, and the server
assigns their provenance from your API key.

These endpoints need a key with the `outcomes:write` scope.

## Artifact types and objectives

Declare what "it worked" means for a kind of artifact once:

```python
from ultrarouter import UltraRouter

client = UltraRouter()
artifact_type = client.artifact_types.upsert(
    name="support-reply",
    archetype="draft",
    objective={
        "metric": "acceptance_rate",
        "unit": "ratio",
        "direction": "higher_is_better",
        "resolution_criteria": "the agent sends the reply without edits",
        "source": "helpdesk",
        "window": "P7D",
    },
)
print(artifact_type.id, artifact_type.version)
```

`archetype` is one of `forecast`, `recommendation`, `draft`, `extraction`, `answer`, `action`.
Upserting again with a different objective appends a new version.

## Artifacts

`create` upserts by your stable `key`, so calling it twice with the same key returns the same
artifact.

```python
artifact = client.artifacts.create(
    key="ticket:4812:reply",
    archetype="draft",
    artifact_type="support-reply",
    request_ids=["req_123"],  # the gateway requests that produced it
    claims=[
        {
            "key": "resolves-ticket",
            "claim_type": "resolution",
            "resolves_by": "2026-02-01T00:00:00Z",
        }
    ],
)
print(artifact.id, artifact.key, artifact.current_version)

again = client.artifacts.get(artifact.id)
page = client.artifacts.list(limit=20, archetype="draft")
print(len(page.data), page.next_cursor)
```

Lists are cursor-paginated: pass `page.next_cursor` back as `cursor=` for the next page.

A simpler way to bind requests to an artifact is to send `ur={"artifact": "<key>"}` on the
chat call; the response's `ur.artifact_id` echoes the bound artifact.

## Recording outcomes

`client.outcomes.record(target, event)` goes through a durable local queue:

1. the event is finalized: `observed_at` and a client-generated `source_event_id` are fixed;
2. it is persisted to the queue's store;
3. it is sent. If the delivery fails, or its result is unknown, the event stays queued;
   `flush()` replays the identical bytes with the same `Idempotency-Key`, so a delivery the server
   already saw counts as a `duplicate`, never a second event.

`record(...)` never raises for a delivery failure. The receipt's `status` says what happened:

| `status` | When | The event |
| --- | --- | --- |
| `delivered` | the server answered 2xx; `receipt.result` is its per-event verdict | removed from the queue |
| `queued` | everything that does not prove the event was recorded or is invalid: a timeout (including the SDK's own deadline), cancellation, a connection failure, **any** 401, 403, 408 or 429 (whatever the body, code or `retryable` flag), any 5xx, a 4xx without a complete gateway error envelope (an HTML page or an empty body from a proxy, a missing field, `retryable: null` or `"false"`), an unknown or contradictory error code, and a 2xx answer that is not an outcome result (`{}`, `{"data": [{}]}`, an unreadable body) | kept, unchanged, for `flush()`; `receipt.error` says why |
| `rejected` | a validated refusal of the **event**: a 4xx other than 401/403/408/429 whose body is a complete envelope `{"error": {"code", "message", "request_id", "retryable": false}}` with `invalid_request` at 400, `not_found` at 404 or `conflict` at 409 | dropped; `receipt.error` says why |

`delivered` needs a result the contract defines: an object whose `status` is `accepted`,
`duplicate`, `conflict` or `rejected` (the server's verdict on the event), or `pending` (an
outcome reported on a request the gateway has not stored yet: the gateway holds a durable receipt
and applies it when the request lands). These rules are the same in the TypeScript SDK; both run
the same shared fixture of 273 response cases.

```python
receipt = client.outcomes.record(artifact.id, {"channel": "behavioral", "kind": "accepted"})
print(receipt.status)  # "delivered", "queued" (will be retried by flush) or "rejected"
print(client.outcomes.size())  # events still waiting in the queue (no network)

# Delayed outcome, attached to a request instead of an artifact:
client.outcomes.record(
    {"request": "req_123"},
    {
        "channel": "resolution",
        "kind": "resolved",
        "value": {"correct": True},
        "claim_key": "resolves-ticket",
    },
)

report = client.outcomes.flush()  # e.g. at shutdown
print(report.delivered, report.rejected, report.pending)
```

| Event field | Meaning |
| --- | --- |
| `channel` (required) | `mechanical`, `correction`, `behavioral`, `resolution`, `computable` or `proxy` |
| `kind` (required) | your event name, for example `accepted`, `edited`, `resolved` |
| `value` | a JSON object with the details |
| `claim_key` / `claim_id` | the claim this event resolves |
| `confidence` | 0..1 |
| `observed_at` | ISO-8601 time; defaults to now |
| `source_event_id` | your idempotency id; generated if omitted |
| `artifact_version`, `alternative_id`, `evidence_hash`, `supersedes_event_id`, `tool_error_class` | optional details |

`client.record_outcome(...)` is an alias of `client.outcomes.record(...)`.

### Durable stores

The default store keeps queued events in memory for the lifetime of the client. To survive
restarts, use a file:

```python
import tempfile
from pathlib import Path

from ultrarouter import FileOutcomeStore

queue_file = Path(tempfile.mkdtemp()) / "outcomes.json"
durable = UltraRouter(outcome_store=FileOutcomeStore(queue_file))
durable.outcomes.record(artifact.id, {"channel": "behavioral", "kind": "accepted"})
durable.outcomes.flush()
```

The file is rewritten atomically with mode `0600`. It starts empty only when it does not exist:
a file that cannot be read, is not valid JSON or does not hold a list of queue entries raises
`OutcomeStoreError` on every operation (including `record` and `flush`) and is never overwritten,
so its events can be recovered by hand. Implement the `OutcomeStore` protocol (`append`,
`update`, `remove`, `list`) to use your own storage.

A client derived with `with_options(...)` shares its parent's store; whichever client delivers an
event uses its own options (see [Clients](clients.md#per-call-settings-and-with_options)).

### Batches and pending claims

```python
batch = client.outcomes.batch(
    [
        {
            "artifact_key": "ticket:4812:reply",
            "channel": "behavioral",
            "kind": "accepted",
            "source_event_id": "evt-1",
        },
        {
            "request_id": "req_123",
            "channel": "proxy",
            "kind": "clicked",
            "source_event_id": "evt-2",
        },
    ]
)
print(batch.accepted, batch.duplicate, batch.conflict, batch.rejected)

pending = client.outcomes.pending(state="overdue", limit=50)
for claim in pending.data:
    print(claim.artifact_key, claim.claim_key, claim.resolves_by)
```

A batch takes up to 1,000 events; each row names its own target. `pending` lists claims that are
waiting for a resolution (cursor-paginated).

## The human-approved final

When a person edits and approves an artifact, record the final version. With the workspace's
corrections consent, you may send the texts; without it, send only statistics and a hash:

```python
from ultrarouter import diff_stats

draft = "Your order will arrive Monday."
final = "Your order will arrive Tuesday, sorry for the delay."
stats = diff_stats(draft, final)
version = client.artifacts.final(artifact.id, diff_stats=stats, final_hash=stats["final_hash"])
print(version.stored, version.client_computed)  # "metadata_only", True
```

See [Diff statistics](diff-stats.md).

## The artifact scope

`with client.with_artifact(key) as scope:` binds chat and embeddings calls to an artifact, records
outcomes on it (creating it on first use) and flushes the queue when the block exits, even on
an exception:

```python
with client.with_artifact("ticket:4813:reply") as scope:
    reply = scope.chat.completions.create(
        model="openai/gpt-5.2-mini",
        messages=[{"role": "user", "content": "Draft a reply about a refund."}],
    )
    scope.record({"channel": "behavioral", "kind": "accepted"})
print(scope.artifact_id)
```

The async client's scope is `async with client.with_artifact(key) as scope:` and
`await scope.artifact_id()`.
