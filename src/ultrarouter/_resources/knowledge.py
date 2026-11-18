"""Company knowledge: browse, read and ask. Content export needs the owner/admin session.

Stored text is untrusted reference data. Current candidates need not be active; neither state
proves that a lesson improves outcomes. ``list`` and ``get`` never call a model or mutate
knowledge; ``ask`` makes one metered completion when the question matches stored knowledge.
"""

from __future__ import annotations

import re
from typing import Literal

from typing_extensions import Unpack

from .._base_client import RequestOptions
from .._errors import InvalidRequestError
from .._types import compact
from ..types import (
    CompanyKnowledgeAnswer,
    CompanyKnowledgeAskParams,
    CompanyKnowledgeDetail,
    CompanyKnowledgeList,
)
from ._base import AsyncAPIResource, SyncAPIResource, build, seg


def _item_path(item_id: str) -> str:
    if (
        len(item_id) > 450
        or re.fullmatch(r"(?:fact:[A-Za-z0-9_-]+|lesson:[A-Za-z0-9_-]+:L[0-9]+)", item_id) is None
    ):
        raise InvalidRequestError("invalid company knowledge id", status=0)
    return f"/v1/knowledge/{seg(item_id)}"


def _ask_options(options: RequestOptions | None) -> RequestOptions:
    # A knowledge ask is not idempotent: never retried unless the caller asks for it.
    merged: RequestOptions = {"max_retries": 0}
    if options is not None:
        merged.update(options)
    return merged


class Knowledge(SyncAPIResource):
    """Browse/search stored lessons and safe fact summaries with config:read or config:write,
    and ask the knowledge base a question (also gateway:invoke)."""

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

    def ask(
        self,
        *,
        options: RequestOptions | None = None,
        **params: Unpack[CompanyKnowledgeAskParams],
    ) -> CompanyKnowledgeAnswer:
        """Ask the knowledge base a ``question`` (``POST /v1/knowledge/ask``) and get an answer
        with its citations.

        Optional ``kind`` (``lesson`` or ``fact``), ``call_type_id``, ``max_items`` and ``model``
        narrow it. No match means no model call and no charge; otherwise one metered completion is
        billed under ``request_id`` (``req_int_…``), which the learning routes refuse
        (``internal_knowledge_ask``). An ask is not idempotent (a retry is a new question and a
        new charge), so it is sent once: pass ``options={"max_retries": n}`` to allow retries.
        """
        return self._client.request_model(
            build(
                "POST",
                "/v1/knowledge/ask",
                body=dict(params),
                options=_ask_options(options),
            ),
            CompanyKnowledgeAnswer,
        )


class AsyncKnowledge(AsyncAPIResource):
    """Browse/search stored lessons and safe fact summaries with config:read or config:write,
    and ask the knowledge base a question (also gateway:invoke)."""

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

    async def ask(
        self,
        *,
        options: RequestOptions | None = None,
        **params: Unpack[CompanyKnowledgeAskParams],
    ) -> CompanyKnowledgeAnswer:
        """Ask the knowledge base a question; async twin of :meth:`Knowledge.ask` (sent once)."""
        return await self._client.request_model(
            build(
                "POST",
                "/v1/knowledge/ask",
                body=dict(params),
                options=_ask_options(options),
            ),
            CompanyKnowledgeAnswer,
        )
