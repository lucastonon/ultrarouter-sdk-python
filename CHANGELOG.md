# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/) (before 1.0, minor versions may contain breaking changes).

## [Unreleased]

## [0.0.1] - 2026-10-13

First public release.

### Added

- `UltraRouter` and `AsyncUltraRouter` clients with the same surface: configuration from
  `ULTRAROUTER_API_KEY` / `ULTRAROUTER_BASE_URL`, automatic retries with jittered backoff and
  `Retry-After`, idempotency keys on every non-streaming `POST`, custom `httpx` clients, and
  context-manager lifecycles.
- A total time budget per call (`timeout`) enforced as a real deadline across connecting,
  waiting, reading the whole response body, retries and backoff (a slowly dripping body cannot
  outlive it). A timed-out synchronous call stops its transfer at once (no request thread keeps
  reading), and request threads are bounded per client. For streams, `timeout` is the deadline
  for the response to start (including reading an error body) and then the longest silence
  allowed between chunks; a stall or a broken connection mid-stream raises `APITimeoutError` /
  `APIConnectionError` from the iterator.
- `with_options(...)`: a derived client whose own headers, timeout and retries also apply to the
  outcome events and reviewer decisions it delivers; it shares the parent's connection pool,
  durable stores and preflight cache (documented policy).
- OpenAI-compatible surface: `chat.completions.create` (streaming, tools, structured outputs),
  `embeddings.create`, `models.list`, `models.retrieve`, and `as_openai()` returning a configured
  `openai.OpenAI` / `openai.AsyncOpenAI` (optional `openai` extra).
- `Stream` / `AsyncStream` with `text()`, and the final chunk's `usage` and `ur` block kept on the
  stream object.
- `UltraRouterError.envelope` and `parse_gateway_error_envelope(...)`: the validated gateway error
  envelope, present only for a complete `{"error": {code, message, request_id, retryable}}` body.
- Typed errors for every gateway error code, including `ModelUnpricedError` (`model_unpriced`,
  HTTP 403) and `ModelDeniedByPolicyError` (`model_denied_by_policy`, HTTP 403); both are never
  retried. Retries also respect the gateway's `retryable: false` flag on 5xx responses, and a
  code the taxonomy marks non-retryable stays non-retryable even if a response claims
  `retryable: true`.
- Preflight: `client.preflight(...)` with the two-lifetime client-side cache and a never-cached
  exposure grant; the optional `messages=` argument, required for case-based learned modules
  (without it the gateway answers `knowledge_reason="case_query_missing"`); `use_learned(...)`
  returning a `LearnedSession` (`apply`, `record`); `get_prompt(...)`. The cache is bounded
  (`preflight_cache_size=`, default `DEFAULT_PREFLIGHT_CACHE_SIZE` = 1024, least recently used
  evicted first, expired entries dropped).
- Call types (create, list, get, update, eval triggers and runs, recommendations), hosted prompts
  (create, list, get, activate, deactivate, proposal) and verified memory (get, enable, disable).
- Feedback, generation lookup, key introspection (`client.key.get()`), and the Autopilot intent and
  readiness report.
- Bench: status, freeze, run (with `wait=True` polling), get, wait, report (JSON, Markdown,
  bundle), expectations, outcomes, baseline and compare gate.
- Outcome ledger: artifact types, artifacts (create, get, list, final), outcome events through a
  durable queue (`MemoryOutcomeStore`, `FileOutcomeStore`, `outcomes.size()`), batches, pending
  claims, history imports, and the `with_artifact(...)` scope. An event leaves the queue only on
  a valid outcome result or a validated refusal of the event (a complete gateway error envelope
  with `invalid_request`, `not_found` or `conflict` at that code's status and `retryable: false`,
  on a 4xx other than 401/403/408/429); timeouts, cancellation, connection failures, any
  401/403/408/429, 5xx, incomplete envelopes and malformed successes keep it queued, replayed
  later with the same identity and `Idempotency-Key`. The reviewer queue removes an event only on
  a valid per-event verdict. The rules match the TypeScript SDK case for case (a shared fixture). A `FileOutcomeStore` starts empty only when its file is absent: a damaged or
  unreadable file raises `OutcomeStoreError` and is never overwritten.
- Flywheel: status and calibration, exposure grants, candidates (list, confirmation, signed
  decisions, rollout evaluation), confirmations, learning plans, prompt candidates, improvement
  reads, oracles (register, get, qualify, test, revoke, signed pull-transport jobs and verdicts),
  and verdict sources and source checks.
- Reviewer adapter: signed, durable reviewer decisions with dead letters and repair.
- `ultrarouter.context`: a pure context runtime (`from_messages`, `to_messages`, `compile`,
  `render`, `to_wire`, compatibility profiles) whose output is checked against the TypeScript
  SDK on shared synthetic fixtures, including keys named like JavaScript prototype members
  (`__proto__`), which canonical JSON and `from_messages` / `to_messages` keep at every depth.
- Pure helpers: `diff_stats`, `render_prompt`, `render_hosted_prompt_result`,
  `learned_placement_index`, `apply_learned_context`, and the signing helpers.
- Response models and request shapes generated from the API specification, shipped with
  `py.typed` and checked with `mypy --strict`.
- Documentation for every surface, an API reference, a types reference, an endpoint coverage
  table, runnable examples, `AGENTS.md`, `llms.txt` and `llms-full.txt`.
- Tested dependency floors: `httpx>=0.27`, `pydantic>=2.7`, `typing-extensions>=4.12` and, for
  the `openai` extra, `openai>=1.55.3` (older `openai` releases cannot build a client with
  `httpx` 0.28 or newer). The suite runs at these floors in CI.

[Unreleased]: https://github.com/lucastonon/ultrarouter-sdk-python/compare/v0.0.1...HEAD
[0.0.1]: https://github.com/lucastonon/ultrarouter-sdk-python/releases/tag/v0.0.1
