"""``client.requests``, ``client.generation`` and ``client.autopilot``."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from .._base_client import RequestOptions
from .._types import compact
from ..types import AuditReadiness, Feedback, GenerationStats
from ._base import AsyncAPIResource, SyncAPIResource, build, seg

__all__ = [
    "AsyncAutopilot",
    "AsyncGeneration",
    "AsyncRequests",
    "Autopilot",
    "Generation",
    "Requests",
]


def _feedback_body(
    rating: Literal[1, -1], tags: Sequence[str] | None, comment: str | None
) -> dict[str, object]:
    return compact(rating=rating, tags=list(tags) if tags is not None else None, comment=comment)


class Requests(SyncAPIResource):
    """``client.requests``: act on a served request by its ``req_...`` id."""

    def feedback(
        self,
        request_id: str,
        *,
        rating: Literal[1, -1],
        tags: Sequence[str] | None = None,
        comment: str | None = None,
        options: RequestOptions | None = None,
    ) -> Feedback:
        """Attach thumbs-up (``1``) or thumbs-down (``-1``) feedback to a request.

        ``POST /v1/requests/{id}/feedback``. Use the id from ``response.ur.request_id``.

        Args:
            request_id: The ``req_...`` id of the request.
            rating: ``1`` (good) or ``-1`` (bad).
            tags: Optional free-form tags.
            comment: Optional comment.
            options: Per-call request options.
        """
        return self._client.request_model(
            build(
                "POST",
                f"/v1/requests/{seg(request_id)}/feedback",
                body=_feedback_body(rating, tags, comment),
                options=options,
            ),
            Feedback,
            unwrap="feedback",
        )


class AsyncRequests(AsyncAPIResource):
    """``client.requests`` on :class:`~ultrarouter.AsyncUltraRouter`."""

    async def feedback(
        self,
        request_id: str,
        *,
        rating: Literal[1, -1],
        tags: Sequence[str] | None = None,
        comment: str | None = None,
        options: RequestOptions | None = None,
    ) -> Feedback:
        """Attach feedback to a request; async twin of :meth:`Requests.feedback`."""
        return await self._client.request_model(
            build(
                "POST",
                f"/v1/requests/{seg(request_id)}/feedback",
                body=_feedback_body(rating, tags, comment),
                options=options,
            ),
            Feedback,
            unwrap="feedback",
        )


class Generation(SyncAPIResource):
    """``client.generation``: post-hoc stats for one request."""

    def get(self, request_id: str, *, options: RequestOptions | None = None) -> GenerationStats:
        """Get tokens, cost, timing, routing decision and outcomes for a request.

        ``GET /v1/generation?id=...``. The request row is written asynchronously, so a lookup
        immediately after the call can return :class:`~ultrarouter.NotFoundError`; retry
        briefly in that case.
        """
        return self._client.request_model(
            build("GET", "/v1/generation", query={"id": request_id}, options=options),
            GenerationStats,
        )


class AsyncGeneration(AsyncAPIResource):
    """``client.generation`` on :class:`~ultrarouter.AsyncUltraRouter`."""

    async def get(
        self, request_id: str, *, options: RequestOptions | None = None
    ) -> GenerationStats:
        """Get stats for a request; async twin of :meth:`Generation.get`."""
        return await self._client.request_model(
            build("GET", "/v1/generation", query={"id": request_id}, options=options),
            GenerationStats,
        )


class Autopilot(SyncAPIResource):
    """``client.autopilot``: the configured Autopilot intent and the readiness report."""

    @property
    def mode(self) -> str | None:
        """The ``autopilot`` intent the client was created with (``None`` when unset)."""
        return self._client.autopilot_mode

    def status(self, *, options: RequestOptions | None = None) -> AuditReadiness:
        """Read the workspace readiness report (``GET /v1/audit/readiness``).

        Read-only: it observes traffic and reports per-call-type readiness; it changes nothing.
        """
        return self._client.request_model(
            build("GET", "/v1/audit/readiness", options=options), AuditReadiness
        )


class AsyncAutopilot(AsyncAPIResource):
    """``client.autopilot`` on :class:`~ultrarouter.AsyncUltraRouter`."""

    @property
    def mode(self) -> str | None:
        """The ``autopilot`` intent the client was created with (``None`` when unset)."""
        return self._client.autopilot_mode

    async def status(self, *, options: RequestOptions | None = None) -> AuditReadiness:
        """Read the readiness report; async twin of :meth:`Autopilot.status`."""
        return await self._client.request_model(
            build("GET", "/v1/audit/readiness", options=options), AuditReadiness
        )
