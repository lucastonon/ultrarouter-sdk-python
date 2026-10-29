"""``client.learning``: per-call-type learning status and controls.

Learning turns trustworthy outcomes into candidate adaptations of a call type, evaluates each
candidate against the incumbent, and promotes it only when the evaluation justifies it. These
methods inspect and steer that loop:

* :meth:`Learning.status` — state, provider, active version, candidate, evaluation, evidence
  arrived vs verified vs incorporated, backlog and budget;
* :meth:`Learning.enable` (self-serve, needs the workspace's corrections consent), ``pause``,
  ``resume``, ``disable``;
* :meth:`Learning.versions`, :meth:`Learning.version`, :meth:`Learning.rollback`,
  :meth:`Learning.promote`, :meth:`Learning.reject`, :meth:`Learning.evaluations`.

Reads need the ``config:read`` scope, controls ``config:write``; manual promote/reject need an
owner or admin. Refusals raise an actionable :class:`~ultrarouter.LearningError` subclass
(consent missing, provider unavailable, quota or budget exhausted, not found, forbidden) whose
``hint`` says what to do.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal, TypeVar

import pydantic

from .._base_client import APIRequest, RequestOptions, parse_model
from .._errors import APIStatusError, InvalidRequestError, learning_error
from .._types import compact
from ..types._learning import (
    LearningEvaluationList,
    LearningStatus,
    LearningVersion,
    LearningVersionList,
)
from ._base import AsyncAPIResource, SyncAPIResource, build, seg

__all__ = ["AsyncLearning", "Learning", "LearningObjective", "PromotionMode"]

ModelT = TypeVar("ModelT", bound=pydantic.BaseModel)

#: Envelope keys a learning response may be wrapped in (``{"learning": {...}}``).
_ENVELOPES = ("learning", "status", "version", "evaluation")


def _base(call_type_id: str) -> str:
    return f"/v1/call-types/{seg(call_type_id)}/learning"


def _unwrap(data: Any) -> Any:
    if isinstance(data, dict) and len(data) == 1:
        ((key, value),) = data.items()
        if key in _ENVELOPES and isinstance(value, dict):
            return value
    return data


PromotionMode = Literal["evaluate", "manual", "immediate"]
"""How a candidate becomes active: ``evaluate``, ``manual`` or ``immediate``."""

LearningObjective = Literal["success", "cost_noninferior"]
"""What an evaluation must show: better ``success``, or lower cost without losing more success than
the declared margin (``cost_noninferior``)."""


def _enable_body(
    reflection_model: str,
    promotion: PromotionMode | str | Mapping[str, Any] | None,
    objective: LearningObjective | str | None,
    recipe: str | None,
) -> dict[str, Any]:
    if not isinstance(reflection_model, str) or not reflection_model:
        raise InvalidRequestError("reflection_model is required", status=0)
    policy: Any = dict(promotion) if isinstance(promotion, Mapping) else promotion
    if objective is not None:
        policy = {**(policy if isinstance(policy, dict) else {"mode": policy or "evaluate"})}
        policy["objective"] = objective
    return compact(reflection_model=reflection_model, promotion=policy, recipe=recipe)


class Learning(SyncAPIResource):
    """``client.learning``: inspect and control learning for one call type at a time."""

    def _call(self, req: APIRequest, model: type[ModelT]) -> ModelT:
        try:
            data = self._client.request_json(req)
        except APIStatusError as error:
            mapped = learning_error(error)
            if mapped is error:
                raise
            raise mapped from error
        return parse_model(model, _unwrap(data))

    def status(self, call_type_id: str, *, options: RequestOptions | None = None) -> LearningStatus:
        """The learning status of a call type (``GET /v1/call-types/{id}/learning``).

        ``state`` is one of ``not_enabled``, ``active``, ``paused``, ``disabled``,
        ``unavailable`` (no usable provider), ``quota_exhausted`` or ``budget_exhausted``: a
        stopped learner always says why, never silently.
        """
        return self._call(build("GET", _base(call_type_id), options=options), LearningStatus)

    def enable(
        self,
        call_type_id: str,
        *,
        reflection_model: str,
        promotion: PromotionMode | Mapping[str, Any] | None = None,
        objective: LearningObjective | None = None,
        recipe: str | None = None,
        options: RequestOptions | None = None,
    ) -> LearningStatus:
        """Turn learning on for a call type (``POST .../learning/enable``), self-serve.

        Needs a ``config:write`` key (or an owner/admin session) and the workspace's corrections
        consent; raises :class:`~ultrarouter.LearningConsentRequiredError` without it and
        :class:`~ultrarouter.LearningProviderUnavailableError` when the reflection model has no
        usable workspace provider (learning never falls back to a platform or paid provider).

        Args:
            call_type_id: The call type id or slug.
            reflection_model: The model (one the workspace has configured) that writes candidate
                adaptations.
            promotion: How a candidate becomes active: ``"evaluate"`` (the gateway's default: a
                randomized evaluation against the incumbent, under a rule frozen before it
                starts), ``"manual"`` (an owner or admin decides) or ``"immediate"``
                (publication is activation); or a policy mapping ``{"mode", "objective"}``.
            objective: What an evaluation must show: ``"success"`` or ``"cost_noninferior"``.
            recipe: A named learning recipe (default: the gateway's default recipe).
            options: Per-call request options.
        """
        return self._call(
            build(
                "POST",
                f"{_base(call_type_id)}/enable",
                body=_enable_body(reflection_model, promotion, objective, recipe),
                options=options,
            ),
            LearningStatus,
        )

    def pause(self, call_type_id: str, *, options: RequestOptions | None = None) -> LearningStatus:
        """Stop reflecting and evaluating; keep serving the active version."""
        return self._call(
            build("POST", f"{_base(call_type_id)}/pause", body={}, options=options), LearningStatus
        )

    def resume(self, call_type_id: str, *, options: RequestOptions | None = None) -> LearningStatus:
        """Resume a paused (or quota- or budget-stopped) learner."""
        return self._call(
            build("POST", f"{_base(call_type_id)}/resume", body={}, options=options), LearningStatus
        )

    def disable(
        self, call_type_id: str, *, options: RequestOptions | None = None
    ) -> LearningStatus:
        """Stop learning and stop serving learned lessons for the call type (the kill switch)."""
        return self._call(
            build("POST", f"{_base(call_type_id)}/disable", body={}, options=options),
            LearningStatus,
        )

    def versions(
        self,
        call_type_id: str,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        options: RequestOptions | None = None,
    ) -> LearningVersionList:
        """Version history with each version's state (``GET .../learning/versions``)."""
        return self._call(
            build(
                "GET",
                f"{_base(call_type_id)}/versions",
                query={"limit": limit, "cursor": cursor},
                options=options,
            ),
            LearningVersionList,
        )

    def version(
        self, call_type_id: str, version_id: str, *, options: RequestOptions | None = None
    ) -> LearningVersion:
        """One version's lessons and provenance summary (``GET .../learning/versions/{id}``)."""
        return self._call(
            build("GET", f"{_base(call_type_id)}/versions/{seg(version_id)}", options=options),
            LearningVersion,
        )

    def rollback(
        self,
        call_type_id: str,
        *,
        version_id: str,
        reason: str | None = None,
        options: RequestOptions | None = None,
    ) -> LearningStatus:
        """Point the active version at an exact earlier, immutable version (``reason`` is recorded
        with the audit event)."""
        return self._call(
            build(
                "POST",
                f"{_base(call_type_id)}/rollback",
                body=compact(version_id=version_id, reason=reason),
                options=options,
            ),
            LearningStatus,
        )

    def promote(
        self,
        call_type_id: str,
        version_id: str,
        *,
        reason: str | None = None,
        options: RequestOptions | None = None,
    ) -> LearningVersion:
        """Manually promote a candidate version to active (owner or admin); ``reason`` is recorded
        with the audit event."""
        return self._call(
            build(
                "POST",
                f"{_base(call_type_id)}/versions/{seg(version_id)}/promote",
                body=compact(reason=reason),
                options=options,
            ),
            LearningVersion,
        )

    def reject(
        self,
        call_type_id: str,
        version_id: str,
        *,
        reason: str | None = None,
        options: RequestOptions | None = None,
    ) -> LearningVersion:
        """Manually reject a candidate version; the incumbent stays active (owner or admin)."""
        return self._call(
            build(
                "POST",
                f"{_base(call_type_id)}/versions/{seg(version_id)}/reject",
                body=compact(reason=reason),
                options=options,
            ),
            LearningVersion,
        )

    def evaluations(
        self,
        call_type_id: str,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        options: RequestOptions | None = None,
    ) -> LearningEvaluationList:
        """Evaluations with their frozen rule, arms, interval and decision."""
        return self._call(
            build(
                "GET",
                f"{_base(call_type_id)}/evaluations",
                query={"limit": limit, "cursor": cursor},
                options=options,
            ),
            LearningEvaluationList,
        )


class AsyncLearning(AsyncAPIResource):
    """``client.learning`` on :class:`~ultrarouter.AsyncUltraRouter`."""

    async def _call(self, req: APIRequest, model: type[ModelT]) -> ModelT:
        try:
            data = await self._client.request_json(req)
        except APIStatusError as error:
            mapped = learning_error(error)
            if mapped is error:
                raise
            raise mapped from error
        return parse_model(model, _unwrap(data))

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
        promotion: PromotionMode | Mapping[str, Any] | None = None,
        objective: LearningObjective | None = None,
        recipe: str | None = None,
        options: RequestOptions | None = None,
    ) -> LearningStatus:
        """Turn learning on; async twin of :meth:`Learning.enable`."""
        return await self._call(
            build(
                "POST",
                f"{_base(call_type_id)}/enable",
                body=_enable_body(reflection_model, promotion, objective, recipe),
                options=options,
            ),
            LearningStatus,
        )

    async def pause(
        self, call_type_id: str, *, options: RequestOptions | None = None
    ) -> LearningStatus:
        """Pause; async twin of :meth:`Learning.pause`."""
        return await self._call(
            build("POST", f"{_base(call_type_id)}/pause", body={}, options=options), LearningStatus
        )

    async def resume(
        self, call_type_id: str, *, options: RequestOptions | None = None
    ) -> LearningStatus:
        """Resume; async twin of :meth:`Learning.resume`."""
        return await self._call(
            build("POST", f"{_base(call_type_id)}/resume", body={}, options=options), LearningStatus
        )

    async def disable(
        self, call_type_id: str, *, options: RequestOptions | None = None
    ) -> LearningStatus:
        """Disable; async twin of :meth:`Learning.disable`."""
        return await self._call(
            build("POST", f"{_base(call_type_id)}/disable", body={}, options=options),
            LearningStatus,
        )

    async def versions(
        self,
        call_type_id: str,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        options: RequestOptions | None = None,
    ) -> LearningVersionList:
        """Version history; async twin of :meth:`Learning.versions`."""
        return await self._call(
            build(
                "GET",
                f"{_base(call_type_id)}/versions",
                query={"limit": limit, "cursor": cursor},
                options=options,
            ),
            LearningVersionList,
        )

    async def version(
        self, call_type_id: str, version_id: str, *, options: RequestOptions | None = None
    ) -> LearningVersion:
        """One version; async twin of :meth:`Learning.version`."""
        return await self._call(
            build("GET", f"{_base(call_type_id)}/versions/{seg(version_id)}", options=options),
            LearningVersion,
        )

    async def rollback(
        self,
        call_type_id: str,
        *,
        version_id: str,
        reason: str | None = None,
        options: RequestOptions | None = None,
    ) -> LearningStatus:
        """Roll back; async twin of :meth:`Learning.rollback`."""
        return await self._call(
            build(
                "POST",
                f"{_base(call_type_id)}/rollback",
                body=compact(version_id=version_id, reason=reason),
                options=options,
            ),
            LearningStatus,
        )

    async def promote(
        self,
        call_type_id: str,
        version_id: str,
        *,
        reason: str | None = None,
        options: RequestOptions | None = None,
    ) -> LearningVersion:
        """Promote; async twin of :meth:`Learning.promote`."""
        return await self._call(
            build(
                "POST",
                f"{_base(call_type_id)}/versions/{seg(version_id)}/promote",
                body=compact(reason=reason),
                options=options,
            ),
            LearningVersion,
        )

    async def reject(
        self,
        call_type_id: str,
        version_id: str,
        *,
        reason: str | None = None,
        options: RequestOptions | None = None,
    ) -> LearningVersion:
        """Reject; async twin of :meth:`Learning.reject`."""
        return await self._call(
            build(
                "POST",
                f"{_base(call_type_id)}/versions/{seg(version_id)}/reject",
                body=compact(reason=reason),
                options=options,
            ),
            LearningVersion,
        )

    async def evaluations(
        self,
        call_type_id: str,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        options: RequestOptions | None = None,
    ) -> LearningEvaluationList:
        """Evaluations; async twin of :meth:`Learning.evaluations`."""
        return await self._call(
            build(
                "GET",
                f"{_base(call_type_id)}/evaluations",
                query={"limit": limit, "cursor": cursor},
                options=options,
            ),
            LearningEvaluationList,
        )
