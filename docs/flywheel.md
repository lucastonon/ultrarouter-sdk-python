# Flywheel

The flywheel turns your recorded outcomes into improvement candidates (learned context, model
changes, hosted-prompt drafts), screens them offline, confirms them on live traffic against a
holdout, and lets a person adopt them. This page covers the read and decision surfaces; most
reads need `config:read`, writes need `outcomes:write`.

## Status

```python
from ultrarouter import UltraRouter

client = UltraRouter()
status = client.flywheel.status()
print(status.usage.tracked_artifacts, status.usage.accepted_outcomes)
for channel in status.channels:
    print(channel.channel, channel.accepted_outcomes, channel.last_observed_at)
print(status.imports.total, status.learning.flywheel_class)

learning = client.flywheel.calibration()  # the same read's `learning` block
print(learning.calibration_available, learning.flywheel_class_reason)
```

`calibration()` reports whether calibration is available; it never fabricates a track record.

## Improvement reads

For every call type, two reads side by side: can it spend less (a cheaper model is enough) and can
it get better (a quality improvement is available). Each half is one state with the next action.

```python
reads = client.improvement_reads.list()
for row in reads.call_types:
    print(row.slug, row.spend_less.state, row.get_better.state, row.get_better.next_action)
```

States are `evidence`, `collecting`, `needs_confirmation`, `keep_incumbent` and `unavailable`.
An `evidence` read names its evidence tier and is labelled when it is an estimate.

## What to do next

```python
plan = client.flywheel.moat_next(lever_family="learned_context")
for item in plan.items:
    print(item.call_type_id, item.situation_class, item.ready, item.next_action)
```

## Exposure grants

A grant assigns one call to the treated or holdout arm of a live experiment, so improvement can be
measured even when you call providers directly. [Preflight](preflight.md) returns the grant for you;
mint one directly with:

```python
grant = client.flywheel.grant(artifact_key="ticket:4812:reply", call_type="support-reply")
print(grant.grant_id, grant.arm, grant.epoch, grant.valid_until_epoch_close)
```

The same key in the same epoch always yields the same grant. Pass either `artifact_key` or
`trace_id`.

## Candidates, confirmations and decisions

```python
candidates = client.flywheel.candidates.list()
for candidate in candidates.candidates:
    print(candidate.run_id, candidate.lever_key, candidate.offline_verdict, candidate.live_verdict)

confirmations = client.flywheel.confirmations()
for confirmation in confirmations.confirmations:
    print(
        confirmation.candidate_ref,
        confirmation.status,
        confirmation.result_outcome,
        confirmation.adoptable,
    )

state = client.flywheel.candidates.confirmation("cand_ref_1")
print(state.present, state.adoptable, state.adopt_refusal)
```

A person records accept / reject / revert decisions. The request is signed with your API key and
replay-safe (re-sending the same decision returns `duplicate`); the decision is an audit record,
never a learning label:

```python
decision = client.flywheel.candidates.decide(
    "cand_ref_1",
    decision="accept",
    actor_id="alice@example.com",
    reason="Screening and live confirmation both reviewed.",
    evidence_hash="0" * 64,
    workspace_id="ws_123",
)
print(decision.status, decision.callback_id)
```

A CI system can ask whether a screened candidate's controlled rollout is unlocked; the server
decides and names every blocker, and never starts the rollout itself:

```python
rollout = client.flywheel.candidates.rollout(
    "cand_ref_1",
    candidate_state="screened",
    change_shape="gateway_owned",
    observed_identity={
        "repository": "acme/app",
        "workflowId": "support-reply",
        "baseSha": "a1b2c3",
        "headSha": "d4e5f6",
        "configHash": "cfg-1",
        "datasetSplit": "holdout",
        "evaluatorVersion": "ev-1",
        "evidenceEpoch": "1",
        "harnessHash": "h-1",
        "lockDigest": "l-1",
        "objective": "acceptance_rate",
    },
    requires_repository_write=False,
)
print(rollout.unlocked, [b.reason for b in rollout.blockers], rollout.pressed)
```

## Learning plans and prompt candidates

```python
for proposal in client.flywheel.plans().plans:
    print(proposal.id, proposal.workflow_id, proposal.review_state, proposal.provenance)

envelope = client.flywheel.plan("support-reply")  # plan is None while still collecting
print(envelope.workflow_id, envelope.plan.review_state if envelope.plan else "collecting")

for draft in client.flywheel.prompt_candidates().candidates:
    print(draft.version_id, draft.status, draft.is_active_version, draft.approve_refusal)
```

Related: [Oracles and verdict sources](oracles.md), [Reviewer adapter](reviewer.md),
[Preflight and learned context](preflight.md).
