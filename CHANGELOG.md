# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/) (before 1.0, minor versions may contain breaking changes).

## [Unreleased]

- The `request_refused` error code (404, not retryable) and its class `RequestRefusedError`, a
  subclass of `NotFoundError`. A request the gateway refused before any provider was called (a spend
  cap, a rate limit, an invalid body, an unpriced or denied model) is never recorded; the request
  lookups now answer `request_refused` for 20 minutes instead of `request_not_landed`, so the
  client raises at once instead of retrying for 15 minutes.
- New methods for the memory operations the synced API specification adds, each with an async
  twin, under `client.learning`: `memory_items(...)` / `set_memory_items(...)` (serve a call type
  from memory items), `rules(...)`, `create_rule(...)`, `retire_rule(...)` and `restore_rule(...)`
  (rules, notes and feedback comments), `validate_item(...)` (a developer's or tenant admin's
  validation), `conversation_memory(...)` / `set_conversation_memory(...)` (each end user's own
  earlier conversations; switching on is the workspace owner's, signed in) and
  `set_retrieval(...)` (how memory picks examples; `None` goes back to picking by words only).
  Storing a rule or a note is not idempotent, so `create_rule` is sent once unless
  `options={"max_retries": n}` allows retries. The workspace's memory tenant setting is an
  owner-session operation without a method. New public models: `ConversationMemory`,
  `MemoryItemsSetting`, `MemoryItemValidation`, `MemoryRule`, `MemoryRuleList`, `MemoryRuleChange`,
  `RetrievalRecipe` and their `...Params`; the `GivenBy` literal names who gives an item.
- **Feedback right after an answer, and who gives it.** Feedback sent the moment an answer arrives
  (`client.requests.feedback`), the generation lookup (`client.generation.get`) and an artifact
  declared with `request_ids` can answer `503 request_not_landed` (retryable, `Retry-After: 2`)
  while the gateway records the request; nothing is stored on the 503 and the SDK retries it.
  `client.requests.feedback` gains `given_by` (`developer`, `tenant_admin` or `end_user`; the first
  two are honoured only from an API key marked server-side) and `user` (the giver's end-user key;
  the gateway stores only a digest); `Feedback` gains `giver_role` and `memory_item_id` (the memory
  item a comment became when the workspace granted the corrections consent, or `None`). API keys
  in key listings carry `serverSide` and `memoryTenantBound`.
- New methods for the operations the synced API specification adds, each with an async twin:
  `client.call_types.episode_memory.evictions(...)` (the operations log), `.evict(...)` (evict,
  or erase with `erase=True`; `dry_run=True` counts only), `.import_pairs(...)` (approved pairs),
  `.precedents(...)` and `.precedent(...)`; `client.learning.set_read_limit(call_type_id, ms)`
  (the learned-memory read deadline, 25 to 2,000 ms) and `client.learning.cost(...)`; and
  `client.knowledge.ask(question=...)`, which is not idempotent (a retry is a new charge) and is
  therefore sent once unless `options={"max_retries": n}` allows retries. Correction-lesson sharing,
  its approval and restoring an eviction are owner-session operations without a method.
- **The end-user key, `ur.memory_partition`** (generated in `UrParams`, 1 to 1,024 characters). It
  names the end user a request is for. Under a call type scoped `partitioned`, a verified answer is
  shown only to later requests with the same key. First match wins: this field, then the
  `X-UR-Memory-Partition` header, then the OpenAI `user` field. The gateway stores only a digest of
  it.
- **Self-serve precedent memory and its end-user scope.** The first enable of episode memory on a
  call type (`episode_memory.self_serve`) declares its end-user scope (`memory_scope`: `shared` or
  `partitioned`). Only the workspace owner, signed in, can make it: in the dashboard's agent memory
  control for the call type, or with the owner's session. An API key cannot. After that first
  enable, a `config:write` key can re-enable the call type with the scope and the
  `source_call_type_id` in force (naming the scope or leaving it out), for example to change `k`.
  The two refusals a key meets: leaving `memory_scope` out on a call type with no scope recorded is
  `400 invalid_request`, message `memory_scope_required: …`; naming a scope on a first enable, a
  different scope, or another `source_call_type_id` is `403 permission`, message
  `scope_declaration_owner_only: …`. An admin's session gets the same 403.
- **Requests must land first.** An outcome, a final or a reviewer event naming a request that has
  not been recorded yet answers `503 request_not_landed` (retryable, `Retry-After: 2`); the SDK
  retries it (`RequestNotLandedError` once retries are spent). After the 15-minute window a request
  that never landed answers `404 request_not_found`, the same as an id from another workspace. No
  pending receipt is held for such a request any more. Request ids are plain `req_` + a ULID again;
  ids issued before stay valid. An outcome receipt can read `status: "erased"`
  (`reason: "end_user_erased"`): the end user of its request was erased; the episode association's
  `reason` can be `end_user_erased`. `Idempotency-Key` replays are kept per API key: the same key
  sent by two API keys is two separate claims. The memory erasure response counts each store it
  cleared in `erased` and, per store, the rows an earlier erasure had already erased in
  `already_erased`.
- Three gateway error codes, each with its class: `request_not_landed` (`RequestNotLandedError`)
  and `workspace_busy` (`WorkspaceBusyError`), both 503 and retried after `Retry-After`, and
  `internal_knowledge_ask` (`InternalKnowledgeAskError`, a 403 `PermissionDeniedError`, never
  retried: a knowledge-ask `req_int_…` id named where a learning request belongs).
- Generated types follow the synced specification: the learning status adds `explanation`,
  `serving_stopped`, `correction_lesson_sharing` and `memory_read`; an evaluation adds `observed`
  and `outcome_source`; a version adds `lesson_source` and can be `held_for_approval`; a receipt's
  `episode` adds `reason`; `GenerationStats` adds `client_request_id`; the chat `ur` block adds
  `learned_injection` and `learning_serving`. The new models have public names
  (`EpisodeEvictionList`, `EpisodeEvictionResult`, `EpisodeMemoryImportResult`,
  `EpisodePrecedentList`, `EpisodePrecedent`, `LearningCost`, `CompanyKnowledgeAnswer`, ...).
- The type generator types a reference to a named string (an id) as `str` instead of an empty
  class, keeps `OutcomeReceiptRecord`, `ChatContentPartParam` and `CacheControlParam` when a new
  operation repeats their shape, and gives a functional `TypedDict` its docstring.

- `client.call_types.episode_memory.self_serve(...)` (and its async twin) turns precedent episode
  memory on through the customer route `POST /v1/call-types/{id}/episode-memory/self-serve`, with
  the same knobs as `enable` except `lessons`, and no lab grant.

- Read-only company knowledge browsing/search and detail, with typed results, cursors and
  namespaced item IDs. Examples inspect state and provenance without model calls. Content export
  remains a separate owner/admin session operation; malformed and reserved export IDs fail locally.

- Exact-answer learning examples now verify trimmed `OK`, including negative tests for a wrong
  non-empty answer or an empty answer, instead of reporting success for any text or hardcoding pass.

- Learning examples resolve a call type before inference, send its slug on every call and use its
  `ct_...` ID for learning controls. The controls-only example rejects missing IDs and slugs before
  making requests. Setup requires the full workspace knowledge and corrections opt-in. Corrected
  learning documentation and actionable errors that previously suggested slugs on ID-only routes.

- Learning setup and refusal guidance require the full owner/admin self-learning opt-in
  (knowledge and corrections consent); the synced API specification carries the same requirement.

## [0.1.0] - Unreleased

The plug-and-play learning surface. The version moves to 0.1.0 with it (the TypeScript SDK's
matching release is planned at the same version). The package is not published to PyPI; install
from a locally built wheel or the GitHub source (the README and the installation guide no longer
advertise a registry install).

### Added

- **Request and episode correlation.** `chat.completions.create(...)` and `embeddings.create(...)`
  take `request_id=` (sent as `x-ur-request-id`, `[A-Za-z0-9_-]{1,64}`) and `episode_key=` (sent as
  `X-UR-Artifact`); `UltraRouter(request_ids="client")` mints a request id for every call.
  `new_request_id()` (`req_c_<ULID>`), `new_episode_key()`, `correlation_headers(...)` (for the
  `openai` package or any HTTP client), `request_id_of(result)` (SDK results, streams, `openai`
  responses, raw responses and headers), `REQUEST_ID_HEADER` and `EPISODE_HEADER`.
  `Stream.request_id` / `AsyncStream.request_id` are known as soon as a stream opens. An error raised
  for a call that carried a minted id, without an answer from the gateway, reports that id.
- **Episodes.** `client.episode(key=None)` is a (async) context manager whose
  `episode.chat.completions.create(...)` steps carry the key and a freshly minted request id each;
  `episode.report(...)` reports the terminal verdict on the last step.
- **Verdict reports.** `client.outcomes.report(request_id, verdict, source=..., idempotency_key=,
  observed_at=, evidence_hash=, supersedes=)` maps `pass` / `fail` from `verifier`,
  `business_rule`, `webhook`, `human_review` or `self_rating` to an outcome channel and kind
  through the verdict table shared byte for byte with the TypeScript SDK
  (`ultrarouter/_data/outcome_verdicts.json`); `unknown` sends nothing (`NotReportedOutcome`). The
  return type shows whether the report teaches (`TeachingOutcomeReport`) or is a proxy that never
  teaches (`ProxyOutcomeReport`). The `source_event_id` is derived (`report_source_event_id`,
  identical to the TypeScript SDK's) and the event goes through the durable queue under that
  identity, so a lost acknowledgement, a flush or a repeated call replays the identical event, and
  concurrent repeats share one send.
- **Outcome receipts.** A `pending` answer is now a delivered outcome result (an outcome reported
  before the gateway stored its request: the gateway holds a durable receipt and applies it when
  the request lands); the shared queue-retention fixture, copied again from the TypeScript SDK,
  has 273 cases including the two `pending` ones. `outcomes.receipt(id)`,
  `outcomes.receipts_for_request(request_id)` and `outcomes.wait_for_receipt(receipt, timeout=)`
  (bounded backoff polling of the public receipt endpoint, 250 ms doubling to 4 s, 30 s by
  default; a read that timed out or failed retryably is one missed poll; cancellable on the async
  client; `ReceiptWaitTimeoutError` carries the last receipt read). A receipt (`ocr_...`) carries
  its status, reason, `outcome_status`, episode association (`status`, `trace_id`, `verdict`) and
  deadline.
- **Learning controls.** `client.learning.status / enable / pause / resume / disable / versions /
  version / rollback / promote / reject / evaluations(call_type_id, ...)`, sync and async. `status`
  returns a `LearningStatus` (state, reason, active version and latest candidate, running and
  latest evaluation, promotion policy, recipe, evidence, outcome receipts by state, reflection
  provider, budget, usage); every control returns a `LearningControl` (`action`, `changed`, the
  version acted on, a stopped evaluation, the resulting status). Refusals raise actionable typed
  errors recognised from the gateway's refusal code (the first token of its message), each with
  `reason`, `refusal`, `detail` and `action`: `LearningConsentRequiredError`,
  `LearningProviderUnavailableError`, `LearningPolicyInvalidError`, `LearningNotEnabledError`,
  `LearningVersionConflictError`,
  `LearningQuotaExhaustedError`, `LearningBudgetExhaustedError`, `LearningNotFoundError`,
  `LearningForbiddenError`.
- **Episode memory.** `client.call_types.episode_memory.get / enable / disable`, the lower-level
  setting learning writes (`enable` is a lab-authorised lever).
- `outcome_backlog_full` (429, retryable after `Retry-After`) joins the error taxonomy as
  `OutcomeBacklogFullError`.
- **Outcome adapters** (`ultrarouter.adapters`), with the TypeScript SDK's semantics, reasons and
  hashes: `run_verifier`, `verdict_from_command` and `run_test_suite` (a computable check, a
  command's exit code or a test suite as a verdict; a check that cannot decide is `unknown`),
  `validate_output` (pydantic structured-output validation plus named business rules; always
  `pass` or `fail`, reasons without values), `evidence_hash` (`sha256:` over canonical JSON), and
  `WebhookVerifier` / `WebhookOutcomeHandler` / `sign_webhook` (`x-webhook-signature` =
  HMAC-SHA256 over `"<timestamp>.<body>"`, `x-webhook-timestamp` within ±300 s, constant-time
  comparison, secret rotation, secret from `ULTRAROUTER_WEBHOOK_SECRET`, event-id deduplication
  for 7 days through a `DedupeStore` with an in-memory default; the handler answers `reported` /
  `duplicate` 200, `rejected` 401/400 or `deferred` 503 with the claim released).
- **A demonstration environment** (`ultrarouter.demo.OrderDesk`): the deterministic order-desk
  tools, exact rules and verifier (orders in task order, and each SKU's stock consistent with its
  reservations) from the fixture shared with the TypeScript SDK; labelled a demonstration, not
  evidence that learning improves an agent. As in JSON Schema, an integral number (`2.0`) is an
  integer argument and `2.5` is not, so both SDKs answer every tool call identically.
- The OpenAPI specification is resynced: the receipt, learning and episode-memory operations are
  generated models (`OutcomeReceiptRecord`, `OutcomeReceiptRecordList`, `RequestOutcomeResult`,
  `LearningStatus`, `LearningControl`, `LearningVersionList`, `LearningVersionDetail`,
  `LearningEvaluationList`, `LearningEnableParams`, `EpisodeMemoryStatus`, ...) and every one is
  mapped in the API coverage table, sync and async. `is_terminal_receipt_status()` and
  `RECEIPT_TERMINAL_STATUSES` tell a final receipt status.
- New guide `docs/learning.md`; eight runnable examples (`examples/learning_*.py`: the `openai`
  package, a native verifier, a tool episode, an immediate outcome, a delayed webhook,
  acknowledgement loss, learning controls, the async client). The mock gateway in
  `tests/support/` answers the new endpoints.
- The bounded-experiment RUN surface under `client.flywheel.experiments` (sync and async), for a key
  with the `flywheel:experiment:run` scope: `enrol(experiment_id, phase=, pair_key=, slot=)` enrols
  one execution slot (the gateway decides the arm, never the caller; a repeat of the same tuple
  returns the same execution, so a resume is safe), `outcome(experiment_id, execution_id, ...,
  dry_run=False)` records the one body-free terminal outcome and, with `dry_run=True`, sends
  `?dry_run=true` and returns the dry-run answer with nothing written (both shapes are the
  `ExperimentExecutionOutcome` model, discriminated by `object` — the generator merges the response
  `oneOf`), and `evaluate_screen` / `evaluate_test` run the screen / prospective-test evaluation
  explicitly. Named refusals (`experiment_not_live`, `phase_not_open`, `outcome_conflict`,
  `receipt_missing:<stage>`, …) reach the caller on the typed error. `EXPERIMENT_EXECUTION_HEADER`
  (`x-ur-experiment-execution`) is exported for the header every call of a run carries. The
  owner-session operations (holds, reconcile, judgements, acknowledge, test fund / manifest) stay
  unmapped — an API key cannot call them. New guide section: "Running a bounded experiment" in
  `docs/flywheel.md`.
- Native passthrough for the OpenAI Responses API (`POST /v1/responses`) and the Anthropic Messages
  API (`POST /v1/messages`). The gateway forwards these bodies verbatim and meters the call; point
  the official `openai` and `anthropic` SDKs at the gateway, or reach the routes from this SDK's raw
  request surface. New guide: `docs/passthrough.md`.
- `APIRequest` is now exported from the package: the prepared call passed to a client's
  `request`, `request_json`, `request_model` and `request_text` methods for endpoints the typed
  methods do not wrap. A non-`None` `body` is now sent automatically (no need to set `has_body`).
- `ConfigurationError`, a subclass of `UltraRouterError` raised before any network call when the
  client cannot be constructed because the API key or the gateway base URL is missing. Exported
  from the package.

### Changed

- The gateway base URL is now required. `UltraRouter` and `AsyncUltraRouter` resolve it from the
  `base_url=` argument, then `ULTRAROUTER_BASE_URL`, then `UR_BASE_URL`; with none set, the
  constructor raises `ConfigurationError` (`code="missing_base_url"`) whose message names the
  argument, both environment variables and `http://localhost:8080` as the local-gateway example.
  There is no hosted gateway to default to.
- A missing API key now raises the new `ConfigurationError` (`code="missing_api_key"`, unchanged
  code and message) instead of a bare `UltraRouterError`; `except UltraRouterError` still catches it.

### Removed

- `DEFAULT_BASE_URL`. The SDK no longer ships a default gateway URL; supply one explicitly via
  `base_url=`, `ULTRAROUTER_BASE_URL` or `UR_BASE_URL`.

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
