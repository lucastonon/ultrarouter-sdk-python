"""The ultrarouter clients: :class:`UltraRouter` (sync) and :class:`AsyncUltraRouter` (async)."""

from __future__ import annotations

import copy
import time
from collections.abc import Awaitable, Callable, Mapping, Sequence
from types import TracebackType
from typing import Any, Literal

import httpx

from ._base_client import (
    AsyncAPIClient,
    RequestOptions,
    SyncAPIClient,
    default_async_sleep,
    default_rand,
    default_sleep,
    parse_model,
)
from ._config import (
    AutopilotMode,
    BenchTag,
    Defaults,
    apply_chat_defaults,
    apply_embedding_defaults,
)
from ._constants import DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT_S
from ._episode import AsyncEpisode, Episode
from ._errors import InvalidRequestError, UltraRouterError
from ._learned_placement import apply_learned_context
from ._preflight import (
    DEFAULT_PREFLIGHT_CACHE_SIZE,
    PREFLIGHT_GRANT_HEADER,
    PreflightCache,
    build_cache_entry,
    decide_preflight_cache,
    parse_grant_header,
    preflight_cache_key,
    preflight_has_cluster_key,
    with_header_grant,
)
from ._queue import (
    AsyncOutcomeQueue,
    AsyncReviewerQueue,
    MemoryOutcomeStore,
    OutcomeFlushReport,
    OutcomeQueue,
    OutcomeReceipt,
    OutcomeStore,
    QueuedEntry,
    ReviewerQueue,
)
from ._resources._base import build, seg
from ._resources.bench import AsyncBench, Bench
from ._resources.call_types import AsyncCallTypes, CallTypes
from ._resources.chat import AsyncChat, Chat
from ._resources.embeddings import (
    AsyncEmbeddings,
    AsyncKey,
    AsyncModels,
    Embeddings,
    Key,
    Models,
)
from ._resources.flywheel import AsyncFlywheel, Flywheel
from ._resources.learning import AsyncLearning, Learning
from ._resources.ledger import (
    Archetype,
    Artifacts,
    ArtifactTypes,
    AsyncArtifacts,
    AsyncArtifactTypes,
    AsyncImports,
    AsyncImprovementReads,
    AsyncOutcomes,
    Imports,
    ImprovementReadsResource,
    Outcomes,
)
from ._resources.misc import (
    AsyncAutopilot,
    AsyncGeneration,
    AsyncRequests,
    Autopilot,
    Generation,
    Requests,
)
from ._resources.reviewer import AsyncReviewer, Reviewer, signed_events_request
from ._streaming import AsyncStream, Stream
from .types import (
    ArtifactFinal,
    ChatCompletion,
    CreateEmbeddingResponse,
    OutcomeParams,
    PreflightGrant,
    PreflightKnowledge,
    PreflightPrompt,
    PreflightResponse,
)

__all__ = [
    "ArtifactScope",
    "AsyncArtifactScope",
    "AsyncLearnedSession",
    "AsyncUltraRouter",
    "LearnedSession",
    "UltraRouter",
]


RequestIdMode = Literal["gateway", "client"]
"""Who mints request ids: the gateway (default) or the client (``x-ur-request-id``)."""


def _request_id_mode(value: str) -> str:
    if value not in ("gateway", "client"):
        raise ValueError(f"request_ids must be 'gateway' or 'client' (got {value!r})")
    return value


def _now_ms() -> float:
    return time.time() * 1000


def _preflight_params(
    call_type: str,
    artifact_key: str | None,
    trace_id: str | None,
    budget: Mapping[str, Any] | None,
    messages: Sequence[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    params: dict[str, Any] = {"call_type": call_type}
    if artifact_key is not None:
        params["artifact_key"] = artifact_key
    if trace_id is not None:
        params["trace_id"] = trace_id
    if budget is not None:
        params["budget"] = dict(budget)
    if messages is not None:
        params["messages"] = [dict(m) for m in messages]
    return params


def _learned_artifact_params(
    artifact_key: str | None, archetype: str, grant: PreflightGrant | None
) -> dict[str, Any]:
    if artifact_key is None:
        raise InvalidRequestError(
            "LearnedSession.record needs artifact_key= on use_learned(...) to attach the grant "
            "to an artifact",
            status=0,
        )
    params: dict[str, Any] = {"key": artifact_key, "archetype": archetype}
    if grant is not None:
        params["grant_id"] = grant.grant_id
        params["attestation"] = "applied"
    return params


def _merge_extra_body(body: dict[str, Any], extra_body: Mapping[str, Any] | None) -> dict[str, Any]:
    if extra_body:
        body.update(extra_body)
    return body


def _bind_artifact(kwargs: dict[str, Any], key: str) -> dict[str, Any]:
    ur = dict(kwargs.get("ur") or {})
    ur.setdefault("artifact", key)  # an explicit per-call ur.artifact wins
    return {**kwargs, "ur": ur}


def _import_openai(name: str) -> Any:
    try:
        import openai
    except ImportError as exc:
        raise UltraRouterError(
            "as_openai() needs the openai package: install it (pip install openai), or install "
            "the ultrarouter wheel with its [openai] extra",
            code="dependency_missing",
        ) from exc
    return getattr(openai, name)


# ═══════════════════════════════════════ sync ═══════════════════════════════════════


class UltraRouter(SyncAPIClient):
    """The synchronous ultrarouter client.

    Example::

        from ultrarouter import UltraRouter

        client = UltraRouter()  # reads ULTRAROUTER_API_KEY (and ULTRAROUTER_BASE_URL)
        reply = client.chat.completions.create(
            model="openai/gpt-5.2-mini",
            messages=[{"role": "user", "content": "Say hello"}],
        )
        print(reply.choices[0].message.content, reply.ur.request_id)

    Args:
        api_key: Your ``ur_sk_...`` key. Defaults to ``ULTRAROUTER_API_KEY`` (or ``UR_API_KEY``).
        base_url: The gateway URL. Falls back to ``ULTRAROUTER_BASE_URL`` (or ``UR_BASE_URL``).
            There is no default gateway: with none from any source the constructor raises
            :class:`~ultrarouter.ConfigurationError`. A trailing ``/v1`` is accepted.
        default_model: Model used when a call does not pass ``model``.
        defaults: Per-call defaults (``router``, ``compression``, ``call_type``, ``provider``,
            ``max_cost_usd``); an explicit per-call value always wins.
        autopilot: ``"audit"``, ``"recommend"`` or ``"auto"``: the routing intent and the
            ceiling a per-call ``router`` can lower but never raise.
        bench: Tag every request for a Bench suite (``"suite"`` or
            ``{"suite": ..., "run": ..., "trace": ...}``). Defaults to ``UR_BENCH``.
        timeout: Total seconds per call, across retries (default 600).
        max_retries: Automatic retries for retryable failures (default 2).
        default_headers: Headers added to every request.
        outcome_store: Durable store for queued outcome events (default in-memory).
        reviewer_store: Durable store for queued reviewer decisions (default in-memory).
        preflight_cache_size: Most preflight identities kept in the client-side cache (least
            recently used evicted first; expired entries are dropped). ``0`` disables it.
            Default 1024.
        request_ids: Who mints request ids. ``"gateway"`` (default): the gateway does.
            ``"client"``: the SDK sends a freshly minted ``x-ur-request-id`` on every chat and
            embeddings call that does not pass ``request_id=``, so each call's id is known
            before it returns (and is set on the error when a call fails without an answer).
        http_client: Your own ``httpx.Client`` (proxies, transports, mocking). The SDK does not
            close a client you pass in.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str | None = None,
        default_model: str | None = None,
        defaults: Defaults | Mapping[str, Any] | None = None,
        autopilot: AutopilotMode | None = None,
        bench: str | BenchTag | Mapping[str, Any] | None = None,
        timeout: float = DEFAULT_TIMEOUT_S,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Mapping[str, str] | None = None,
        outcome_store: OutcomeStore | None = None,
        reviewer_store: OutcomeStore | None = None,
        preflight_cache_size: int = DEFAULT_PREFLIGHT_CACHE_SIZE,
        request_ids: RequestIdMode = "gateway",
        http_client: httpx.Client | None = None,
        _sleep: Callable[[float], None] = default_sleep,
        _rand: Callable[[], float] = default_rand,
        _clock: Callable[[], float] = time.time,
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            default_headers=default_headers,
            autopilot=autopilot,
            bench=bench,
            http_client=http_client,
            sleep=_sleep,
            rand=_rand,
            clock=_clock,
        )
        self.default_model: str | None = default_model
        self.defaults: dict[str, Any] = dict(defaults or {})
        self.request_ids = _request_id_mode(request_ids)
        self._outcome_queue = OutcomeQueue(
            outcome_store or MemoryOutcomeStore(), self._send_outcome
        )
        self._reviewer_queue = ReviewerQueue(
            reviewer_store or MemoryOutcomeStore(), self._send_reviewer_batch
        )
        self._preflight_cache = PreflightCache(preflight_cache_size)
        self._init_resources()

    def _init_resources(self) -> None:
        self.chat = Chat(self)
        """OpenAI-compatible chat completions: ``client.chat.completions.create(...)``."""
        self.embeddings = Embeddings(self)
        """OpenAI-compatible embeddings."""
        self.models = Models(self)
        """The model catalog."""
        self.key = Key(self)
        """Introspect the API key."""
        self.call_types = CallTypes(self)
        """Call types, config, evals, hosted prompts, verified memory."""
        self.requests = Requests(self)
        """Feedback on served requests."""
        self.generation = Generation(self)
        """Post-hoc stats for a request."""
        self.autopilot = Autopilot(self)
        """The Autopilot intent and readiness report."""
        self.bench = Bench(self)
        """Bench suites, runs, reports and the compare gate."""
        self.artifact_types = ArtifactTypes(self)
        """Artifact types and their objectives."""
        self.artifacts = Artifacts(self)
        """Artifacts (the units of value your app produces)."""
        self.outcomes = Outcomes(self)
        """Outcome events (durably queued)."""
        self.imports = Imports(self)
        """History imports."""
        self.improvement_reads = ImprovementReadsResource(self)
        """Per call type: can it spend less, can it get better."""
        self.flywheel = Flywheel(self)
        """Status, grants, candidates, oracles, plans and verdict sources."""
        self.reviewer = Reviewer(self)
        """Signed reviewer decisions."""
        self.learning = Learning(self)
        """Per-call-type learning: status, enable/pause/resume/disable, versions, evaluations."""

    # ── request shaping ────────────────────────────────────────────────────

    def _chat_body(
        self, params: dict[str, Any], extra_body: Mapping[str, Any] | None
    ) -> dict[str, Any]:
        body = apply_chat_defaults(
            params, self.default_model, self.defaults, self._autopilot_router
        )
        return _merge_extra_body(body, extra_body)

    def _embedding_body(
        self, params: dict[str, Any], extra_body: Mapping[str, Any] | None
    ) -> dict[str, Any]:
        body = apply_embedding_defaults(params, self.default_model, self.defaults)
        return _merge_extra_body(body, extra_body)

    # ── queue transports ───────────────────────────────────────────────────

    def _send_outcome(self, entry: QueuedEntry, options: Mapping[str, Any]) -> Any:
        target = entry["target"]
        event = entry["event"]
        # The same key on every attempt, across flushes and restarts (the event never changes).
        options = {**options, "idempotency_key": entry.get("idempotency_key") or entry["id"]}
        if "request" in target:
            return self.request_json(
                build(
                    "POST",
                    f"/v1/requests/{seg(target['request'])}/outcomes",
                    body=event,
                    options=options,
                )
            )
        data = self.request_json(
            build(
                "POST",
                f"/v1/artifacts/{seg(target['artifact'])}/outcomes",
                body={"outcomes": [event]},
                options=options,
            )
        )
        rows = data.get("data") if isinstance(data, dict) else None
        if not isinstance(rows, list) or not rows:
            raise UltraRouterError("outcomes response had no result row", code="invalid_response")
        return rows[0]  # validated by the queue before anything is removed

    def _send_reviewer_batch(
        self,
        entries: list[QueuedEntry],
        backfill: Any,
        reviewer_system: Any,
        options: Mapping[str, Any],
    ) -> dict[str, Any]:
        data = self.request_json(
            signed_events_request(
                self.api_key, [e["event"] for e in entries], backfill, reviewer_system, options
            )
        )
        return dict(data) if isinstance(data, dict) else {}

    # ── preflight / learned context / hosted prompts ──────────────────────

    def preflight(
        self,
        *,
        call_type: str,
        artifact_key: str | None = None,
        trace_id: str | None = None,
        budget: Mapping[str, Any] | None = None,
        messages: Sequence[Mapping[str, Any]] | None = None,
        no_cache: bool = False,
        max_age_s: float | None = None,
        now_ms: Callable[[], float] | None = None,
        options: RequestOptions | None = None,
    ) -> PreflightResponse:
        """Ask what the gateway would decide for a call you are about to make yourself.

        ``POST /v1/preflight`` returns the routing decision (model + health-ordered fallbacks),
        the learned context module to inject and where, the active hosted prompt, and with a
        cluster key (``artifact_key`` or ``trace_id``) the exposure grant for this call.

        Responses are cached client-side with the gateway's two lifetimes (see the preflight
        guide in the documentation); the grant is never cached.

        Args:
            call_type: The call type slug or id.
            artifact_key: Cluster key: the artifact this call contributes to (mints a grant).
            trace_id: Cluster key alternative when there is no artifact (mints a grant).
            budget: Optional hints: ``{"max_usd": ..., "max_latency_ms": ...}``.
            messages: The messages the call will send. Needed when the learned module is
                case-based (rendered for this input); without them such a module comes back as
                ``knowledge=None`` with ``knowledge_reason="case_query_missing"``. Never stored.
            no_cache: Bypass the client-side cache.
            max_age_s: Shrink the live-part freshness window (seconds).
            now_ms: Clock override returning epoch milliseconds (for tests).
            options: Per-call request options.
        """
        params = _preflight_params(call_type, artifact_key, trace_id, budget, messages)
        return parse_model(
            PreflightResponse,
            self._preflight_resolve(params, no_cache, max_age_s, now_ms or _now_ms, options),
        )

    def _preflight_resolve(
        self,
        params: dict[str, Any],
        no_cache: bool,
        max_age_s: float | None,
        now_ms: Callable[[], float],
        options: RequestOptions | None,
    ) -> dict[str, Any]:
        key = preflight_cache_key(params)
        now = now_ms()
        entry = None if no_cache else self._preflight_cache.get(key, now)
        decision = decide_preflight_cache(entry, now, preflight_has_cluster_key(params), max_age_s)
        if decision.kind == "fresh" and entry is not None:
            return with_header_grant(entry.body, None)
        revalidate = decision.kind == "revalidate"
        headers = (
            {"if-none-match": decision.if_none_match}
            if revalidate and decision.if_none_match
            else {}
        )
        response = self.request(
            build(
                "POST",
                "/v1/preflight",
                body=params,
                headers=headers,
                options=options,
                accept_not_modified=revalidate,
            )
        )
        grant = parse_grant_header(response.headers.get(PREFLIGHT_GRANT_HEADER))
        if response.status_code == 304 and entry is not None:
            return with_header_grant(entry.body, grant)
        body = response.json() if response.content else {}
        etag = response.headers.get("etag")
        if etag and not no_cache and isinstance(body, dict):
            self._preflight_cache.set(
                key, build_cache_entry(body, etag, response.headers, now_ms())
            )
        return with_header_grant(body if isinstance(body, dict) else {}, grant)

    def get_prompt(
        self,
        call_type: str,
        *,
        no_cache: bool = False,
        max_age_s: float | None = None,
        options: RequestOptions | None = None,
    ) -> PreflightPrompt | None:
        """The active hosted prompt of ``call_type``, or ``None`` when the call type is code-owned.

        Render it with :func:`ultrarouter.render_prompt`. Uses the same cached preflight read.
        """
        return self.preflight(
            call_type=call_type, no_cache=no_cache, max_age_s=max_age_s, options=options
        ).prompt

    def use_learned(
        self,
        *,
        call_type: str,
        artifact_key: str | None = None,
        trace_id: str | None = None,
        budget: Mapping[str, Any] | None = None,
        messages: Sequence[Mapping[str, Any]] | None = None,
        no_cache: bool = False,
        max_age_s: float | None = None,
        options: RequestOptions | None = None,
    ) -> LearnedSession:
        """Preflight once and return a :class:`LearnedSession` for a call you make yourself.

        ``session.apply(messages)`` inserts the learned module where the gateway would;
        ``session.record(outcome)`` records an outcome on the artifact with the grant attached.
        Pass the same ``messages`` you will send when the module may be case-based.
        """
        response = self.preflight(
            call_type=call_type,
            artifact_key=artifact_key,
            trace_id=trace_id,
            budget=budget,
            messages=messages,
            no_cache=no_cache,
            max_age_s=max_age_s,
            options=options,
        )
        return LearnedSession(self, response, artifact_key)

    # ── artifact scope ─────────────────────────────────────────────────────

    def with_artifact(self, key: str) -> ArtifactScope:
        """A context manager bound to one artifact ``key``.

        Inside it, ``scope.chat.completions.create(...)`` and ``scope.embeddings.create(...)``
        send ``ur.artifact=key``; ``scope.record(...)`` and ``scope.final(...)`` target the
        artifact (created on first use); queued outcomes are flushed on exit::

            from ultrarouter import UltraRouter

            client = UltraRouter()
            with client.with_artifact("ticket:4812:reply") as scope:
                scope.chat.completions.create(
                    model="openai/gpt-5.2-mini", messages=[{"role": "user", "content": "Hi"}]
                )
                scope.record({"channel": "behavioral", "kind": "accepted"})
        """
        return ArtifactScope(self, key)

    def episode(self, key: str | None = None) -> Episode:
        """A context manager for one multi-step task (an episode); see :class:`Episode`.

        Every ``episode.chat.completions.create(...)`` step carries the episode key
        (``X-UR-Artifact``) and a request id minted before the call;
        ``episode.report(verdict, source=...)`` reports the terminal verdict on the last step.
        Without ``key`` a unique one is minted. Concurrent tasks need distinct keys: steps with
        no key are grouped by their opening text, which identical concurrent tasks share.
        """
        return Episode(self, key)

    # ── misc ───────────────────────────────────────────────────────────────

    def record_outcome(
        self,
        target: str | Mapping[str, str],
        outcome: OutcomeParams | Mapping[str, Any],
        *,
        options: RequestOptions | None = None,
    ) -> OutcomeReceipt:
        """Alias of ``client.outcomes.record(target, outcome)``."""
        return self.outcomes.record(target, outcome, options=options)

    def as_openai(self, cls: Any | None = None) -> Any:
        """Return an ``openai.OpenAI`` client preconfigured for this gateway.

        The returned client uses ``<base_url>/v1``, this API key and any default (Bench)
        headers. Requires the ``openai`` package (the ``openai`` extra) unless ``cls`` is given.
        To know a call's request id up front, pass
        ``extra_headers=ultrarouter.correlation_headers(request_id=ultrarouter.new_request_id())``;
        afterwards :func:`ultrarouter.request_id_of` reads it from the response.
        """
        factory = cls if cls is not None else _import_openai("OpenAI")
        return factory(**self._openai_preset())

    def with_options(
        self,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        default_headers: Mapping[str, str] | None = None,
    ) -> UltraRouter:
        """Return a copy with different defaults that shares this client's connection pool.

        Everything the copy sends uses its own options, including the outcome and reviewer
        queues it flushes. The copy shares the parent's outcome store, reviewer store and
        preflight cache: an event queued by either client is visible to both, and whichever
        client delivers it uses its own headers, timeout and retries (a replay keeps the
        event's identity and idempotency key, so delivering it twice is harmless). Closing the
        copy does not close the shared pool.
        """
        clone = copy.copy(self)
        clone._owns_http = False
        if timeout is not None:
            clone.timeout = float(timeout)
        if max_retries is not None:
            clone.max_retries = int(max_retries)
        if default_headers is not None:
            clone._default_headers = {**self._default_headers, **default_headers}
        clone._outcome_queue = self._outcome_queue.with_sender(clone._send_outcome)
        clone._reviewer_queue = self._reviewer_queue.with_sender(clone._send_reviewer_batch)
        clone._init_resources()
        return clone

    def __enter__(self) -> UltraRouter:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"UltraRouter(base_url={self.base_url!r})"


class LearnedSession:
    """What :meth:`UltraRouter.use_learned` returns.

    Attributes:
        preflight: The full :class:`~ultrarouter.types.PreflightResponse`.
        grant: The exposure grant (``None`` without a cluster key).
        knowledge: The learned module and placement (``None`` for a holdout arm or when
            nothing is configured; see ``preflight.knowledge_reason``).
        model: The recommended model id, if any.
    """

    def __init__(
        self, client: UltraRouter, preflight: PreflightResponse, artifact_key: str | None
    ) -> None:
        self.preflight: PreflightResponse = preflight
        self.grant: PreflightGrant | None = preflight.grant
        self.knowledge: PreflightKnowledge | None = preflight.knowledge
        model = preflight.routing.model
        self.model: str | None = model.id if model is not None else None
        self._client = client
        self._artifact_key = artifact_key

    def apply(self, messages: Sequence[Any]) -> list[Any]:
        """Return ``messages`` with the learned module inserted after the leading system run.

        Messages are returned unchanged (as a new list) when there is no module.
        """
        content = self.knowledge.module.content if self.knowledge is not None else None
        return apply_learned_context(messages, content)

    def record(
        self,
        outcome: OutcomeParams | Mapping[str, Any],
        *,
        archetype: Archetype = "answer",
        options: RequestOptions | None = None,
    ) -> OutcomeReceipt:
        """Upsert the artifact (``artifact_key``) with the grant, then record ``outcome``."""
        artifact = self._client.artifacts.create(
            **_learned_artifact_params(self._artifact_key, archetype, self.grant)
        )
        return self._client._outcome_queue.enqueue({"artifact": artifact.id}, outcome, options)


class _ScopedCompletions:
    def __init__(self, client: UltraRouter, key: str) -> None:
        self._client = client
        self._key = key

    def create(self, **kwargs: Any) -> ChatCompletion | Stream:
        """``client.chat.completions.create`` with ``ur.artifact`` set to the scope key."""
        result: ChatCompletion | Stream = self._client.chat.completions.create(
            **_bind_artifact(kwargs, self._key)
        )
        return result


class _ScopedChat:
    def __init__(self, client: UltraRouter, key: str) -> None:
        self.completions = _ScopedCompletions(client, key)


class _ScopedEmbeddings:
    def __init__(self, client: UltraRouter, key: str) -> None:
        self._client = client
        self._key = key

    def create(self, **kwargs: Any) -> CreateEmbeddingResponse:
        """``client.embeddings.create`` with ``ur.artifact`` set to the scope key."""
        return self._client.embeddings.create(**_bind_artifact(kwargs, self._key))


class ArtifactScope:
    """The scope yielded by :meth:`UltraRouter.with_artifact` (a context manager)."""

    def __init__(self, client: UltraRouter, key: str) -> None:
        self.key = key
        """The artifact key this scope is bound to."""
        self._client = client
        self._artifact_id: str | None = None
        self.chat = _ScopedChat(client, key)
        """Chat completions bound to the artifact."""
        self.embeddings = _ScopedEmbeddings(client, key)
        """Embeddings bound to the artifact."""

    @property
    def artifact_id(self) -> str:
        """The artifact id (the artifact is created/upserted on first access)."""
        if self._artifact_id is None:
            self._artifact_id = self._client.artifacts.create(key=self.key).id
        return self._artifact_id

    def record(
        self, outcome: OutcomeParams | Mapping[str, Any], *, options: RequestOptions | None = None
    ) -> OutcomeReceipt:
        """Record an outcome on this artifact (durably queued)."""
        return self._client._outcome_queue.enqueue({"artifact": self.artifact_id}, outcome, options)

    def final(self, **params: Any) -> ArtifactFinal:
        """Record the approved final of this artifact; see ``client.artifacts.final``."""
        result: ArtifactFinal = self._client.artifacts.final(self.artifact_id, **params)
        return result

    def flush(self) -> OutcomeFlushReport:
        """Deliver queued outcomes now."""
        return self._client._outcome_queue.flush()

    def __enter__(self) -> ArtifactScope:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._client._outcome_queue.flush()


# ═══════════════════════════════════════ async ═══════════════════════════════════════


class AsyncUltraRouter(AsyncAPIClient):
    """The asynchronous ultrarouter client; every method is the ``await``-able twin of
    :class:`UltraRouter`'s. Takes the same arguments (``http_client`` is an
    ``httpx.AsyncClient``).

    Example::

        import asyncio
        from ultrarouter import AsyncUltraRouter

        async def main() -> None:
            async with AsyncUltraRouter() as client:
                reply = await client.chat.completions.create(
                    model="openai/gpt-5.2-mini",
                    messages=[{"role": "user", "content": "Say hello"}],
                )
                print(reply.choices[0].message.content)

        asyncio.run(main())
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str | None = None,
        default_model: str | None = None,
        defaults: Defaults | Mapping[str, Any] | None = None,
        autopilot: AutopilotMode | None = None,
        bench: str | BenchTag | Mapping[str, Any] | None = None,
        timeout: float = DEFAULT_TIMEOUT_S,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Mapping[str, str] | None = None,
        outcome_store: OutcomeStore | None = None,
        reviewer_store: OutcomeStore | None = None,
        preflight_cache_size: int = DEFAULT_PREFLIGHT_CACHE_SIZE,
        request_ids: RequestIdMode = "gateway",
        http_client: httpx.AsyncClient | None = None,
        _sleep: Callable[[float], Awaitable[None]] = default_async_sleep,
        _rand: Callable[[], float] = default_rand,
        _clock: Callable[[], float] = time.time,
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            default_headers=default_headers,
            autopilot=autopilot,
            bench=bench,
            http_client=http_client,
            sleep=_sleep,
            rand=_rand,
            clock=_clock,
        )
        self.default_model: str | None = default_model
        self.defaults: dict[str, Any] = dict(defaults or {})
        self.request_ids = _request_id_mode(request_ids)
        self._outcome_queue = AsyncOutcomeQueue(
            outcome_store or MemoryOutcomeStore(), self._send_outcome
        )
        self._reviewer_queue = AsyncReviewerQueue(
            reviewer_store or MemoryOutcomeStore(), self._send_reviewer_batch
        )
        self._preflight_cache = PreflightCache(preflight_cache_size)
        self._init_resources()

    def _init_resources(self) -> None:
        self.chat = AsyncChat(self)
        """OpenAI-compatible chat completions."""
        self.embeddings = AsyncEmbeddings(self)
        """OpenAI-compatible embeddings."""
        self.models = AsyncModels(self)
        """The model catalog."""
        self.key = AsyncKey(self)
        """Introspect the API key."""
        self.call_types = AsyncCallTypes(self)
        """Call types, config, evals, hosted prompts, verified memory."""
        self.requests = AsyncRequests(self)
        """Feedback on served requests."""
        self.generation = AsyncGeneration(self)
        """Post-hoc stats for a request."""
        self.autopilot = AsyncAutopilot(self)
        """The Autopilot intent and readiness report."""
        self.bench = AsyncBench(self)
        """Bench suites, runs, reports and the compare gate."""
        self.artifact_types = AsyncArtifactTypes(self)
        """Artifact types and their objectives."""
        self.artifacts = AsyncArtifacts(self)
        """Artifacts."""
        self.outcomes = AsyncOutcomes(self)
        """Outcome events (durably queued)."""
        self.imports = AsyncImports(self)
        """History imports."""
        self.improvement_reads = AsyncImprovementReads(self)
        """Per call type: can it spend less, can it get better."""
        self.flywheel = AsyncFlywheel(self)
        """Status, grants, candidates, oracles, plans and verdict sources."""
        self.reviewer = AsyncReviewer(self)
        """Signed reviewer decisions."""
        self.learning = AsyncLearning(self)
        """Per-call-type learning: status, enable/pause/resume/disable, versions, evaluations."""

    def _chat_body(
        self, params: dict[str, Any], extra_body: Mapping[str, Any] | None
    ) -> dict[str, Any]:
        body = apply_chat_defaults(
            params, self.default_model, self.defaults, self._autopilot_router
        )
        return _merge_extra_body(body, extra_body)

    def _embedding_body(
        self, params: dict[str, Any], extra_body: Mapping[str, Any] | None
    ) -> dict[str, Any]:
        body = apply_embedding_defaults(params, self.default_model, self.defaults)
        return _merge_extra_body(body, extra_body)

    async def _send_outcome(self, entry: QueuedEntry, options: Mapping[str, Any]) -> Any:
        target = entry["target"]
        event = entry["event"]
        # The same key on every attempt, across flushes and restarts (the event never changes).
        options = {**options, "idempotency_key": entry.get("idempotency_key") or entry["id"]}
        if "request" in target:
            return await self.request_json(
                build(
                    "POST",
                    f"/v1/requests/{seg(target['request'])}/outcomes",
                    body=event,
                    options=options,
                )
            )
        data = await self.request_json(
            build(
                "POST",
                f"/v1/artifacts/{seg(target['artifact'])}/outcomes",
                body={"outcomes": [event]},
                options=options,
            )
        )
        rows = data.get("data") if isinstance(data, dict) else None
        if not isinstance(rows, list) or not rows:
            raise UltraRouterError("outcomes response had no result row", code="invalid_response")
        return rows[0]  # validated by the queue before anything is removed

    async def _send_reviewer_batch(
        self,
        entries: list[QueuedEntry],
        backfill: Any,
        reviewer_system: Any,
        options: Mapping[str, Any],
    ) -> dict[str, Any]:
        data = await self.request_json(
            signed_events_request(
                self.api_key, [e["event"] for e in entries], backfill, reviewer_system, options
            )
        )
        return dict(data) if isinstance(data, dict) else {}

    async def preflight(
        self,
        *,
        call_type: str,
        artifact_key: str | None = None,
        trace_id: str | None = None,
        budget: Mapping[str, Any] | None = None,
        messages: Sequence[Mapping[str, Any]] | None = None,
        no_cache: bool = False,
        max_age_s: float | None = None,
        now_ms: Callable[[], float] | None = None,
        options: RequestOptions | None = None,
    ) -> PreflightResponse:
        """Ask what the gateway would decide; async twin of :meth:`UltraRouter.preflight`."""
        params = _preflight_params(call_type, artifact_key, trace_id, budget, messages)
        return parse_model(
            PreflightResponse,
            await self._preflight_resolve(params, no_cache, max_age_s, now_ms or _now_ms, options),
        )

    async def _preflight_resolve(
        self,
        params: dict[str, Any],
        no_cache: bool,
        max_age_s: float | None,
        now_ms: Callable[[], float],
        options: RequestOptions | None,
    ) -> dict[str, Any]:
        key = preflight_cache_key(params)
        now = now_ms()
        entry = None if no_cache else self._preflight_cache.get(key, now)
        decision = decide_preflight_cache(entry, now, preflight_has_cluster_key(params), max_age_s)
        if decision.kind == "fresh" and entry is not None:
            return with_header_grant(entry.body, None)
        revalidate = decision.kind == "revalidate"
        headers = (
            {"if-none-match": decision.if_none_match}
            if revalidate and decision.if_none_match
            else {}
        )
        response = await self.request(
            build(
                "POST",
                "/v1/preflight",
                body=params,
                headers=headers,
                options=options,
                accept_not_modified=revalidate,
            )
        )
        grant = parse_grant_header(response.headers.get(PREFLIGHT_GRANT_HEADER))
        if response.status_code == 304 and entry is not None:
            return with_header_grant(entry.body, grant)
        body = response.json() if response.content else {}
        etag = response.headers.get("etag")
        if etag and not no_cache and isinstance(body, dict):
            self._preflight_cache.set(
                key, build_cache_entry(body, etag, response.headers, now_ms())
            )
        return with_header_grant(body if isinstance(body, dict) else {}, grant)

    async def get_prompt(
        self,
        call_type: str,
        *,
        no_cache: bool = False,
        max_age_s: float | None = None,
        options: RequestOptions | None = None,
    ) -> PreflightPrompt | None:
        """The active hosted prompt; async twin of :meth:`UltraRouter.get_prompt`."""
        response = await self.preflight(
            call_type=call_type, no_cache=no_cache, max_age_s=max_age_s, options=options
        )
        return response.prompt

    async def use_learned(
        self,
        *,
        call_type: str,
        artifact_key: str | None = None,
        trace_id: str | None = None,
        budget: Mapping[str, Any] | None = None,
        messages: Sequence[Mapping[str, Any]] | None = None,
        no_cache: bool = False,
        max_age_s: float | None = None,
        options: RequestOptions | None = None,
    ) -> AsyncLearnedSession:
        """Preflight once and return an :class:`AsyncLearnedSession`."""
        response = await self.preflight(
            call_type=call_type,
            artifact_key=artifact_key,
            trace_id=trace_id,
            budget=budget,
            messages=messages,
            no_cache=no_cache,
            max_age_s=max_age_s,
            options=options,
        )
        return AsyncLearnedSession(self, response, artifact_key)

    def with_artifact(self, key: str) -> AsyncArtifactScope:
        """An async context manager bound to one artifact ``key``; see
        :meth:`UltraRouter.with_artifact`."""
        return AsyncArtifactScope(self, key)

    def episode(self, key: str | None = None) -> AsyncEpisode:
        """An async context manager for one multi-step task; see :meth:`UltraRouter.episode`."""
        return AsyncEpisode(self, key)

    async def record_outcome(
        self,
        target: str | Mapping[str, str],
        outcome: OutcomeParams | Mapping[str, Any],
        *,
        options: RequestOptions | None = None,
    ) -> OutcomeReceipt:
        """Alias of ``await client.outcomes.record(target, outcome)``."""
        return await self.outcomes.record(target, outcome, options=options)

    def as_openai(self, cls: Any | None = None) -> Any:
        """Return an ``openai.AsyncOpenAI`` client preconfigured for this gateway."""
        factory = cls if cls is not None else _import_openai("AsyncOpenAI")
        return factory(**self._openai_preset())

    def with_options(
        self,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        default_headers: Mapping[str, str] | None = None,
    ) -> AsyncUltraRouter:
        """Return a copy with different defaults sharing the connection pool.

        The same policy as :meth:`UltraRouter.with_options`: the copy delivers its queues with
        its own options and shares the parent's stores and preflight cache.
        """
        clone = copy.copy(self)
        clone._owns_http = False
        if timeout is not None:
            clone.timeout = float(timeout)
        if max_retries is not None:
            clone.max_retries = int(max_retries)
        if default_headers is not None:
            clone._default_headers = {**self._default_headers, **default_headers}
        clone._outcome_queue = self._outcome_queue.with_sender(clone._send_outcome)
        clone._reviewer_queue = self._reviewer_queue.with_sender(clone._send_reviewer_batch)
        clone._init_resources()
        return clone

    async def __aenter__(self) -> AsyncUltraRouter:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.close()

    def __repr__(self) -> str:
        return f"AsyncUltraRouter(base_url={self.base_url!r})"


class AsyncLearnedSession:
    """What :meth:`AsyncUltraRouter.use_learned` returns; see :class:`LearnedSession`."""

    def __init__(
        self, client: AsyncUltraRouter, preflight: PreflightResponse, artifact_key: str | None
    ) -> None:
        self.preflight: PreflightResponse = preflight
        self.grant: PreflightGrant | None = preflight.grant
        self.knowledge: PreflightKnowledge | None = preflight.knowledge
        model = preflight.routing.model
        self.model: str | None = model.id if model is not None else None
        self._client = client
        self._artifact_key = artifact_key

    def apply(self, messages: Sequence[Any]) -> list[Any]:
        """Insert the learned module; see :meth:`LearnedSession.apply`."""
        content = self.knowledge.module.content if self.knowledge is not None else None
        return apply_learned_context(messages, content)

    async def record(
        self,
        outcome: OutcomeParams | Mapping[str, Any],
        *,
        archetype: Archetype = "answer",
        options: RequestOptions | None = None,
    ) -> OutcomeReceipt:
        """Upsert the artifact with the grant, then record ``outcome``."""
        artifact = await self._client.artifacts.create(
            **_learned_artifact_params(self._artifact_key, archetype, self.grant)
        )
        return await self._client._outcome_queue.enqueue(
            {"artifact": artifact.id}, outcome, options
        )


class _AsyncScopedCompletions:
    def __init__(self, client: AsyncUltraRouter, key: str) -> None:
        self._client = client
        self._key = key

    async def create(self, **kwargs: Any) -> ChatCompletion | AsyncStream:
        """``client.chat.completions.create`` with ``ur.artifact`` set to the scope key."""
        result: ChatCompletion | AsyncStream = await self._client.chat.completions.create(
            **_bind_artifact(kwargs, self._key)
        )
        return result


class _AsyncScopedChat:
    def __init__(self, client: AsyncUltraRouter, key: str) -> None:
        self.completions = _AsyncScopedCompletions(client, key)


class _AsyncScopedEmbeddings:
    def __init__(self, client: AsyncUltraRouter, key: str) -> None:
        self._client = client
        self._key = key

    async def create(self, **kwargs: Any) -> CreateEmbeddingResponse:
        """``client.embeddings.create`` with ``ur.artifact`` set to the scope key."""
        return await self._client.embeddings.create(**_bind_artifact(kwargs, self._key))


class AsyncArtifactScope:
    """The scope yielded by :meth:`AsyncUltraRouter.with_artifact` (an async context manager)."""

    def __init__(self, client: AsyncUltraRouter, key: str) -> None:
        self.key = key
        """The artifact key this scope is bound to."""
        self._client = client
        self._artifact_id: str | None = None
        self.chat = _AsyncScopedChat(client, key)
        """Chat completions bound to the artifact."""
        self.embeddings = _AsyncScopedEmbeddings(client, key)
        """Embeddings bound to the artifact."""

    async def artifact_id(self) -> str:
        """The artifact id (created/upserted on first call)."""
        if self._artifact_id is None:
            self._artifact_id = (await self._client.artifacts.create(key=self.key)).id
        return self._artifact_id

    async def record(
        self, outcome: OutcomeParams | Mapping[str, Any], *, options: RequestOptions | None = None
    ) -> OutcomeReceipt:
        """Record an outcome on this artifact (durably queued)."""
        return await self._client._outcome_queue.enqueue(
            {"artifact": await self.artifact_id()}, outcome, options
        )

    async def final(self, **params: Any) -> ArtifactFinal:
        """Record the approved final of this artifact."""
        result: ArtifactFinal = await self._client.artifacts.final(
            await self.artifact_id(), **params
        )
        return result

    async def flush(self) -> OutcomeFlushReport:
        """Deliver queued outcomes now."""
        return await self._client._outcome_queue.flush()

    async def __aenter__(self) -> AsyncArtifactScope:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self._client._outcome_queue.flush()
