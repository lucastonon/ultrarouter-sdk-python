"""Integration tests against a real ultrarouter gateway.

Skipped unless BOTH ``ULTRAROUTER_API_KEY`` and ``ULTRAROUTER_BASE_URL`` are set. Use a test key
(``ur_sk_test_...``) and a non-production gateway: these tests send real (small) model requests.

Optional:

* ``ULTRAROUTER_TEST_MODEL``: chat model (default: the first catalog model with tools support,
  else ``openai/gpt-5.2-mini``);
* ``ULTRAROUTER_TEST_EMBEDDING_MODEL``: embedding model (embedding tests skip when unset).

Run: ``uv run pytest tests/integration -m integration``.
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any

import pytest

from ultrarouter import (
    AsyncUltraRouter,
    AuthenticationError,
    NotFoundError,
    UltraRouter,
)

API_KEY = os.environ.get("ULTRAROUTER_API_KEY")
BASE_URL = os.environ.get("ULTRAROUTER_BASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not (API_KEY and BASE_URL),
        reason="set ULTRAROUTER_API_KEY and ULTRAROUTER_BASE_URL to run against a real gateway",
    ),
]

MESSAGES = [{"role": "user", "content": "Reply with the single word: ok"}]


@pytest.fixture(scope="module")
def client() -> Any:
    with UltraRouter(api_key=API_KEY, base_url=BASE_URL, timeout=120) as live:
        yield live


@pytest.fixture(scope="module")
def chat_model(client: UltraRouter) -> str:
    explicit = os.environ.get("ULTRAROUTER_TEST_MODEL")
    if explicit:
        return explicit
    catalog = client.models.list()
    return catalog.data[0].id if catalog.data else "openai/gpt-5.2-mini"


def _until(fn: Any, attempts: int = 20, delay: float = 0.5) -> Any:
    for _ in range(attempts):
        try:
            return fn()
        except NotFoundError:
            time.sleep(delay)
    return fn()


def test_key_introspection(client: UltraRouter) -> None:
    info = client.key.get()
    assert info.mode in ("live", "test")
    assert isinstance(info.scopes, list)


def test_models_catalog(client: UltraRouter) -> None:
    catalog = client.models.list()
    assert catalog.object == "list"
    if catalog.data:
        detail = client.models.retrieve(catalog.data[0].id)
        assert detail.id == catalog.data[0].id


def test_chat_completion(client: UltraRouter, chat_model: str) -> None:
    reply = client.chat.completions.create(model=chat_model, messages=MESSAGES, max_tokens=16)
    assert reply.object == "chat.completion"
    assert reply.ur.request_id.startswith("req_")
    assert isinstance(reply.ur.cost_usd, (int, float))


def test_chat_stream(client: UltraRouter, chat_model: str) -> None:
    stream = client.chat.completions.create(
        model=chat_model, messages=MESSAGES, max_tokens=16, stream=True
    )
    text = stream.text()
    assert isinstance(text, str)
    assert stream.ur is not None


def test_generation_and_feedback(client: UltraRouter, chat_model: str) -> None:
    reply = client.chat.completions.create(model=chat_model, messages=MESSAGES, max_tokens=16)
    stats = _until(lambda: client.generation.get(reply.ur.request_id))
    assert stats.id == reply.ur.request_id
    feedback = _until(
        lambda: client.requests.feedback(reply.ur.request_id, rating=1, tags=["sdk-integration"])
    )
    assert feedback.request_id == reply.ur.request_id


def test_embeddings(client: UltraRouter) -> None:
    model = os.environ.get("ULTRAROUTER_TEST_EMBEDDING_MODEL")
    if not model:
        pytest.skip("set ULTRAROUTER_TEST_EMBEDDING_MODEL to test embeddings")
    response = client.embeddings.create(model=model, input=["integration test"])
    assert len(response.data) == 1


def test_unknown_model_is_not_found(client: UltraRouter) -> None:
    with pytest.raises(NotFoundError):
        client.chat.completions.create(model="nonexistent/model-for-sdk-tests", messages=MESSAGES)


def test_bad_key_is_rejected() -> None:
    with (
        UltraRouter(api_key="ur_sk_test_not_a_real_key", base_url=BASE_URL, max_retries=0) as bad,
        pytest.raises(AuthenticationError),
    ):
        bad.models.list()


def test_async_chat(chat_model: str) -> None:
    async def run() -> str:
        async with AsyncUltraRouter(api_key=API_KEY, base_url=BASE_URL, timeout=120) as live:
            reply = await live.chat.completions.create(
                model=chat_model, messages=MESSAGES, max_tokens=16
            )
            return reply.ur.request_id

    assert asyncio.run(run()).startswith("req_")
