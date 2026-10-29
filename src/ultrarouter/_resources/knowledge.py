"""Read-only company knowledge. Content export requires the owner/admin session workflow.

Stored text is untrusted reference data. Current candidates need not be active; neither state
proves that a lesson improves outcomes. These reads never call a model or mutate knowledge.
"""

from __future__ import annotations

import re
from typing import Literal

from .._base_client import RequestOptions
from .._errors import InvalidRequestError
from .._types import compact
from ..types import CompanyKnowledgeDetail, CompanyKnowledgeList
from ._base import AsyncAPIResource, SyncAPIResource, build, seg


def _item_path(item_id: str) -> str:
    if (
        len(item_id) > 450
        or re.fullmatch(r"(?:fact:[A-Za-z0-9_-]+|lesson:[A-Za-z0-9_-]+:L[0-9]+)", item_id) is None
    ):
        raise InvalidRequestError("invalid company knowledge id", status=0)
    return f"/v1/knowledge/{seg(item_id)}"


class Knowledge(SyncAPIResource):
    """Browse/search stored lessons and safe fact summaries with config:read or config:write."""

    def list(
        self,
        *,
        q: str | None = None,
        kind: Literal["lesson", "fact"] | None = None,
        call_type_id: str | None = None,
        version_id: str | None = None,
        include_history: bool | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        options: RequestOptions | None = None,
    ) -> CompanyKnowledgeList:
        """Read one bounded page; omit q to browse and pass next_cursor with the same filters.

        Current items can include candidates; active is separate. Raw source transcripts are
        excluded. The gateway applies consent and workspace permissions to every request.
        """
        return self._client.request_model(
            build(
                "GET",
                "/v1/knowledge",
                query=compact(
                    q=q,
                    kind=kind,
                    call_type_id=call_type_id,
                    version_id=version_id,
                    include_history=include_history,
                    limit=limit,
                    cursor=cursor,
                ),
                options=options,
            ),
            CompanyKnowledgeList,
        )

    def get(self, item_id: str, *, options: RequestOptions | None = None) -> CompanyKnowledgeDetail:
        """Read a namespaced id from list(); reserved export and malformed ids are refused."""
        return self._client.request_model(
            build("GET", _item_path(item_id), options=options), CompanyKnowledgeDetail
        )


class AsyncKnowledge(AsyncAPIResource):
    """Browse/search stored lessons and safe fact summaries with config:read or config:write."""

    async def list(
        self,
        *,
        q: str | None = None,
        kind: Literal["lesson", "fact"] | None = None,
        call_type_id: str | None = None,
        version_id: str | None = None,
        include_history: bool | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        options: RequestOptions | None = None,
    ) -> CompanyKnowledgeList:
        """Read one bounded page; omit q to browse and pass next_cursor with the same filters.

        Current items can include candidates; active is separate. Raw source transcripts are
        excluded. The gateway applies consent and workspace permissions to every request.
        """
        return await self._client.request_model(
            build(
                "GET",
                "/v1/knowledge",
                query=compact(
                    q=q,
                    kind=kind,
                    call_type_id=call_type_id,
                    version_id=version_id,
                    include_history=include_history,
                    limit=limit,
                    cursor=cursor,
                ),
                options=options,
            ),
            CompanyKnowledgeList,
        )

    async def get(
        self, item_id: str, *, options: RequestOptions | None = None
    ) -> CompanyKnowledgeDetail:
        """Read a namespaced id from list(); reserved export and malformed ids are refused."""
        return await self._client.request_model(
            build("GET", _item_path(item_id), options=options), CompanyKnowledgeDetail
        )
