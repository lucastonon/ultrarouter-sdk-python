"""Knowledge browsing is typed, read-only, paginated and never a session-export workaround."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from ultrarouter import AsyncUltraRouter, InvalidRequestError, UltraRouter, UltraRouterError
from ultrarouter.types import CompanyKnowledgeDetail, CompanyKnowledgeList

PAGE = json.loads((Path(__file__).parent / "fixtures" / "company-knowledge.json").read_text())


def transport(status: int = 200) -> tuple[httpx.MockTransport, list[httpx.Request]]:
    """Capture transport calls and return synthetic contract-shaped knowledge."""
    calls: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        response: Any
        if status != 200:
            response = {
                "error": {
                    "code": "permission" if status == 403 else "not_found",
                    "message": "knowledge unavailable",
                    "retryable": False,
                }
            }
        elif request.url.path == "/v1/knowledge":
            response = {
                **PAGE,
                "has_more": len(calls) == 1,
                "next_cursor": "opaque+/=" if len(calls) == 1 else None,
            }
        else:
            response = {"object": "knowledge_item", "item": PAGE["data"][0]}
        return httpx.Response(status, json=response)

    return httpx.MockTransport(handle), calls


def test_filters_cursor_and_detail() -> None:
    mock, calls = transport()
    with UltraRouter(
        api_key="ur_sk_test_example",
        base_url="https://gateway.example.com",
        http_client=httpx.Client(transport=mock),
    ) as client:
        first = client.knowledge.list(
            q="capacity & pending?",
            kind="lesson",
            call_type_id="ct_example",
            version_id="epb_example",
            include_history=False,
            limit=2,
        )
        assert isinstance(first, CompanyKnowledgeList)
        assert first.data[0].current and not first.data[0].active
        assert first.data[1].content_projection == "derived_statistics"
        second = client.knowledge.list(
            q="capacity & pending?",
            kind="lesson",
            call_type_id="ct_example",
            version_id="epb_example",
            include_history=False,
            limit=2,
            cursor=first.next_cursor,
        )
        assert second.next_cursor is None
        assert dict(calls[1].url.params) == {
            "q": "capacity & pending?",
            "kind": "lesson",
            "call_type_id": "ct_example",
            "version_id": "epb_example",
            "include_history": "false",
            "limit": "2",
            "cursor": "opaque+/=",
        }
        detail = client.knowledge.get("lesson:epb_example:L1")
        assert isinstance(detail, CompanyKnowledgeDetail)
        assert detail.item.content_hash == "a" * 64
        assert calls[-1].url.raw_path == b"/v1/knowledge/lesson%3Aepb_example%3AL1"
        assert not hasattr(client.knowledge, "export")
        assert all(call.method == "GET" and not call.content for call in calls)


async def test_async_list_and_detail() -> None:
    mock, calls = transport()
    async with AsyncUltraRouter(
        api_key="ur_sk_test_example",
        base_url="https://gateway.example.com",
        http_client=httpx.AsyncClient(transport=mock),
    ) as client:
        page = await client.knowledge.list(limit=10)
        detail = await client.knowledge.get(page.data[0].id)
        assert isinstance(page, CompanyKnowledgeList)
        assert isinstance(detail, CompanyKnowledgeDetail)
        assert detail.item.id == page.data[0].id
        assert all(call.method == "GET" for call in calls)


@pytest.mark.parametrize(
    "item_id", ["export", "../export", "fact:a/b", "lesson:epb_1:L1?x=1", "fact:" + "x" * 451]
)
async def test_invalid_ids_never_reach_transport(item_id: str) -> None:
    mock, calls = transport()
    with UltraRouter(
        api_key="ur_sk_test_example",
        base_url="https://gateway.example.com",
        http_client=httpx.Client(transport=mock),
    ) as client:
        with pytest.raises(InvalidRequestError):
            client.knowledge.get(item_id)
    async with AsyncUltraRouter(
        api_key="ur_sk_test_example",
        base_url="https://gateway.example.com",
        http_client=httpx.AsyncClient(transport=mock),
    ) as client:
        with pytest.raises(InvalidRequestError):
            await client.knowledge.get(item_id)
    assert not calls


@pytest.mark.parametrize("status", [403, 404])
async def test_refusals_have_no_retry_or_alternate_route(status: int) -> None:
    mock, calls = transport(status)
    async with AsyncUltraRouter(
        api_key="ur_sk_test_example",
        base_url="https://gateway.example.com",
        http_client=httpx.AsyncClient(transport=mock),
    ) as client:
        with pytest.raises(UltraRouterError) as caught:
            await client.knowledge.get("fact:kf_missing")
        assert caught.value.status == status
    assert len(calls) == 1
    assert calls[0].url.raw_path == b"/v1/knowledge/fact%3Akf_missing"
