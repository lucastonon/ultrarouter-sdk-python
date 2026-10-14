# Bench

Bench compares candidate models against your current configuration on your own captured
traffic: capture requests into a *suite*, freeze them into datasets, run a paired comparison
within a budget, and read an immutable report. In CI, pin a baseline and gate changes on a
compare run.

Bench needs a key with the `bench:run` scope (freezing needs `config:write`). Use a test key:
the gateway refuses Bench capture on live keys unless a workspace owner allows it.

## 1. Capture traffic into a suite

Tag requests with a suite, either for the whole client or per call:

```python
from ultrarouter import UltraRouter

client = UltraRouter(bench={"suite": "checkout-assistant", "run": "commit-abc123"})
reply = client.chat.completions.create(
    model="openai/gpt-5.2-mini",
    call_type="support-reply",
    messages=[{"role": "user", "content": "Can I change my delivery address?"}],
)
print(reply.ur.bench)  # capture status for this request

status = client.bench.status("checkout-assistant")
print(status.total_captured, [ct.captured for ct in status.call_types])
```

## 2. Freeze, add expectations and outcomes

```python
frozen = client.bench.freeze("checkout-assistant", max_items=500)
for dataset in frozen.datasets:
    print(dataset.call_type_id, dataset.card.unique_count, dataset.card.power_plan.summary)
for warning in frozen.warnings or []:
    print("warning:", warning.code, warning.message)

client.bench.expect(
    "checkout-assistant",
    [
        {
            "kind": "json_schema",
            "call_type": "support-reply",
            "config": {"required_fields": ["answer"]},
        }
    ],
)
client.bench.record([{"trace": "order-1001", "passed": True}], suite="checkout-assistant")
```

## 3. Run

Start with a dry run: it estimates cost and says, per call type, whether the run can proceed
(`runnable`, `not_runnable`, `deduped`, `budget_queued`) without spending anything.

```python
estimate = client.bench.run(
    suite="checkout-assistant",
    max_cost_usd=5,
    candidates=["openai/gpt-5.2"],
    dry_run=True,
)
print(estimate.estimate_usd, [(d.call_type_id, d.disposition) for d in estimate.dispositions])

run = client.bench.run(
    suite="checkout-assistant",
    max_cost_usd=5,
    candidates=["openai/gpt-5.2"],
    wait=True,  # poll until complete or failed
    poll_interval=2.0,
    wait_timeout=600,
)
print(run.status)
```

With `wait=True` the return type is `BenchRunTrigger | BenchRun` (a dry run, or a trigger that
created no run, comes back unchanged). Narrow it before using run-only fields:

```python
from ultrarouter.types import BenchRun

assert isinstance(run, BenchRun)
print(run.id, [eval_run.status for eval_run in run.runs])
```

`max_cost_usd` is a hard budget for the run. `wait=True` returns the finished
[`BenchRun`](types-reference.md#benchrun) (or raises `APITimeoutError` after `wait_timeout`);
without it you get the [`BenchRunTrigger`](types-reference.md#benchruntrigger) and can poll with
`client.bench.get(run_id)` or `client.bench.wait(run_id)`.

## 4. Read the report

```python
report = client.bench.report(run.id)
print(report.status, report.content_hash)
for call_type in report.call_types:
    for verdict in call_type.verdicts:
        print(call_type.call_type_id, verdict.model, verdict.overall, verdict.reasons)
print(report.limitations)

markdown = client.bench.report(run.id, format="md")  # a Markdown export (str)
bundle = client.bench.report(run.id, format="bundle")  # an offline-verifiable evidence bundle (str)
```

Reports state their evidence level and limitations; read those before acting on a result.

## 5. Baseline and compare gate (CI)

Pin a completed run as the suite baseline, then run a compare run for a change and read the
tri-state gate (`pass`, `fail`, `inconclusive`):

```python
client.bench.baseline(run.id)
compare = client.bench.run(
    suite="checkout-assistant",
    max_cost_usd=5,
    compare=True,
    baseline_run_id=run.id,
    wait=True,
)
assert isinstance(compare, BenchRun)
gate = client.bench.gate(compare.id)
print(gate.verdict, gate.reasons)
if gate.verdict != "pass":
    raise SystemExit(2)
```

## Async

Every method has an async twin on `AsyncUltraRouter`, including `run(wait=True)` and `wait()`.
