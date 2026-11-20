"""Memory items, rules and notes, conversation memory and the retrieval setting.

The methods under ``client.learning`` send the bodies and queries the spec declares, parse into their
public models, and ``create_rule`` (not idempotent) is sent once unless the caller allows retries.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from conftest import TEST_KEY, MockGateway
from ultrarouter import AsyncUltraRouter, UltraRouter, UltraRouterError
from ultrarouter.types import (
    ConversationMemory,
    LearningStatus,
    MemoryItemsSetting,
    MemoryItemValidation,
    MemoryRule,
    MemoryRuleChange,
    MemoryRuleList,
)

BASE = "/v1/call-types/support-reply/learning"


def _last(gateway: MockGateway, method: str, path: str) -> dict[str, Any]:
    rows = [r for r in gateway.requests if r["method"] == method and r["path"] == path]
    assert rows, f"no {method} {path}"
    return rows[-1]


def test_the_memory_methods_send_what_the_spec_declares(mock_gateway: MockGateway) -> None:
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        learning = client.learning
        assert isinstance(learning.conversation_memory("support-reply"), ConversationMemory)
        memory = learning.set_conversation_memory(
            "support-reply", True, k=3, acknowledged_consequence_sha256="ab" * 32
        )
        assert isinstance(memory, ConversationMemory)
        assert isinstance(learning.memory_items("support-reply"), MemoryItemsSetting)
        items = learning.set_memory_items("support-reply", True, validation_first=True)
        assert isinstance(items, MemoryItemsSetting)
        check = learning.validate_item("support-reply", "mit_1", given_by="tenant_admin", user="a")
        assert isinstance(check, MemoryItemValidation)
        assert isinstance(learning.rules("support-reply", include_retired=True), MemoryRuleList)
        rule = learning.create_rule("support-reply", "Answer in the customer's language.")
        assert isinstance(rule, MemoryRule)
        assert isinstance(learning.retire_rule("support-reply", "mit_1"), MemoryRuleChange)
        assert isinstance(learning.restore_rule("support-reply", "mit_1"), MemoryRuleChange)
        assert isinstance(learning.set_retrieval("support-reply", "recommended"), LearningStatus)

    assert _last(mock_gateway, "PUT", f"{BASE}/conversation-memory")["body"] == {
        "enabled": True,
        "k": 3,
        "acknowledged_consequence_sha256": "ab" * 32,
    }
    assert _last(mock_gateway, "PUT", f"{BASE}/items")["body"] == {
        "enabled": True,
        "validation_first": True,
    }
    assert _last(mock_gateway, "POST", f"{BASE}/items/mit_1/validate")["body"] == {
        "given_by": "tenant_admin",
        "user": "a",
    }
    assert _last(mock_gateway, "GET", f"{BASE}/rules")["query"] == {"include_retired": "true"}
    assert _last(mock_gateway, "POST", f"{BASE}/rules")["body"] == {
        "text": "Answer in the customer's language."
    }
    assert _last(mock_gateway, "POST", f"{BASE}/rules/mit_1/retire")["path"].endswith("/retire")
    assert _last(mock_gateway, "PUT", f"{BASE}/retrieval")["body"] == {"retrieval": "recommended"}


def test_set_retrieval_none_sends_an_explicit_null(mock_gateway: MockGateway) -> None:
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        client.learning.set_retrieval("support-reply", None, lessons_selector="els1")
    # `null` goes back to picking by words only; leaving the key out would be refused.
    assert _last(mock_gateway, "PUT", f"{BASE}/retrieval")["body"] == {
        "retrieval": None,
        "lessons_selector": "els1",
    }


def _rule_transport(statuses: list[int]) -> tuple[httpx.MockTransport, list[httpx.Request]]:
    calls: list[httpx.Request] = []
    rule = {
        "object": "memory_item",
        "id": "mit_01JZ0000000000000000000000",
        "call_type_id": "ct_1",
        "sort": "rule",
        "text": "Answer in the customer's language.",
        "giver_role": "developer",
        "named_tenant": False,
        "tenant_scoped": False,
        "text_sha256": "0" * 64,
        "has_vectors": False,
        "request_id": None,
        "expires_at": None,
        "retired_at": None,
        "created_at": "2026-01-15T12:00:00Z",
    }

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        status = statuses[min(len(calls) - 1, len(statuses) - 1)]
        if status != 201:
            return httpx.Response(
                status,
                headers={"retry-after": "0"},
                json={"error": {"code": "workspace_busy", "message": "busy", "retryable": True}},
            )
        return httpx.Response(201, json=rule)

    return httpx.MockTransport(handle), calls


def test_create_rule_is_sent_once_by_default() -> None:
    mock, calls = _rule_transport([503, 503, 201])
    with UltraRouter(
        api_key="ur_sk_test_example",
        base_url="https://gateway.example.com",
        http_client=httpx.Client(transport=mock),
        _sleep=lambda _: None,
    ) as client:
        # Storing is not idempotent (a retry after a lost response stores the item twice).
        with pytest.raises(UltraRouterError):
            client.learning.create_rule("ct_1", "Answer in the customer's language.", sort="rule")
        assert len(calls) == 1
        assert json.loads(calls[0].content) == {
            "text": "Answer in the customer's language.",
            "sort": "rule",
        }
        # The caller can opt into retries.
        rule = client.learning.create_rule(
            "ct_1", "Answer in the customer's language.", options={"max_retries": 1}
        )
    assert isinstance(rule, MemoryRule) and rule.sort == "rule"
    assert len(calls) == 3
    assert calls[0].url.path == "/v1/call-types/ct_1/learning/rules"


async def test_async_create_rule_is_sent_once_by_default() -> None:
    mock, calls = _rule_transport([503, 201])
    async with AsyncUltraRouter(
        api_key="ur_sk_test_example",
        base_url="https://gateway.example.com",
        http_client=httpx.AsyncClient(transport=mock),
    ) as client:
        with pytest.raises(UltraRouterError):
            await client.learning.create_rule("ct_1", "Answer in the customer's language.")
    assert len(calls) == 1


async def test_async_twins_send_the_same_requests(mock_gateway: MockGateway) -> None:
    async with AsyncUltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        learning = client.learning
        assert isinstance(await learning.conversation_memory("support-reply"), ConversationMemory)
        await learning.set_conversation_memory("support-reply", False)
        assert isinstance(await learning.memory_items("support-reply"), MemoryItemsSetting)
        await learning.set_memory_items("support-reply", False)
        await learning.validate_item("support-reply", "ept_1", given_by="developer")
        assert isinstance(await learning.rules("support-reply", limit=5), MemoryRuleList)
        await learning.retire_rule("support-reply", "mit_2")
        await learning.restore_rule("support-reply", "mit_2")
        await learning.set_retrieval("support-reply", None)
    assert _last(mock_gateway, "PUT", f"{BASE}/conversation-memory")["body"] == {"enabled": False}
    assert _last(mock_gateway, "GET", f"{BASE}/rules")["query"] == {"limit": "5"}
    assert _last(mock_gateway, "POST", f"{BASE}/rules/mit_2/restore")["method"] == "POST"
    assert _last(mock_gateway, "PUT", f"{BASE}/retrieval")["body"] == {"retrieval": None}
