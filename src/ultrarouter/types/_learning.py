"""Learning-loop response models: outcome receipts and per-call-type learning (hand-written).

These endpoints are newer than the synced API specification, so their models are written by hand
here, isolated from the generated ones, and are **provisional**: when the specification gains
them, the generated models replace these (same names where possible). Every field the SDK does
not rely on is optional and unknown fields are kept (``model.model_extra``), so a gateway that
returns more, or slightly different, data never breaks parsing.

Endpoints:

* ``GET /v1/outcome-receipts/{id}`` and ``GET /v1/requests/{id}/outcome-receipts``:
  :class:`OutcomeReceiptRecord`, :class:`OutcomeReceiptRecordList`;
* ``GET /v1/call-types/{id}/learning`` and the control routes: :class:`LearningStatus`;
* ``GET /v1/call-types/{id}/learning/versions[/{version_id}]``: :class:`LearningVersion`,
  :class:`LearningVersionList`;
* ``GET /v1/call-types/{id}/learning/evaluations``: :class:`LearningEvaluation`,
  :class:`LearningEvaluationList`.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from .._models import BaseModel

__all__ = [
    "RECEIPT_TERMINAL_STATUSES",
    "LearningArmEvidence",
    "LearningBudget",
    "LearningEvaluation",
    "LearningEvaluationInterval",
    "LearningEvaluationList",
    "LearningEvidenceCounts",
    "LearningLesson",
    "LearningPromotionPolicy",
    "LearningProvenance",
    "LearningProvider",
    "LearningStatus",
    "LearningVersion",
    "LearningVersionList",
    "LearningVersionRef",
    "OutcomeReceiptRecord",
    "OutcomeReceiptRecordList",
]

#: Receipt statuses that never change again.
RECEIPT_TERMINAL_STATUSES: tuple[str, ...] = ("applied", "rejected", "failed", "expired")


class OutcomeReceiptRecord(BaseModel):
    """The durable receipt of one reported outcome (``GET /v1/outcome-receipts/{id}``).

    A report made before the gateway has persisted the request is accepted at once as
    ``pending`` and applied when the request lands; ``status`` then moves to ``applied`` (or
    ``rejected`` / ``failed`` / ``expired`` with a ``reason``).
    """

    id: str
    """The receipt id."""

    object: str | None = None
    """Known values: ``outcome_receipt``."""

    status: str
    """Known values: ``pending``, ``applied``, ``rejected``, ``failed``, ``expired``."""

    reason: str | None = None
    """Why the receipt was rejected, failed or expired (for example ``request_not_found``)."""

    episode: str | None = None
    """Episode association. Known values: ``associated``, ``pending``, ``not_recorded``,
    ``not_applicable``."""

    request_id: str | None = None
    """The request the outcome was reported on."""

    channel: str | None = None
    """The outcome channel."""

    kind: str | None = None
    """The channel kind."""

    source_event_id: str | None = None
    """The idempotency discriminator the report carried."""

    outcome_event_id: str | None = None
    """The recorded outcome event, once applied."""

    created_at: str | None = None
    """When the report was received (ISO-8601)."""

    updated_at: str | None = None
    """When the receipt last changed (ISO-8601)."""

    applied_at: str | None = None
    """When the outcome was applied (ISO-8601)."""

    expires_at: str | None = None
    """When a still-pending receipt expires (ISO-8601)."""

    @property
    def is_terminal(self) -> bool:
        """Whether the status is final (``applied``, ``rejected``, ``failed`` or ``expired``)."""
        return self.status in RECEIPT_TERMINAL_STATUSES


class OutcomeReceiptRecordList(BaseModel):
    """Every receipt for one request (``GET /v1/requests/{id}/outcome-receipts``)."""

    object: str | None = None
    """Known values: ``list``."""

    data: list[OutcomeReceiptRecord] = Field(default_factory=list)
    """The receipts, oldest first."""


class LearningProvider(BaseModel):
    """The workspace provider that runs reflection and evaluation for a call type."""

    model: str | None = None
    """The reflection model id."""

    state: str | None = None
    """Whether it is usable. Known values: ``ready``, ``unavailable``, ``quota_exhausted``."""


class LearningPromotionPolicy(BaseModel):
    """How a candidate becomes active."""

    mode: str | None = None
    """Known values: ``evaluate`` (a randomized evaluation against the incumbent, under a rule
    frozen before it starts), ``manual`` (an owner or admin decides), ``immediate`` (publication
    is activation)."""

    objective: str | None = None
    """What an evaluation must show. Known values: ``success``, ``cost_noninferior``."""


class LearningVersionRef(BaseModel):
    """A short reference to a learned version inside a status."""

    id: str
    """The version id."""

    state: str | None = None
    """The version state (see :class:`LearningVersion`)."""

    created_at: str | None = None
    """When the version was created (ISO-8601)."""


class LearningEvidenceCounts(BaseModel):
    """Outcome evidence that arrived, was verified, was incorporated, and is still pending."""

    arrived: int | None = None
    """Outcomes that arrived."""

    verified: int | None = None
    """Outcomes verified against an episode."""

    incorporated: int | None = None
    """Verified outcomes already used to learn."""

    pending: int | None = None
    """Outcomes still waiting (for example on a pending receipt)."""


class LearningBudget(BaseModel):
    """The learning budget: its state and what is left."""

    state: str | None = None
    """Known values: ``ok``, ``exhausted``."""

    remaining_usd: float | None = None
    """What is left, in USD."""


class LearningArmEvidence(BaseModel):
    """One arm's evidence in an evaluation."""

    version_id: str | None = None
    """The version the arm served."""

    verified: int | None = None
    """Episodes with a verified verdict."""

    passed: int | None = None
    """Verified episodes that passed."""

    unknown: int | None = None
    """Episodes whose verdict stayed unknown."""


class LearningEvaluationInterval(BaseModel):
    """The one-sided interval on (candidate − incumbent) success, in percentage points."""

    lower: float | None = None
    """Lower bound."""

    upper: float | None = None
    """Upper bound."""


class LearningEvaluation(BaseModel):
    """A prospective evaluation of a candidate against the incumbent."""

    id: str
    """The evaluation id."""

    decision: str | None = None
    """``running`` until it decides. Known values: ``running``, ``promoted``, ``retained``,
    ``inconclusive``, ``rejected``, ``stopped_budget``, ``stopped_manual``."""

    reason: str | None = None
    """Why it decided, when it has."""

    objective: str | None = None
    """The objective, frozen when the evaluation started."""

    rule: dict[str, Any] | None = None
    """The decision rule, frozen when the evaluation started (minimum and maximum verified
    episodes per arm, interval, minimum effect)."""

    candidate: LearningArmEvidence | None = None
    """The candidate arm."""

    incumbent: LearningArmEvidence | None = None
    """The incumbent arm."""

    interval: LearningEvaluationInterval | None = None
    """The interval the rule reads."""

    started_at: str | None = None
    """When it started (ISO-8601)."""

    decided_at: str | None = None
    """When it decided (ISO-8601), else ``None``."""


class LearningStatus(BaseModel):
    """The learning state of one call type (``GET /v1/call-types/{id}/learning``).

    The control routes (enable, pause, resume, disable, rollback) answer with this too.
    """

    call_type_id: str | None = None
    """The call type id."""

    state: str | None = None
    """Known values: ``not_enabled``, ``active``, ``paused``, ``disabled``, ``unavailable`` (no
    usable learning provider), ``quota_exhausted``, ``budget_exhausted``. A stopped learner always
    says why, never silently."""

    reason: str | None = None
    """A stable machine reason for the state, when there is one (for example
    ``provider_missing``)."""

    provider: LearningProvider | None = None
    """The learning provider: the reflection model and whether it is usable."""

    promotion: LearningPromotionPolicy | None = None
    """The promotion policy."""

    active: LearningVersionRef | None = None
    """The version serving now (the incumbent)."""

    candidate: LearningVersionRef | None = None
    """The newest candidate."""

    evaluation: LearningEvaluation | None = None
    """The running or latest evaluation."""

    evidence: LearningEvidenceCounts | None = None
    """Evidence arrived, verified, incorporated and pending."""

    backlog: int | None = None
    """Outcomes waiting to be learned from."""

    budget: LearningBudget | None = None
    """The learning budget."""


class LearningLesson(BaseModel):
    """One lesson of a learned version."""

    id: str | None = None
    """The lesson id (stable across versions)."""

    text: str | None = None
    """The lesson text."""

    tool: str | None = None
    """The tool the lesson is scoped to, or ``None`` for general guidance."""

    evidence_count: int | None = None
    """How many evidence cases support it."""


class LearningProvenance(BaseModel):
    """Where a version's lessons came from."""

    episodes: int | None = None
    """Episodes the lessons were learned from."""

    outcomes: int | None = None
    """Outcomes behind them."""


class LearningVersion(BaseModel):
    """One immutable learned version; only its state moves.

    The single-version read (``learning.version``) also fills ``lessons`` and ``provenance``.
    """

    id: str
    """The version id."""

    state: str | None = None
    """Known values: ``candidate``, ``evaluating``, ``active``, ``retired``, ``rejected``,
    ``superseded``."""

    state_reason: str | None = None
    """Why the version is in this state (a stable machine code), when known."""

    parent_version_id: str | None = None
    """The version this one was derived from."""

    lesson_count: int | None = None
    """The number of lessons."""

    evaluation_id: str | None = None
    """The evaluation that decided this version, when one did."""

    created_at: str | None = None
    """When the version was created (ISO-8601)."""

    lessons: list[LearningLesson] | None = None
    """The lessons (on the single-version read)."""

    provenance: LearningProvenance | None = None
    """A summary of where the lessons came from (on the single-version read)."""


class LearningVersionList(BaseModel):
    """Version history, newest first (``GET /v1/call-types/{id}/learning/versions``)."""

    data: list[LearningVersion] = Field(default_factory=list)
    """The versions."""


class LearningEvaluationList(BaseModel):
    """Evaluations, newest first (``GET /v1/call-types/{id}/learning/evaluations``)."""

    data: list[LearningEvaluation] = Field(default_factory=list)
    """The evaluations."""
