# Reviewer adapter

`client.reviewer` sends your reviewers' decisions (approved, approved with edits, rejected,
regenerated) into the outcome ledger. It is the contract your review tool posts to; no
third-party connectors are included.

Properties you can rely on:

- **Signed.** Every delivery is signed with your API key: `HMAC-SHA256` over
  `"<unix-seconds>.<exact body>"`, sent as `X-UR-Reviewer-Signature: sha256=<hex>` with
  `X-UR-Reviewer-Timestamp`. The SDK serializes the body once and signs those bytes.
- **Durable.** `record()` persists an event locally without touching the network; `flush()`
  sends queued events in signed batches. Only a valid per-event verdict moves an event: one with
  the event's `event_id` as a string and `status` `accepted` or `duplicate` (removed), or
  `rejected` / `unsupported` with a string `reason` and a boolean `repairable` (dropped when
  `false`, kept as a dead letter when `true`). Anything else (a non-string `event_id`, an unknown
  status, a missing reason, a `data` that is not a list) keeps the event queued. `flush()` never
  raises on a 2xx answer. A failed batch always stays queued: an ambiguous failure (timeout,
  connection failure, 408/429/5xx) ends the flush quietly (`report.pending`), and any other
  non-retryable 4xx (for example an invalid signature) is raised.
- **Nothing lost.** A refusal the server marks *repairable* (for example a version mismatch) is
  kept as a local dead letter so you can `repair()` it; terminal refusals are dropped.
- **Provenance is the server's.** The event shape has no field for source or learning use.

Requires a key with `outcomes:write`.

## Guided setup

```python
from ultrarouter import UltraRouter

client = UltraRouter()
setup = client.reviewer.setup()
print(setup.endpoint, setup.required_scope)
print(setup.signature.header, setup.signature.algorithm, setup.signature.tolerance_seconds)
for row in setup.mapping:
    print(row.decision, "->", row.channel, row.kind)

result = client.reviewer.test("happy")  # also "replay" and "version_mismatch"
print(result.scenario, result.result.status, result.excluded_from_learning)
```

Test scenarios never enter learning or billing.

## Record and flush

```python
event = {
    "event_id": "review-7781",  # your stable id: re-sending it is a no-op
    "artifact_key": "ticket:4812:reply",  # or "artifact_id"
    "artifact_version": 1,
    "decision": "approved_with_edits",
    "effective_at": "2026-01-15T12:00:00Z",
    "reviewer_id": "agent-42",
}
client.reviewer.record(event, reviewer_system="helpdesk")
report = client.reviewer.flush()
print(report.accepted, report.duplicate, report.dead_lettered, report.dropped, report.pending)
```

To send immediately instead of queueing, use `send()` (at most 500 events per call):

```python
response = client.reviewer.send([{**event, "event_id": "review-7782"}], reviewer_system="helpdesk")
print(response.accepted, [row.status for row in response.data])
```

A declared backfill reports progress per id: `record(event, backfill={"id": "import-2026-01",
"total": 1200})`, then `{"id": ..., "complete": True}` on the last batch.

## Including the final text or its statistics

With the workspace's corrections consent you may include the approved text; without it, send
only statistics and a hash:

```python
from ultrarouter import diff_stats

stats = diff_stats("Draft reply.", "Final reply, with edits.")
client.reviewer.record(
    {
        **event,
        "event_id": "review-7783",
        "final": {"diff_stats": stats, "hash": stats["final_hash"]},
    }
)
client.reviewer.flush()
```

## Dead letters and repair

```python
for letter in client.reviewer.dead_letters():
    print(letter["event"]["event_id"], letter["dead_letter"]["reason"])
    repaired = client.reviewer.repair(letter, repin_to_current_version=True)
    print(repaired.before.reason, repaired.result.status if repaired.result else None)

health = client.reviewer.health()
print(health.events.accepted, health.dead_letter_total, health.next_repair.action)
```

A successful repair removes the local dead letter. `health()` names the next repair action.

## Verifying signatures in your own tooling

The signing helpers are exported, so a non-Python reviewer system can be checked against this
implementation:

```python
from ultrarouter import reviewer_signature_headers, sign_payload

body = b'{"events":[]}'
print(sign_payload("ur_sk_test_example", "1760000000", body))
print(reviewer_signature_headers("ur_sk_test_example", body, now_s=1760000000))
```

Durable storage across restarts works as for outcomes: pass
`reviewer_store=FileOutcomeStore(path)` to the client.
