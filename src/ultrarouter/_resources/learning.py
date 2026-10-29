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
* :meth:`Learning.versions`, :meth:`Learning.version`, :meth:`Learning.evaluations`.

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
    LearnerRecipeParams,
    LearningControl,
    LearningEvaluationList,
    LearningPromotionParams,
    LearningStatus,
    LearningToolDocumentation,
    LearningVersionDetail,
    LearningVersionList,
    PutLearningToolDocumentationParamsTool,
)
from ._base import AsyncAPIResource, SyncAPIResource, build, seg

__all__ = ["AsyncLearning", "Learning", "LearningObjective", "LessonsMode", "PromotionMode"]

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


def _base(call_type_id: str) -> str:
    return f"/v1/call-types/{seg(call_type_id)}/learning"


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
            call_type_id: The call type id or slug.
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
