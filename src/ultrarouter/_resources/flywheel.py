"""``client.flywheel``: status, exposure grants, improvement candidates, checks (oracles),
learning plans and verdict sources."""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Mapping, Sequence
from typing import Any, Literal

from .._base_client import APIRequest, RequestOptions
from .._errors import InvalidRequestError
from .._jscompat import canonical_json
from .._queue import iso_from_ms
from .._signing import signature_headers
from .._types import compact
from ..types import (
    CandidateDecisionResult,
    CandidateRolloutIdentityParams,
    CandidateRolloutResult,
    ConfirmationList,
    ConfirmationStatus,
    ExposureGrant,
    FlywheelCandidateList,
    FlywheelStatus,
    FlywheelStatusLearning,
    LearningPlanEnvelope,
    LearningPlanList,
    MoatNext,
    Oracle,
    OracleExampleParams,
    OracleJobList,
    OracleProbeParams,
    OracleQualification,
    OracleRegistration,
    OracleRevocation,
    OracleTestResult,
    OracleVerdictParams,
    OracleVerdictsResult,
    PromptCandidateList,
    VerdictSourceCheck,
    VerdictSourceCheckResult,
    VerdictSourceList,
    VerdictSourceVerdictParams,
)
from ._base import AsyncAPIResource, SyncAPIResource, build, seg

__all__ = [
    "APPCI_SIGNATURE_HEADER",
    "APPCI_TIMESTAMP_HEADER",
    "ORACLE_SIGNATURE_HEADER",
    "ORACLE_TIMESTAMP_HEADER",
    "AsyncCandidates",
    "AsyncFlywheel",
    "AsyncOracles",
    "AsyncSourceChecks",
    "Candidates",
    "Flywheel",
    "Oracles",
    "SourceChecks",
    "candidate_decision_callback_id",
]

#: Header carrying the candidate-decision signature (keyed by the API key).
APPCI_SIGNATURE_HEADER = "x-ur-appci-signature"
#: Header carrying the candidate-decision signature timestamp.
APPCI_TIMESTAMP_HEADER = "x-ur-appci-timestamp"
#: Header carrying a pull-oracle signature (keyed by the oracle secret).
ORACLE_SIGNATURE_HEADER = "x-ur-oracle-signature"
#: Header carrying a pull-oracle signature timestamp.
ORACLE_TIMESTAMP_HEADER = "x-ur-oracle-timestamp"

_DECISION_SCHEMA = "ur.appci.callback.v1"
_ROLLOUT_SCHEMA = "ur.flywheel.rollout.request.v1"

Decision = Literal["accept", "reject", "revert"]
Surface = Literal["pull_request", "dashboard", "cli"]
OracleKind = Literal["label_set", "schema_rules", "test_endpoint", "reconciliation", "customer_ci"]


def candidate_decision_callback_id(
    *, workspace_id: str, candidate_ref: str, evidence_hash: str, decision: str, actor_id: str
) -> str:
    """The deterministic id of a decision, so re-sending the same decision is a no-op.

    ``"urcb1_"`` + the first 32 hex characters of the SHA-256 of the canonical JSON of the
    decision's identity fields.
    """
    subject = canonical_json(
        {
            "candidate_ref": candidate_ref,
            "decision": decision,
            "actor_id": actor_id,
            "evidence_hash": evidence_hash,
            "kind": "decision",
            "workspace_id": workspace_id,
        }
    )
    return "urcb1_" + hashlib.sha256(subject.encode("utf-8")).hexdigest()[:32]


def _signed(
    method: str,
    path: str,
    body: Mapping[str, Any],
    *,
    secret: str,
    signature_header: str,
    timestamp_header: str,
    options: RequestOptions | None,
    now_s: float | None = None,
) -> APIRequest:
    raw = json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    headers = signature_headers(signature_header, timestamp_header, secret, raw, now_s)
    return build(method, path, content=raw, headers=headers, options=options)


def _decision_body(
    ref: str,
    *,
    decision: Decision,
    actor_id: str,
    reason: str,
    evidence_hash: str,
    workspace_id: str,
    surface: Surface,
    decided_at: str | None,
    callback_id: str | None,
) -> dict[str, Any]:
    if decision not in ("accept", "reject", "revert"):
        raise InvalidRequestError(f"unknown decision {decision!r}", status=0)
    if not actor_id.strip():
        raise InvalidRequestError("a decision needs a non-empty actor_id", status=0)
    if not reason.strip():
        raise InvalidRequestError("a decision needs a non-empty reason", status=0)
    return {
        "schema": _DECISION_SCHEMA,
        "kind": "decision",
        "callback_id": callback_id
        or candidate_decision_callback_id(
            workspace_id=workspace_id,
            candidate_ref=ref,
            evidence_hash=evidence_hash,
            decision=decision,
            actor_id=actor_id,
        ),
        "workspace_id": workspace_id,
        "candidate_ref": ref,
        "evidence_hash": evidence_hash,
        "decision": decision,
        "actor_id": actor_id,
        "reason": reason,
        "surface": surface,
        "decided_at": decided_at or iso_from_ms(time.time() * 1000),
    }


def _rollout_body(
    ref: str,
    *,
    candidate_state: str,
    change_shape: str,
    observed_identity: CandidateRolloutIdentityParams | Mapping[str, Any],
    requires_repository_write: bool,
    application_headline: str | None,
) -> dict[str, Any]:
    return {
        "schema": _ROLLOUT_SCHEMA,
        "candidate_ref": ref,
        "candidate_state": candidate_state,
        "change_shape": change_shape,
        "observed_identity": dict(observed_identity),
        "requires_repository_write": requires_repository_write,
        "application_headline": application_headline,
    }


# ─────────────────────────────── sync ───────────────────────────────


class Candidates(SyncAPIResource):
    """``client.flywheel.candidates``: improvement candidates and their live confirmation."""

    def list(self, *, options: RequestOptions | None = None) -> FlywheelCandidateList:
        """List every improvement candidate, newest first, with its offline screening reading."""
        return self._client.request_model(
            build("GET", "/v1/flywheel/candidates", options=options), FlywheelCandidateList
        )

    def confirmation(
        self, ref: str, *, options: RequestOptions | None = None
    ) -> ConfirmationStatus:
        """The live confirmation state of a candidate (status, one-look result, lift, adoptable)."""
        return self._client.request_model(
            build("GET", f"/v1/flywheel/candidates/{seg(ref)}/confirmation", options=options),
            ConfirmationStatus,
        )

    def decide(
        self,
        ref: str,
        *,
        decision: Decision,
        actor_id: str,
        reason: str,
        evidence_hash: str,
        workspace_id: str,
        surface: Surface = "cli",
        decided_at: str | None = None,
        callback_id: str | None = None,
        options: RequestOptions | None = None,
    ) -> CandidateDecisionResult:
        """Record a human accept / reject / revert of a candidate (signed with your API key).

        The decision is an audit record, never a learning label. Re-sending the same decision
        returns ``status="duplicate"`` (the ``callback_id`` is deterministic).

        Args:
            ref: The candidate reference.
            decision: ``accept``, ``reject`` or ``revert``.
            actor_id: Who decided (required, non-empty).
            reason: Why (required, non-empty).
            evidence_hash: The evidence hash the decision was made on.
            workspace_id: Your workspace id.
            surface: Where the decision was made: ``cli``, ``pull_request`` or ``dashboard``.
            decided_at: ISO-8601 decision time (defaults to now).
            callback_id: Override the deterministic callback id.
            options: Per-call request options.
        """
        body = _decision_body(
            ref,
            decision=decision,
            actor_id=actor_id,
            reason=reason,
            evidence_hash=evidence_hash,
            workspace_id=workspace_id,
            surface=surface,
            decided_at=decided_at,
            callback_id=callback_id,
        )
        return self._client.request_model(
            _signed(
                "POST",
                f"/v1/flywheel/candidates/{seg(ref)}/decisions",
                body,
                secret=self._client.api_key,
                signature_header=APPCI_SIGNATURE_HEADER,
                timestamp_header=APPCI_TIMESTAMP_HEADER,
                options=options,
            ),
            CandidateDecisionResult,
        )

    def rollout(
        self,
        ref: str,
        *,
        candidate_state: str,
        change_shape: str,
        observed_identity: CandidateRolloutIdentityParams | Mapping[str, Any],
        requires_repository_write: bool,
        application_headline: str | None = None,
        options: RequestOptions | None = None,
    ) -> CandidateRolloutResult:
        """Ask whether a screened candidate's controlled rollout is unlocked.

        The server decides from permissions, consent, budget and evidence and names every
        blocker. It never starts the rollout (``pressed`` is always ``False``).
        """
        body = _rollout_body(
            ref,
            candidate_state=candidate_state,
            change_shape=change_shape,
            observed_identity=observed_identity,
            requires_repository_write=requires_repository_write,
            application_headline=application_headline,
        )
        return self._client.request_model(
            build(
                "POST", f"/v1/flywheel/candidates/{seg(ref)}/rollout", body=body, options=options
            ),
            CandidateRolloutResult,
        )


class Oracles(SyncAPIResource):
    """``client.flywheel.oracles``: register and qualify your own checks (oracles)."""

    def register(
        self,
        *,
        kind: OracleKind,
        spec: Mapping[str, Any],
        oracle_id: str | None = None,
        transport: Literal["platform", "push", "pull"] | None = None,
        options: RequestOptions | None = None,
    ) -> OracleRegistration:
        """Register a check, or append a new version of one (the same spec is a no-op).

        For a push or pull transport the response carries the signing ``secret`` exactly once;
        store it, it is needed for :meth:`claim_jobs` and :meth:`submit_verdicts`.
        """
        body = compact(kind=kind, spec=dict(spec), oracle_id=oracle_id, transport=transport)
        return self._client.request_model(
            build("POST", "/v1/flywheel/oracles", body=body, options=options), OracleRegistration
        )

    def get(self, oracle_id: str, *, options: RequestOptions | None = None) -> Oracle:
        """Read an oracle: versions, the role it earned, and its transport state."""
        return self._client.request_model(
            build("GET", f"/v1/flywheel/oracles/{seg(oracle_id)}", options=options), Oracle
        )

    def qualify(
        self,
        oracle_id: str,
        *,
        examples: Sequence[OracleExampleParams | Mapping[str, Any]],
        options: RequestOptions | None = None,
    ) -> OracleQualification:
        """Qualify the current version against failures planted into your known-good examples."""
        return self._client.request_model(
            build(
                "POST",
                f"/v1/flywheel/oracles/{seg(oracle_id)}/qualify",
                body={"examples": [dict(e) for e in examples]},
                options=options,
            ),
            OracleQualification,
        )

    def revoke(self, oracle_id: str, *, options: RequestOptions | None = None) -> OracleRevocation:
        """Revoke an oracle (terminal): its receipts stop admitting, open jobs are cancelled."""
        return self._client.request_model(
            build(
                "POST", f"/v1/flywheel/oracles/{seg(oracle_id)}/revoke", body={}, options=options
            ),
            OracleRevocation,
        )

    def test(
        self,
        oracle_id: str,
        *,
        probe: OracleProbeParams | Mapping[str, Any] | None = None,
        options: RequestOptions | None = None,
    ) -> OracleTestResult:
        """Send a test probe end to end (nothing is graded)."""
        body = compact(probe=dict(probe) if probe is not None else None)
        return self._client.request_model(
            build(
                "POST", f"/v1/flywheel/oracles/{seg(oracle_id)}/test", body=body, options=options
            ),
            OracleTestResult,
        )

    def claim_jobs(
        self,
        oracle_id: str,
        *,
        secret: str,
        max: int | None = None,
        lease_seconds: int | None = None,
        options: RequestOptions | None = None,
    ) -> OracleJobList:
        """Pull transport: lease due jobs. Each payload is returned once; signed with ``secret``.

        Args:
            oracle_id: The oracle id.
            secret: The oracle signing secret returned by :meth:`register`.
            max: At most this many jobs (1..50, default 10).
            lease_seconds: Lease length (30..3600, default 900).
            options: Per-call request options.
        """
        return self._client.request_model(
            _signed(
                "POST",
                f"/v1/flywheel/oracles/{seg(oracle_id)}/jobs/claim",
                compact(max=max, lease_seconds=lease_seconds),
                secret=secret,
                signature_header=ORACLE_SIGNATURE_HEADER,
                timestamp_header=ORACLE_TIMESTAMP_HEADER,
                options=options,
            ),
            OracleJobList,
        )

    def submit_verdicts(
        self,
        oracle_id: str,
        *,
        secret: str,
        verdicts: Sequence[OracleVerdictParams | Mapping[str, Any]],
        options: RequestOptions | None = None,
    ) -> OracleVerdictsResult:
        """Pull transport: post one verdict per claimed job (signed with ``secret``).

        Each verdict echoes the job's ``job_id``, ``oracle_version`` and ``candidate_sha256``
        and says ``pass`` or ``fail``. Re-posting the same verdict is a ``duplicate``.
        """
        return self._client.request_model(
            _signed(
                "POST",
                f"/v1/flywheel/oracles/{seg(oracle_id)}/verdicts",
                {"verdicts": [dict(v) for v in verdicts]},
                secret=secret,
                signature_header=ORACLE_SIGNATURE_HEADER,
                timestamp_header=ORACLE_TIMESTAMP_HEADER,
                options=options,
            ),
            OracleVerdictsResult,
        )


class SourceChecks(SyncAPIResource):
    """``client.flywheel.source_checks``: prove your verdict source reports known failures."""

    def issue(
        self, *, call_type_id: str, options: RequestOptions | None = None
    ) -> VerdictSourceCheck:
        """Issue a planted-failure check; answer every returned probe with :meth:`grade`."""
        return self._client.request_model(
            build(
                "POST",
                "/v1/flywheel/source-checks",
                body={"call_type_id": call_type_id},
                options=options,
            ),
            VerdictSourceCheck,
        )

    def grade(
        self,
        check_id: str,
        *,
        verdicts: Sequence[VerdictSourceVerdictParams | Mapping[str, Any]],
        options: RequestOptions | None = None,
    ) -> VerdictSourceCheckResult:
        """Answer every probe (``resolved_true`` / ``resolved_false``); graded once."""
        return self._client.request_model(
            build(
                "POST",
                f"/v1/flywheel/source-checks/{seg(check_id)}/verdicts",
                body={"verdicts": [dict(v) for v in verdicts]},
                options=options,
            ),
            VerdictSourceCheckResult,
        )


class Flywheel(SyncAPIResource):
    """``client.flywheel``: the learning loop built on your outcomes."""

    def __init__(self, client: Any) -> None:
        super().__init__(client)
        self.candidates = Candidates(client)
        """Improvement candidates."""
        self.oracles = Oracles(client)
        """Your registered checks."""
        self.source_checks = SourceChecks(client)
        """Verdict-source qualification checks."""

    def status(self, *, options: RequestOptions | None = None) -> FlywheelStatus:
        """Usage, channel health, imports and the learning block (``GET /v1/flywheel/status``)."""
        return self._client.request_model(
            build("GET", "/v1/flywheel/status", options=options), FlywheelStatus
        )

    def calibration(self, *, options: RequestOptions | None = None) -> FlywheelStatusLearning:
        """The ``learning`` block of :meth:`status` (whether calibration is available yet)."""
        return self.status(options=options).learning

    def grant(
        self,
        *,
        artifact_key: str | None = None,
        trace_id: str | None = None,
        call_type: str | None = None,
        options: RequestOptions | None = None,
    ) -> ExposureGrant:
        """Mint the exposure grant for a call you make yourself (``POST /v1/flywheel/grants``).

        Pass one cluster key: ``artifact_key`` or ``trace_id``. The same key in the same epoch
        returns the same grant. :meth:`~ultrarouter.UltraRouter.preflight` returns the grant too.
        """
        if artifact_key is None and trace_id is None:
            raise InvalidRequestError("grant() needs artifact_key= or trace_id=", status=0)
        body = compact(artifact_key=artifact_key, trace_id=trace_id, call_type=call_type)
        return self._client.request_model(
            build("POST", "/v1/flywheel/grants", body=body, options=options), ExposureGrant
        )

    def confirmations(self, *, options: RequestOptions | None = None) -> ConfirmationList:
        """List live-improvement confirmations, newest first (find what is adoptable)."""
        return self._client.request_model(
            build("GET", "/v1/flywheel/confirmations", options=options), ConfirmationList
        )

    def moat_next(
        self, *, lever_family: str | None = None, options: RequestOptions | None = None
    ) -> MoatNext:
        """Per unit (call type, lever family, situation), what is ready and what is missing next."""
        return self._client.request_model(
            build(
                "GET",
                "/v1/flywheel/moat-next",
                query={"lever_family": lever_family},
                options=options,
            ),
            MoatNext,
        )

    def plan(self, workflow: str, *, options: RequestOptions | None = None) -> LearningPlanEnvelope:
        """The learning plan for one workflow (``plan`` is ``None`` while still collecting)."""
        return self._client.request_model(
            build("GET", "/v1/flywheel/plan", query={"workflow": workflow}, options=options),
            LearningPlanEnvelope,
        )

    def plans(self, *, options: RequestOptions | None = None) -> LearningPlanList:
        """List learning-plan proposals, newest first."""
        return self._client.request_model(
            build("GET", "/v1/flywheel/plans", options=options), LearningPlanList
        )

    def prompt_candidates(self, *, options: RequestOptions | None = None) -> PromptCandidateList:
        """List hosted-prompt drafts that earned an offline screening, newest first."""
        return self._client.request_model(
            build("GET", "/v1/flywheel/prompt-candidates", options=options), PromptCandidateList
        )

    def sources(self, *, options: RequestOptions | None = None) -> VerdictSourceList:
        """Every verdict source, whether it counts toward readiness, and why not."""
        return self._client.request_model(
            build("GET", "/v1/flywheel/sources", options=options), VerdictSourceList
        )


# ─────────────────────────────── async ───────────────────────────────


class AsyncCandidates(AsyncAPIResource):
    """``client.flywheel.candidates`` on :class:`~ultrarouter.AsyncUltraRouter`."""

    async def list(self, *, options: RequestOptions | None = None) -> FlywheelCandidateList:
        """List candidates; async twin of :meth:`Candidates.list`."""
        return await self._client.request_model(
            build("GET", "/v1/flywheel/candidates", options=options), FlywheelCandidateList
        )

    async def confirmation(
        self, ref: str, *, options: RequestOptions | None = None
    ) -> ConfirmationStatus:
        """Confirmation state; async twin of :meth:`Candidates.confirmation`."""
        return await self._client.request_model(
            build("GET", f"/v1/flywheel/candidates/{seg(ref)}/confirmation", options=options),
            ConfirmationStatus,
        )

    async def decide(
        self,
        ref: str,
        *,
        decision: Decision,
        actor_id: str,
        reason: str,
        evidence_hash: str,
        workspace_id: str,
        surface: Surface = "cli",
        decided_at: str | None = None,
        callback_id: str | None = None,
        options: RequestOptions | None = None,
    ) -> CandidateDecisionResult:
        """Record a signed decision; async twin of :meth:`Candidates.decide`."""
        body = _decision_body(
            ref,
            decision=decision,
            actor_id=actor_id,
            reason=reason,
            evidence_hash=evidence_hash,
            workspace_id=workspace_id,
            surface=surface,
            decided_at=decided_at,
            callback_id=callback_id,
        )
        return await self._client.request_model(
            _signed(
                "POST",
                f"/v1/flywheel/candidates/{seg(ref)}/decisions",
                body,
                secret=self._client.api_key,
                signature_header=APPCI_SIGNATURE_HEADER,
                timestamp_header=APPCI_TIMESTAMP_HEADER,
                options=options,
            ),
            CandidateDecisionResult,
        )

    async def rollout(
        self,
        ref: str,
        *,
        candidate_state: str,
        change_shape: str,
        observed_identity: CandidateRolloutIdentityParams | Mapping[str, Any],
        requires_repository_write: bool,
        application_headline: str | None = None,
        options: RequestOptions | None = None,
    ) -> CandidateRolloutResult:
        """Evaluate rollout preconditions; async twin of :meth:`Candidates.rollout`."""
        body = _rollout_body(
            ref,
            candidate_state=candidate_state,
            change_shape=change_shape,
            observed_identity=observed_identity,
            requires_repository_write=requires_repository_write,
            application_headline=application_headline,
        )
        return await self._client.request_model(
            build(
                "POST", f"/v1/flywheel/candidates/{seg(ref)}/rollout", body=body, options=options
            ),
            CandidateRolloutResult,
        )


class AsyncOracles(AsyncAPIResource):
    """``client.flywheel.oracles`` on :class:`~ultrarouter.AsyncUltraRouter`."""

    async def register(
        self,
        *,
        kind: OracleKind,
        spec: Mapping[str, Any],
        oracle_id: str | None = None,
        transport: Literal["platform", "push", "pull"] | None = None,
        options: RequestOptions | None = None,
    ) -> OracleRegistration:
        """Register a check; async twin of :meth:`Oracles.register`."""
        body = compact(kind=kind, spec=dict(spec), oracle_id=oracle_id, transport=transport)
        return await self._client.request_model(
            build("POST", "/v1/flywheel/oracles", body=body, options=options), OracleRegistration
        )

    async def get(self, oracle_id: str, *, options: RequestOptions | None = None) -> Oracle:
        """Read an oracle; async twin of :meth:`Oracles.get`."""
        return await self._client.request_model(
            build("GET", f"/v1/flywheel/oracles/{seg(oracle_id)}", options=options), Oracle
        )

    async def qualify(
        self,
        oracle_id: str,
        *,
        examples: Sequence[OracleExampleParams | Mapping[str, Any]],
        options: RequestOptions | None = None,
    ) -> OracleQualification:
        """Qualify a check; async twin of :meth:`Oracles.qualify`."""
        return await self._client.request_model(
            build(
                "POST",
                f"/v1/flywheel/oracles/{seg(oracle_id)}/qualify",
                body={"examples": [dict(e) for e in examples]},
                options=options,
            ),
            OracleQualification,
        )

    async def revoke(
        self, oracle_id: str, *, options: RequestOptions | None = None
    ) -> OracleRevocation:
        """Revoke an oracle; async twin of :meth:`Oracles.revoke`."""
        return await self._client.request_model(
            build(
                "POST", f"/v1/flywheel/oracles/{seg(oracle_id)}/revoke", body={}, options=options
            ),
            OracleRevocation,
        )

    async def test(
        self,
        oracle_id: str,
        *,
        probe: OracleProbeParams | Mapping[str, Any] | None = None,
        options: RequestOptions | None = None,
    ) -> OracleTestResult:
        """Send a test probe; async twin of :meth:`Oracles.test`."""
        body = compact(probe=dict(probe) if probe is not None else None)
        return await self._client.request_model(
            build(
                "POST", f"/v1/flywheel/oracles/{seg(oracle_id)}/test", body=body, options=options
            ),
            OracleTestResult,
        )

    async def claim_jobs(
        self,
        oracle_id: str,
        *,
        secret: str,
        max: int | None = None,
        lease_seconds: int | None = None,
        options: RequestOptions | None = None,
    ) -> OracleJobList:
        """Lease jobs; async twin of :meth:`Oracles.claim_jobs`."""
        return await self._client.request_model(
            _signed(
                "POST",
                f"/v1/flywheel/oracles/{seg(oracle_id)}/jobs/claim",
                compact(max=max, lease_seconds=lease_seconds),
                secret=secret,
                signature_header=ORACLE_SIGNATURE_HEADER,
                timestamp_header=ORACLE_TIMESTAMP_HEADER,
                options=options,
            ),
            OracleJobList,
        )

    async def submit_verdicts(
        self,
        oracle_id: str,
        *,
        secret: str,
        verdicts: Sequence[OracleVerdictParams | Mapping[str, Any]],
        options: RequestOptions | None = None,
    ) -> OracleVerdictsResult:
        """Post verdicts; async twin of :meth:`Oracles.submit_verdicts`."""
        return await self._client.request_model(
            _signed(
                "POST",
                f"/v1/flywheel/oracles/{seg(oracle_id)}/verdicts",
                {"verdicts": [dict(v) for v in verdicts]},
                secret=secret,
                signature_header=ORACLE_SIGNATURE_HEADER,
                timestamp_header=ORACLE_TIMESTAMP_HEADER,
                options=options,
            ),
            OracleVerdictsResult,
        )


class AsyncSourceChecks(AsyncAPIResource):
    """``client.flywheel.source_checks`` on :class:`~ultrarouter.AsyncUltraRouter`."""

    async def issue(
        self, *, call_type_id: str, options: RequestOptions | None = None
    ) -> VerdictSourceCheck:
        """Issue a check; async twin of :meth:`SourceChecks.issue`."""
        return await self._client.request_model(
            build(
                "POST",
                "/v1/flywheel/source-checks",
                body={"call_type_id": call_type_id},
                options=options,
            ),
            VerdictSourceCheck,
        )

    async def grade(
        self,
        check_id: str,
        *,
        verdicts: Sequence[VerdictSourceVerdictParams | Mapping[str, Any]],
        options: RequestOptions | None = None,
    ) -> VerdictSourceCheckResult:
        """Grade a check; async twin of :meth:`SourceChecks.grade`."""
        return await self._client.request_model(
            build(
                "POST",
                f"/v1/flywheel/source-checks/{seg(check_id)}/verdicts",
                body={"verdicts": [dict(v) for v in verdicts]},
                options=options,
            ),
            VerdictSourceCheckResult,
        )


class AsyncFlywheel(AsyncAPIResource):
    """``client.flywheel`` on :class:`~ultrarouter.AsyncUltraRouter`."""

    def __init__(self, client: Any) -> None:
        super().__init__(client)
        self.candidates = AsyncCandidates(client)
        """Improvement candidates."""
        self.oracles = AsyncOracles(client)
        """Your registered checks."""
        self.source_checks = AsyncSourceChecks(client)
        """Verdict-source qualification checks."""

    async def status(self, *, options: RequestOptions | None = None) -> FlywheelStatus:
        """Flywheel status; async twin of :meth:`Flywheel.status`."""
        return await self._client.request_model(
            build("GET", "/v1/flywheel/status", options=options), FlywheelStatus
        )

    async def calibration(self, *, options: RequestOptions | None = None) -> FlywheelStatusLearning:
        """The learning block; async twin of :meth:`Flywheel.calibration`."""
        return (await self.status(options=options)).learning

    async def grant(
        self,
        *,
        artifact_key: str | None = None,
        trace_id: str | None = None,
        call_type: str | None = None,
        options: RequestOptions | None = None,
    ) -> ExposureGrant:
        """Mint an exposure grant; async twin of :meth:`Flywheel.grant`."""
        if artifact_key is None and trace_id is None:
            raise InvalidRequestError("grant() needs artifact_key= or trace_id=", status=0)
        body = compact(artifact_key=artifact_key, trace_id=trace_id, call_type=call_type)
        return await self._client.request_model(
            build("POST", "/v1/flywheel/grants", body=body, options=options), ExposureGrant
        )

    async def confirmations(self, *, options: RequestOptions | None = None) -> ConfirmationList:
        """List confirmations; async twin of :meth:`Flywheel.confirmations`."""
        return await self._client.request_model(
            build("GET", "/v1/flywheel/confirmations", options=options), ConfirmationList
        )

    async def moat_next(
        self, *, lever_family: str | None = None, options: RequestOptions | None = None
    ) -> MoatNext:
        """Readiness per unit; async twin of :meth:`Flywheel.moat_next`."""
        return await self._client.request_model(
            build(
                "GET",
                "/v1/flywheel/moat-next",
                query={"lever_family": lever_family},
                options=options,
            ),
            MoatNext,
        )

    async def plan(
        self, workflow: str, *, options: RequestOptions | None = None
    ) -> LearningPlanEnvelope:
        """A workflow's learning plan; async twin of :meth:`Flywheel.plan`."""
        return await self._client.request_model(
            build("GET", "/v1/flywheel/plan", query={"workflow": workflow}, options=options),
            LearningPlanEnvelope,
        )

    async def plans(self, *, options: RequestOptions | None = None) -> LearningPlanList:
        """List plan proposals; async twin of :meth:`Flywheel.plans`."""
        return await self._client.request_model(
            build("GET", "/v1/flywheel/plans", options=options), LearningPlanList
        )

    async def prompt_candidates(
        self, *, options: RequestOptions | None = None
    ) -> PromptCandidateList:
        """List prompt candidates; async twin of :meth:`Flywheel.prompt_candidates`."""
        return await self._client.request_model(
            build("GET", "/v1/flywheel/prompt-candidates", options=options), PromptCandidateList
        )

    async def sources(self, *, options: RequestOptions | None = None) -> VerdictSourceList:
        """List verdict sources; async twin of :meth:`Flywheel.sources`."""
        return await self._client.request_model(
            build("GET", "/v1/flywheel/sources", options=options), VerdictSourceList
        )
