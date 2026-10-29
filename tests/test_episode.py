"""``client.episode``: one multi-step task, every step correlated, the terminal verdict reported once."""

from __future__ import annotations

import pytest

from conftest import TEST_KEY, MockGateway
from ultrarouter import (
    EPISODE_HEADER,
    REQUEST_ID_HEADER,
    AsyncEpisode,
    AsyncUltraRouter,
    Episode,
    InvalidRequestError,
    NotReportedOutcome,
    TeachingOutcomeReport,
    UltraRouter,
)

MODEL = "openai/gpt-5.2-mini"
MESSAGES = [{"role": "user", "content": "Process order A-100."}]


def _chat_requests(gateway: MockGateway) -> list[dict]:
    return [r for r in gateway.requests if r["path"] == "/v1/chat/completions"]


def test_every_step_carries_the_key_and_its_own_minted_id(mock_gateway: MockGateway) -> None:
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        with client.episode("order:A-100") as episode:
            assert isinstance(episode, Episode) and episode.last_request_id is None
            first = episode.chat.completions.create(model=MODEL, messages=MESSAGES)
            second = episode.chat.completions.create(
                model=MODEL, messages=MESSAGES, request_id="req_c_mine"
            )
            stream = episode.chat.completions.create(model=MODEL, messages=MESSAGES, stream=True)
            with stream:
                stream.text()
            report = episode.report("pass", source="verifier")
    sent = _chat_requests(mock_gateway)
    assert {r["headers"][EPISODE_HEADER] for r in sent} == {"order:A-100"}
    ids = [r["headers"][REQUEST_ID_HEADER] for r in sent]
    assert ids[0].startswith("req_c_") and ids[1] == "req_c_mine" and ids[2].startswith("req_c_")
    assert episode.request_ids == ids
    assert first.ur.request_id == ids[0] and second.ur.request_id == "req_c_mine"
    assert stream.request_id == ids[2]
    assert isinstance(report, TeachingOutcomeReport) and report.request_id == ids[2]
    assert episode.reports == [report]
    outcome_posts = [r for r in mock_gateway.requests if r["path"].endswith("/outcomes")]
    assert [r["path"] for r in outcome_posts] == [f"/v1/requests/{ids[2]}/outcomes"]


def test_a_key_is_minted_and_an_explicit_target_is_honoured(mock_gateway: MockGateway) -> None:
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        with client.episode() as episode:
            episode.chat.completions.create(model=MODEL, messages=MESSAGES)
            report = episode.report("fail", source="human_review", request_id="req_c_other")
    assert episode.key.startswith("ep_")
    assert report.request_id == "req_c_other"


def test_no_step_no_report_and_unknown_sends_nothing(mock_gateway: MockGateway) -> None:
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        with client.episode() as episode:
            with pytest.raises(InvalidRequestError, match="no step"):
                episode.report("pass", source="verifier")
            episode.chat.completions.create(model=MODEL, messages=MESSAGES)
            silent = episode.report("unknown", source="verifier")
    assert isinstance(silent, NotReportedOutcome)
    assert not [r for r in mock_gateway.requests if r["path"].endswith("/outcomes")]


def test_invalid_keys_are_refused() -> None:
    client = UltraRouter(api_key=TEST_KEY, base_url="http://x")
    with pytest.raises(InvalidRequestError):
        client.episode(" padded ")


def test_leaving_the_episode_flushes_a_queued_report(mock_gateway: MockGateway) -> None:
    mock_gateway.fail("/v1/requests/req_c_q/outcomes", status=503, times=1)
    with UltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url, max_retries=0) as client:
        with client.episode() as episode:
            episode.chat.completions.create(model=MODEL, messages=MESSAGES)
            queued = episode.report("pass", source="verifier", request_id="req_c_q")
            assert queued.status == "queued" and client.outcomes.size() == 1
        assert client.outcomes.size() == 0


async def test_async_episode(mock_gateway: MockGateway) -> None:
    async with AsyncUltraRouter(api_key=TEST_KEY, base_url=mock_gateway.url) as client:
        async with client.episode("order:B-200") as episode:
            assert isinstance(episode, AsyncEpisode)
            await episode.chat.completions.create(model=MODEL, messages=MESSAGES)
            stream = await episode.chat.completions.create(
                model=MODEL, messages=MESSAGES, stream=True
            )
            async with stream:
                await stream.text()
            with pytest.raises(InvalidRequestError):
                await client.episode().report("pass", source="verifier")
            report = await episode.report("pass", source="webhook", idempotency_key="evt_1")
    sent = _chat_requests(mock_gateway)
    assert {r["headers"][EPISODE_HEADER] for r in sent} == {"order:B-200"}
    assert episode.request_ids == [r["headers"][REQUEST_ID_HEADER] for r in sent]
    assert report.reported and report.request_id == episode.last_request_id
