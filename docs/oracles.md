# Oracles and verdict sources

An *oracle* is a check you own that can tell a right answer from a wrong one (a label set, schema
rules, a test endpoint, a reconciliation job, or your CI). Registered checks earn a role
(`detector` or `certifier`) by being qualified against planted failures; only qualified checks
count. A *verdict source* is anything that reports task outcomes; it must show it reports known
failures as failures before its verdicts count toward readiness.

## Register a check

```python
from ultrarouter import UltraRouter

client = UltraRouter()
registration = client.flywheel.oracles.register(
    kind="customer_ci",
    transport="pull",
    spec={"description": "Runs the order-status contract tests"},
)
print(registration.oracle_id, registration.version_hash, registration.inserted)
secret = registration.secret  # pull / push only: returned once, store it securely
```

`kind` is `label_set`, `schema_rules`, `test_endpoint`, `reconciliation` or `customer_ci`;
`transport` is `platform` (runs inside the gateway), `push` (the gateway calls your endpoint) or
`pull` (your worker claims jobs). Registering the same spec again is a no-op; a changed spec
appends a version.

```python
oracle = client.flywheel.oracles.get(registration.oracle_id)
print(
    oracle.revoked,
    oracle.role.qualified,
    oracle.role.reason,
    [v.version_hash for v in oracle.versions],
)
```

## Qualify and test

```python
qualification = client.flywheel.oracles.qualify(
    registration.oracle_id,
    examples=[{"input": f"order {n} status?", "output": f"Order {n} shipped."} for n in range(10)],
)
print(qualification.status, qualification.result, qualification.role)

probe = client.flywheel.oracles.test(registration.oracle_id, probe={"input": "q", "output": "a"})
print(probe.status, probe.verdict)
```

Qualification plants failures into your known-good examples; a pull check's probes wait for your
worker (`status="pending"`) and are graded when the last verdict arrives.

## Pull transport: claim jobs and post verdicts

A pull worker claims due jobs and answers each with `pass` or `fail`. Both calls are signed with
the oracle secret (`X-UR-Oracle-Signature`); the SDK signs the exact bytes it sends.

```python
jobs = client.flywheel.oracles.claim_jobs(registration.oracle_id, secret=secret or "", max=10)
verdicts = []
for job in jobs.data:
    passed = job.output.strip() != ""  # your real check goes here
    verdicts.append(
        {
            "job_id": job.job_id,
            "oracle_version": job.oracle_version,
            "candidate_sha256": job.candidate_sha256,
            "verdict": "pass" if passed else "fail",
            **({} if passed else {"reasons": ["missing_field"]}),
        }
    )
if verdicts:
    result = client.flywheel.oracles.submit_verdicts(
        registration.oracle_id, secret=secret or "", verdicts=verdicts
    )
    print(result.accepted, result.duplicate, result.refused)
```

Each job payload is returned once. Posting the same verdict again is a visible `duplicate`; a
different answer for an answered job is a `conflict` and never overwrites.

## Revoke

```python
revocation = client.flywheel.oracles.revoke(registration.oracle_id)
print(revocation.already_revoked, revocation.cancelled_jobs)
```

Revocation is terminal: every receipt of every version stops counting.

## Verdict sources

```python
sources = client.flywheel.sources()
for source in sources.data:
    print(source.verdict_source, source.eligible, source.reason, source.eligible_task_verdicts)
```

To qualify a source, issue a planted-failure check and answer every probe exactly once with
`resolved_true` or `resolved_false`:

```python
check = client.flywheel.source_checks.issue(call_type_id="ct_123")
answers = [{"probe_id": probe.probe_id, "kind": "resolved_false"} for probe in check.probes]
graded = client.flywheel.source_checks.grade(check.id, verdicts=answers)
print(graded.result, graded.qualified, graded.recall.value, graded.specificity.value)
```

Only the credential that issued a check can answer it, and a check is graded once.
