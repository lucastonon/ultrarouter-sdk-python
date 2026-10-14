"""Every API-key operation in the spec, mapped to the SDK call that exercises it.

Used by ``tests/test_api_coverage.py`` (each expression runs against the mock gateway, sync and
async, and the request it sends is validated against the spec) and by
``scripts/gen_coverage_doc.py`` (renders ``docs/api-coverage.md``). An expression is evaluated
with ``client`` bound to an :class:`~ultrarouter.UltraRouter` (or awaited on an
:class:`~ultrarouter.AsyncUltraRouter`) and ``ultrarouter`` imported.
"""

from __future__ import annotations

ORACLE_SECRET = "orsec_mock_signing_secret"

_IDENTITY = (
    '{"baseSha": "a1b2c3", "headSha": "d4e5f6", "configHash": "cfg1", "datasetSplit": "holdout", '
    '"evaluatorVersion": "ev1", "evidenceEpoch": "1", "harnessHash": "h1", "lockDigest": "l1", '
    '"objective": "acceptance_rate", "repository": "acme/app", "workflowId": "support-reply"}'
)

_REVIEWER_EVENT = (
    '{"event_id": "evt_1", "artifact_key": "ticket:1:reply", "artifact_version": 1, '
    '"decision": "approved_with_edits", "effective_at": "2026-01-15T12:00:00Z", '
    '"final": {"diff_stats": ultrarouter.diff_stats("draft", "final"), '
    '"hash": ultrarouter.diff_stats("draft", "final")["final_hash"]}}'
)

#: operationId -> SDK call expression (sync form; the async form is ``await <expression>``).
COVERAGE: dict[str, str] = {
    # OpenAI-compatible surface
    "createChatCompletion": (
        'client.chat.completions.create(model="openai/gpt-5.2-mini", '
        'messages=[{"role": "user", "content": "Hello"}])'
    ),
    "createEmbeddings": (
        'client.embeddings.create(model="openai/text-embedding-3-small", input=["a", "b"])'
    ),
    "listModels": 'client.models.list(provider="openai")',
    "getModel": 'client.models.retrieve("openai/gpt-5.2")',
    "getKey": "client.key.get()",
    # Requests
    "submitFeedback": 'client.requests.feedback("req_123", rating=1, tags=["helpful"])',
    "getGeneration": 'client.generation.get("req_123")',
    "getAuditReadiness": "client.autopilot.status()",
    # Call types
    "listCallTypes": "client.call_types.list()",
    "createCallType": (
        'client.call_types.create(slug="support-reply", config={"model_pin": "openai/gpt-5.2-mini"})'
    ),
    "getCallType": 'client.call_types.get("support-reply")',
    "updateCallType": 'client.call_types.update("support-reply", compression_mode="off")',
    "listCallTypeEvals": 'client.call_types.list_evals("support-reply")',
    "enqueueCallTypeEval": 'client.call_types.enqueue_eval("support-reply", mode="request")',
    "listCallTypeRecommendations": 'client.call_types.list_recommendations("support-reply")',
    "listHostedPrompts": 'client.call_types.prompts.list("support-reply")',
    "createHostedPrompt": (
        'client.call_types.prompts.create("support-reply", template="You are a {{tone}} agent.", '
        'variables=[{"name": "tone", "required": False}])'
    ),
    "getHostedPrompt": 'client.call_types.prompts.get("support-reply", 3)',
    "activateHostedPrompt": (
        'client.call_types.prompts.activate("support-reply", 3, gateway_apply=True)'
    ),
    "deactivateHostedPrompt": 'client.call_types.prompts.deactivate("support-reply")',
    "getHostedPromptProposal": 'client.call_types.prompts.proposal("support-reply")',
    "getVerifiedMemory": 'client.call_types.verified_memory.get("support-reply")',
    "enableVerifiedMemory": (
        'client.call_types.verified_memory.enable("support-reply", target_precision=0.95)'
    ),
    "disableVerifiedMemory": 'client.call_types.verified_memory.disable("support-reply")',
    # Preflight
    "preflight": (
        'client.preflight(call_type="support-reply", artifact_key="ticket:1:reply", '
        'messages=[{"role": "user", "content": "Where is my refund?"}])'
    ),
    # Bench
    "getBenchSuiteStatus": 'client.bench.status("my-suite")',
    "freezeBenchSuite": 'client.bench.freeze("my-suite", max_items=100)',
    "triggerBenchRun": (
        'client.bench.run(suite="my-suite", max_cost_usd=5, dry_run=True, '
        'candidates=["openai/gpt-5.2-mini"])'
    ),
    "getBenchRun": 'client.bench.get("bench_run_1")',
    "getBenchRunReport": 'client.bench.report("bench_run_1")',
    "attachBenchExpectations": (
        'client.bench.expect("my-suite", [{"kind": "json_schema", '
        '"config": {"required_fields": ["answer"]}}])'
    ),
    "recordBenchSuiteOutcomes": (
        'client.bench.record([{"trace": "trace-1", "passed": True}], suite="my-suite")'
    ),
    "recordBenchRunOutcomes": (
        'client.bench.record([{"trace": "trace-1", "passed": True}], run="bench_run_1")'
    ),
    "pinBenchBaseline": 'client.bench.baseline("bench_run_1")',
    "getBenchCompareGate": 'client.bench.gate("bench_run_1")',
    # Outcome ledger
    "upsertArtifactType": (
        'client.artifact_types.upsert(name="support-reply", archetype="draft", objective={'
        '"metric": "acceptance_rate", "unit": "ratio", "direction": "higher_is_better", '
        '"resolution_criteria": "approved without edits", "source": "reviewer", "window": "P7D"})'
    ),
    "createArtifact": 'client.artifacts.create(key="ticket:1:reply", archetype="draft")',
    "getArtifact": 'client.artifacts.get("art_123")',
    "listArtifacts": 'client.artifacts.list(limit=10, archetype="draft")',
    "recordArtifactFinal": (
        'client.artifacts.final("art_123", diff_stats=ultrarouter.diff_stats("draft", "final"), '
        'final_hash=ultrarouter.diff_stats("draft", "final")["final_hash"])'
    ),
    "recordArtifactOutcomes": (
        'client.outcomes.record("art_123", {"channel": "behavioral", "kind": "accepted"})'
    ),
    "recordRequestOutcome": (
        'client.outcomes.record({"request": "req_123"}, {"channel": "behavioral", '
        '"kind": "accepted"})'
    ),
    "recordOutcomesBatch": (
        'client.outcomes.batch([{"artifact_key": "ticket:1:reply", "channel": "resolution", '
        '"kind": "resolved", "value": {"correct": True}, "source_event_id": "evt-1"}])'
    ),
    "listPendingOutcomes": 'client.outcomes.pending(limit=10, state="overdue")',
    "createImport": (
        'client.imports.create(format="openai_usage", records=[{"model": "gpt-5.2-mini", '
        '"input_tokens": 10, "output_tokens": 5}], mode="preview")'
    ),
    "getImport": 'client.imports.get("imp_123")',
    "listImports": "client.imports.list(limit=10)",
    "cancelImport": 'client.imports.cancel("imp_123")',
    "listImprovementReads": "client.improvement_reads.list()",
    # Flywheel
    "getFlywheelStatus": "client.flywheel.status()",
    "mintExposureGrant": (
        'client.flywheel.grant(artifact_key="ticket:1:reply", call_type="support-reply")'
    ),
    "listFlywheelCandidates": "client.flywheel.candidates.list()",
    "getCandidateConfirmation": 'client.flywheel.candidates.confirmation("cand_1")',
    "recordCandidateDecision": (
        'client.flywheel.candidates.decide("cand_1", decision="accept", actor_id="alice", '
        'reason="reviewed the screening evidence", evidence_hash="0" * 64, workspace_id="ws_123")'
    ),
    "evaluateCandidateRollout": (
        'client.flywheel.candidates.rollout("cand_1", candidate_state="screened", '
        f'change_shape="gateway_owned", observed_identity={_IDENTITY}, '
        "requires_repository_write=False)"
    ),
    "listConfirmations": "client.flywheel.confirmations()",
    "getMoatNext": "client.flywheel.moat_next()",
    "getLearningPlan": 'client.flywheel.plan("support")',
    "listLearningPlans": "client.flywheel.plans()",
    "listPromptCandidates": "client.flywheel.prompt_candidates()",
    "listVerdictSources": "client.flywheel.sources()",
    "issueVerdictSourceCheck": 'client.flywheel.source_checks.issue(call_type_id="ct_123")',
    "gradeVerdictSourceCheck": (
        'client.flywheel.source_checks.grade("vsc_123", verdicts=[{"probe_id": "p1", '
        '"kind": "resolved_false"}])'
    ),
    "registerOracle": (
        'client.flywheel.oracles.register(kind="customer_ci", transport="pull", '
        'spec={"description": "my CI check"})'
    ),
    "getOracle": 'client.flywheel.oracles.get("orc_123")',
    "qualifyOracle": (
        'client.flywheel.oracles.qualify("orc_123", examples=[{"input": "q", "output": "a"}])'
    ),
    "testOracle": ('client.flywheel.oracles.test("orc_123", probe={"input": "q", "output": "a"})'),
    "revokeOracle": 'client.flywheel.oracles.revoke("orc_123")',
    "claimOracleJobs": (
        f'client.flywheel.oracles.claim_jobs("orc_123", secret="{ORACLE_SECRET}", max=5)'
    ),
    "submitOracleVerdicts": (
        f'client.flywheel.oracles.submit_verdicts("orc_123", secret="{ORACLE_SECRET}", '
        'verdicts=[{"job_id": "job_1", "oracle_version": "v1", "candidate_sha256": "0" * 64, '
        '"verdict": "pass"}])'
    ),
    # Reviewer
    "getReviewerSetup": "client.reviewer.setup()",
    "runReviewerTest": 'client.reviewer.test("happy")',
    "recordReviewerEvents": f"client.reviewer.send([{_REVIEWER_EVENT}])",
    "repairReviewerEvent": (
        f'client.reviewer.repair({{"id": "entry_1", "event": {_REVIEWER_EVENT}}}, '
        "repin_to_current_version=True)"
    ),
    "getReviewerHealth": "client.reviewer.health()",
}

#: Operations reachable with an API key that the SDK deliberately does not wrap.
EXCLUDED: dict[str, str] = {
    "echo": "Diagnostic auth echo; client.key.get() verifies a key and returns more.",
}
