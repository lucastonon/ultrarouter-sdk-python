"""Episodes: one multi-step task, its steps correlated, its terminal outcome reported once.

``client.episode(key)`` is a context manager. Every chat call made through it carries the
episode key (``X-UR-Artifact``) and a request id minted before the call, so each step's id is
known even for a stream or a failed call. When the task ends, ``episode.report(...)`` reports the
terminal verdict on the last step; leaving the block flushes the outcome queue. If no verdict is
reported, nothing is sent: the episode's outcome stays unknown.

A key is minted when none is given. Pass your own stable key (``"order:A-100"``) to join steps
made from different processes; give concurrent tasks distinct keys, or tasks that open with the
same text are grouped into one episode.
"""

from __future__ import annotations

from datetime import datetime
from types import TracebackType
from typing import TYPE_CHECKING, Any

from ._base_client import RequestOptions
from ._correlation import new_episode_key, new_request_id, validate_episode_key
from ._errors import InvalidRequestError
from ._outcome_report import OutcomeReport
from ._verdicts import OutcomeSource, Verdict

if TYPE_CHECKING:
    from ._client import AsyncUltraRouter, UltraRouter
    from ._streaming import AsyncStream, Stream
    from .types import ChatCompletion

__all__ = ["AsyncEpisode", "Episode"]


def _step_kwargs(key: str, kwargs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    request_id = kwargs.pop("request_id", None) or new_request_id()
    kwargs.pop("episode_key", None)
    return request_id, {**kwargs, "request_id": request_id, "episode_key": key}


class _EpisodeCompletions:
    def __init__(self, episode: Episode) -> None:
        self._episode = episode

    def create(self, **kwargs: Any) -> ChatCompletion | Stream:
        """``client.chat.completions.create`` as one step of the episode.

        Sends the episode key and a freshly minted request id (or the ``request_id`` you pass);
        the id is appended to ``episode.request_ids`` once the call returns.
        """
        request_id, step = _step_kwargs(self._episode.key, kwargs)
        result: ChatCompletion | Stream = self._episode._client.chat.completions.create(**step)
        self._episode.request_ids.append(request_id)
        return result


class _EpisodeChat:
    def __init__(self, episode: Episode) -> None:
        self.completions = _EpisodeCompletions(episode)


class Episode:
    """One multi-step task; returned by :meth:`UltraRouter.episode` (a context manager)::

    from ultrarouter import UltraRouter

    client = UltraRouter()
    with client.episode("order:A-100") as episode:
        episode.chat.completions.create(
            model="openai/gpt-5.2-mini",
            messages=[{"role": "user", "content": "Process order A-100."}],
        )
        # ... more steps (tool calls) ...
        episode.report("pass", source="verifier")  # the terminal verdict, on the last step
    """

    def __init__(self, client: UltraRouter, key: str | None = None) -> None:
        self.key: str = validate_episode_key(key) if key is not None else new_episode_key()
        """The episode key every step carries (``X-UR-Artifact``)."""
        self.request_ids: list[str] = []
        """The request id of every step made through this episode, in order."""
        self.reports: list[OutcomeReport] = []
        """What :meth:`report` returned, in order."""
        self._client = client
        self.chat = _EpisodeChat(self)
        """Chat completions as steps of this episode."""

    @property
    def last_request_id(self) -> str | None:
        """The request id of the latest step, or ``None`` before the first."""
        return self.request_ids[-1] if self.request_ids else None

    def report(
        self,
        verdict: Verdict,
        *,
        source: OutcomeSource,
        request_id: str | None = None,
        idempotency_key: str | None = None,
        observed_at: str | datetime | None = None,
        evidence_hash: str | None = None,
        supersedes: str | None = None,
        options: RequestOptions | None = None,
    ) -> OutcomeReport:
        """Report the episode's terminal verdict (on the last step unless ``request_id`` is given).

        See :meth:`~ultrarouter._resources.ledger.Outcomes.report` for the arguments.
        """
        target = request_id or self.last_request_id
        if target is None:
            raise InvalidRequestError(
                "this episode has no step yet: make a call through episode.chat first",
                status=0,
            )
        report: OutcomeReport = self._client.outcomes.report(
            target,
            verdict,
            source=source,
            idempotency_key=idempotency_key,
            observed_at=observed_at,
            evidence_hash=evidence_hash,
            supersedes=supersedes,
            options=options,
        )
        self.reports.append(report)
        return report

    def __enter__(self) -> Episode:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self.reports:
            self._client.outcomes.flush()


class _AsyncEpisodeCompletions:
    def __init__(self, episode: AsyncEpisode) -> None:
        self._episode = episode

    async def create(self, **kwargs: Any) -> ChatCompletion | AsyncStream:
        """``client.chat.completions.create`` as one step of the episode (async)."""
        request_id, step = _step_kwargs(self._episode.key, kwargs)
        result: ChatCompletion | AsyncStream = await self._episode._client.chat.completions.create(
            **step
        )
        self._episode.request_ids.append(request_id)
        return result


class _AsyncEpisodeChat:
    def __init__(self, episode: AsyncEpisode) -> None:
        self.completions = _AsyncEpisodeCompletions(episode)


class AsyncEpisode:
    """One multi-step task on :class:`~ultrarouter.AsyncUltraRouter` (an async context manager);
    see :class:`Episode`."""

    def __init__(self, client: AsyncUltraRouter, key: str | None = None) -> None:
        self.key: str = validate_episode_key(key) if key is not None else new_episode_key()
        """The episode key every step carries (``X-UR-Artifact``)."""
        self.request_ids: list[str] = []
        """The request id of every step, in order."""
        self.reports: list[OutcomeReport] = []
        """What :meth:`report` returned, in order."""
        self._client = client
        self.chat = _AsyncEpisodeChat(self)
        """Chat completions as steps of this episode."""

    @property
    def last_request_id(self) -> str | None:
        """The request id of the latest step, or ``None`` before the first."""
        return self.request_ids[-1] if self.request_ids else None

    async def report(
        self,
        verdict: Verdict,
        *,
        source: OutcomeSource,
        request_id: str | None = None,
        idempotency_key: str | None = None,
        observed_at: str | datetime | None = None,
        evidence_hash: str | None = None,
        supersedes: str | None = None,
        options: RequestOptions | None = None,
    ) -> OutcomeReport:
        """Report the terminal verdict; async twin of :meth:`Episode.report`."""
        target = request_id or self.last_request_id
        if target is None:
            raise InvalidRequestError(
                "this episode has no step yet: make a call through episode.chat first",
                status=0,
            )
        report: OutcomeReport = await self._client.outcomes.report(
            target,
            verdict,
            source=source,
            idempotency_key=idempotency_key,
            observed_at=observed_at,
            evidence_hash=evidence_hash,
            supersedes=supersedes,
            options=options,
        )
        self.reports.append(report)
        return report

    async def __aenter__(self) -> AsyncEpisode:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self.reports:
            await self._client.outcomes.flush()
