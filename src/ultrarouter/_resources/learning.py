"""``client.learning``: per-call-type learning status and controls.

Learning turns trustworthy outcomes into candidate versions of a call type's lessons, evaluates each
candidate against the incumbent in a prospective randomized evaluation, and promotes it only when
the evaluation (under a rule frozen before it starts) justifies it. These methods inspect and steer
that loop:

* :meth:`Learning.status`: the state, the active version and the latest candidate, the running and
  latest evaluation, evidence (recorded vs verified vs incorporated vs pending), outcome receipts
  by state, the reflection provider, the budget and the usage;
* :meth:`Learning.enable` (self-serve; needs the workspace's knowledge and corrections consent and a
  workspace-owned reflection model), ``pause``, ``resume``, ``disable`` (the kill switch),
  ``rollback``, ``promote`` and ``reject``: each returns a
  :class:`~ultrarouter.types.LearningControl` (``changed`` is ``False`` when it was already in
  effect) with the resulting status;
* :meth:`Learning.versions`, :meth:`Learning.version`, :meth:`Learning.evaluations`;
* :meth:`Learning.set_read_limit` (the learned-memory read deadline) and :meth:`Learning.cost`
  (what episode memory costs the call type);
* memory items: :meth:`Learning.memory_items` / :meth:`Learning.set_memory_items` (the switch),
  :meth:`Learning.rules`, :meth:`Learning.create_rule`, :meth:`Learning.retire_rule`,
  :meth:`Learning.restore_rule` (rules, notes and feedback comments) and
  :meth:`Learning.validate_item`;
* :meth:`Learning.conversation_memory` / :meth:`Learning.set_conversation_memory` (each end user's
  own conversations) and :meth:`Learning.set_retrieval` (how memory picks examples).

Reads need the ``config:read`` scope, controls ``config:write``. Refusals raise an actionable
:class:`~ultrarouter.LearningError` subclass whose ``reason`` names the problem, ``refusal`` the
gateway's refusal code and ``action`` what to do.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, TypeVar

import pydantic

from .._base_client import APIRequest, RequestOptions
from .._errors import APIStatusError, InvalidRequestError, learning_error
from .._types import compact
from ..types import (
    ConversationMemory,
    LearnerRecipeParams,
    LearningControl,
    LearningCost,
    LearningEvaluationList,
    LearningPromotionParams,
    LearningStatus,
    LearningToolDocumentation,
    LearningVersionDetail,
    LearningVersionList,
    MemoryItemsSetting,
    MemoryItemValidation,
    MemoryRule,
    MemoryRuleChange,
    MemoryRuleList,
    PutLearningToolDocumentationParamsTool,
    RetrievalRecipeParams,
)
from ._base import AsyncAPIResource, SyncAPIResource, build, seg

__all__ = [
    "AsyncLearning",
    "GivenBy",
    "Learning",
    "LearningObjective",
    "LessonsMode",
    "PromotionMode",
]

ModelT = TypeVar("ModelT", bound=pydantic.BaseModel)

PromotionMode = Literal["evaluate", "manual", "immediate"]
"""How a candidate becomes active: ``evaluate`` (it must win a prospective randomized evaluation
against the incumbent), ``manual`` (an owner or admin decides) or ``immediate`` (publication is
activation)."""

LearningObjective = Literal["success", "cost_noninferior"]
"""What an evaluation must show: a higher whole-task ``success`` rate, or lower cost without losing
more success than the margin (``cost_noninferior``)."""

LessonsMode = Literal["only", "with_precedents"]
"""What is served: the learned lessons ``only``, or lessons then similar verified past episodes."""

GivenBy = Literal["developer", "tenant_admin", "end_user"]
"""Who gives a memory item or a validation. ``developer`` and ``tenant_admin`` are honoured only
from an API key marked server-side; anything else is recorded as ``end_user``."""


def _base(call_type_id: str) -> str:
    return f"/v1/call-types/{seg(call_type_id)}/learning"


def _send_once(options: RequestOptions | None) -> RequestOptions:
    # Storing a rule or a note is not idempotent: never retried unless the caller asks for it.
    merged: RequestOptions = {"max_retries": 0}
    if options is not None:
        merged.update(options)
    return merged


def _enable_body(
    reflection_model: str,
    lessons_mode: str | None,
    lessons_k: int | None,
    promotion: LearningPromotionParams | Mapping[str, Any] | str | None,
    recipe: LearnerRecipeParams | Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(reflection_model, str) or not reflection_model:
        raise InvalidRequestError("reflection_model is required", status=0)
    policy = {"mode": promotion} if isinstance(promotion, str) else promotion
    return compact(
        reflection_model=reflection_model,
        lessons_mode=lessons_mode,
        lessons_k=lessons_k,
        promotion=dict(policy) if policy is not None else None,
        recipe=dict(recipe) if recipe is not None else None,
    )


class Learning(SyncAPIResource):
    """``client.learning``: inspect and control learning for one call type at a time."""

    def tool_documentation(
        self, call_type_id: str, *, options: RequestOptions | None = None
    ) -> LearningToolDocumentation:
        """Read stored tool summaries and their digest; original descriptions are not retained."""
        return self._call(
            build("GET", f"{_base(call_type_id)}/tool-documentation", options=options),
            LearningToolDocumentation,
        )

    def put_tool_documentation(
        self,
        call_type_id: str,
        *,
        tools: list[PutLearningToolDocumentationParamsTool],
        options: RequestOptions | None = None,
    ) -> LearningToolDocumentation:
        """Replace the tool schemas (at most 256, 1 MiB); an empty list clears the stored set."""
        return self._call(
            build(
                "PUT",
                f"{_base(call_type_id)}/tool-documentation",
                body={"tools": tools},
                options=options,
            ),
            LearningToolDocumentation,
        )

    def _call(self, req: APIRequest, model: type[ModelT]) -> ModelT:
        try:
            return self._client.request_model(req, model)
        except APIStatusError as error:
            mapped = learning_error(error)
            if mapped is error:
                raise
            raise mapped from error

    def status(self, call_type_id: str, *, options: RequestOptions | None = None) -> LearningStatus:
        """The learning status of a call type (``GET /v1/call-types/{id}/learning``).

        ``state`` is ``off``, ``collecting`` (enabled, waiting for evidence), ``learning`` (a
        reflection is due or an evaluation runs), ``paused``, ``disabled`` (the kill switch),
        ``unavailable`` (no workspace-owned reflection provider), ``quota_exhausted`` or
        ``budget_exhausted``, with ``reason`` explaining it: a stopped learner always says why.
        """
        return self._call(build("GET", _base(call_type_id), options=options), LearningStatus)

    def enable(
        self,
        call_type_id: str,
        *,
        reflection_model: str,
        lessons_mode: LessonsMode | None = None,
        lessons_k: int | None = None,
        promotion: LearningPromotionParams | Mapping[str, Any] | PromotionMode | None = None,
        recipe: LearnerRecipeParams | Mapping[str, Any] | None = None,
        options: RequestOptions | None = None,
    ) -> LearningControl:
        """Turn learning on for a call type, self-serve (``POST .../learning/enable``).

        Needs a ``config:write`` key (or an owner/admin session) and the workspace's full
        self-learning opt-in: knowledge and corrections consent
        (:class:`~ultrarouter.LearningConsentRequiredError` otherwise). An owner/admin session
        must grant consent separately; an API key cannot do so. The reflection
        model must resolve to a workspace-owned offer: one of the workspace's custom providers, or
        a provider it stored its own key for; there is no platform or paid fallback
        (:class:`~ultrarouter.LearningProviderUnavailableError`, ``detail`` names why).

        Args:
            call_type_id: The ct_... call type id, not its slug.
            reflection_model: The model the learner reflects with.
            lessons_mode: ``"only"`` (default) or ``"with_precedents"``.
            lessons_k: Lessons served per episode (1 to 20; default 8).
            promotion: The promotion policy changes, merged over the current policy: a mapping
                (``mode``, ``objective``, ``min_verified_per_arm``, ``max_verified_per_arm``,
                ``alpha``, ``min_effect_pp``, ``noninferiority_margin_pp``, ``candidate_share``,
                ``max_duration_hours``), or just the mode (``"evaluate"``, ``"manual"``,
                ``"immediate"``).
            recipe: The learner recipe (``validator``, ``generation``, ``observations``); an
                absent field is the legacy value.
            options: Per-call request options.
        """
        return self._call(
            build(
                "POST",
                f"{_base(call_type_id)}/enable",
                body=_enable_body(reflection_model, lessons_mode, lessons_k, promotion, recipe),
                options=options,
            ),
            LearningControl,
        )

    def pause(self, call_type_id: str, *, options: RequestOptions | None = None) -> LearningControl:
        """Stop reflecting and evaluation decisions; the active version keeps serving."""
        return self._call(
            build("POST", f"{_base(call_type_id)}/pause", options=options), LearningControl
        )

    def resume(
        self, call_type_id: str, *, options: RequestOptions | None = None
    ) -> LearningControl:
        """Resume a paused learner."""
        return self._call(
            build("POST", f"{_base(call_type_id)}/resume", options=options), LearningControl
        )

    def disable(
        self, call_type_id: str, *, options: RequestOptions | None = None
    ) -> LearningControl:
        """Stop serving learned lessons for the call type (the kill switch)."""
        return self._call(
            build("POST", f"{_base(call_type_id)}/disable", options=options), LearningControl
        )

    def versions(
        self, call_type_id: str, *, options: RequestOptions | None = None
    ) -> LearningVersionList:
        """The immutable versions, newest first, each with its state, why and since when."""
        return self._call(
            build("GET", f"{_base(call_type_id)}/versions", options=options), LearningVersionList
        )

    def version(
        self, call_type_id: str, version_id: str, *, options: RequestOptions | None = None
    ) -> LearningVersionDetail:
        """One version: its lessons, the reflection receipt (hashes and token counts only) and
        every state transition."""
        return self._call(
            build("GET", f"{_base(call_type_id)}/versions/{seg(version_id)}", options=options),
            LearningVersionDetail,
        )

    def rollback(
        self,
        call_type_id: str,
        *,
        version_id: str | None = None,
        options: RequestOptions | None = None,
    ) -> LearningControl:
        """Point the active version at an earlier immutable version: ``version_id``, or the version
        active immediately before the current one. A running evaluation stops."""
        return self._call(
            build(
                "POST",
                f"{_base(call_type_id)}/rollback",
                body=compact(version_id=version_id),
                options=options,
            ),
            LearningControl,
        )

    def promote(
        self, call_type_id: str, version_id: str, *, options: RequestOptions | None = None
    ) -> LearningControl:
        """Make a version active now (owner/admin decision); a running evaluation stops."""
        return self._call(
            build(
                "POST",
                f"{_base(call_type_id)}/versions/{seg(version_id)}/promote",
                options=options,
            ),
            LearningControl,
        )

    def reject(
        self, call_type_id: str, version_id: str, *, options: RequestOptions | None = None
    ) -> LearningControl:
        """Never activate a candidate (owner/admin decision); its running evaluation stops."""
        return self._call(
            build(
                "POST",
                f"{_base(call_type_id)}/versions/{seg(version_id)}/reject",
                options=options,
            ),
            LearningControl,
        )

    def evaluations(
        self, call_type_id: str, *, options: RequestOptions | None = None
    ) -> LearningEvaluationList:
        """Every evaluation, newest first: the frozen rule and its hash, each arm's verified / pass
        / unknown episodes, the interval on the difference, and the decision."""
        return self._call(
            build("GET", f"{_base(call_type_id)}/evaluations", options=options),
            LearningEvaluationList,
        )

    def set_read_limit(
        self,
        call_type_id: str,
        learned_read_timeout_ms: int,
        *,
        options: RequestOptions | None = None,
    ) -> LearningStatus:
        """Change only the learned-memory read deadline (``PATCH .../learning``), 25 to 2,000 ms.

        A ceiling, not a delay: a read that completes in 3 ms costs 3 ms. The default is 250 ms;
        lower it when first-token latency matters more than memory. Other settings stay in place.
        Needs an existing memory setting with learning enabled, and ``config:write``.
        """
        return self._call(
            build(
                "PATCH",
                _base(call_type_id),
                body={"learned_read_timeout_ms": learned_read_timeout_ms},
                options=options,
            ),
            LearningStatus,
        )

    def cost(
        self,
        call_type_id: str,
        *,
        window: str | None = None,
        options: RequestOptions | None = None,
    ) -> LearningCost:
        """What episode memory costs the call type over a window (``window="30d"``, 1 to 90 days).

        Integer micro-USD: the call type's spend, the estimate of the memory block's cost, and the
        observed difference in cost per request against the standing holdout (display only).
        """
        return self._call(
            build(
                "GET", f"{_base(call_type_id)}/cost", query=compact(window=window), options=options
            ),
            LearningCost,
        )

    # ── memory items, rules and notes, conversation memory, retrieval ──

    def conversation_memory(
        self, call_type_id: str, *, options: RequestOptions | None = None
    ) -> ConversationMemory:
        """Read conversation memory (``GET .../learning/conversation-memory``).

        Whether the call type remembers each end user's conversations, for that end user only; what
        switching it on does (``consequence``, and the ``consequence_sha256`` to send back); the
        retention window; the most it adds to one request; and what it holds, as counts only.
        Needs ``config:read``.
        """
        return self._call(
            build("GET", f"{_base(call_type_id)}/conversation-memory", options=options),
            ConversationMemory,
        )

    def set_conversation_memory(
        self,
        call_type_id: str,
        enabled: bool,
        *,
        k: int | None = None,
        min_similarity: float | None = None,
        user_field_identifies_person: bool | None = None,
        acknowledged_consequence_sha256: str | None = None,
        options: RequestOptions | None = None,
    ) -> ConversationMemory:
        """Switch conversation memory on or off (``PUT .../learning/conversation-memory``).

        Switching on is the workspace owner's, through a signed-in session (an API key is refused),
        and needs ``acknowledged_consequence_sha256``: the ``consequence_sha256`` that
        :meth:`conversation_memory` returns for the same ``k`` and ``user_field_identifies_person``.
        Switching off stops recording and serving on the next request and deletes nothing; a
        ``config:write`` key may do it. The same values again are a no-op (``changed`` is
        ``False``).
        """
        return self._call(
            build(
                "PUT",
                f"{_base(call_type_id)}/conversation-memory",
                body=compact(
                    enabled=enabled,
                    k=k,
                    min_similarity=min_similarity,
                    user_field_identifies_person=user_field_identifies_person,
                    acknowledged_consequence_sha256=acknowledged_consequence_sha256,
                ),
                options=options,
            ),
            ConversationMemory,
        )

    def memory_items(
        self, call_type_id: str, *, options: RequestOptions | None = None
    ) -> MemoryItemsSetting:
        """Read the memory-items switch (``GET .../learning/items``): whether the call type is
        served from memory items, since when, and the ranker's meaning floor. Needs ``config:read``.
        """
        return self._call(
            build("GET", f"{_base(call_type_id)}/items", options=options), MemoryItemsSetting
        )

    def set_memory_items(
        self,
        call_type_id: str,
        enabled: bool,
        *,
        validation_first: bool | None = None,
        dense_floor: float | None = None,
        options: RequestOptions | None = None,
    ) -> MemoryItemsSetting:
        """Serve the call type from memory items, or as before (``PUT .../learning/items``).

        Switching on records the instant: only items stored at or after it are served, and
        switching on again keeps it. ``validation_first`` makes a tenant admin's own item wait for a
        validation; ``dense_floor`` (omitted: off) is the ranker's meaning floor. A key bound to a
        tenant cannot change it. Needs ``config:write``; the same values again are a no-op.
        """
        return self._call(
            build(
                "PUT",
                f"{_base(call_type_id)}/items",
                body=compact(
                    enabled=enabled, validation_first=validation_first, dense_floor=dense_floor
                ),
                options=options,
            ),
            MemoryItemsSetting,
        )

    def validate_item(
        self,
        call_type_id: str,
        item_id: str,
        *,
        given_by: GivenBy | None = None,
        tenant: str | None = None,
        user: str | None = None,
        options: RequestOptions | None = None,
    ) -> MemoryItemValidation:
        """Vouch for a memory item (``POST .../learning/items/{item_id}/validate``).

        ``item_id`` is a rule, note or comment (``mit_…``) or a corrected request's episode
        (``ept_…``). Only a developer (an API key marked server-side claiming
        ``given_by="developer"``) or a tenant admin (a server-side key claiming
        ``given_by="tenant_admin"``) may validate; anyone else is refused ``403``. A validation
        opens an end user's item to its own tenant, never further. Needs ``config:write``.
        """
        return self._call(
            build(
                "POST",
                f"{_base(call_type_id)}/items/{seg(item_id)}/validate",
                body=compact(given_by=given_by, tenant=tenant, user=user),
                options=options,
            ),
            MemoryItemValidation,
        )

    def set_retrieval(
        self,
        call_type_id: str,
        retrieval: Literal["recommended"] | RetrievalRecipeParams | Mapping[str, Any] | None,
        *,
        lessons_selector: Literal["els1", "els2"] | None = None,
        options: RequestOptions | None = None,
    ) -> LearningStatus:
        """Set how memory picks examples (``PUT .../learning/retrieval``); nothing else changes.

        ``"recommended"`` is the measured recipe for the deployment's encoder (by meaning and by
        words); an explicit recipe must name the encoder the deployment configures
        (``memory_encoder`` in :meth:`status`); ``None`` goes back to picking by words only.
        Needs an existing memory setting, learning enabled and ``config:write``.
        """
        body: dict[str, Any] = {"retrieval": retrieval}
        if lessons_selector is not None:
            body["lessons_selector"] = lessons_selector
        return self._call(
            build("PUT", f"{_base(call_type_id)}/retrieval", body=body, options=options),
            LearningStatus,
        )

    def rules(
        self,
        call_type_id: str,
        *,
        limit: int | None = None,
        include_retired: bool | None = None,
        options: RequestOptions | None = None,
    ) -> MemoryRuleList:
        """The call type's rules and notes, newest first (``GET .../learning/rules``).

        ``limit`` is 1 to 500 (default 100); ``include_retired=True`` adds retired ones. A key bound
        to a tenant sees only the items given in, or named for, its tenant. Needs ``config:read``.
        """
        return self._call(
            build(
                "GET",
                f"{_base(call_type_id)}/rules",
                query=compact(limit=limit, include_retired=include_retired),
                options=options,
            ),
            MemoryRuleList,
        )

    def create_rule(
        self,
        call_type_id: str,
        text: str,
        *,
        sort: Literal["rule", "note"] | None = None,
        every_kind: bool | None = None,
        given_by: GivenBy | None = None,
        tenant: str | None = None,
        user: str | None = None,
        options: RequestOptions | None = None,
    ) -> MemoryRule:
        """Store a rule (a standing instruction) or a note (a standing fact), served verbatim
        (``POST .../learning/rules``).

        Who gives it decides who it reaches: a developer's (a server-side key claiming
        ``given_by="developer"``) reaches every request of the call type (or of every kind with
        ``every_kind=True``), or only the one ``tenant`` it names; a tenant admin's reaches its own
        tenant; anything else is an end user's and reaches only that end user (``user``). It is
        served only while the call type's memory-items switch is on. Needs ``config:write``.

        Storing is not idempotent (a retry after a lost response stores the item twice), so it is
        sent once: pass ``options={"max_retries": n}`` to allow retries.
        """
        return self._call(
            build(
                "POST",
                f"{_base(call_type_id)}/rules",
                body=compact(
                    text=text,
                    sort=sort,
                    every_kind=every_kind,
                    given_by=given_by,
                    tenant=tenant,
                    user=user,
                ),
                options=_send_once(options),
            ),
            MemoryRule,
        )

    def retire_rule(
        self, call_type_id: str, item_id: str, *, options: RequestOptions | None = None
    ) -> MemoryRuleChange:
        """Stop serving a rule, a note or a feedback comment (its ``memory_item_id``) from the next
        request on (``POST .../learning/rules/{item_id}/retire``). It stays stored and can be
        restored. Idempotent (``changed`` is ``False`` when already retired). Needs
        ``config:write``.
        """
        return self._call(
            build("POST", f"{_base(call_type_id)}/rules/{seg(item_id)}/retire", options=options),
            MemoryRuleChange,
        )

    def restore_rule(
        self, call_type_id: str, item_id: str, *, options: RequestOptions | None = None
    ) -> MemoryRuleChange:
        """Serve a retired item again (``POST .../learning/rules/{item_id}/restore``). Idempotent
        (``changed`` is ``False`` when not retired). Needs ``config:write``.
        """
        return self._call(
            build("POST", f"{_base(call_type_id)}/rules/{seg(item_id)}/restore", options=options),
            MemoryRuleChange,
        )


class AsyncLearning(AsyncAPIResource):
    """``client.learning`` on :class:`~ultrarouter.AsyncUltraRouter`."""

    async def tool_documentation(
        self, call_type_id: str, *, options: RequestOptions | None = None
    ) -> LearningToolDocumentation:
        """Read stored tool summaries; async twin of :meth:`Learning.tool_documentation`."""
        return await self._call(
            build("GET", f"{_base(call_type_id)}/tool-documentation", options=options),
            LearningToolDocumentation,
        )

    async def put_tool_documentation(
        self,
        call_type_id: str,
        *,
        tools: list[PutLearningToolDocumentationParamsTool],
        options: RequestOptions | None = None,
    ) -> LearningToolDocumentation:
        """Replace tool schemas; async twin of :meth:`Learning.put_tool_documentation`."""
        return await self._call(
            build(
                "PUT",
                f"{_base(call_type_id)}/tool-documentation",
                body={"tools": tools},
                options=options,
            ),
            LearningToolDocumentation,
        )

    async def _call(self, req: APIRequest, model: type[ModelT]) -> ModelT:
        try:
            return await self._client.request_model(req, model)
        except APIStatusError as error:
            mapped = learning_error(error)
            if mapped is error:
                raise
            raise mapped from error

    async def status(
        self, call_type_id: str, *, options: RequestOptions | None = None
    ) -> LearningStatus:
        """The learning status; async twin of :meth:`Learning.status`."""
        return await self._call(build("GET", _base(call_type_id), options=options), LearningStatus)

    async def enable(
        self,
        call_type_id: str,
        *,
        reflection_model: str,
        lessons_mode: LessonsMode | None = None,
        lessons_k: int | None = None,
        promotion: LearningPromotionParams | Mapping[str, Any] | PromotionMode | None = None,
        recipe: LearnerRecipeParams | Mapping[str, Any] | None = None,
        options: RequestOptions | None = None,
    ) -> LearningControl:
        """Turn learning on; async twin of :meth:`Learning.enable`."""
        return await self._call(
            build(
                "POST",
                f"{_base(call_type_id)}/enable",
                body=_enable_body(reflection_model, lessons_mode, lessons_k, promotion, recipe),
                options=options,
            ),
            LearningControl,
        )

    async def pause(
        self, call_type_id: str, *, options: RequestOptions | None = None
    ) -> LearningControl:
        """Pause; async twin of :meth:`Learning.pause`."""
        return await self._call(
            build("POST", f"{_base(call_type_id)}/pause", options=options), LearningControl
        )

    async def resume(
        self, call_type_id: str, *, options: RequestOptions | None = None
    ) -> LearningControl:
        """Resume; async twin of :meth:`Learning.resume`."""
        return await self._call(
            build("POST", f"{_base(call_type_id)}/resume", options=options), LearningControl
        )

    async def disable(
        self, call_type_id: str, *, options: RequestOptions | None = None
    ) -> LearningControl:
        """Disable; async twin of :meth:`Learning.disable`."""
        return await self._call(
            build("POST", f"{_base(call_type_id)}/disable", options=options), LearningControl
        )

    async def versions(
        self, call_type_id: str, *, options: RequestOptions | None = None
    ) -> LearningVersionList:
        """Version history; async twin of :meth:`Learning.versions`."""
        return await self._call(
            build("GET", f"{_base(call_type_id)}/versions", options=options), LearningVersionList
        )

    async def version(
        self, call_type_id: str, version_id: str, *, options: RequestOptions | None = None
    ) -> LearningVersionDetail:
        """One version; async twin of :meth:`Learning.version`."""
        return await self._call(
            build("GET", f"{_base(call_type_id)}/versions/{seg(version_id)}", options=options),
            LearningVersionDetail,
        )

    async def rollback(
        self,
        call_type_id: str,
        *,
        version_id: str | None = None,
        options: RequestOptions | None = None,
    ) -> LearningControl:
        """Roll back; async twin of :meth:`Learning.rollback`."""
        return await self._call(
            build(
                "POST",
                f"{_base(call_type_id)}/rollback",
                body=compact(version_id=version_id),
                options=options,
            ),
            LearningControl,
        )

    async def promote(
        self, call_type_id: str, version_id: str, *, options: RequestOptions | None = None
    ) -> LearningControl:
        """Promote; async twin of :meth:`Learning.promote`."""
        return await self._call(
            build(
                "POST",
                f"{_base(call_type_id)}/versions/{seg(version_id)}/promote",
                options=options,
            ),
            LearningControl,
        )

    async def reject(
        self, call_type_id: str, version_id: str, *, options: RequestOptions | None = None
    ) -> LearningControl:
        """Reject; async twin of :meth:`Learning.reject`."""
        return await self._call(
            build(
                "POST",
                f"{_base(call_type_id)}/versions/{seg(version_id)}/reject",
                options=options,
            ),
            LearningControl,
        )

    async def evaluations(
        self, call_type_id: str, *, options: RequestOptions | None = None
    ) -> LearningEvaluationList:
        """Evaluations; async twin of :meth:`Learning.evaluations`."""
        return await self._call(
            build("GET", f"{_base(call_type_id)}/evaluations", options=options),
            LearningEvaluationList,
        )

    async def set_read_limit(
        self,
        call_type_id: str,
        learned_read_timeout_ms: int,
        *,
        options: RequestOptions | None = None,
    ) -> LearningStatus:
        """The read deadline; async twin of :meth:`Learning.set_read_limit`."""
        return await self._call(
            build(
                "PATCH",
                _base(call_type_id),
                body={"learned_read_timeout_ms": learned_read_timeout_ms},
                options=options,
            ),
            LearningStatus,
        )

    async def cost(
        self,
        call_type_id: str,
        *,
        window: str | None = None,
        options: RequestOptions | None = None,
    ) -> LearningCost:
        """What episode memory costs; async twin of :meth:`Learning.cost`."""
        return await self._call(
            build(
                "GET", f"{_base(call_type_id)}/cost", query=compact(window=window), options=options
            ),
            LearningCost,
        )

    # ── memory items, rules and notes, conversation memory, retrieval ──

    async def conversation_memory(
        self, call_type_id: str, *, options: RequestOptions | None = None
    ) -> ConversationMemory:
        """Read conversation memory; async twin of :meth:`Learning.conversation_memory`."""
        return await self._call(
            build("GET", f"{_base(call_type_id)}/conversation-memory", options=options),
            ConversationMemory,
        )

    async def set_conversation_memory(
        self,
        call_type_id: str,
        enabled: bool,
        *,
        k: int | None = None,
        min_similarity: float | None = None,
        user_field_identifies_person: bool | None = None,
        acknowledged_consequence_sha256: str | None = None,
        options: RequestOptions | None = None,
    ) -> ConversationMemory:
        """Switch conversation memory; async twin of :meth:`Learning.set_conversation_memory`."""
        return await self._call(
            build(
                "PUT",
                f"{_base(call_type_id)}/conversation-memory",
                body=compact(
                    enabled=enabled,
                    k=k,
                    min_similarity=min_similarity,
                    user_field_identifies_person=user_field_identifies_person,
                    acknowledged_consequence_sha256=acknowledged_consequence_sha256,
                ),
                options=options,
            ),
            ConversationMemory,
        )

    async def memory_items(
        self, call_type_id: str, *, options: RequestOptions | None = None
    ) -> MemoryItemsSetting:
        """Read the memory-items switch; async twin of :meth:`Learning.memory_items`."""
        return await self._call(
            build("GET", f"{_base(call_type_id)}/items", options=options), MemoryItemsSetting
        )

    async def set_memory_items(
        self,
        call_type_id: str,
        enabled: bool,
        *,
        validation_first: bool | None = None,
        dense_floor: float | None = None,
        options: RequestOptions | None = None,
    ) -> MemoryItemsSetting:
        """Switch memory items; async twin of :meth:`Learning.set_memory_items`."""
        return await self._call(
            build(
                "PUT",
                f"{_base(call_type_id)}/items",
                body=compact(
                    enabled=enabled, validation_first=validation_first, dense_floor=dense_floor
                ),
                options=options,
            ),
            MemoryItemsSetting,
        )

    async def validate_item(
        self,
        call_type_id: str,
        item_id: str,
        *,
        given_by: GivenBy | None = None,
        tenant: str | None = None,
        user: str | None = None,
        options: RequestOptions | None = None,
    ) -> MemoryItemValidation:
        """Vouch for a memory item; async twin of :meth:`Learning.validate_item`."""
        return await self._call(
            build(
                "POST",
                f"{_base(call_type_id)}/items/{seg(item_id)}/validate",
                body=compact(given_by=given_by, tenant=tenant, user=user),
                options=options,
            ),
            MemoryItemValidation,
        )

    async def set_retrieval(
        self,
        call_type_id: str,
        retrieval: Literal["recommended"] | RetrievalRecipeParams | Mapping[str, Any] | None,
        *,
        lessons_selector: Literal["els1", "els2"] | None = None,
        options: RequestOptions | None = None,
    ) -> LearningStatus:
        """Set how memory picks examples; async twin of :meth:`Learning.set_retrieval`."""
        body: dict[str, Any] = {"retrieval": retrieval}
        if lessons_selector is not None:
            body["lessons_selector"] = lessons_selector
        return await self._call(
            build("PUT", f"{_base(call_type_id)}/retrieval", body=body, options=options),
            LearningStatus,
        )

    async def rules(
        self,
        call_type_id: str,
        *,
        limit: int | None = None,
        include_retired: bool | None = None,
        options: RequestOptions | None = None,
    ) -> MemoryRuleList:
        """The rules and notes; async twin of :meth:`Learning.rules`."""
        return await self._call(
            build(
                "GET",
                f"{_base(call_type_id)}/rules",
                query=compact(limit=limit, include_retired=include_retired),
                options=options,
            ),
            MemoryRuleList,
        )

    async def create_rule(
        self,
        call_type_id: str,
        text: str,
        *,
        sort: Literal["rule", "note"] | None = None,
        every_kind: bool | None = None,
        given_by: GivenBy | None = None,
        tenant: str | None = None,
        user: str | None = None,
        options: RequestOptions | None = None,
    ) -> MemoryRule:
        """Store a rule or a note; async twin of :meth:`Learning.create_rule` (sent once)."""
        return await self._call(
            build(
                "POST",
                f"{_base(call_type_id)}/rules",
                body=compact(
                    text=text,
                    sort=sort,
                    every_kind=every_kind,
                    given_by=given_by,
                    tenant=tenant,
                    user=user,
                ),
                options=_send_once(options),
            ),
            MemoryRule,
        )

    async def retire_rule(
        self, call_type_id: str, item_id: str, *, options: RequestOptions | None = None
    ) -> MemoryRuleChange:
        """Retire a rule, note or comment; async twin of :meth:`Learning.retire_rule`."""
        return await self._call(
            build("POST", f"{_base(call_type_id)}/rules/{seg(item_id)}/retire", options=options),
            MemoryRuleChange,
        )

    async def restore_rule(
        self, call_type_id: str, item_id: str, *, options: RequestOptions | None = None
    ) -> MemoryRuleChange:
        """Restore a retired item; async twin of :meth:`Learning.restore_rule`."""
        return await self._call(
            build("POST", f"{_base(call_type_id)}/rules/{seg(item_id)}/restore", options=options),
            MemoryRuleChange,
        )
