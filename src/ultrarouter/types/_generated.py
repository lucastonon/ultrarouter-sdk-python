"""Typed API shapes generated from ``openapi/openapi.yaml``.

Do not edit by hand: run ``python scripts/gen_types.py`` after re-syncing the spec.
Response models subclass :class:`ultrarouter.BaseModel` (unknown fields are kept);
request shapes are ``TypedDict`` classes used to type method arguments.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field
from typing_extensions import Required, TypedDict

from .._models import BaseModel

__all__ = [
    "OPERATIONS",
    "Artifact",
    "ArtifactClaim",
    "ArtifactCreateParams",
    "ArtifactEnvelope",
    "ArtifactFinal",
    "ArtifactFinalParams",
    "ArtifactList",
    "ArtifactObjective",
    "ArtifactObjectiveParams",
    "ArtifactType",
    "ArtifactTypeEnvelope",
    "ArtifactTypeUpsertParams",
    "AuditReadiness",
    "AuditReadinessCallType",
    "AuditReadinessCallTypeCapture",
    "AuditReadinessCallTypeCostProvenance",
    "AuditReadinessCoverage",
    "AuditReadinessEmergingShape",
    "AuditReadinessInventory",
    "AuditReadinessOpportunity",
    "BatchOutcomeParams",
    "BatchOutcomeResult",
    "BatchOutcomesParams",
    "BatchOutcomesResponse",
    "BenchAllowance",
    "BenchAttachedExpectation",
    "BenchBaseline",
    "BenchCompareGate",
    "BenchCompareGateCallType",
    "BenchCompareGateCallTypeCostCeiling",
    "BenchCompareGateCallTypePairing",
    "BenchDatasetCard",
    "BenchDatasetExclusion",
    "BenchDatasetFreeze",
    "BenchDatasetFreezeDataset",
    "BenchDatasetFreezeDatasetEvaluator",
    "BenchDatasetFreezeDatasetEvaluatorAssertion",
    "BenchDatasetFreezeWarning",
    "BenchDatasetStaleness",
    "BenchDatasetStratum",
    "BenchDisposition",
    "BenchEntitlement",
    "BenchEvalRun",
    "BenchEvalRunArm",
    "BenchEvidenceClass",
    "BenchExpectationParams",
    "BenchExpectations",
    "BenchExpectationsParams",
    "BenchFreezeParams",
    "BenchInterval",
    "BenchOutcomeParams",
    "BenchOutcomes",
    "BenchOutcomesParams",
    "BenchPowerAdvisory",
    "BenchPowerPlan",
    "BenchRecordedOutcome",
    "BenchReport",
    "BenchReportCallType",
    "BenchReportCallTypeArm",
    "BenchReportCallTypeArmCostView",
    "BenchReportCallTypeInversion",
    "BenchReportCallTypePower",
    "BenchReportCallTypeProjection",
    "BenchReportCallTypeProjectionBasis",
    "BenchReportCallTypeTaskViewItem",
    "BenchReportCallTypeVerdict",
    "BenchReportExport",
    "BenchReportReproducibility",
    "BenchRun",
    "BenchRunParams",
    "BenchRunTrigger",
    "BenchSuiteStatus",
    "BenchSuiteStatusCallType",
    "BenchSuiteStatusCallTypeQualified",
    "BenchSuiteStatusCapture",
    "BenchTagParam",
    "CacheControlParam",
    "CallType",
    "CallTypeConfigParams",
    "CallTypeConfigVersion",
    "CallTypeCreateParams",
    "CallTypeImprovementReads",
    "CallTypeImprovementReadsHoldoutGap",
    "CallTypeList",
    "CandidateDecisionParams",
    "CandidateDecisionResult",
    "CandidateRolloutBlocker",
    "CandidateRolloutIdentityParams",
    "CandidateRolloutParams",
    "CandidateRolloutResult",
    "ChatCompletion",
    "ChatCompletionChoice",
    "ChatCompletionCreateParams",
    "ChatCompletionMessage",
    "ChatCompletionUsage",
    "ChatCompletionUsagePromptTokensDetails",
    "ChatContentPartParam",
    "ChatMessageParam",
    "ClaimParams",
    "CompressionParam",
    "Confirmation",
    "ConfirmationLift",
    "ConfirmationLiftInterval",
    "ConfirmationList",
    "ConfirmationStatus",
    "ConfirmationStatusAutoAdopt",
    "ContextModuleRefParam",
    "CreateEmbeddingResponse",
    "CreateMessageParams",
    "CreateMessageResponse",
    "DiffLengthsParams",
    "DiffStatsParams",
    "Embedding",
    "EmbeddingCreateParams",
    "EmbeddingUrBlock",
    "EmbeddingUrBlockRouting",
    "EmbeddingUsage",
    "EnqueueEvalParams",
    "EnqueueEvalResponse",
    "EpisodeMemoryDisableResult",
    "EpisodeMemoryEnableParams",
    "EpisodeMemoryEnableParamsLessons",
    "EpisodeMemoryEnableResult",
    "EpisodeMemoryStatus",
    "EpisodeMemoryStatusMemory",
    "EpisodeMemoryStatusPlaybook",
    "EpisodeMemoryStatusSetting",
    "EpisodeMemoryStatusSettingLessons",
    "EpisodeMemoryStatusSettingLessonsRecipe",
    "EpisodeMemoryStatusTraces",
    "EvalRun",
    "EvalRunCandidate",
    "EvalRunJudge",
    "EvalRunList",
    "EvalRunSpec",
    "EvalRunSpecCandidate",
    "EvalRunSpecHypothesis",
    "EvalRunSpecProfile",
    "EvalRunSpecProfileEvaluatorSuite",
    "EvalRunSpecProfileEvaluatorSuiteJudge",
    "EvalRunSpecProfileEvaluatorSuiteScorerInstance",
    "ExperimentEnrolParams",
    "ExperimentExecution",
    "ExperimentExecutionOutcome",
    "ExperimentExecutionOutcomeCost",
    "ExperimentExecutionOutcomeOpenHold",
    "ExperimentOutcomeParams",
    "ExperimentReceiptParams",
    "ExperimentScreenEvaluation",
    "ExperimentScreenEvaluationScreen",
    "ExperimentScreenEvaluationScreenExecution",
    "ExperimentScreenEvaluationScreenProgress",
    "ExperimentScreenEvaluationScreenVerdict",
    "ExperimentScreenEvaluationScreenVerdictClause",
    "ExperimentScreenEvaluationScreenVerdictClauseDetail",
    "ExperimentScreenEvaluationScreenVerdictClauseDetailFeature",
    "ExperimentScreenEvaluationScreenVerdictClauseDetailVerdict",
    "ExperimentScreenEvaluationScreenVerdictInputs",
    "ExperimentScreenEvaluationScreenVerdictInputsExecution",
    "ExperimentScreenEvaluationScreenVerdictInputsJudgement",
    "ExperimentScreenEvaluationScreenVerdictInputsObservation",
    "ExperimentScreenEvaluationScreenVerdictInputsPhaseHolds",
    "ExperimentScreenEvaluationScreenVerdictRule",
    "ExperimentTestEvaluation",
    "ExperimentTestEvaluationTest",
    "ExperimentTestEvaluationTestProgress",
    "ExperimentTestEvaluationTestVerdict",
    "ExperimentTestEvaluationTestVerdictEconomics",
    "ExperimentTestEvaluationTestVerdictGoodhart",
    "ExperimentTestEvaluationTestVerdictGoodhartArm",
    "ExperimentTestEvaluationTestVerdictPrimary",
    "ExperimentTestEvaluationTestVerdictQuality",
    "ExperimentTestEvaluationTestVerdictQualityPerJudgeItem",
    "ExperimentTestEvaluationTestVerdictRule",
    "ExposureGrant",
    "ExposureGrantParams",
    "Feedback",
    "FeedbackCreateParams",
    "FeedbackEnvelope",
    "FlywheelCandidate",
    "FlywheelCandidateList",
    "FlywheelCandidateOffline",
    "FlywheelCandidateOfflineCost",
    "FlywheelCandidateOfflineEconomics",
    "FlywheelCandidateOfflineEconomicsCostPerAvoidedErrorMicroUsd",
    "FlywheelCandidateOfflineEconomicsErrorsAvoidedPer1000",
    "FlywheelChannelHealth",
    "FlywheelStatus",
    "FlywheelStatusImports",
    "FlywheelStatusLearning",
    "FlywheelUsageBlock",
    "FlywheelUsageBlockActualCogs",
    "FlywheelUsageBlockAnalysisUnits",
    "FlywheelUsageBlockEvaluationComputeUsd",
    "FlywheelUsageBlockStorage",
    "GenerationStats",
    "GenerationStatsCost",
    "GenerationStatsExposure",
    "GenerationStatsLever",
    "GenerationStatsOutcome",
    "GenerationStatsTiming",
    "GenerationStatsTokens",
    "HostedPrompt",
    "HostedPromptActivateParams",
    "HostedPromptActivation",
    "HostedPromptCreateParams",
    "HostedPromptList",
    "HostedPromptProposal",
    "HostedPromptVariable",
    "HostedPromptVariableParam",
    "Import",
    "ImportCreateParams",
    "ImportCreateParamsReasonVocabulary",
    "ImportEnvelope",
    "ImportList",
    "ImportParseError",
    "ImportReport",
    "ImportReportWorkflow",
    "ImportReportWorkflowCostReconciliationItem",
    "ImprovementCollecting",
    "ImprovementRead",
    "ImprovementReads",
    "KeyInfo",
    "KeyInfoLimits",
    "KeyInfoUsage",
    "LearnerRecipeParams",
    "LearningControl",
    "LearningEnableParams",
    "LearningEvaluation",
    "LearningEvaluationArm",
    "LearningEvaluationArms",
    "LearningEvaluationDecidedBy",
    "LearningEvaluationDifference",
    "LearningEvaluationList",
    "LearningEvaluationRule",
    "LearningPlan",
    "LearningPlanCallTypeBinding",
    "LearningPlanCallTypeBindingLabelFieldProposal",
    "LearningPlanCallTypeBindingLabelFieldProposalCandidate",
    "LearningPlanEnvelope",
    "LearningPlanList",
    "LearningPlanProposal",
    "LearningPromotionParams",
    "LearningPromotionPolicy",
    "LearningRollbackParams",
    "LearningStatus",
    "LearningStatusBudget",
    "LearningStatusEvidence",
    "LearningStatusOutcomeReceipts",
    "LearningStatusRecipe",
    "LearningStatusReflection",
    "LearningStatusReflectionNext",
    "LearningStatusReflectionProvider",
    "LearningStatusUsage",
    "LearningToolDocumentation",
    "LearningToolDocumentationTool",
    "LearningToolDocumentationToolDocumentedItem",
    "LearningVersion",
    "LearningVersionCohort",
    "LearningVersionDetail",
    "LearningVersionDetailDistiller",
    "LearningVersionDetailLesson",
    "LearningVersionDetailTransition",
    "LearningVersionList",
    "LearningVersionRef",
    "ManifestWireEntryParam",
    "ManifestWireParam",
    "ManifestWireRangeParam",
    "MoatNext",
    "MoatNextExperiment",
    "MoatNextExperimentAdmission",
    "MoatNextExperimentAdmissionApplied",
    "MoatNextExperimentAdmissionEvidence",
    "MoatNextExperimentBudget",
    "MoatNextExperimentReservations",
    "MoatNextExperimentReservationsPhase",
    "MoatNextItem",
    "MoatNextPrecondition",
    "Model",
    "ModelDetail",
    "ModelList",
    "ModelOffer",
    "ModelPricing",
    "Oracle",
    "OracleClaimParams",
    "OracleCurrent",
    "OracleExampleParams",
    "OracleJob",
    "OracleJobList",
    "OracleProbeParams",
    "OracleQualification",
    "OracleQualificationCertifier",
    "OracleQualificationDetector",
    "OracleQualificationExamples",
    "OracleQualificationJobs",
    "OracleQualificationOutcome",
    "OracleQualifyParams",
    "OracleRegisterParams",
    "OracleRegistration",
    "OracleRevocation",
    "OracleRevokeParams",
    "OracleRole",
    "OracleTestParams",
    "OracleTestResult",
    "OracleTestResultRequest",
    "OracleTransportState",
    "OracleTransportStateCanaries",
    "OracleTransportStateCanaryPool",
    "OracleTransportStateJobs",
    "OracleTransportStateQualification",
    "OracleVerdictParams",
    "OracleVerdictResult",
    "OracleVerdictsParams",
    "OracleVerdictsResult",
    "OracleVersion",
    "OutcomeParams",
    "OutcomeReceiptRecord",
    "OutcomeReceiptRecordEpisode",
    "OutcomeReceiptRecordList",
    "OutcomeResult",
    "PendingClaim",
    "PendingClaimList",
    "PreflightBudgetParams",
    "PreflightFallback",
    "PreflightGrant",
    "PreflightKnowledge",
    "PreflightKnowledgeModule",
    "PreflightLineage",
    "PreflightModel",
    "PreflightOfferScore",
    "PreflightParams",
    "PreflightPrompt",
    "PreflightPromptVariable",
    "PreflightResponse",
    "PreflightRouting",
    "PreflightWhy",
    "PreflightWhyChosen",
    "PromptCandidate",
    "PromptCandidateList",
    "ProviderPreferencesParam",
    "PutLearningToolDocumentationParams",
    "PutLearningToolDocumentationParamsTool",
    "PutLearningToolDocumentationParamsToolFunction",
    "ReasoningParam",
    "RecordOutcomesParams",
    "RecordOutcomesResponse",
    "RequestOutcomeResult",
    "ResponseFormatJsonObjectParam",
    "ResponseFormatJsonSchemaParam",
    "ResponseFormatTextParam",
    "ReviewerBackfillParams",
    "ReviewerBackfillProgress",
    "ReviewerDeadLetter",
    "ReviewerEvent",
    "ReviewerEventResult",
    "ReviewerEventsParams",
    "ReviewerEventsResponse",
    "ReviewerFinalParams",
    "ReviewerHealth",
    "ReviewerHealthEventCounts",
    "ReviewerHealthNextRepair",
    "ReviewerMappingRow",
    "ReviewerRepairBefore",
    "ReviewerRepairParams",
    "ReviewerRepairResult",
    "ReviewerSetup",
    "ReviewerSignatureRecipe",
    "ReviewerTestParams",
    "ReviewerTestResult",
    "SegmentHintParam",
    "SelfImproveGuardrailsParams",
    "UrBlock",
    "UrBlockBench",
    "UrBlockCompression",
    "UrBlockRouting",
    "UrBlockVerifiedMemory",
    "UrParams",
    "UsageExposureRow",
    "VerdictSource",
    "VerdictSourceCheck",
    "VerdictSourceCheckParams",
    "VerdictSourceCheckResult",
    "VerdictSourceCheckResultPerFamilyItem",
    "VerdictSourceCheckResultRecall",
    "VerdictSourceGradeParams",
    "VerdictSourceLastAdmission",
    "VerdictSourceList",
    "VerdictSourceProbe",
    "VerdictSourceReviewFlag",
    "VerdictSourceVerdictParams",
    "VerifiedMemoryDisableResult",
    "VerifiedMemoryEnableParams",
    "VerifiedMemoryEnableResult",
    "VerifiedMemoryEnableResultCalibration",
    "VerifiedMemoryEnableResultPool",
    "VerifiedMemoryEnableResultPoolAdmission",
    "VerifiedMemoryEnableResultPoolContent",
    "VerifiedMemoryStatus",
    "VerifiedMemoryStatusLivePool",
    "VerifiedMemoryStatusPostPin",
    "VerifiedMemoryStatusServable",
    "VerifiedMemoryStatusSetting",
    "VerifiedMemoryStatusSettingCalibration",
    "VerifiedMemoryStatusSettingOperatingPoint",
    "VerifiedMemoryStatusSettingPool",
    "VerifiedMemoryStatusSettingPoolDropped",
]


class ArtifactTypeUpsertParams(TypedDict, total=False):
    """Register an artifact type / append an objective version."""

    archetype: Required[
        Literal["forecast", "recommendation", "draft", "extraction", "answer", "action"]
    ]
    """The archetype every artifact of this type declares."""

    name: Required[str]
    """The customer-named type (`thesis`, `tax_plan`, `article`) — unique per workspace."""

    objective: Required[ArtifactObjectiveParams]
    """What “it worked” means for this artifact type — the ONE thing never inferred."""


class ArtifactObjectiveParams(TypedDict, total=False):
    """What “it worked” means for this artifact type — the ONE thing never inferred."""

    alternatives: list[str]
    """Named alternatives for computable comparisons (`alternative_id`)."""

    direction: Required[str]
    """Which direction is good (e.g. `true_is_good`, `higher_is_better`)."""

    metric: Required[
        Literal[
            "claim_resolution",
            "oracle_delta",
            "correction_rate",
            "acceptance_rate",
            "engagement_rate",
            "task_success",
        ]
    ]
    """The objective metric (closed vocabulary)."""

    predicate_id: Literal["equals", "within_tolerance", "ge", "le", "resolved_by_source"]
    """An optional machine predicate over the resolution (closed set)."""

    resolution_criteria: Required[str]
    """How the objective resolves — REDACTED free text, never a body."""

    source: Required[str]
    """Where the resolving signal comes from (e.g. `analyst`, `filing`, an oracle name)."""

    unit: Required[str]
    """The unit the metric is measured in (e.g. `boolean`, `ratio`, `usd`)."""

    window: Required[str]
    """The resolution window as an ISO-8601 DURATION (e.g. `P12M`), never an instant."""


class ArtifactTypeEnvelope(BaseModel):
    """The current artifact-type objective version, wrapped in the `artifact_type` envelope."""

    artifact_type: ArtifactType
    """An artifact-type objective version (append-only)."""


class ArtifactType(BaseModel):
    """An artifact-type objective version (append-only)."""

    archetype: str
    """The artifact archetype (closed vocabulary).

    Known values: ``forecast``, ``recommendation``, ``draft``, ``extraction``, ``answer``, ``action``.
    """

    created_at: str

    id: str

    name: str

    object: str
    """Known values: ``artifact_type``."""

    objective: ArtifactObjective
    """What “it worked” means for this artifact type — the ONE thing never inferred."""

    version: int
    """The append-only objective version (max+1 per name; never rewritten)."""


class ArtifactObjective(BaseModel):
    """What “it worked” means for this artifact type — the ONE thing never inferred."""

    alternatives: list[str] | None = None
    """Named alternatives for computable comparisons (`alternative_id`)."""

    direction: str
    """Which direction is good (e.g. `true_is_good`, `higher_is_better`)."""

    metric: str
    """The objective metric (closed vocabulary).

    Known values: ``claim_resolution``, ``oracle_delta``, ``correction_rate``, ``acceptance_rate``, ``engagement_rate``, ``task_success``.
    """

    predicate_id: str | None = None
    """An optional machine predicate over the resolution (closed set).

    Known values: ``equals``, ``within_tolerance``, ``ge``, ``le``, ``resolved_by_source``.
    """

    resolution_criteria: str
    """How the objective resolves — REDACTED free text, never a body."""

    source: str
    """Where the resolving signal comes from (e.g. `analyst`, `filing`, an oracle name)."""

    unit: str
    """The unit the metric is measured in (e.g. `boolean`, `ratio`, `usd`)."""

    window: str
    """The resolution window as an ISO-8601 DURATION (e.g. `P12M`), never an instant."""


class ArtifactList(BaseModel):
    """A keyset-paginated page of artifacts (cursor-based; never offset)."""

    data: list[Artifact]

    next_cursor: str | None
    """Opaque keyset cursor for the next page (null = end)."""

    object: str
    """Known values: ``list``."""


class Artifact(BaseModel):
    """An artifact (metadata only — bodies are stored separately, never here)."""

    archetype: str
    """The artifact archetype (closed vocabulary).

    Known values: ``forecast``, ``recommendation``, ``draft``, ``extraction``, ``answer``, ``action``.
    """

    artifact_type_version_id: str | None

    call_type_id: str | None

    claims: list[ArtifactClaim]
    """The artifact’s ACTIVE claims (one per claim_key) + their current claim state. `claim_key` on an outcome resolves to these.
    """

    created_at: str

    current_version: int
    """The artifact’s current (max) version."""

    exposure_arm: str | None

    exposure_epoch: int | None

    grant_attestation: str | None
    """The customer attestation `served` | `applied` (null when no grant)."""

    grant_id: str | None
    """The exposure grant this artifact carries (null when unarmed/observation-only)."""

    id: str

    key: str

    lifecycle: str

    object: str
    """Known values: ``artifact``."""

    occurred_at: str

    request_ids: list[str]
    """The ACTIVE request memberships (assembly lineage)."""

    situation_key: str | None

    superseded_claims: list[ArtifactClaim]
    """History: platform-extracted claims a later declared claim superseded for the same claim_key — kept (state `superseded`) and linked through `superseded_by_claim_id`, never deleted; their outcome events stay on them. Usually empty.
    """

    updated_at: str


class ArtifactClaim(BaseModel):
    """A claim on an artifact (metadata only)."""

    artifact_version: int

    claim_key: str

    claim_type: str

    created_at: str

    id: str

    provenance: str
    """Who asserted the claim: `declared` = yours (declared claims always win their claim_key); `extracted` = the platform’s claim extractor.

    Known values: ``declared``, ``extracted``.
    """

    qualification: str
    """The trust label: `declared` for a declared claim; for an extracted claim, the extractor’s verdict at extraction (`unqualified` never feeds learning).

    Known values: ``declared``, ``qualified``, ``unqualified``.
    """

    resolves_by: str | None

    state: str
    """The current claim state (derived from the claim’s outcome events). `superseded` is terminal: a later customer-declared claim took this claim’s claim_key (only ever listed under `superseded_claims`).

    Known values: ``pending``, ``overdue``, ``resolved``, ``censored``, ``voided``, ``disputed``, ``superseded``.
    """

    state_version: int

    stated_confidence: float | None

    superseded_at: str | None
    """When a later declared claim superseded this one (null for an active claim)."""

    superseded_by_claim_id: str | None
    """The declared claim that superseded this one (null for an active claim)."""


class ArtifactCreateParams(TypedDict, total=False):
    """Create or upsert an artifact by key."""

    archetype: Literal["forecast", "recommendation", "draft", "extraction", "answer", "action"]
    """Defaults to `answer` when omitted."""

    artifact_type: str
    """A registered artifact-type name — its current objective version is pinned."""

    attestation: Literal["served", "applied"]
    """CUSTOMER attestation (`served` = the grant was issued; `applied` = the recommended module/model was actually used). Defaults to `served`. Shown beside lift, NEVER provenance.
    """

    claims: list[ClaimParams]
    """Declared claims."""

    grant_id: str
    """An exposure GRANT from `POST /v1/flywheel/grants`. When present + VALID, the artifact is stamped with the GRANT’s arm (a non-proxied call becomes armed — for granted artifacts only). Absent ⇒ `unarmed_observation`. An unknown grant is a 400 (fail closed).
    """

    key: Required[str]
    """The canonical artifact alias (unique per workspace)."""

    occurred_at: str
    """When the artifact was created in the customer world (ISO-8601; defaults to now)."""

    request_ids: list[str]
    """The requests this artifact is assembled from (declared, post-hoc; assembly_source=api)."""

    situation_facets: dict[str, Any]
    """Declared situation facets (customer-declared; hashed into the situation key)."""


class ClaimParams(TypedDict, total=False):
    """A customer-declared claim."""

    claim_type: Required[str]
    """The namespaced claim type (e.g. earnings_direction)."""

    key: Required[str]
    """The customer claim key (one active claim per key per artifact; a declared claim supersedes a platform-extracted claim on the same key).
    """

    resolves_by: str
    """ISO-8601 resolution deadline (passing ⇒ overdue)."""

    stated_confidence: float
    """The customer stated confidence ∈ (0,1)."""

    statement: str
    """A REDACTED claim statement (never a raw body — redact upstream)."""


class ArtifactEnvelope(BaseModel):
    """A single artifact, wrapped in the `artifact` envelope."""

    artifact: Artifact
    """An artifact (metadata only — bodies are stored separately, never here)."""


class ArtifactFinalParams(TypedDict, total=False):
    """Record the human-approved final output version (the correction channel)."""

    artifact_version: int
    """The draft version this final approves (defaults to the current version)."""

    diff_stats: DiffStatsParams
    """CLIENT-computed diff stats (the no-consent path; the SDK `diffStats` helper)."""

    draft: str
    """The draft body — used ONLY to compute server-side diff_stats under consent."""

    final: str
    """The final body — stored ONLY under corrections_consent."""

    final_hash: str
    """The final content hash (required on the no-consent metadata-only path)."""


class DiffStatsParams(TypedDict, total=False):
    """CLIENT-computed diff stats (the no-consent path; the SDK `diffStats` helper)."""

    changed_spans: int

    edit_ratio: float

    final_hash: str

    lengths: DiffLengthsParams


class DiffLengthsParams(TypedDict, total=False):
    """Request shape ``DiffLengthsParams``."""

    draft: Required[int]

    final: Required[int]


class ArtifactFinal(BaseModel):
    """The appended final artifact version."""

    artifact_id: str

    client_computed: bool

    created_at: str

    diff_stats: dict[str, Any]

    final_hash: str | None

    id: str

    object: str
    """Known values: ``artifact_version``."""

    stored: str
    """`blob` (body stored under consent) | `metadata_only` (no consent).

    Known values: ``blob``, ``metadata_only``.
    """

    version: int


class RecordOutcomesParams(TypedDict, total=False):
    """Record 1..N outcome events on an artifact or its claims."""

    outcomes: Required[list[OutcomeParams]]
    """1..N outcome events."""


class OutcomeParams(TypedDict, total=False):
    """A single outcome event to record (the server assigns provenance + learning_use)."""

    alternative_id: str
    """A computable-comparison alternative id."""

    artifact_version: int
    """The pinned artifact version (defaults to the artifact’s current version)."""

    channel: Required[
        Literal["mechanical", "correction", "behavioral", "resolution", "computable", "proxy"]
    ]
    """The outcome channel (closed vocabulary)."""

    claim_id: str
    """Target a specific claim by id (else the artifact)."""

    claim_key: str
    """Target a claim by its customer key — the key’s ACTIVE claim (else the artifact)."""

    confidence: float
    """An optional confidence ∈ (0,1)."""

    evidence_hash: str
    """A content hash of supporting evidence (never a body)."""

    kind: Required[str]
    """The channel `kind` (a closed vocabulary per channel)."""

    observed_at: str
    """The effective time (ISO-8601; must be ≥ the artifact occurred_at). Defaults to now."""

    source_event_id: str
    """The caller idempotency discriminator (ULID at enqueue). Defaults to a server ULID."""

    supersedes_event_id: str
    """The event this one supersedes."""

    tool_error_class: Literal["model", "infra", "unclassified"]
    """For mechanical:tool_error — refines learning_use (only model-class teaches)."""

    value: dict[str, Any]
    """The typed numeric/diff-stats payload — never a body."""


class RecordOutcomesResponse(BaseModel):
    """The per-event results (202 only after the durable insert)."""

    data: list[OutcomeResult]

    object: str
    """Known values: ``list``."""


class OutcomeResult(BaseModel):
    """One outcome event’s server-assigned result."""

    artifact_version: int | None

    canonical_target_id: str | None

    id: str | None
    """The outcome-event id when accepted/duplicate; else null."""

    latency_class: str | None
    """Known values: ``instant``, ``delayed``."""

    learning_use: list[str] | None
    """Known values: ``train``, ``calibrate``, ``rank``, ``audit``."""

    reason: str | None
    """The rejection/conflict reason when not accepted."""

    source: str | None
    """Known values: ``declared``, ``inferred``, ``gateway``, ``imported``."""

    source_event_id: str | None

    status: str
    """Per-event acceptance: accepted | duplicate (no-op) | conflict (409) | rejected.

    Known values: ``accepted``, ``duplicate``, ``conflict``, ``rejected``.
    """

    target_kind: str | None
    """Known values: ``artifact``, ``claim``."""


class AuditReadiness(BaseModel):
    """Audit Autopilot passive readiness report (zero-config, zero authority)."""

    call_types: list[AuditReadinessCallType]

    computed_at: str | None
    """When the rollup was computed (ISO 8601), or null."""

    config_version: int
    """The config_version the rollup used."""

    coverage: AuditReadinessCoverage
    """Evidence-coverage summary — visibly surfaces the no-consent metadata sampling."""

    emerging_shapes: list[AuditReadinessEmergingShape]

    generated: bool
    """False when the analyze worker has not produced a rollup yet (honest empty)."""

    inventory: AuditReadinessInventory
    """Workspace inventory observed in the window."""

    object: str
    """Known values: ``audit_readiness``."""

    observing_call_types: int

    opportunities: list[AuditReadinessOpportunity]

    state: str
    """Workspace audit state — passive observation only.

    Known values: ``observing``.
    """

    total_requests: int

    total_spend_micro_usd: int

    window_end: str
    """Rollup window end (ISO 8601)."""

    window_start: str
    """Rollup window start (ISO 8601)."""


class AuditReadinessCallType(BaseModel):
    """Per-call-type passive readiness."""

    cache_hit_rate: float
    """Fraction of requests that read a provider cache."""

    call_type_id: str
    """The call type id (`ct_…`)."""

    capture: AuditReadinessCallTypeCapture
    """Capture coverage for this call type."""

    confidence: str
    """Confidence this is a real, stable task shape.

    Known values: ``high``, ``medium``, ``low``.
    """

    cost_provenance: AuditReadinessCallTypeCostProvenance
    """Cost-provenance mix (an estimate is never labeled as provider-reported usage)."""

    display_name: str
    """The human display name."""

    error_rate: float
    """Fraction of requests that errored, in [0,1]."""

    evidence_gaps: list[str]
    """Machine-readable evidence gaps — WHAT is unavailable and WHY (honesty)."""

    fallback_rate: float
    """Fraction of requests that fell back to a non-primary offer."""

    lifecycle_state: str
    """Audit lifecycle state — `observing` in this passive subset."""

    models_seen: list[str]
    """Distinct served models observed."""

    providers_seen: list[str]
    """Distinct providers observed."""

    requests: int
    """Observed request volume in the window."""

    slug: str
    """The call type slug."""

    source: str
    """`explicit` (caller slug) or `fingerprint` (automatically inferred from request shape)."""

    spend_micro_usd: int
    """Observed spend (integer µUSD)."""


class AuditReadinessCallTypeCapture(BaseModel):
    """Capture coverage for this call type."""

    confirmed: int

    non_replayable: int

    queued: int


class AuditReadinessCallTypeCostProvenance(BaseModel):
    """Cost-provenance mix (an estimate is never labeled as provider-reported usage)."""

    estimate_only: int
    """Requests whose cost is estimate-only (no replayable evidence)."""

    measured_replayable: int
    """Requests with a confirmed, replayable envelope → provider-reported usage."""


class AuditReadinessCoverage(BaseModel):
    """Evidence-coverage summary — visibly surfaces the no-consent metadata sampling."""

    confirmed_envelopes: int

    non_replayable_envelopes: int

    notes: list[str]
    """Human-readable coverage/honesty notes."""

    payload_consented: bool
    """True only when retention is `full` (replay consent)."""

    queued_envelopes: int

    retention_mode: str
    """Payload retention (`none`|`metadata`|`full`)."""

    unconsented_capture_sampled: bool
    """True when no-consent shape metadata is sampled (metadata retention)."""

    unconsented_sample_rate: float
    """The deterministic sample rate bounding no-consent metadata-envelope volume."""


class AuditReadinessEmergingShape(BaseModel):
    """An inferred request shape not yet surfaced as a call type."""

    hash8: str
    """The 8-hex-char template label."""

    request_count: int
    """Observed similar requests so far."""

    requests_to_surface: int
    """Requests remaining until the shape crosses the noise gate and surfaces as a call type."""

    sample_prompt_masked: str
    """MASKED template preview (never raw content)."""


class AuditReadinessInventory(BaseModel):
    """Workspace inventory observed in the window."""

    key_modes: list[str]

    models: list[str]

    providers: list[str]


class AuditReadinessOpportunity(BaseModel):
    """A DISCOVERY savings opportunity (blended-price shortlist, never a migration claim)."""

    basis: str
    """Blended per-token price shortlist basis.

    Known values: ``blended_price_discovery``.
    """

    call_type_id: str

    candidate_model: str
    """A cheaper catalog candidate (blended-price shortlist)."""

    candidate_provider: str

    current_model: str
    """The dominant (highest-priced) model observed."""

    est_monthly_savings_micro_usd: int
    """Estimated monthly savings (DISCOVERY — never realized cash)."""

    est_window_savings_micro_usd: int
    """Estimated window savings (DISCOVERY — never realized cash)."""

    label: str
    """Always discovery — never a realized/claimed figure.

    Known values: ``discovery``.
    """

    slug: str

    spend_micro_usd: int


class BenchRun(BaseModel):
    """ultrarouter Bench on-demand run."""

    allowance: BenchAllowance
    """The workspace Bench allowance state."""

    dispositions: list[BenchDisposition]
    """The per-call-type dispositions."""

    estimate_usd: float
    """The aggregate pre-run estimate (USD)."""

    id: str
    """The umbrella `br_*` id."""

    mode: str
    """Known values: ``request``, ``task``."""

    object: str
    """Known values: ``bench_run``."""

    runs: list[BenchEvalRun]
    """The child eval runs (tier + per-arm evidence)."""

    selection_mode: str
    """Known values: ``selection``, ``noninferiority``."""

    status: str
    """The umbrella status.

    Known values: ``queued``, ``running``, ``complete``, ``failed``.
    """

    suite: str
    """The bench suite slug."""


class BenchAllowance(BaseModel):
    """The workspace Bench allowance state."""

    available_usd: float
    """grant − reserved − spent (USD; 0 when there is no grant)."""

    grant_usd: float | None
    """The prepaid Bench allowance in USD, or null when the workspace has none."""

    reserved_usd: float
    """Open reservations for in-flight runs (USD)."""

    spent_usd: float
    """Settled Bench spend to date (USD)."""


class BenchDisposition(BaseModel):
    """A per-call-type bench run disposition."""

    call_type_id: str
    """The frozen call type."""

    dataset_hash: str | None
    """The frozen dataset content address, or null."""

    disposition: str
    """runnable | not_runnable | deduped | budget_queued.

    Known values: ``runnable``, ``not_runnable``, ``deduped``, ``budget_queued``.
    """

    estimate_usd: float
    """This child run's bounded planning estimate in USD (before global admission)."""

    eval_run_id: str | None
    """The fanned child eval run id (runnable), else null."""

    judge_worst_case_usd: float | None = None
    """The CONSERVATIVE worst-case JUDGE-phase cost (USD) this call type could incur — the SAME arithmetic the phase-time guard uses (pairs × positions × tiers × pinned maxTokens at judge rates + a re-invoke allowance), surfaced additively (NOT folded into estimate_usd). 0 for a judge_disabled (all-asserted / zero-judge) call type or an unpriced/stub judge. The umbrella admission checks arms + this bound against max_cost, so an unaffordable judge phase is refused at the trigger (judge_phase_unaffordable) before any arm spend.
    """

    power: BenchPowerAdvisory | None = None
    """Pre-spend power advisory — attached to runnable/deduped/budget_queued and the underpowered park (a not_runnable without a frozen card carries none).
    """

    prior_run_id: str | None
    """The prior run linked when deduped, else null."""

    reason: str | None
    """Why not_runnable (insufficient_items/not_frozen/no_incumbent/no_candidates/underpowered), else null.
    """

    reserved_usd: float
    """The atomically-reserved allowance held for this run (USD)."""

    tier: str
    """The PLANNING verdict tier from the frozen card (<10/10–29/≥30 unique) — never a verdict.

    Known values: ``insufficient_items``, ``exploratory``, ``standard``.
    """

    tier_summary: str
    """Planning-language readout of the tier."""

    unique_count: int
    """The PINNED item count driving the tier + runnability: card.item_count (post-cap) — exactly the items the run executes. Equals the frozen unique count when uncapped; a max_items cap makes it the smaller pinned count so the tier reflects what actually runs.
    """

    unmatched_candidates: list[str] | None = None
    """EXPLICIT candidate ids that matched an offer globally but were NOT challengers for THIS call type (e.g. they resolve to the incumbent here) — a partial match is legal but VISIBLE. A fully-unmatched id is a 400 at the trigger, never a silent drop.
    """


class BenchPowerAdvisory(BaseModel):
    """Pre-spend power advisory — attached to runnable/deduped/budget_queued and the underpowered park (a not_runnable without a frozen card carries none)."""

    cluster_n: int
    """The frozen card independent-cluster n (the inferential unit)."""

    margin_pp: float
    """The registered non-inferiority margin Δ (pp) the advisory sizes power against."""

    mde_pp: float
    """The planning MDE (pp) recomputed from the card prior SD + cluster n vs THIS margin — a power diagnostic, never a verdict.
    """

    required_clusters: int
    """The minimum clusters THIS margin needs at the plan alpha/power (never loosened)."""

    underpowered: bool
    """True when cluster_n < required_clusters (mde_pp > margin_pp) — advisory, never a blocking gate.
    """


class BenchEvalRun(BaseModel):
    """A child eval run of a bench run."""

    arms: list[BenchEvalRunArm]
    """The per-arm evidence (incumbent + challengers)."""

    budget_spent_usd: float
    """The settled bench spend for this child (USD)."""

    call_type_id: str
    """The call type this child ran."""

    dataset_hash: str | None
    """The frozen dataset content address."""

    eval_run_id: str
    """The child eval run id."""

    evidence_classes: list[BenchEvidenceClass]
    """Per-metric evidence-class tags (empty until merged)."""

    judge_disabled: bool
    """Whether the ruler retired the judge residue (an all-asserted zero-judge run)."""

    judged_pairs: int
    """The LIVE count of fully-judged pairs. On a `judge_running` child it advances during the judge phase (diagnosable at a glance); at terminal it is the final judged count; 0 before judging.
    """

    status: str
    """The eval-run status (queued/running/scored/judge_pending/judge_running/complete/failed)."""

    tier: str
    """The PLANNING verdict tier (planning language, never a verdict)."""

    trust_class: str | None
    """The composite trust class (A/B/C), or null.

    Known values: ``A``, ``B``, ``C``.
    """


class BenchEvalRunArm(BaseModel):
    """One arm of a child bench eval run."""

    composite_score: float | None
    """The composite quality score, or null when skipped."""

    is_incumbent: bool
    """Whether this is the re-invoked incumbent arm."""

    model: str
    """The arm model id."""

    passed: bool | None
    """The non-inferiority pass flag, or null."""

    provider: str
    """The serving provider slug."""

    skip_reason: str | None
    """Why the arm was skipped, else null."""

    skipped: bool
    """Whether the arm was skipped (keyless / no offer / envelope_mismatch)."""

    total_cost_usd: float
    """The arm total cost (USD)."""


class BenchEvidenceClass(BaseModel):
    """An evidence-class-tagged composite metric row."""

    evidence_class: str
    """The evidence class the metric belongs to.

    Known values: ``programmatic``, ``outcome``, ``reference``, ``judge``.
    """

    scorer_id: str
    """The composite scorer id (or `outcome`)."""

    share: float
    """The composite weight share (0–1)."""

    weight: float
    """The absolute composite weight."""


class BenchBaseline(BaseModel):
    """ultrarouter Bench baseline pin result."""

    baseline_run_id: str
    """The newly-pinned baseline run (`br_…`)."""

    object: str
    """Known values: ``bench_baseline``."""

    previous_baseline_run_id: str | None
    """The baseline run this pin replaced, or null (first pin)."""

    suite: str
    """The bench suite slug."""

    suite_id: str
    """The bench suite id (`bs_…`)."""


class BenchCompareGate(BaseModel):
    """The ultrarouter Bench baseline-compare gate (interval-based tri-state)."""

    baseline_run_id: str | None

    bench_run_id: str

    call_types: list[BenchCompareGateCallType]

    cost_ceiling_micro_usd: float | None

    entitlement: BenchEntitlement
    """The bench packaging entitlement — a free workspace gets the verdict WITH a Team-gate notice, never a silent denial.
    """

    object: str
    """Known values: ``bench_compare_gate``."""

    reasons: list[str]
    """The union of every call type’s reasons."""

    verdict: str
    """The CI verdict = the STRICTEST across call types (fail > inconclusive > pass) — fails closed.

    Known values: ``pass``, ``fail``, ``inconclusive``.
    """


class BenchCompareGateCallType(BaseModel):
    """One call type compare gate."""

    baseline_eval_run_id: str | None
    """The paired baseline child eval run, or null (no baseline for this call type)."""

    call_type_id: str

    cost: str
    """Known values: ``pass``, ``fail``, ``inconclusive``."""

    cost_ceiling: BenchCompareGateCallTypeCostCeiling
    """The compare-gate absolute cost ceiling."""

    cost_interval: BenchInterval
    """A decision interval, verbatim."""

    cost_min_savings: float
    """The registered minimum cost-savings bar (fraction)."""

    eval_run_id: str
    """The candidate (current-config) child eval run."""

    mde_pp: float
    """The MDE (pp) — a POWER DIAGNOSTIC, never the verdict."""

    pairing: BenchCompareGateCallTypePairing
    """The compare-gate pairing census."""

    quality: str
    """Known values: ``pass``, ``fail``, ``inconclusive``."""

    quality_interval: BenchInterval
    """A decision interval, verbatim."""

    quality_margin_pp: float
    """The registered non-inferiority margin Δ (pp)."""

    reasons: list[str]
    """Machine-readable reasons the verdict is not a full pass."""

    verdict: str
    """Known values: ``pass``, ``fail``, ``inconclusive``."""


class BenchCompareGateCallTypeCostCeiling(BaseModel):
    """The compare-gate absolute cost ceiling."""

    breached: bool
    """True when the observed mean exceeds the ceiling (a hard cost fail)."""

    ceiling_micro_usd: float | None
    """The absolute per-unit ceiling (µUSD), or null."""

    enabled: bool
    """Whether an absolute cost ceiling is enforced."""

    observed_mean_micro_usd: float | None
    """The candidate mean per-unit cost over eligible pairs (µUSD), or null."""


class BenchInterval(BaseModel):
    """A decision interval, verbatim."""

    bar: float
    """The registered bar the interval is judged against (−Δ or min-savings)."""

    clusters: int

    high: float

    low: float

    n: int

    point: float


class BenchCompareGateCallTypePairing(BaseModel):
    """The compare-gate pairing census."""

    candidate_items: int

    eligible_clusters: int
    """Independent eligible clusters (the true inferential n)."""

    eligible_pairs: int
    """Pairs with a retained baseline artifact."""

    ineligible_missing_artifact: int
    """Pairs whose baseline artifact was missing/expired (excluded, degrades)."""

    unpaired: int
    """Candidate items with no baseline counterpart (excluded, stated)."""


class BenchEntitlement(BaseModel):
    """The bench packaging entitlement — a free workspace gets the verdict WITH a Team-gate notice, never a silent denial."""

    gate_entitled: bool
    """Whether the workspace is entitled to the full CI gate (Team); free keeps read access."""

    max_candidates: int | None
    """Max challenger candidates per run, or null (Team)."""

    max_items_per_call_type: int | None
    """Max frozen items per call-type run, or null (Team)."""

    notice: str | None
    """A legible entitlement notice (e.g. the CI-gate-is-Team notice), or null."""

    plan: str
    """The bench packaging plan.

    Known values: ``free``, ``team``.
    """

    run_count_limit: int | None
    """Free monthly bench-run limit, or null when not run-count-limited (Team / prepaid grant)."""

    run_count_used: int | None
    """Bench runs consumed this UTC calendar month, or null when not run-count-limited."""


class BenchOutcomesParams(TypedDict, total=False):
    """ultrarouter Bench outcomes record request."""

    outcomes: Required[list[BenchOutcomeParams]]
    """The per-trace binary outcomes to record (append-forward, latest wins)."""


class BenchOutcomeParams(TypedDict, total=False):
    """A first-party per-trace outcome input."""

    call_type: str
    """The call type the trace belongs to (optional)."""

    labels: dict[str, Any]
    """Optional free-form labels (no PII)."""

    passed: Required[bool]
    """The binary ground-truth verdict for the whole trace."""

    trace: Required[str]
    """The task/trace id the outcome grades (the stats cluster id)."""


class BenchOutcomes(BaseModel):
    """ultrarouter Bench outcomes record result."""

    bench_run_id: str | None
    """The run scope, or null (suite-scoped)."""

    object: str
    """Known values: ``bench_outcomes``."""

    recorded: list[BenchRecordedOutcome]
    """One row per recorded outcome."""

    suite: str
    """The bench suite slug."""

    suite_id: str
    """The bench suite id (`bs_…`)."""

    total: int
    """How many outcomes were recorded."""


class BenchRecordedOutcome(BaseModel):
    """A recorded Bench outcome."""

    created: bool
    """False when the identical outcome already existed (idempotent)."""

    id: str
    """The outcome id (`bo_…`)."""

    trace: str
    """The graded trace id."""

    version: int
    """The per-suite monotonic version stamp."""


class BenchReport(BaseModel):
    """The immutable ultrarouter Bench evidence report."""

    bench_run_id: str

    call_types: list[BenchReportCallType]
    """One block per call type (sections 1–7)."""

    content_hash: str
    """The content address — a re-read is byte-stable."""

    export: BenchReportExport
    """The audited export links (JSON / Markdown / verifiable bundle)."""

    limitations: list[str]
    """The report-level limitations union."""

    mode: str
    """Known values: ``request``, ``task``."""

    object: str
    """Known values: ``bench_report``."""

    reproducibility: BenchReportReproducibility
    """Section 8: the reproducibility appendix (spec/profile/evidence/decision ids, seeds, versions).
    """

    selection_mode: str
    """Known values: ``selection``, ``noninferiority``."""

    status: str

    suite: str

    version: int


class BenchReportCallType(BaseModel):
    """One call type report block."""

    arms: list[BenchReportCallTypeArm]
    """Section 3: per-arm headline rows."""

    call_type_id: str

    dataset_card: BenchDatasetCard | None
    """Section 1: the frozen dataset card."""

    eval_run_id: str

    evidence_classes: list[BenchEvidenceClass]

    inversions: list[BenchReportCallTypeInversion]
    """Cost inversion callouts (per-request-cheaper but per-task-costlier)."""

    judge_disabled: bool

    limitations: list[str]
    """Section 7: auto-generated limitations."""

    partial: bool

    power: BenchReportCallTypePower
    """Section 2: the power statement (unique n, planning MDE, pre-registered margins)."""

    projection: BenchReportCallTypeProjection
    """Section 5: the honest projection (ESTIMATE only where trailing volume exists)."""

    status: str

    task_view: list[BenchReportCallTypeTaskViewItem]
    """Section 6: per-trace task view."""

    tier: str
    """The PLANNING verdict tier (planning language, never a verdict)."""

    trust_class: str | None
    """The PINNED composite trust class, never a live read.

    Known values: ``A``, ``B``, ``C``.
    """

    trust_statement: str | None

    verdicts: list[BenchReportCallTypeVerdict]
    """Section 4: interval-based verdicts, verbatim."""


class BenchReportCallTypeArm(BaseModel):
    """One arm headline row (report section 3)."""

    completeness: float | None

    composite_score: float | None

    cost_basis_label: str | None
    """`measured` only for the measured family; `estimated` otherwise.

    Known values: ``measured``, ``estimated``.
    """

    cost_evidence_id: str | None
    """The immutable CostEvidenceV2 id (source unity)."""

    cost_views: list[BenchReportCallTypeArmCostView]

    denominator: int

    is_incumbent: bool
    """The re-invoked incumbent arm — never a fictitious $0 row."""

    model: str

    observed_per_request_micro_usd: float | None

    observed_per_task_micro_usd: float | None

    p95_latency_ms: float | None

    provider: str

    quality_interval: BenchInterval | None
    """A decision interval, verbatim."""

    skip_reason: str | None

    skipped: bool

    token_components: dict[str, int] | None
    """Billed unit components (input/output/cached/reasoning/…) — never a universal efficiency unit.
    """

    uncertainty_micro_usd: float | None

    unit: str
    """The honest cost unit: $/task only with task proof.

    Known values: ``$/request``, ``$/task``.
    """

    usage_basis: str | None


class BenchReportCallTypeArmCostView(BaseModel):
    """A CostEvidenceV2 cost view, by basis."""

    per_unit_micro_usd: float | None
    """total ÷ denominator — the per-UNIT figure (µUSD)."""

    total_micro_usd: float | None
    """The all-arm total for the view (µUSD), or null."""

    view: str
    """The CostEvidenceV2 view.

    Known values: ``observed_eval_charge``, ``constant_rate_technical``, ``modeled_online_net``, ``marginal_cash``, ``invoice_reconciled``.
    """


class BenchDatasetCard(BaseModel):
    """Section 1: the frozen dataset card."""

    admitted_count: int
    """n admitted (captured − PII/empty)."""

    attestation: bool
    """Whether the audited low-confidence-PII attestation admitted otherwise-excluded items."""

    call_type_id: str
    """The call type this dataset is compiled for."""

    captured_count: int
    """n confirmed envelopes fed in."""

    cluster_count: int
    """The VERDICT-LEVEL inferential-cluster n — one cluster per independent task/trace, else per item identity: the SAME unit the deciding interval-based verdict uses. Powers the power plan; the SimHash near-duplicate group count is reported separately as near_dup_cluster_count.
    """

    dataset_hash: str
    """Content address — identical captures ⇒ identical hash."""

    exclusions: list[BenchDatasetExclusion]
    """Visible per-item exclusions."""

    item_count: int
    """n items in the frozen dataset (post ≤500 cap)."""

    near_dup_cluster_count: int | None = None
    """The SimHash near-DUPLICATE group count (masked-template redundancy) — a SEPARATE disclosure, NOT the plan n. Absent on legacy cards frozen before this field existed.
    """

    power_plan: BenchPowerPlan
    """The preregistered power plan — planning language, never a verdict."""

    shape: str
    """Request- or task-shaped overall.

    Known values: ``request``, ``task``.
    """

    staleness: BenchDatasetStaleness
    """Prior-run staleness disclosure."""

    strata: list[BenchDatasetStratum]
    """Per-stratum summaries + thin warnings."""

    task_count: int
    """Distinct task/trace ids present."""

    unique_count: int
    """n exact-dedup uniques (before the cap)."""


class BenchDatasetExclusion(BaseModel):
    """A dataset-card exclusion."""

    envelope_ids: list[str]
    """The confirmed envelope ids excluded together."""

    reason: str
    """Why the item(s) were excluded (visible per-item on the card).

    Known values: ``pii_low_confidence``, ``empty_content``, ``over_cap``.
    """


class BenchPowerPlan(BaseModel):
    """The preregistered power plan — planning language, never a verdict."""

    adequately_powered: bool
    """Power adequacy HINT (mde_pp ≤ margin_pp) — still never a verdict."""

    alpha: float
    """The significance level the plan assumed."""

    cluster_n: int
    """The VERDICT-LEVEL inferential-cluster n — the SAME unit the deciding interval-based verdict bootstraps (one cluster per task/trace, else per item identity), NOT the SimHash near-duplicate group count.
    """

    margin_pp: float
    """The preregistered non-inferiority margin Δ (pp)."""

    mde_pp: float
    """The minimum detectable effect (pp) — a PLANNING number, not a verdict."""

    power: float
    """The target power (e.g. 0.8)."""

    prior_quality_sd: float
    """The conservative-prior (or A/A) composite-quality SD."""

    required_clusters: int | None = None
    """The minimum verdict-level clusters this margin needs at the plan alpha/power (so "cap < required" is visible AT FREEZE) — a PLANNING number, never a gate (the margin is never loosened). Absent on legacy cards frozen before this field existed.
    """

    summary: str
    """Planning-language readout ("can detect ~Xpp at 80% power")."""


class BenchDatasetStaleness(BaseModel):
    """Prior-run staleness disclosure."""

    prior_run_count: int
    """Runs referencing this dataset_hash."""

    stale: bool
    """Whether the run count trips the staleness flag."""


class BenchDatasetStratum(BaseModel):
    """A dataset-card stratum summary."""

    frequency_weight: int
    """Frequency-weighted population share of the stratum (the shared population weight)."""

    key: str
    """The stratum key (length/lang/tools/feedback tuple)."""

    thin: bool
    """True when the stratum is under-powered (below the thin threshold)."""

    unique_count: int
    """Unique items in this stratum."""


class BenchReportCallTypeInversion(BaseModel):
    """Response shape ``BenchReportCallTypeInversion``."""

    candidate_model: str

    candidate_per_request_micro_usd: float

    candidate_per_task_micro_usd: float

    incumbent_model: str

    incumbent_per_request_micro_usd: float

    incumbent_per_task_micro_usd: float

    note: str


class BenchReportCallTypePower(BaseModel):
    """Section 2: the power statement (unique n, planning MDE, pre-registered margins)."""

    adequately_powered: bool

    alpha: float

    cluster_n: int

    cost_min_savings: float

    margin_pp: float

    margin_source: str
    """WHERE the margin came from (`run_spec` = pinned at enqueue)."""

    mde_pp: float

    power: float

    unique_n: int


class BenchReportCallTypeProjection(BaseModel):
    """Section 5: the honest projection (ESTIMATE only where trailing volume exists)."""

    available: bool

    basis: BenchReportCallTypeProjectionBasis

    candidate_model: str | None

    estimate_micro_usd_month: float | None

    per_unit_saving_micro_usd: float | None

    reason: str | None

    unit: str
    """Known values: ``$/request``, ``$/task``."""


class BenchReportCallTypeProjectionBasis(BaseModel):
    """Response shape ``BenchReportCallTypeProjectionBasis``."""

    calls: int

    input_tokens: int

    output_tokens: int


class BenchReportCallTypeTaskViewItem(BaseModel):
    """A per-trace task-view row (report section 6)."""

    candidate_passed: bool | None

    incumbent_passed: bool | None

    items_in_trace: int

    outcome_delta: float | None

    trace_id: str


class BenchReportCallTypeVerdict(BaseModel):
    """A candidate verdict, verbatim (report section 4)."""

    cost: str
    """Known values: ``pass``, ``fail``, ``inconclusive``."""

    cost_interval: BenchInterval
    """A decision interval, verbatim."""

    mde_pp: float
    """The MDE (pp) — a POWER DIAGNOSTIC, never the verdict."""

    model: str

    outcome_interval: BenchInterval | None
    """The folded first-party outcome interval."""

    overall: str
    """Known values: ``pass``, ``fail``, ``inconclusive``."""

    quality: str
    """Known values: ``pass``, ``fail``, ``inconclusive``."""

    quality_interval: BenchInterval
    """A decision interval, verbatim."""

    reasons: list[str]

    remediation: str | None
    """The named remediation for a keep/inconclusive verdict."""


class BenchReportExport(BaseModel):
    """The audited export links (JSON / Markdown / verifiable bundle)."""

    bundle_url: str
    """The independently verifiable evidence-bundle export path (`?format=bundle`)."""

    json_url: str
    """The JSON report export path (`?format=json`)."""

    markdown_url: str
    """The Markdown export path (`?format=md`)."""


class BenchReportReproducibility(BaseModel):
    """Section 8: the reproducibility appendix (spec/profile/evidence/decision ids, seeds, versions)."""

    cost_evidence_ids: list[str]

    dataset_hashes: list[str]

    decision_ids: list[str]

    execution_profile_hashes: list[str]

    run_spec_ids: list[str]

    seeds: list[float]

    versions: dict[str, str]


class BenchExpectationsParams(TypedDict, total=False):
    """ultrarouter Bench assertions attach request."""

    expectations: Required[list[BenchExpectationParams]]
    """The customer assertions to attach (validated against the closed vocabulary)."""


class BenchExpectationParams(TypedDict, total=False):
    """A customer Bench assertion input."""

    call_type: str
    """Scope the assertion to a call type id, or omit for the whole suite."""

    config: dict[str, Any]
    """The scorer config (required_fields / field / pattern+flags; a json_schema assertion may set closed:true to reject any leaf outside the pinned set); validated per kind.
    """

    item_content_hash: str
    """Narrow the assertion to a specific dataset item content hash."""

    kind: Required[str]
    """The assertion kind (json_schema/exact_field/regex_match/citation_substring)."""

    request_id: str
    """Narrow the assertion to a specific captured request id."""


class BenchExpectations(BaseModel):
    """ultrarouter Bench assertions attach result."""

    accepted: int
    """How many assertions validated + attached."""

    attached: list[BenchAttachedExpectation]
    """One row per input assertion (attached or rejected with a reason)."""

    object: str
    """Known values: ``bench_expectations``."""

    rejected: int
    """How many were rejected (invalid config/kind)."""

    suite: str
    """The bench suite slug."""

    suite_id: str
    """The bench suite id (`bs_…`)."""


class BenchAttachedExpectation(BaseModel):
    """An attached (or rejected) Bench assertion."""

    call_type: str | None
    """The scoped call type id, or null (suite-wide)."""

    created: bool
    """False when the identical assertion already existed (idempotent)."""

    hash: str
    """The content address of (kind + config)."""

    id: str
    """The assertion id (`bx_…`), or empty when rejected."""

    kind: str
    """The echoed assertion kind (may be an unknown kind when rejected)."""

    reason: str | None
    """The validation rejection reason, or null when valid."""

    valid: bool
    """Whether the assertion passed closed-vocabulary validation."""

    version: int
    """The per-suite monotonic version stamp (0 when rejected)."""


class BenchFreezeParams(TypedDict, total=False):
    """ultrarouter Bench dataset freeze request."""

    max_items: int
    """Optional per-call-type frozen-item cap (default 500; ≤ the hard ceiling of 5000 items, which bounds the O(n²) compile). Over-cap uniques are dropped keeping the highest frequency, recorded as `over_cap` exclusions. NO entitlement gate applies at freeze — the run-time free-tier shape cap remains the enforcement point.
    """


class BenchDatasetFreeze(BaseModel):
    """ultrarouter Bench dataset freeze result."""

    datasets: list[BenchDatasetFreezeDataset]
    """One immutable, content-addressed dataset + card per call type frozen."""

    object: str
    """Known values: ``bench_dataset_freeze``."""

    suite: str
    """The bench suite slug."""

    suite_id: str
    """The bench suite id (`bs_…`)."""

    warnings: list[BenchDatasetFreezeWarning] | None = None
    """Non-fatal freeze warnings — e.g. confirmed captures exist but 0 datasets froze because none carry an explicit call_type. Absent/empty when the freeze was clean.
    """


class BenchDatasetFreezeDataset(BaseModel):
    """A frozen per-call-type Bench dataset + its card + evaluator merge."""

    call_type_id: str
    """The call type this dataset was frozen for."""

    card: BenchDatasetCard
    """The immutable dataset card (qualified-evidence readiness — replaces raw counts)."""

    dataset_hash: str
    """Content address — identical captures ⇒ identical hash."""

    dataset_id: str
    """The immutable dataset id (`bd_…`)."""

    evaluator: BenchDatasetFreezeDatasetEvaluator
    """The freeze-time evaluator merge result for a call type."""


class BenchDatasetFreezeDatasetEvaluator(BaseModel):
    """The freeze-time evaluator merge result for a call type."""

    accepted_count: int

    applied: bool
    """Whether the merged suite was applied to the call type."""

    assertions: list[BenchDatasetFreezeDatasetEvaluatorAssertion]
    """Per-assertion accept/reject dispositions (never silent)."""

    call_type_id: str
    """The call type the evaluator was merged for."""

    judge_disabled: bool
    """Whether the merged suite retired the judge residue (the zero-judge path)."""

    judge_share: float

    not_applied_reason: str | None
    """Why the merged suite was not applied, else null."""

    programmatic_outcome_share: float

    rejected_count: int

    requalified: bool
    """The MANDATORY merged-suite mutation re-qualification (apply only when true)."""

    suite_hash: str | None
    """The merged evaluator suite content address."""

    trust_class: str
    """The composite trust class (A/B/C).

    Known values: ``A``, ``B``, ``C``.
    """


class BenchDatasetFreezeDatasetEvaluatorAssertion(BaseModel):
    """A freeze-time customer-assertion disposition."""

    accepted: bool
    """Whether the assertion passed qualification and was merged."""

    hash: str
    """The content address of (kind + config)."""

    index: int
    """The assertion position (a stable per-item handle)."""

    kind: str
    """The closed programmatic assertion kind.

    Known values: ``json_schema``, ``exact_field``, ``regex_match``, ``citation_substring``.
    """

    reason: str | None
    """The visible rejection reason (vacuous/contradicts_reference/…), or null."""

    scorer_id: str
    """The programmatic scorer id it compiles to."""


class BenchDatasetFreezeWarning(BaseModel):
    """A bench-freeze warning."""

    code: str
    """The machine-readable warning code.

    Known values: ``no_call_type_attribution``.
    """

    confirmed_captures: int
    """How many confirmed captures the warning concerns (e.g. unattributed captures)."""

    message: str
    """A human-readable explanation of the condition + the fix."""


class BenchRunParams(TypedDict, total=False):
    """ultrarouter Bench on-demand run trigger request."""

    baseline_run_id: str
    """The baseline run (`br_*`) to compare against; defaults to the suite’s pinned baseline."""

    call_types: list[str]
    """Restrict the fan-out to these frozen call-type ids (default: every runnable one)."""

    candidates: list[str]
    """Explicit challenger model ids (default: auto-selected from the catalog)."""

    compare: bool
    """COMPARE mode: run the CURRENT effective config as the single arm (the "candidate": the new prompt/pin/config) and gate it against a pinned baseline run — `candidates` are ignored.
    """

    cost_ceiling_usd: float
    """Absolute per-unit measured-cost ceiling (USD) — a breach FAILS the gate independent of quality. Omit for no ceiling.
    """

    dry_run: bool
    """When true: return the estimate + dispositions + allowance with NO reservation/dispatch. When false (default) and the paid-dispatch kill switch is ON, a real paired run is dispatched; when that kill switch is OFF (or unseeded ⇒ fail-closed), otherwise-valid paid shapes are labeled not_runnable/atomic_spend_guard_unavailable instead.
    """

    force: bool
    """Bench-only: skip the <14 d RunSpec-hash dedupe and always run fresh (audited)."""

    max_cost_usd: Required[float]
    """MANDATORY global umbrella reservation ceiling in USD across all accepted child runs. Live paid dispatch is gated by the platform paid-dispatch kill switch (default ON): when ON, omitting dry_run dispatches a real paired run within this ceiling; when OFF (or unseeded ⇒ fail-closed) live dispatch is refused with atomic_spend_guard_unavailable. dry_run always works.
    """

    max_output_tokens: int
    """Finite per-attempt output-token ceiling, pinned into the immutable RunSpec and used as the output component of reservation math (default 256; changing it is a new measurement epoch). It does not by itself bound provider input accounting or replace the atomic attempt guard.
    """

    mode: Literal["request", "task"]
    """Paired-runner mode: `request` (default) or `task` (whole-trace, only evidence that may claim $/task).
    """

    require_power: bool
    """Opt-in pre-spend power gate (default false): when true, an UNDERPOWERED call type (its power advisory `underpowered`) becomes `not_runnable(underpowered)` and is excluded from the estimate/reservation BEFORE any budget reserve. Advisory-only by default — the run proceeds.
    """

    selection_mode: Literal["selection", "noninferiority"]
    """Selection mode: `selection` (default; ranked exploratory evidence, NEVER a recommendation) or `noninferiority` (incumbent-paired, migrate-eligible).
    """


class BenchRunTrigger(BaseModel):
    """ultrarouter Bench on-demand run trigger result."""

    allowance: BenchAllowance
    """The workspace Bench allowance state."""

    bench_run_id: str | None
    """The umbrella `br_*` id (null on a dry_run)."""

    dispositions: list[BenchDisposition]
    """Per-call-type dispositions + estimate breakdown."""

    dry_run: bool
    """True when no reservation/dispatch happened (estimate only)."""

    entitlement: BenchEntitlement
    """The bench packaging entitlement (plan + free-tier caps + run-count usage)."""

    estimate_usd: float
    """Total pre-run estimate across runnable call types (USD)."""

    judge_worst_case_usd: float
    """The run-total CONSERVATIVE worst-case JUDGE-phase cost (USD) across judge-enabled call types — surfaced additively alongside estimate_usd (the two are never summed into one figure). 0 when every runnable call type is zero-judge / has no priced judge.
    """

    mode: str
    """Known values: ``request``, ``task``."""

    object: str
    """Known values: ``bench_run_trigger``."""

    selection_mode: str
    """Known values: ``selection``, ``noninferiority``."""

    suite: str
    """The bench suite slug."""


class BenchSuiteStatus(BaseModel):
    """ultrarouter Bench suite readiness meter."""

    call_types: list[BenchSuiteStatusCallType]
    """Per-call-type readiness rows."""

    capture: BenchSuiteStatusCapture
    """Workspace-wide capture health (confirmed/queued/failed/non_replayable)."""

    object: str
    """Known values: ``bench_suite_status``."""

    suite: str
    """The bench suite slug."""

    suite_id: str
    """The bench suite id (`bs_…`)."""

    total_captured: int
    """Total CONFIRMED (durable, replayable) items in the suite."""

    ttl_days: int
    """Capture TTL in days (1–90)."""


class BenchSuiteStatusCallType(BaseModel):
    """Per-call-type bench readiness."""

    call_type: str | None
    """The resolved call type id, or null (unattributed)."""

    captured: int
    """Current confirmed captures (PROVENANCE, never a verdict — the verdict is the power plan)."""

    new_since_freeze: int | None
    """Confirmed captures accrued since the last freeze (re-freeze to qualify), or null."""

    qualified: BenchSuiteStatusCallTypeQualified | None
    """The qualified-evidence readiness (latest frozen card), or null until frozen."""

    task_claim_blocked: bool
    """True when no trace coverage exists — `$/task` claims are blocked."""

    trace_coverage: float
    """Fraction of confirmed captures with a task/trace id (0 blocks task claims)."""

    trace_covered: int
    """Confirmed captures carrying a task/trace id."""

    trace_mean_confidence: float | None
    """Mean stored [0,1] confidence over covered captures, or null when none."""

    trace_source_mix: dict[str, int]
    """Confirmed captures per resolved trace source (explicit_trace/traceparent/… → count)."""


class BenchSuiteStatusCallTypeQualified(BaseModel):
    """The qualified-evidence readiness (latest frozen card), or null until frozen."""

    captured_at_freeze: int
    """Confirmed captures at the moment of the freeze."""

    card: BenchDatasetCard
    """The immutable dataset card (qualified-evidence readiness — replaces raw counts)."""

    dataset_hash: str
    """The latest frozen dataset content address."""

    frozen_at: str
    """When the dataset was frozen (ISO timestamp)."""


class BenchSuiteStatusCapture(BaseModel):
    """Workspace-wide capture health (confirmed/queued/failed/non_replayable)."""

    confirmed: int
    """Durable, replayable envelopes (persisted only — never over-claimed)."""

    failed: int
    """Captures that failed (DB/blob outage after retries, or stream-tee overflow)."""

    non_replayable: int
    """Refused captures (no consent / size ceiling) — shape metadata only, no body."""

    queued: int
    """Captures awaiting background persistence (not yet confirmed)."""


class CallTypeList(BaseModel):
    """Workspace call-type list (GET /v1/call-types)."""

    data: list[CallType]

    object: str
    """Known values: ``list``."""


class CallType(BaseModel):
    """A call type with its active config version."""

    config: CallTypeConfigVersion | None
    """The active config version, or null."""

    created_at: str

    current_config_version: int | None

    display_name: str

    id: str

    lifecycle_reason: str | None
    """The evidence reason for the last automatic lifecycle transition (null before the first)."""

    lifecycle_state: str
    """Audit Autopilot lifecycle state (observing | evaluator_building | benchmarkable | recommendable | canary | verified | held). ZERO serving authority.
    """

    lifecycle_transitioned_at: str | None
    """When the last lifecycle transition was applied (ISO 8601), or null."""

    object: str
    """Known values: ``call_type``."""

    slug: str

    source: str
    """`explicit` (caller slug) or `fingerprint` (automatically inferred from request shape)."""

    updated_at: str


class CallTypeConfigVersion(BaseModel):
    """One immutable call-type config version."""

    case_precedents_enabled: bool | None = None
    """Whether this version serves PER-REQUEST CASE PRECEDENTS into the learned data slot (default false).
    """

    compression_mode: str | None

    created_at: str

    fallbacks: list[str] | None

    learned_context_delivery: str | None = None
    """Learned-context delivery on this version (gateway_inject_after_stable_prefix | off).

    Known values: ``gateway_inject_after_stable_prefix``, ``off``.
    """

    model_pin: str | None

    provider_prefs: dict[str, Any] | None

    router_mode: str | None

    version: int


class CallTypeCreateParams(TypedDict, total=False):
    """Create a call type with an explicit slug (POST /v1/call-types)."""

    config: CallTypeConfigParams
    """Optional initial config version."""

    slug: Required[str]
    """The explicit call-type slug (workspace-unique)."""


class CallTypeConfigParams(TypedDict, total=False):
    """Call-type config body (the validated shape). On PATCH, an omitted field keeps its current value and an explicit null clears it."""

    case_precedents_enabled: bool
    """Whether the gateway serves PER-REQUEST CASE PRECEDENTS into the learned data slot for this call type — a CASE is a VIEW over the outcome ledger, retrieved fresh per request (contrastive corrected-failure + success exemplars, ≤ 300 tokens, never an instruction). Default false (the case path is inert; serving byte-identical). Turning this on by default for customers is gated on internal validation, not on this flag. Omitted ⇒ the current value is preserved.
    """

    compression_mode: Literal["off", "semantic_safe", "adaptive", "lossless", "auto"] | None
    """Compression safety tier: off (default, no model-visible rewrite), semantic_safe (deterministic, evidence-qualified) or adaptive (guarded pruning). The legacy lossless/auto values remain parseable for backward compatibility.
    """

    fallbacks: list[str] | None
    """Ordered fallback model ids (OpenRouter parity)."""

    learned_context_delivery: Literal["gateway_inject_after_stable_prefix", "off"]
    """Learned-context DELIVERY for this call type: gateway_inject_after_stable_prefix (default — the gateway injects the learned module after the stable prefix) or off (the gateway never injects; SDK/preflight consumers still resolve the module — off keeps the standing holdout and measurement intact, arms are still assigned and stamped). A FLIP starts a NEW learned_context epoch and invalidates any open confirmation (its baseline moved). "Inject at end" is DEFERRED (it returns behind this field once a confirmation has been run with it). Omitted ⇒ the current delivery is preserved.
    """

    model_pin: str | None
    """Pinned model id for this call type (the call-type layer of the config precedence chain: request > key defaults > call type > workspace defaults > system defaults).
    """

    provider_prefs: dict[str, Any] | None
    """OpenRouter-parity provider preferences object."""

    router_mode: Literal["pinned", "auto", "candidates", "off"] | None
    """Router mode for this call type."""

    self_improve_guardrails: SelfImproveGuardrailsParams
    """Autopilot guardrail config (the cost budget + enabled surfaces). Omitted ⇒ the current guardrails are preserved.
    """

    self_improve_mode: Literal["off", "assist", "autopilot"]
    """Self-improve mode: off (capture outcomes only), assist (default — propose/test/push passed improvements to your inbox), or autopilot (adopt passed improvements automatically within guardrails). Omitted ⇒ the current mode is preserved.
    """


class SelfImproveGuardrailsParams(TypedDict, total=False):
    """Autopilot guardrail config (the cost budget + enabled surfaces). Omitted ⇒ the current guardrails are preserved."""

    max_cost_per_success_micro_usd: int | None
    """Autopilot cost budget: the max cost per successful task (integer µUSD). Null (or omitted) ⇒ NO budget registered, which fails autopilot closed.
    """

    surfaces: list[Literal["knowledge_injection", "model_routing", "hosted_prompt"]]
    """The surfaces enabled for autopilot. Only knowledge_injection is wired today; model_routing and hosted_prompt are accepted but refuse auto-adopt until wired.
    """


class EpisodeMemoryStatus(BaseModel):
    """A call type’s episode-memory status."""

    call_type_id: str

    config_version: int | None

    enabled: bool
    """Whether the active config version carries a readable EXPLICIT setting (false for the explicit-off marker, an unreadable value, or no setting).
    """

    lab_authorised: bool
    """The workspace’s staff-granted lab authorisation (`flywheel.episode_memory_lab`)."""

    memory: EpisodeMemoryStatusMemory
    """A content-addressed preview of the memory the setting (or `?as_of`) would serve now."""

    object: str
    """Known values: ``episode_memory``."""

    playbook: EpisodeMemoryStatusPlaybook
    """The latest learned playbook of the source call type (version null when none)."""

    setting: EpisodeMemoryStatusSetting | None
    """The frozen episode-memory setting on a call-type config version."""

    source: str
    """The per-call-type state — `explicit` (a readable setting is stored), `off` (an explicit opt-out, or an unreadable value fail-closed), or `default` (nothing stored — the call type follows the workspace default `flywheel.episode_memory_default`).

    Known values: ``explicit``, ``default``, ``off``.
    """

    traces: EpisodeMemoryStatusTraces
    """The call type’s episode-trace accounting (counts only)."""


class EpisodeMemoryStatusMemory(BaseModel):
    """A content-addressed preview of the memory the setting (or `?as_of`) would serve now."""

    as_of: str | None
    """The pin the digest was taken under (ISO), or null = live."""

    digest: str
    """`emd1_…` — a content address of the ordered eligible set (stable for a frozen checkpoint)."""

    source_call_type_id: str
    """The call type whose verified episodes would be served."""

    verified_pass: int
    """Eligible verified pass episodes of the source (verified_at ≤ pin, or all when live)."""


class EpisodeMemoryStatusPlaybook(BaseModel):
    """The latest learned playbook of the source call type (version null when none)."""

    active_lessons: int
    """The active-lesson count of the latest version."""

    cohort_size: int
    """The sealed cohort size of the latest version."""

    digest: str | None
    """The latest version digest (`epb1_…`), or null."""

    source_call_type_id: str
    """The call type whose playbook is reported."""

    version: int | None
    """The latest version number, or null when none."""

    version_id: str | None
    """The latest version row id (`epb_…`), or null."""


class EpisodeMemoryStatusSetting(BaseModel):
    """The frozen episode-memory setting on a call-type config version."""

    as_of: str | None
    """A frozen memory version (ISO), or null for live memory."""

    dedupe: bool | None = None
    """Present only when true."""

    framing: str | None = None
    """Present only when not the default `reuse`.

    Known values: ``reuse``, ``adapt``.
    """

    k: int

    lessons: EpisodeMemoryStatusSettingLessons | None = None
    """Present only when the learned-playbook mode is not `off`."""

    max_chars_per_episode: int

    min_similarity: float | None = None
    """Present only when set (not 0)."""

    observation_chars: int

    prefer_shorter: bool | None = None
    """Present only when true."""

    record: bool

    retrieval_key: str | None = None
    """Present only when not the default `first_user_message`.

    Known values: ``first_user_message``, ``content_lines``.
    """

    rule_version: str
    """`epm1` — the pure rule version a stored setting is parsed under."""

    self_serve: bool | None = None
    """Present (true) only when learning was enabled self-serve through `POST /v1/call-types/{id}/learning/enable` — a published version is then a candidate. In evaluate mode it receives a randomized share of eligible episodes before the policy can make it the active version.
    """

    source_call_type_id: str | None


class EpisodeMemoryStatusSettingLessons(BaseModel):
    """Present only when the learned-playbook mode is not `off`."""

    distiller_model: str | None

    k: int

    mode: str
    """Known values: ``off``, ``only``, ``with_precedents``."""

    recipe: EpisodeMemoryStatusSettingLessonsRecipe | None = None
    """Present only for a non-legacy learner recipe (absent ⇒ the legacy learner)."""

    version_id: str | None


class EpisodeMemoryStatusSettingLessonsRecipe(BaseModel):
    """Present only for a non-legacy learner recipe (absent ⇒ the legacy learner)."""

    generation: str
    """Known values: ``bundled``, ``atomic``."""

    observations: str
    """Known values: ``legacy``, ``elo2``."""

    validator: str
    """Known values: ``elv1``, ``elv2``."""


class EpisodeMemoryStatusTraces(BaseModel):
    """The call type’s episode-trace accounting (counts only)."""

    fail: int

    latest_verified_at: str | None
    """The newest pass verification instant (ISO), or null."""

    pass_: int = Field(..., alias="pass")
    """Episodes a whole-episode teaching outcome verified as passing."""

    total: int

    unverified: int
    """Episodes still recording (no verdict yet)."""


class EpisodeMemoryDisableResult(BaseModel):
    """The result of disabling episode memory (model-only serving within one 5 s window)."""

    call_type_id: str

    changed: bool
    """False when memory was already off (nothing written — idempotent)."""

    config_version: int | None

    object: str
    """Known values: ``episode_memory_disable``."""

    previous: EpisodeMemoryStatusSetting | None
    """The frozen episode-memory setting on a call-type config version."""


class EpisodeMemoryEnableParams(TypedDict, total=False):
    """Enable episode memory for a call type (the lab-authorised, pre-evidence activation)."""

    as_of: str | None
    """Serve only episodes verified at or before this instant (ISO) — a frozen memory version; null = live.
    """

    dedupe: bool
    """Serve at most one of near-identical precedents (default false)."""

    framing: Literal["reuse", "adapt"]
    """How served precedents are framed: `reuse` (default) invites reusing their calls; `adapt` presents them as evidence of how the tools behave, not values to copy.
    """

    k: int
    """Precedents served per episode (1..5; default 3)."""

    lessons: EpisodeMemoryEnableParamsLessons
    """The learned-playbook block (absent ⇒ lessons off, byte-identical)."""

    max_chars_per_episode: int
    """Characters of actions shown per precedent (500..8000; default 3500)."""

    min_similarity: float
    """Serve only precedents at least this similar to the task (0..1; default 0, no floor)."""

    observation_chars: int
    """Characters of each kept action’s observation shown under it (0 = actions only; default 0)."""

    prefer_shorter: bool
    """Among near-equally similar precedents, serve the shortest verified solutions first (default false).
    """

    record: bool
    """Record this call type’s episodes so outcomes can verify them (default true); false = serve only.
    """

    retrieval_key: Literal["first_user_message", "content_lines"]
    """What precedents are ranked on: the whole first user message (default) or its content lines — without lines carrying a personal identifier or a timestamp.
    """

    source_call_type_id: str | None
    """The call type whose verified episodes are served (same workspace); null = this call type."""


class EpisodeMemoryEnableParamsLessons(TypedDict, total=False):
    """The learned-playbook block (absent ⇒ lessons off, byte-identical)."""

    distiller_model: str | None
    """The model the distiller uses; null = the call type’s own model."""

    k: int
    """Lessons served per episode (1..20; default 8)."""

    mode: Required[Literal["off", "only", "with_precedents"]]
    """Serve a distilled playbook — `off` (default, byte-identical), `only` (lessons, no precedents), `with_precedents` (lessons before precedents).
    """

    recipe: LearnerRecipeParams
    """The learner recipe the distiller runs (absent ⇒ the legacy learner)."""

    version_id: str | None
    """A frozen-arm pin: serve exactly this playbook version (`epb_…`) of the source call type; null = the latest.
    """


class LearnerRecipeParams(TypedDict, total=False):
    """The learner recipe the distiller runs (absent ⇒ the legacy learner)."""

    generation: Literal["bundled", "atomic"]
    """Lesson generation: `bundled` (legacy, the default) or `atomic` (one complete rule per item with conditions, exceptions and required tools; never clipped).
    """

    observations: Literal["legacy", "elo2"]
    """Observation selection: `legacy` (the default) or `elo2` (error→correction transitions, passed-case results and labelled user turns at the same total budget, with measured omissions).
    """

    validator: Literal["elv1", "elv2"]
    """Lesson admission: `elv1` (legacy literal rule, the default) or `elv2` (provenance-aware: evidence support + value handling, documented constants scoped to their tool).
    """


class EpisodeMemoryEnableResult(BaseModel):
    """The result of enabling episode memory (a refusal is a named HTTP error, never a 200)."""

    call_type_id: str

    config_version: int
    """The new config version carrying the setting."""

    enabled: bool
    """Known values: ``True``."""

    object: str
    """Known values: ``episode_memory_enable``."""

    previous: EpisodeMemoryStatusSetting | None
    """The setting this one replaced (null when off)."""

    setting: EpisodeMemoryStatusSetting
    """The frozen episode-memory setting on a call-type config version."""


class EvalRunList(BaseModel):
    """A call type's eval runs, each exposing its immutable RunSpec."""

    data: list[EvalRun]

    object: str
    """Known values: ``list``."""


class EvalRun(BaseModel):
    """One eval run + its RunSpec + candidate summaries."""

    candidates: list[EvalRunCandidate]

    created_at: str

    finished_at: str | None

    id: str
    """The eval run id (`evr_…`)."""

    item_count: int

    judge: EvalRunJudge
    """Judge cascade bookkeeping."""

    run_spec: EvalRunSpec | None
    """The immutable RunSpec pinning this run; null on legacy runs. A run whose stored spec FAILED its content-address integrity check renders as the integrity-refused stub (`integrity_refused: true` + `tamper_class`), NEVER as authoritative evidence.
    """

    stage: str

    status: str

    trigger: str


class EvalRunCandidate(BaseModel):
    """A candidate aggregate on an eval run."""

    composite_score: float | None

    cost_evidence_id: str | None
    """This arm’s immutable cost-evidence record id (the incumbent arm carries one too now that it is re-invoked + charged); null when the arm was skipped or on a legacy run.
    """

    is_incumbent: bool

    judge_score: float | None

    model: str

    passed: bool | None

    provider: str

    skip_reason: str | None

    skipped: bool

    usage_basis: str | None
    """The arm’s folded usage basis (`provider_reported` … `estimated`)."""


class EvalRunJudge(BaseModel):
    """Judge cascade bookkeeping."""

    escalated_pairs: int

    escalation_rate: float

    judge_cost_usd: float

    judged_pairs: int

    tier_a_model: str | None

    tier_b_model: str | None


class EvalRunSpec(BaseModel):
    """The immutable RunSpec pinning this run; null on legacy runs. A run whose stored spec FAILED its content-address integrity check renders as the integrity-refused stub (`integrity_refused: true` + `tamper_class`), NEVER as authoritative evidence."""

    billing_assumptions: str | None = None

    candidates: list[EvalRunSpecCandidate] | None = None

    cost_min_savings: float | None = None
    """The pre-registered COST BAR: the minimum per-item cost-savings fraction a candidate must clear for its cost gate to pass, SNAPSHOTTED at enqueue. The verdict reads THIS pinned value, never the live config. Null on pre-v3 legacy specs (the cost bar arrived at RunSpec v3).
    """

    hypothesis: EvalRunSpecHypothesis | None = None

    incumbent: EvalRunSpecCandidate | None = None
    """A resolved offer identity + price snapshot (the alias resolved at enqueue)."""

    integrity_refused: bool
    """Always false on a verified RunSpec (the integrity-refused stub carries true)."""

    item_count: int | None = None
    """The number of frozen golden items."""

    margin_pp: float | None = None
    """The pre-registered non-inferiority margin Δ (pp)."""

    population_weights: str | None = None

    profile: EvalRunSpecProfile | None = None
    """The immutable ExecutionProfile."""

    profile_hash: str
    """The ExecutionProfile content hash."""

    run_spec_id: str
    """The immutable RunSpec id (`rspec_…`)."""

    seed: int | None = None
    """The deterministic seed pinned into the run."""

    spec_hash: str
    """The run-spec content hash (the dedupe key)."""

    spec_version: int | None = None

    stage: str | None = None

    task_clusters: str | None = None

    tamper_class: str | None = None
    """The machine-readable observed drift: `spec_version` (nulled/lowered specVersion) | `hash_mismatch` (a pinned component was edited) | `malformed` (a structurally broken spec — a nulled evaluator suite / deleted items / deleted candidates / a non-object spec).
    """


class EvalRunSpecCandidate(BaseModel):
    """A resolved offer identity + price snapshot (the alias resolved at enqueue)."""

    alias: str
    """The requested logical model id (the mutable alias)."""

    custom: bool
    """Whether this is a workspace custom-provider offer."""

    input_micro_usd_per_1m: float
    """Input price snapshot (micro-USD / 1M tokens)."""

    model: str
    """The resolved logical model id."""

    output_micro_usd_per_1m: float
    """Output price snapshot (micro-USD / 1M tokens)."""

    provider: str
    """The serving provider slug."""

    provider_id: str
    """The concrete versioned provider row id."""


class EvalRunSpecHypothesis(BaseModel):
    """Response shape ``EvalRunSpecHypothesis``."""

    cost_min_savings: float | None
    """The pinned cost-savings bar inside the pre-registered decision hypothesis. Null on pre-v3 legacy specs (the cost bar arrived at RunSpec v3).
    """

    kind: str

    latency_slo_ms: float | None
    """The pinned latency SLO (ms) snapshotted at enqueue from the eval config `latency_slo_ms`. Null = the latency gate is off / a legacy spec that predates this field.
    """

    margin_pp: float

    quality_floor: float | None
    """The pinned EMISSION quality floor snapshotted at enqueue from the eval config `recommendation_quality_floor`. Null = not configured (the emission default applies) / a legacy spec that predates this field.
    """


class EvalRunSpecProfile(BaseModel):
    """The immutable ExecutionProfile."""

    batch_policy: str

    cache_policy: str

    cee_schema_version: str

    compression_policy: str

    context_policy: str

    evaluator_suite: EvalRunSpecProfileEvaluatorSuite
    """The pinned evaluator suite."""

    fallback_policy: str

    harness_version: str

    mode: str
    """Paired execution mode: `request` (paired counterfactual) or `task`."""

    parameters: dict[str, Any]

    prompt_template: str

    retry_policy: str

    routing_policy: str

    runner_mode: str

    service_tier: str

    task_outcome_adapter: str

    tools: str


class EvalRunSpecProfileEvaluatorSuite(BaseModel):
    """The pinned evaluator suite."""

    composite_margin: float

    contract_digest: str | None
    """The evaluator-contract content digest backing the suite qualification (activation barrier); null on a legacy RunSpec or when not yet available.
    """

    embedding_model: str | None

    family: str

    judge: EvalRunSpecProfileEvaluatorSuiteJudge
    """The pinned judge suite."""

    judge_disabled: bool | None
    """Whether the pinned run retires the secondary judge phase; null means a legacy v1-v3 RunSpec did not pin this decision.
    """

    judge_dominant: bool | None
    """Whether the pinned evaluator suite is judge-dominant (its deterministic tiers do not cover the applicable risks); a judge-dominant ruler can never certify a migration. Null on a legacy RunSpec that predates this field or when no persisted suite matched at enqueue.
    """

    qualification_provenance: dict[str, Any] | None
    """The evaluator-suite qualification provenance (activation barrier); null on a legacy RunSpec or when not yet available.
    """

    scorer_instances: list[EvalRunSpecProfileEvaluatorSuiteScorerInstance] | None
    """The pinned per-scorer INSTANCE ruler the run grades on; null on a legacy (v1-v4) RunSpec or a non-instance suite.
    """

    scorers: list[str]

    suite_hash: str | None
    """Content address of the compiled evaluator suite; null for legacy or non-compiler-authored suites.
    """

    weights: dict[str, float]


class EvalRunSpecProfileEvaluatorSuiteJudge(BaseModel):
    """The pinned judge suite."""

    length_penalty_enabled: bool

    panel: bool

    panel_models: list[str]

    pass_threshold: float

    prompt_version: str
    """The judge-prompt template version pinned into the run."""

    rubric_family: str | None
    """The pinned effective judge-rubric family the judge phase grades on; null on a legacy (v1-v4) RunSpec that pinned no family and falls back to the live rubric.
    """

    tier_a_model: str

    tier_b_model: str

    weight: float


class EvalRunSpecProfileEvaluatorSuiteScorerInstance(BaseModel):
    """A pinned scorer instance in the evaluator ruler."""

    config: dict[str, Any]
    """The instance `scorer_config` (may be empty)."""

    hard: bool
    """Whether a failure on this instance HARD-fails the candidate on that item."""

    id: str
    """The scorer id backing this instance."""

    key: str
    """The stable instance address: the scorer id, or `id#<hash>` when configured."""

    weight: float
    """The instance relative composite weight (the composite normalizes)."""


class EnqueueEvalParams(TypedDict, total=False):
    """Optional manual-eval trigger body (selects the eval runner mode)."""

    mode: Literal["request", "task"]
    """Eval runner mode: request (default) or task (whole-trace, $/task evidence)."""


class EnqueueEvalResponse(BaseModel):
    """The manual-eval trigger result: the enqueued run (202) or a documented no-op (200)."""

    candidate_count: int | None = None
    """The number of pinned candidate offers selected for this run."""

    enqueued: bool

    object: str
    """Known values: ``eval_run``."""

    run_id: str | None = None
    """The enqueued eval run id (`evr_…`)."""

    deduped: bool | None = None
    """True when the no-op is a dedupe onto a fresh identical run within the window."""

    prior_run_id: str | None = None
    """The run this request DEDUPED ONTO (`evr_…`) — present only on a dedupe, read through the tenant-scoped reader (never another workspace’s run).
    """

    reason: str | None = None
    """The documented no-op reason.

    Known values: ``no_golden_set``, ``no_candidates``, ``no_incumbent``, ``not_relevant``, ``deduped``, ``auto_eval_disabled``, ``no_op``.
    """

    status: str | None = None
    """The prior run’s current status (`queued`|`running`|`scored`|`failed`) — present only on a dedupe.
    """

    trigger: str | None = None
    """The prior run’s trigger (e.g. `manual`, `model.release`) — present only on a dedupe."""


class LearningStatus(BaseModel):
    """A call type’s learning status."""

    active_version: LearningVersionRef | None
    """The incumbent served outside an evaluation."""

    budget: LearningStatusBudget

    call_type_id: str

    config_version: int | None

    enabled: bool
    """Lessons are switched on for the call type."""

    evaluation: LearningEvaluation | None
    """The RUNNING evaluation, if any."""

    evidence: LearningStatusEvidence
    """Evidence arrived vs verified vs incorporated vs pending."""

    governed: bool
    """Uses a configured promotion policy. In evaluate mode, candidates receive a randomized share of eligible episodes before any active-version change.
    """

    last_evaluation: LearningEvaluation | None
    """The newest evaluation (any decision)."""

    latest_candidate: LearningVersionRef | None

    object: str
    """Known values: ``learning``."""

    outcome_receipts: LearningStatusOutcomeReceipts
    """Outcome receipts (`POST /v1/requests/{id}/outcomes`) attributed to this call type’s requests, by state: a receipt counts once its request or its episode has been recorded for the call type. Settled receipts are counted until they are purged (30 days).
    """

    paused: bool

    promotion: LearningPromotionPolicy | None
    """The promotion policy (null for an ungoverned study learner — its latest version serves)."""

    reason: str
    """A bounded code explaining the state."""

    recipe: LearningStatusRecipe | None
    """The learner recipe the next reflection runs, read from the call type’s episode-memory setting (the one place it lives); null when the call type has no explicit setting.
    """

    reflection: LearningStatusReflection

    self_serve: bool
    """Enabled through this API (not a staff-granted study)."""

    state: str
    """`collecting` (enabled, waiting for evidence), `learning` (a reflection is due or an evaluation runs), `paused`, `disabled` (the kill switch), `unavailable` (consent, provider or repeated failures), `quota_exhausted` / `budget_exhausted` (refused for resources — retried with backoff), `off`.

    Known values: ``off``, ``collecting``, ``learning``, ``paused``, ``disabled``, ``unavailable``, ``quota_exhausted``, ``budget_exhausted``.
    """

    usage: LearningStatusUsage
    """Subscription / token usage, recorded separately from cash."""


class LearningVersionRef(BaseModel):
    """The incumbent served outside an evaluation."""

    active_lessons: int

    created_at: str
    """ISO 8601 instant."""

    digest: str

    id: str

    state: str
    """`candidate` (published, waiting), `evaluating`, `active` (served outside an evaluation), `retired` (replaced), `rejected` (lost / stopped / rejected by an owner), `superseded` (a newer candidate, or identical to the active version).

    Known values: ``candidate``, ``evaluating``, ``active``, ``retired``, ``rejected``, ``superseded``.
    """

    version: int


class LearningStatusBudget(BaseModel):
    """Response shape ``LearningStatusBudget``."""

    consecutive_refusals: int

    failure_ceiling: int

    failures_since_reset: int

    last_refusal_at: str | None
    """ISO 8601 instant."""

    state: str
    """Known values: ``ok``, ``quota_exhausted``, ``budget_exhausted``."""


class LearningEvaluation(BaseModel):
    """A prospective randomized evaluation of a candidate against the incumbent."""

    arms: LearningEvaluationArms

    call_type_id: str

    candidate_version_id: str

    decided_at: str | None
    """ISO 8601 instant."""

    decided_by: LearningEvaluationDecidedBy | None

    decision: str
    """Every decision except `promoted` keeps the incumbent.

    Known values: ``running``, ``promoted``, ``retained``, ``inconclusive``, ``rejected``, ``stopped_budget``, ``stopped_manual``.
    """

    decision_reason: str

    difference: LearningEvaluationDifference | None
    """candidate − incumbent success (a fraction) with one-sided bounds at the frozen alpha; null until both arms have a verified episode.
    """

    id: str
    """`lev_…`"""

    incumbent_version_id: str | None
    """Null: the candidate is compared with serving no lessons."""

    object: str
    """Known values: ``learning_evaluation``."""

    rule: LearningEvaluationRule | None
    """The decision rule frozen when the evaluation started. lpr2 selects episodes before inspecting their outcomes, freezes one cohort, and makes one decision only from complete selected outcomes or the fixed deadline.
    """

    rule_hash: str
    """`lrh1_…` content address of the frozen rule."""

    started_at: str
    """ISO 8601 instant."""


class LearningEvaluationArms(BaseModel):
    """Response shape ``LearningEvaluationArms``."""

    candidate: LearningEvaluationArm

    incumbent: LearningEvaluationArm


class LearningEvaluationArm(BaseModel):
    """Response shape ``LearningEvaluationArm``."""

    cost_micro_usd: int | None
    """Summed request cost of verified episodes within the selected cohort (cost objective only)."""

    mean_cost_micro_usd: float | None

    pass_: int = Field(..., alias="pass")

    success_rate: float | None
    """Descriptive pass / verified rate. Under lpr2 a promotion decision waits for complete outcomes in the frozen cohort.
    """

    unknown: int
    """Selected episodes without an eligible verified outcome, including reports after the fixed deadline. Under lpr2 they remain in the frozen cohort and block promotion; missing outcomes at the fixed deadline leave the incumbent active. Historical lpr1 evaluations excluded and counted unknown outcomes.
    """

    verified: int
    """Episodes with a verified teaching outcome."""


class LearningEvaluationDecidedBy(BaseModel):
    """Response shape ``LearningEvaluationDecidedBy``."""

    id: str | None

    type: str
    """Known values: ``system``, ``user``, ``api_key``."""


class LearningEvaluationDifference(BaseModel):
    """candidate − incumbent success (a fraction) with one-sided bounds at the frozen alpha; null until both arms have a verified episode."""

    lower: float

    point: float

    upper: float


class LearningEvaluationRule(BaseModel):
    """The decision rule frozen when the evaluation started. lpr2 selects episodes before inspecting their outcomes, freezes one cohort, and makes one decision only from complete selected outcomes or the fixed deadline."""

    alpha_one_sided: float

    candidate_share: float

    interval: str
    """`newcombe_hybrid_score`."""

    max_duration_hours: int

    max_verified_per_arm: int

    min_effect_pp: float

    min_verified_per_arm: int

    noninferiority_margin_pp: float

    objective: str
    """`success`: a higher whole-task success rate (the one-sided lower bound of the difference > 0 and the point difference ≥ `min_effect_pp`). `cost_noninferior`: a lower mean cost per episode with success not worse than the incumbent by more than `noninferiority_margin_pp`.

    Known values: ``success``, ``cost_noninferior``.
    """

    outcome_source: str
    """`verified_teaching_episode`."""

    rule_version: str
    """lpr2 freezes enrollment before waiting for outcomes; lpr1 identifies historical verified-only rules.
    """


class LearningStatusEvidence(BaseModel):
    """Evidence arrived vs verified vs incorporated vs pending."""

    backlog: int
    """Verified, not yet reflected over."""

    consumed: int
    """Verified episodes the learner has reflected over (its working line)."""

    incorporated_active: int
    """Verified episodes in the ACTIVE version’s line — arrived is not incorporated."""

    latest_verified_at: str | None
    """ISO 8601 instant."""

    pending_reflection: int

    recorded: int
    """Episodes recorded."""

    unknown: int
    """Recorded without a verdict — never counted as success or failure."""

    verified: int

    verified_fail: int

    verified_pass: int


class LearningStatusOutcomeReceipts(BaseModel):
    """Outcome receipts (`POST /v1/requests/{id}/outcomes`) attributed to this call type’s requests, by state: a receipt counts once its request or its episode has been recorded for the call type. Settled receipts are counted until they are purged (30 days)."""

    applied: int
    """Recorded against the request."""

    episode_pending: int
    """Applied teaching outcomes still waiting for their episode to be recorded."""

    expired: int
    """The request was never recorded within the receipt’s time limit."""

    failed: int
    """Given up after repeated database errors while applying."""

    pending: int
    """Accepted, waiting for the request to be recorded."""

    rejected: int
    """Refused (validation or conflict)."""


class LearningPromotionPolicy(BaseModel):
    """The promotion policy. Defaults: evaluate / success / enrollment thresholds 30–200 episodes per arm / one-sided alpha 0.05 / 0 pp minimum effect / 5 pp margin / 0.5 candidate share / 720 h. Changeable before an evaluation starts; a running evaluation keeps the rule it froze."""

    alpha: float
    """One-sided significance level of the interval on the difference (default 0.05)."""

    candidate_share: float
    """The share of NEW enrolled episodes assigned the candidate while enrollment is open (default 0.5). After enrollment closes, new episodes use the active version while selected episodes finish.
    """

    max_duration_hours: int
    """The fixed deadline from evaluation start, including time to receive selected outcomes (default 720). Incomplete evidence cannot promote a candidate; the deadline never resets.
    """

    max_verified_per_arm: int
    """Compatibility field name. Under lpr2, enrollment also closes when EITHER arm reaches this many enrolled episodes; each frozen arm contains at most this many (default 200).
    """

    min_effect_pp: float
    """`success`: the minimum point improvement in percentage points (default 0)."""

    min_verified_per_arm: int
    """Compatibility field name. Under lpr2, enrollment closes when BOTH arms have this many enrolled episodes (default 30); the selected episodes are then frozen and their verified outcomes are awaited.
    """

    mode: str
    """`evaluate`: a candidate must win a prospective randomized evaluation against the incumbent under a rule frozen when the evaluation starts; it serves a randomized share of eligible episodes during that comparison. `manual`: a candidate waits for an owner/admin promote or reject. `immediate`: publication is activation (the legacy behaviour).

    Known values: ``evaluate``, ``manual``, ``immediate``.
    """

    noninferiority_margin_pp: float
    """`cost_noninferior`: the success non-inferiority margin in percentage points (default 5)."""

    objective: str
    """`success`: a higher whole-task success rate (the one-sided lower bound of the difference > 0 and the point difference ≥ `min_effect_pp`). `cost_noninferior`: a lower mean cost per episode with success not worse than the incumbent by more than `noninferiority_margin_pp`.

    Known values: ``success``, ``cost_noninferior``.
    """


class LearningStatusRecipe(BaseModel):
    """The learner recipe the next reflection runs, read from the call type’s episode-memory setting (the one place it lives); null when the call type has no explicit setting."""

    generation: str
    """Known values: ``bundled``, ``atomic``."""

    legacy: bool
    """All three are the legacy values (the original learner)."""

    observations: str
    """Known values: ``legacy``, ``elo2``."""

    validator: str
    """Known values: ``elv1``, ``elv2``."""


class LearningStatusReflection(BaseModel):
    """Response shape ``LearningStatusReflection``."""

    last_attempt_at: str | None
    """ISO 8601 instant."""

    last_attempt_reason: str | None

    last_attempt_status: str | None

    last_published_at: str | None
    """ISO 8601 instant."""

    model: str | None

    next: LearningStatusReflectionNext
    """Whether the next server reflection scan will reflect, and why (not)."""

    provider: LearningStatusReflectionProvider


class LearningStatusReflectionNext(BaseModel):
    """Whether the next server reflection scan will reflect, and why (not)."""

    idle_minutes: int

    min_episodes: int

    reason: str

    retry_at: str | None
    """ISO 8601 instant."""

    will_run: bool


class LearningStatusReflectionProvider(BaseModel):
    """Response shape ``LearningStatusReflectionProvider``."""

    available: bool

    ownership: str | None
    """Known values: ``custom``, ``byok``, ``platform``."""

    provider_slug: str | None

    reason: str | None
    """Why it is unavailable: `no_reflection_model`, `no_offer`, `platform_offer_only`, `no_workspace_key`, `model_denied_by_policy`.
    """


class LearningStatusUsage(BaseModel):
    """Subscription / token usage, recorded separately from cash."""

    cash_micro_usd: int

    failed_calls: int

    input_tokens: int

    output_tokens: int

    reflections: int


class LearningControl(BaseModel):
    """The result of a learning control."""

    action: str
    """Known values: ``enable``, ``pause``, ``resume``, ``disable``, ``rollback``, ``promote``, ``reject``.
    """

    call_type_id: str

    changed: bool
    """False when the control was already in effect (idempotent)."""

    learning: LearningStatus
    """A call type’s learning status."""

    object: str
    """Known values: ``learning_control``."""

    stopped_evaluation_id: str | None
    """A running evaluation the control stopped (`stopped_manual`)."""

    version_id: str | None
    """The version a rollback / promote / reject acted on."""


class LearningEnableParams(TypedDict, total=False):
    """Enable learning for a call type (owner/admin session or a `config:write` key)."""

    lessons_k: int
    """Lessons served per episode (1..20; default 8)."""

    lessons_mode: Literal["only", "with_precedents"]
    """`only` (default): serve the learned lessons; `with_precedents`: lessons first, then similar verified past episodes.
    """

    promotion: LearningPromotionParams
    """Promotion-policy changes, merged over the current policy (or the defaults)."""

    recipe: LearnerRecipeParams
    """The learner recipe the reflection runs — its validator, lesson generation and observation selection, each optional (an absent field is the legacy value). Stored on the call type’s episode-memory setting, the ONE place the recipe lives. Omitted: the call type keeps its current recipe (the legacy learner when it has none).
    """

    reflection_model: Required[str]
    """The model the learner reflects with. It must resolve to a WORKSPACE-OWNED offer — one of the workspace’s custom providers, or a catalog provider the workspace stored its own key for. A platform-keyed model is refused; there is no paid fallback.
    """


class LearningPromotionParams(TypedDict, total=False):
    """Promotion-policy changes, merged over the current policy (or the defaults)."""

    alpha: float
    """One-sided significance level of the interval on the difference (default 0.05)."""

    candidate_share: float
    """The share of NEW enrolled episodes assigned the candidate while enrollment is open (default 0.5). After enrollment closes, new episodes use the active version while selected episodes finish.
    """

    max_duration_hours: int
    """The fixed deadline from evaluation start, including time to receive selected outcomes (default 720). Incomplete evidence cannot promote a candidate; the deadline never resets.
    """

    max_verified_per_arm: int
    """Compatibility field name. Under lpr2, enrollment also closes when EITHER arm reaches this many enrolled episodes; each frozen arm contains at most this many (default 200).
    """

    min_effect_pp: float
    """`success`: the minimum point improvement in percentage points (default 0)."""

    min_verified_per_arm: int
    """Compatibility field name. Under lpr2, enrollment closes when BOTH arms have this many enrolled episodes (default 30); the selected episodes are then frozen and their verified outcomes are awaited.
    """

    mode: Literal["evaluate", "manual", "immediate"]
    """`evaluate`: a candidate must win a prospective randomized evaluation against the incumbent under a rule frozen when the evaluation starts; it serves a randomized share of eligible episodes during that comparison. `manual`: a candidate waits for an owner/admin promote or reject. `immediate`: publication is activation (the legacy behaviour).
    """

    noninferiority_margin_pp: float
    """`cost_noninferior`: the success non-inferiority margin in percentage points (default 5)."""

    objective: Literal["success", "cost_noninferior"]
    """`success`: a higher whole-task success rate (the one-sided lower bound of the difference > 0 and the point difference ≥ `min_effect_pp`). `cost_noninferior`: a lower mean cost per episode with success not worse than the incumbent by more than `noninferiority_margin_pp`.
    """


class LearningEvaluationList(BaseModel):
    """The evaluations, newest first."""

    data: list[LearningEvaluation]

    object: str
    """Known values: ``list``."""


class LearningRollbackParams(TypedDict, total=False):
    """Roll the active pointer back to an earlier immutable version."""

    version_id: str
    """The EARLIER version to make active (`epb_…`). Omitted: the version that was active immediately before the current one.
    """


class LearningToolDocumentation(BaseModel):
    """A call type’s customer-supplied tool documentation (bounded summaries; no prose)."""

    call_type_id: str

    changed: bool | None = None
    """PUT only: false when the same documentation was already stored (idempotent)."""

    digest: str | None
    """`etd1_…` — the content address of the stored set; null when none is stored."""

    object: str
    """Known values: ``learning_tool_documentation``."""

    tool_count: int

    tools: list[LearningToolDocumentationTool]

    updated_at: str | None


class LearningToolDocumentationTool(BaseModel):
    """One tool’s stored summary."""

    documented: list[LearningToolDocumentationToolDocumentedItem]
    """Every constant the spec documents (bounded)."""

    fingerprint: str
    """`tsf1_…` — the schema fingerprint the documented constants are scoped to."""

    name: str

    params: list[str]
    """Parameter names (bounded)."""


class LearningToolDocumentationToolDocumentedItem(BaseModel):
    """Response shape ``LearningToolDocumentationToolDocumentedItem``."""

    param: str | None
    """The parameter it belongs to, or null for the function’s own description."""

    source: str
    """Known values: ``enum``, ``const``, ``default``, ``description``."""

    value: str


class PutLearningToolDocumentationParams(TypedDict, total=False):
    """The call type’s tool documentation (replaces any stored set)."""

    tools: Required[list[PutLearningToolDocumentationParamsTool]]
    """At most 256 specs with unique names; an empty list clears the documentation."""


class PutLearningToolDocumentationParamsTool(TypedDict, total=False):
    """One OpenAI-style function tool spec."""

    function: Required[PutLearningToolDocumentationParamsToolFunction]
    """The function declaration."""

    type: Required[Literal["function"]]


class PutLearningToolDocumentationParamsToolFunction(TypedDict, total=False):
    """The function declaration."""

    description: str
    """Read for the CONSTANTS it states (numbers and quoted tokens) — the prose itself is never stored.
    """

    name: Required[str]
    """The tool’s name exactly as the agent calls it (`fillFuelTank`, `api.fillFuelTank` → `fillFuelTank`).
    """

    parameters: dict[str, Any]
    """The JSON Schema of the arguments; its `enum` / `const` / `default` values are documented constants.
    """

    strict: bool


class LearningVersionList(BaseModel):
    """The version history, newest first."""

    data: list[LearningVersion]

    object: str
    """Known values: ``list``."""


class LearningVersion(BaseModel):
    """A learned playbook version."""

    active_lessons: int

    cohort: LearningVersionCohort
    """The verified episodes the version was learned from."""

    created_at: str
    """ISO 8601 instant."""

    digest: str
    """A content address of the version’s active lessons (`epb1_…`)."""

    evaluation_id: str | None
    """The evaluation that set the state, if any."""

    id: str
    """The immutable version id (`epb_…`)."""

    object: str
    """Known values: ``learning_version``."""

    parent_id: str | None

    recipe: str

    reflection_model: str | None

    state: str
    """`candidate` (published, waiting), `evaluating`, `active` (served outside an evaluation), `retired` (replaced), `rejected` (lost / stopped / rejected by an owner), `superseded` (a newer candidate, or identical to the active version).

    Known values: ``candidate``, ``evaluating``, ``active``, ``retired``, ``rejected``, ``superseded``.
    """

    state_reason: str | None
    """Why it entered its state (a bounded code); null when the state is derived."""

    state_since: str | None
    """ISO 8601 instant."""

    version: int


class LearningVersionCohort(BaseModel):
    """The verified episodes the version was learned from."""

    fail: int

    pass_: int = Field(..., alias="pass")

    size: int


class LearningVersionDetail(BaseModel):
    """One version’s lessons and provenance summary."""

    active_lessons: int

    cohort: LearningVersionCohort
    """The verified episodes the version was learned from."""

    created_at: str
    """ISO 8601 instant."""

    digest: str
    """A content address of the version’s active lessons (`epb1_…`)."""

    distiller: LearningVersionDetailDistiller
    """The body-free reflection receipt (hashes and token counts only)."""

    evaluation_id: str | None
    """The evaluation that set the state, if any."""

    id: str
    """The immutable version id (`epb_…`)."""

    known_functions: int

    lessons: list[LearningVersionDetailLesson]
    """The version’s active lessons, in served-ranking order input."""

    object: str
    """Known values: ``learning_version``."""

    parent_id: str | None

    recipe: str

    reflection_model: str | None

    retired_lessons: int

    state: str
    """`candidate` (published, waiting), `evaluating`, `active` (served outside an evaluation), `retired` (replaced), `rejected` (lost / stopped / rejected by an owner), `superseded` (a newer candidate, or identical to the active version).

    Known values: ``candidate``, ``evaluating``, ``active``, ``retired``, ``rejected``, ``superseded``.
    """

    state_reason: str | None
    """Why it entered its state (a bounded code); null when the state is derived."""

    state_since: str | None
    """ISO 8601 instant."""

    transitions: list[LearningVersionDetailTransition]
    """Every recorded state transition, oldest first."""

    version: int


class LearningVersionDetailDistiller(BaseModel):
    """The body-free reflection receipt (hashes and token counts only)."""

    input_tokens: int | None

    model: str | None

    output_tokens: int | None

    provider: str | None

    request_hash: str | None

    response_hash: str | None


class LearningVersionDetailLesson(BaseModel):
    """Response shape ``LearningVersionDetailLesson``."""

    evidence_cases: int

    id: str

    text: str


class LearningVersionDetailTransition(BaseModel):
    """Response shape ``LearningVersionDetailTransition``."""

    actor_id: str | None

    actor_type: str
    """Known values: ``system``, ``user``, ``api_key``."""

    at: str
    """ISO 8601 instant."""

    evaluation_id: str | None

    reason: str

    state: str
    """`candidate` (published, waiting), `evaluating`, `active` (served outside an evaluation), `retired` (replaced), `rejected` (lost / stopped / rejected by an owner), `superseded` (a newer candidate, or identical to the active version).

    Known values: ``candidate``, ``evaluating``, ``active``, ``retired``, ``rejected``, ``superseded``.
    """


class HostedPromptList(BaseModel):
    """A call type’s hosted prompt versions + the active pointer."""

    active_version: int | None
    """The active version number, or null when code-owned."""

    data: list[HostedPrompt]

    gateway_apply: bool
    """Whether the active version is gateway-applied (false if none)."""

    object: str
    """Known values: ``list``."""


class HostedPrompt(BaseModel):
    """One immutable hosted prompt version."""

    active: bool
    """Whether this version is the call type’s currently ACTIVE hosted prompt."""

    call_type_id: str

    content_sha256: str
    """sha256 of the template — its immutable byte identity."""

    created_at: str

    created_by: str | None

    gateway_apply: bool
    """Whether the gateway applies the ACTIVE version when proxying (false unless active)."""

    id: str

    object: str
    """Known values: ``hosted_prompt_version``."""

    source: str
    """`human` (written through the API) or `flywheel` (a later flywheel-proposed version).

    Known values: ``human``, ``flywheel``.
    """

    template: str

    variables: list[HostedPromptVariable]

    version: int
    """Monotonic per call type; activating an older one rolls back."""


class HostedPromptVariable(BaseModel):
    """A declared hosted-prompt template variable."""

    name: str
    """The `{{name}}` slot this variable fills."""

    required: bool | None = None
    """Whether the caller MUST supply a value. A missing REQUIRED variable is a named `prompt_variables_missing` refusal at gateway apply (never a silent blank).
    """


class HostedPromptCreateParams(TypedDict, total=False):
    """Create a hosted prompt version (POST /v1/call-types/{id}/prompts)."""

    template: Required[str]
    """The prompt template text (`{{name}}` variables substituted at gateway apply)."""

    variables: list[HostedPromptVariableParam]
    """The declared template variables (name + required flag). Omitted ⇒ none declared."""


class HostedPromptVariableParam(TypedDict, total=False):
    """A declared hosted-prompt template variable."""

    name: Required[str]
    """The `{{name}}` slot this variable fills."""

    required: bool
    """Whether the caller MUST supply a value. A missing REQUIRED variable is a named `prompt_variables_missing` refusal at gateway apply (never a silent blank).
    """


class HostedPromptActivation(BaseModel):
    """The active hosted-prompt pointer after an activate/deactivate."""

    active_version: int | None
    """The active version number AFTER the write (null when deactivated ⇒ code-owned)."""

    active_version_id: str | None

    call_type_id: str

    config_version: int
    """The new call-type config version the change landed on."""

    gateway_apply: bool

    object: str
    """Known values: ``hosted_prompt_activation``."""


class HostedPromptProposal(BaseModel):
    """The host-your-prompt onboarding proposal for a call type."""

    available: bool
    """Whether a proposal is available (a most-common leading instruction was found)."""

    call_type_id: str

    content_sha256: str | None
    """sha256 of the proposed template (its byte identity), or null when unavailable."""

    distinct_instructions: int
    """How many DISTINCT leading instructions were observed across the sample."""

    object: str
    """Known values: ``hosted_prompt_proposal``."""

    occurrences: int
    """How many sampled consented requests carried EXACTLY this leading instruction."""

    reason: str | None
    """The NAMED reason `available` is false (null when a proposal WAS found).

    Known values: ``already_hosted``, ``no_consent``, ``no_system_message``, ``capture_unavailable``.
    """

    sample_size: int
    """How many consented captured requests were inspected to build the proposal."""

    template: str | None
    """The proposed v1 template — the most common leading system instruction. Present only when available.
    """

    template_length: int | None
    """Character length of the proposed template, or null when unavailable."""

    variables: list[HostedPromptVariable]
    """The declared template variables (none are inferred from captured traffic; always [])."""


class HostedPromptActivateParams(TypedDict, total=False):
    """Activate a hosted prompt version (optional gateway_apply)."""

    gateway_apply: bool
    """Whether the gateway renders + applies this version when proxying (replacing the leading system instruction). Default false — preflight/SDK read the version regardless.
    """


class VerifiedMemoryStatus(BaseModel):
    """A call type’s verified-memory status."""

    call_type_id: str

    config_version: int | None

    enabled: bool
    """Whether the active config version carries a setting (readable or not — an unreadable one is `setting: null` + `servable.reason = setting_unreadable`).
    """

    lab_authorised: bool
    """The workspace’s staff-granted lab authorisation (`flywheel.verified_memory_lab`)."""

    live_pool: VerifiedMemoryStatusLivePool | None

    object: str
    """Known values: ``verified_memory``."""

    post_pin: VerifiedMemoryStatusPostPin | None
    """The CURRENT lever version’s precision on verdicts that arrived after its pin (null when memory is off).
    """

    servable: VerifiedMemoryStatusServable | None
    """Whether the setting can answer NOW (null when memory is off)."""

    setting: VerifiedMemoryStatusSetting | None
    """The frozen verified-memory setting on a call-type config version."""


class VerifiedMemoryStatusLivePool(BaseModel):
    """Response shape ``VerifiedMemoryStatusLivePool``."""

    hash: str | None

    size: int

    status: str
    """`over_budget`: never loaded — the workspace’s memory call types already fill the per-snapshot item budget (earliest pins first); requests are refused `pool_unavailable` and reach the model.

    Known values: ``loaded``, ``unavailable``, ``unreadable``, ``too_large``, ``over_budget``.
    """


class VerifiedMemoryStatusPostPin(BaseModel):
    """The CURRENT lever version’s precision on verdicts that arrived after its pin (null when memory is off)."""

    answered: int
    """Requests this lever version answered from memory."""

    correct: int
    """Accepted as-is (`accepted_unchanged` / edit ratio 0)."""

    precision: float | None
    """correct / with_verdict (null before any verdict)."""

    unknown: int
    """Answered, no verdict yet — correctness UNKNOWN."""

    wilson_high: float | None

    wilson_low: float | None

    with_verdict: int
    """Of those, how many carry a DECLARED correction-channel verdict (never an inferred proxy)."""

    wrong: int
    """Edited by the customer (edit ratio > 0)."""


class VerifiedMemoryStatusServable(BaseModel):
    """Whether the setting can answer NOW (null when memory is off)."""

    ok: bool

    reason: str | None
    """`setting_unreadable`: the active config version stores a setting the gateway cannot load (it serves the call type model-only, stamps `setting_unreadable` on every request row and logs it per snapshot read) — disable + re-enable to re-freeze it.

    Known values: ``setting_unreadable``, ``not_lab_authorised``, ``rule_version_unsupported``, ``pool_unavailable``, ``pool_changed``.
    """


class VerifiedMemoryStatusSetting(BaseModel):
    """The frozen verified-memory setting on a call-type config version."""

    alpha: float

    calibration: VerifiedMemoryStatusSettingCalibration
    """The held-out read of the frozen operating point (grouped cross-fitting by cluster: each item’s ARTIFACT cluster is held out — not the clusters of the cases a memory-answered item was decided by). Its Wilson bound is computed on the SAME rows the threshold was searched on — a selection-optimistic in-sample estimate, NOT an independent precision guarantee (the independent read is `post_pin`).
    """

    candidates_evaluated: int

    frozen_at: str
    """When the thresholds were frozen (ISO; provenance only)."""

    lever_version: str
    """`vmv1_…` — a content address over everything that can change an answer."""

    operating_point: VerifiedMemoryStatusSettingOperatingPoint

    pool: VerifiedMemoryStatusSettingPool

    pool_fact_id: str
    """The materialized `verified_memory_pool` knowledge fact."""

    pool_hash: str
    """`vmp1_…` — the frozen pool (serving refuses any other)."""

    pool_size: int

    rule_version: str
    """`vmr1_…` — the pure rule the thresholds were calibrated for."""

    target_precision: float
    """The DECLARED precision the Wilson lower bound had to clear."""

    v: float
    """Known values: ``1``."""


class VerifiedMemoryStatusSettingCalibration(BaseModel):
    """The held-out read of the frozen operating point (grouped cross-fitting by cluster: each item’s ARTIFACT cluster is held out — not the clusters of the cases a memory-answered item was decided by). Its Wilson bound is computed on the SAME rows the threshold was searched on — a selection-optimistic in-sample estimate, NOT an independent precision guarantee (the independent read is `post_pin`)."""

    abstained: int
    """Rows with no neighbour once their own artifact cluster (fold) was held out — correctness UNKNOWN.
    """

    answered: int
    """Rows the rule answers at the point."""

    answered_accuracy: float

    correct: int

    coverage: float

    deferred: int
    """Rows with a neighbour the rule declines (a threshold) — correctness UNKNOWN."""

    folds: int

    items: int
    """Calibration rows (one per pool item)."""

    method: str
    """Known values: ``grouped_cross_fitting``."""

    wilson_high: float

    wilson_low: float

    wrong: int


class VerifiedMemoryStatusSettingOperatingPoint(BaseModel):
    """Response shape ``VerifiedMemoryStatusSettingOperatingPoint``."""

    k: int
    """Neighbour depth."""

    tau_a: float
    """Minimum top-k label agreement share."""

    tau_s: float
    """Minimum top-1 lexical similarity."""


class VerifiedMemoryStatusSettingPool(BaseModel):
    """Response shape ``VerifiedMemoryStatusSettingPool``."""

    admitted_outcomes: int

    dropped: VerifiedMemoryStatusSettingPoolDropped

    items: int


class VerifiedMemoryStatusSettingPoolDropped(BaseModel):
    """Response shape ``VerifiedMemoryStatusSettingPoolDropped``."""

    masked_empty: int

    no_content: int

    no_input: int

    over_cap: int


class VerifiedMemoryDisableResult(BaseModel):
    """The result of disabling verified memory (model-only serving within one 5 s window)."""

    call_type_id: str

    changed: bool
    """False when memory was already off (nothing written — idempotent)."""

    config_version: int | None

    object: str
    """Known values: ``verified_memory_disable``."""

    previous_lever_version: str | None


class VerifiedMemoryEnableParams(TypedDict, total=False):
    """Enable verified memory for a label-contract call type."""

    target_precision: float
    """The DECLARED precision the calibration’s Wilson lower bound (α = 0.05) must clear (default 0.95).
    """


class VerifiedMemoryEnableResult(BaseModel):
    """The result of enabling verified memory."""

    calibration: VerifiedMemoryEnableResultCalibration | None
    """The held-out read of the frozen operating point (grouped cross-fitting by cluster: each item’s ARTIFACT cluster is held out — not the clusters of the cases a memory-answered item was decided by). Its Wilson bound is computed on the SAME rows the threshold was searched on — a selection-optimistic in-sample estimate, NOT an independent precision guarantee (the independent read is `post_pin`).
    """

    call_type_id: str

    config_version: int | None
    """The new call-type config version carrying the setting (null when refused)."""

    enabled: bool

    message: str | None

    object: str
    """Known values: ``verified_memory_enable``."""

    pool: VerifiedMemoryEnableResultPool | None
    """The verified pool an enable attempt built (counts only)."""

    previous_lever_version: str | None
    """The lever version this setting replaced (null when memory was off)."""

    reason: str | None
    """Why the enable was refused (null when enabled). A refusal writes no config version.

    Known values: ``not_label_contract``, ``capture_unavailable``, ``pool_empty``, ``calibration_below_target``, ``snapshot_budget_exceeded``, ``setting_unreadable``.
    """

    setting: VerifiedMemoryStatusSetting | None
    """The frozen verified-memory setting on a call-type config version."""


class VerifiedMemoryEnableResultCalibration(BaseModel):
    """The held-out read of the frozen operating point (grouped cross-fitting by cluster: each item’s ARTIFACT cluster is held out — not the clusters of the cases a memory-answered item was decided by). Its Wilson bound is computed on the SAME rows the threshold was searched on — a selection-optimistic in-sample estimate, NOT an independent precision guarantee (the independent read is `post_pin`)."""

    abstained: int
    """Rows with no neighbour once their own artifact cluster (fold) was held out — correctness UNKNOWN.
    """

    answered: int
    """Rows the rule answers at the point."""

    answered_accuracy: float

    correct: int

    coverage: float

    deferred: int
    """Rows with a neighbour the rule declines (a threshold) — correctness UNKNOWN."""

    items: int
    """Calibration rows (one per pool item)."""

    wilson_high: float

    wilson_low: float

    wrong: int


class VerifiedMemoryEnableResultPool(BaseModel):
    """The verified pool an enable attempt built (counts only)."""

    admission: VerifiedMemoryEnableResultPoolAdmission
    """The ONE correction gate’s accounting."""

    admitted_outcomes: int
    """Admitted, non-holdout verified outcomes of the call type (the ONE admission gate)."""

    content: VerifiedMemoryEnableResultPoolContent
    """Where each outcome’s content came from."""

    corrections_consent: bool

    dropped: VerifiedMemoryStatusSettingPoolDropped

    items: int
    """The effective pool size."""


class VerifiedMemoryEnableResultPoolAdmission(BaseModel):
    """The ONE correction gate’s accounting."""

    admitted_declared: int

    admitted_inferred: int

    dropped_by_reason: dict[str, int]

    receipt_candidates: int

    receipt_rejected_by_reason: dict[str, int]


class VerifiedMemoryEnableResultPoolContent(BaseModel):
    """Where each outcome’s content came from."""

    final: int

    magnitude_only: int

    verified_replacement: int

    verified_replacement_withheld_consent: int


class ChatCompletionCreateParams(TypedDict, total=False):
    """OpenAI-compatible chat-completions request with ultrarouter extensions."""

    call_type: str
    """Stable call-type slug."""

    compression: Literal["off", "semantic_safe", "adaptive", "lossless", "auto"] | CompressionParam

    frequency_penalty: float

    logprobs: bool

    max_completion_tokens: int
    """The modern OpenAI max-output-token budget (visible + reasoning tokens). Carried to every adapter (OpenAI reasoning models require it in place of `max_tokens`; other providers map it to their own max-output field). When BOTH `max_completion_tokens` and `max_tokens` are sent, `max_completion_tokens` wins — the metered ceiling equals the cap actually sent.
    """

    max_tokens: int

    messages: Required[list[ChatMessageParam]]
    """Conversation messages (required)."""

    metadata: dict[str, Any]
    """Opaque JSON stored with the request."""

    model: str
    """Provider-prefixed model id, e.g. "openai/gpt-5.2-mini"."""

    models: list[str]
    """Ordered fallback model ids (OpenRouter)."""

    n: int

    presence_penalty: float

    provider: ProviderPreferencesParam
    """OpenRouter-parity provider preferences."""

    reasoning: ReasoningParam
    """OpenRouter-native reasoning control (`{ effort, max_tokens, exclude }`)."""

    reasoning_effort: Literal["none", "minimal", "low", "medium", "high"]
    """The OpenAI reasoning-effort control, carried to every adapter. Forwarded verbatim to OpenAI-compatible providers (OpenAI reasoning models honour it; it also decides whether sampling parameters such as `temperature` are forwarded to those models); MAPPED to a thinking-token budget for budget-based providers (Anthropic / Gemini / Bedrock-Anthropic per the OpenRouter reference); refused with a NAMED `capability_unsupported` error where a provider has no reasoning knob — never silently dropped. The structured `reasoning` object takes precedence when both are sent.
    """

    response_format: (
        ResponseFormatTextParam | ResponseFormatJsonObjectParam | ResponseFormatJsonSchemaParam
    )
    """Structured-output format (incl. json_schema)."""

    router: Literal["off", "auto", "candidates"]
    """Routing mode; when no config layer sets one, the system default is "off"."""

    seed: int

    stop: str | list[str]

    stream: bool
    """Stream the response as server-sent events (OpenAI `chat.completion.chunk` format)."""

    stream_options: dict[str, Any]

    temperature: float

    tool_choice: str | dict[str, Any]
    """Tool selection strategy."""

    tools: list[Any]
    """Tool/function definitions."""

    top_logprobs: int

    top_p: float

    ur: UrParams
    """ultrarouter per-request controls."""

    user: str


class CompressionParam(TypedDict, total=False):
    """Request shape ``CompressionParam``."""

    max_quality_risk: Literal["low", "medium", "high"]

    mode: Literal["off", "semantic_safe", "adaptive", "lossless", "auto"]

    no_compress_fields: list[str]


class ChatMessageParam(TypedDict, total=False):
    """An OpenAI-shaped chat message."""

    content: str | list[ChatContentPartParam] | None

    name: str

    role: Required[Literal["system", "developer", "user", "assistant", "tool"]]

    tool_call_id: str

    tool_calls: list[Any]


class ChatContentPartParam(TypedDict, total=False):
    """One OpenAI-shaped message content part; may carry a `cache_control` breakpoint."""

    cache_control: CacheControlParam
    """Mark this content part as a prompt-cache breakpoint. Translated to Anthropic `cache_control` on the block; stripped + ignored (structured log) for non-Anthropic providers.
    """

    text: str
    """The text of a text part."""

    type: str
    """The content part type ("text" | "image_url" | …)."""


class CacheControlParam(TypedDict, total=False):
    """Mark this content part as a prompt-cache breakpoint. Translated to Anthropic `cache_control` on the block; stripped + ignored (structured log) for non-Anthropic providers."""

    ttl: str
    """Cache lifetime hint, e.g. "5m" (default) or "1h"."""

    type: Required[Literal["ephemeral"]]
    """The only supported cache type."""


class ProviderPreferencesParam(TypedDict, total=False):
    """OpenRouter-parity provider preferences."""

    allow_fallbacks: bool

    data_collection: Literal["allow", "deny"]

    ignore: list[str]

    order: list[str]

    quantizations: list[str]

    require_parameters: bool

    sort: Literal["price", "throughput", "latency"]


class ReasoningParam(TypedDict, total=False):
    """OpenRouter-native reasoning control (`{ effort, max_tokens, exclude }`)."""

    effort: Literal["none", "minimal", "low", "medium", "high"]
    """Reasoning effort: none | minimal | low | medium | high (OpenAI / OpenRouter reference)."""

    exclude: bool
    """Drop reasoning tokens from the response — unsupported, refused NAMED when true."""

    max_tokens: int
    """Direct thinking-token budget (budget-based providers; min 1024)."""


class ResponseFormatTextParam(TypedDict, total=False):
    """Request shape ``ResponseFormatTextParam``."""

    type: Required[Literal["text"]]


class ResponseFormatJsonObjectParam(TypedDict, total=False):
    """Request shape ``ResponseFormatJsonObjectParam``."""

    type: Required[Literal["json_object"]]


class ResponseFormatJsonSchemaParam(TypedDict, total=False):
    """Request shape ``ResponseFormatJsonSchemaParam``."""

    json_schema: Required[dict[str, Any]]

    type: Required[Literal["json_schema"]]


class UrParams(TypedDict, total=False):
    """ultrarouter per-request controls."""

    artifact: str
    """The DECLARED artifact key this request contributes to (pre-dispatch assembly). Binds the served request to the artifact (`assembly_source=declared_request`) and is the standing-holdout cluster key; the response `ur.artifact_id` echoes the bound id. Equivalent to the `X-UR-Artifact` header; the body wins on conflict.
    """

    bench: str | BenchTagParam
    """ultrarouter Bench capture activation."""

    context_modules: list[ContextModuleRefParam]
    """The ordered `profile.contextModules[]` this call opts into — the `learned_context` lever surface. Each entry pins a module id AND its exact version (a retrieval-backed version IS its recipe hash), so a pack change or a ranker refit can never be served under an old pin. The gateway rebuilds the pack from the pinned recipe, refuses fail-closed on any mismatch, and SKIPS injection entirely for a holdout request.
    """

    manifest: ManifestWireParam
    """Declared context manifest (`toWire(manifest)`); the gateway witnesses it (verifies every hash against the received bytes before any transform) and drives compression eligibility from the declared kinds.
    """

    max_cost_usd: float

    prompt_vars: dict[str, str | float | bool]
    """The values for the ACTIVE hosted prompt’s `{{name}}` variables, when the gateway applies a hosted prompt for this call type (`gateway_apply`). A missing REQUIRED variable is a named `prompt_variables_missing` refusal (never a silent blank). Ignored when no hosted prompt is applied.
    """

    segments: list[SegmentHintParam]
    """SDK segment-part labels to refine compression segmentation."""

    tags: dict[str, str]

    timeout_ms: int

    trace_id: str


class BenchTagParam(TypedDict, total=False):
    """Request shape ``BenchTagParam``."""

    run: str
    """Capture-window label (commit SHA/branch/agent)."""

    suite: Required[str]
    """The bench suite slug (auto-created on first use)."""

    trace: str
    """Multi-call task grouping id."""


class ContextModuleRefParam(TypedDict, total=False):
    """A pinned learned-context module reference."""

    module_id: Required[str]
    """The learned-context module id (`lcm_…`)."""

    module_version: Required[str]
    """The PINNED module version — the recipe hash (`lcm1_…`)."""


class ManifestWireParam(TypedDict, total=False):
    """Declared context manifest (`toWire(manifest)`); the gateway witnesses it (verifies every hash against the received bytes before any transform) and drives compression eligibility from the declared kinds."""

    entries: Required[list[ManifestWireEntryParam]]
    """The ordered declared entries."""

    envelope_hash: Required[str]
    """The declared execution-envelope hash."""

    manifest_hash: Required[str]
    """The declared per-execution manifest hash."""

    scaffold_hash: Required[str]
    """The call-type identity (kinds/slots/ids only, stable across executions)."""


class ManifestWireEntryParam(TypedDict, total=False):
    """One declared context-manifest entry."""

    content_hash: Required[str]
    """sha256 hex over the declared slice (or canonical JSON of an opaque part)."""

    kind: Required[str]
    """The context module kind (opaque label; drives no branching)."""

    mandatory: Required[bool]
    """Whether the module was mandatory in the compiled manifest."""

    memory_class: Required[str]
    """The memory class (opaque label)."""

    order: Required[int]
    """Position in the compiled manifest order."""

    range: ManifestWireRangeParam
    """The exact declared range; absent for an opaque part hashed over canonical JSON."""

    slot: Required[str]
    """The rendering slot ('instruction' | 'reference' | 'exemplar' | …)."""

    trust_class: Required[str]
    """Trust class ('authoritative' | 'approved_derived' | 'untrusted')."""


class ManifestWireRangeParam(TypedDict, total=False):
    """The exact declared range; absent for an opaque part hashed over canonical JSON."""

    end: Required[int]
    """Span end (UTF-16 code-unit offset, exclusive)."""

    message_index: Required[int]
    """Index into the `messages` array."""

    part_index: int
    """Index into a multi-part message content array (omit for string content)."""

    start: Required[int]
    """Span start (UTF-16 code-unit offset)."""


class SegmentHintParam(TypedDict, total=False):
    """An SDK-provided segment label for one message or span."""

    end: int
    """Optional span end (char offset, exclusive) within the message content."""

    index: Required[int]
    """Index into the `messages` array."""

    kind: Required[
        Literal[
            "system_instructions",
            "user_question",
            "reference_context",
            "few_shot_examples",
            "tool_results",
            "history",
        ]
    ]
    """The segment kind the SDK asserts for that message."""

    start: int
    """Optional span start (char offset) within the message content."""


class ChatCompletion(BaseModel):
    """OpenAI-compatible chat-completions response with the ultrarouter `ur` block."""

    choices: list[ChatCompletionChoice]

    created: int

    id: str

    model: str

    object: str
    """Known values: ``chat.completion``."""

    system_fingerprint: str | None = None

    ur: UrBlock
    """ultrarouter response extension block."""

    usage: ChatCompletionUsage
    """OpenAI usage accounting."""


class ChatCompletionChoice(BaseModel):
    """Response shape ``ChatCompletionChoice``."""

    finish_reason: str | None

    index: int

    logprobs: Any = None

    message: ChatCompletionMessage


class ChatCompletionMessage(BaseModel):
    """Response shape ``ChatCompletionMessage``."""

    content: str | None = None

    role: str

    tool_calls: list[Any] | None = None


class UrBlock(BaseModel):
    """ultrarouter response extension block."""

    artifact_id: str | None = None
    """The flywheel artifact id this request was bound to — present only when the request DECLARED an artifact (`ur.artifact` / `X-UR-Artifact`). Absent otherwise.
    """

    bench: UrBlockBench | None = None
    """ultrarouter Bench capture echo — present only on a bench-tagged call."""

    byok: bool
    """Whether a workspace BYOK key served the request."""

    call_type: str | None
    """Resolved call type, or null when none was resolved."""

    compression: UrBlockCompression
    """Compression summary — the applied compression safety tier + honest savings provenance."""

    cost_usd: float
    """Total request cost in USD."""

    model_served: str
    """The model actually served."""

    provider: str
    """The provider that served it."""

    request_id: str
    """Correlation id (`req_…`)."""

    routing: UrBlockRouting
    """Routing decision summary."""

    verified_memory: UrBlockVerifiedMemory | None = None
    """Verified-memory answer details: present ONLY when the request was answered from the workspace’s verified memory (no provider was called; `ur.routing.engine` = `verified_memory`, `cost_usd` = 0).
    """


class UrBlockBench(BaseModel):
    """ultrarouter Bench capture echo — present only on a bench-tagged call."""

    capture_status: str
    """Honest capture status: an API response may only ever say "queued" — the capture is enqueued durably (same-tx outbox); only a persisted envelope is "confirmed" (read it via the bench suite readiness meter).

    Known values: ``queued``.
    """

    run: str | None
    """The capture-window run tag, or null."""

    suite: str
    """The bench suite slug this call was captured into."""


class UrBlockCompression(BaseModel):
    """Compression summary — the applied compression safety tier + honest savings provenance."""

    applied: str
    """The compression safety tier actually applied.

    Known values: ``off``, ``semantic_safe``, ``adaptive``.
    """

    deprecated_alias: str | None = None
    """Set when the request used a deprecated legacy compression alias.

    Known values: ``lossless``, ``auto``.
    """

    est_saved_usd: float | None = None
    """Estimated saved USD — a diagnostic (chars/4)."""

    savings_basis: str | None = None
    """Whether a savings ledger line was recorded (provider-reported usage) or the figure is a diagnostic only.

    Known values: ``provider_reported``, ``estimated_diagnostic``.
    """

    source: str | None = None
    """Provenance of the applied tier (unqualified-legacy = no shadow evidence yet).

    Known values: ``off``, ``qualified``, ``unqualified-legacy``.
    """

    tokens_saved: int | None = None

    verify: str | None = None


class UrBlockRouting(BaseModel):
    """Routing decision summary."""

    engine: str | None = None
    """"policy" when the auto-routing policy engine ran (auto/candidates); "verified_memory" when the request was answered from the workspace’s verified memory (no provider was called).
    """

    fallback_used: bool

    mode: str
    """Known values: ``off``, ``auto``, ``candidates``."""


class UrBlockVerifiedMemory(BaseModel):
    """Verified-memory answer details: present ONLY when the request was answered from the workspace’s verified memory (no provider was called; `ur.routing.engine` = `verified_memory`, `cost_usd` = 0)."""

    agreeing_items: int

    agreement: float

    case_ids: list[str]
    """The `cex1_…` ids of the verified cases that decided the answer (nearest first)."""

    k: int

    lever_version: str

    pool_fact_id: str

    pool_hash: str

    rule_version: str

    similarity: float

    tau_a: float

    tau_s: float


class ChatCompletionUsage(BaseModel):
    """OpenAI usage accounting."""

    completion_tokens: int

    prompt_tokens: int

    prompt_tokens_details: ChatCompletionUsagePromptTokensDetails | None = None

    total_tokens: int


class ChatCompletionUsagePromptTokensDetails(BaseModel):
    """Response shape ``ChatCompletionUsagePromptTokensDetails``."""

    cached_tokens: int | None = None


class EmbeddingCreateParams(TypedDict, total=False):
    """OpenAI-compatible embeddings request with ultrarouter extensions."""

    call_type: str
    """Stable call-type slug (selects the call type whose config applies)."""

    dimensions: int
    """Optional output dimensionality (provider-supported models only)."""

    encoding_format: Literal["float", "base64"]
    """Output encoding, passed through to the provider. The official OpenAI SDK defaults to `base64` (it decodes client-side), so both are accepted for OpenAI-client compatibility.
    """

    input: Required[str | list[str]]
    """A string or array of strings to embed."""

    metadata: dict[str, Any]
    """Opaque JSON stored with the request."""

    model: Required[str]
    """Provider-prefixed embeddings model id, e.g. "openai/text-embedding-4-small"."""

    ur: UrParams
    """ultrarouter per-request controls."""

    user: str
    """Opaque end-user id (OpenAI parity)."""


class CreateEmbeddingResponse(BaseModel):
    """OpenAI-compatible embeddings response with the ultrarouter `ur` block."""

    data: list[Embedding]

    model: str

    object: str
    """Known values: ``list``."""

    ur: EmbeddingUrBlock
    """ultrarouter response extension block."""

    usage: EmbeddingUsage


class Embedding(BaseModel):
    """Response shape ``Embedding``."""

    embedding: list[float] | str

    index: int

    object: str
    """Known values: ``embedding``."""


class EmbeddingUrBlock(BaseModel):
    """ultrarouter response extension block."""

    byok: bool

    call_type: str | None

    cost_usd: float

    model_served: str

    provider: str

    request_id: str

    routing: EmbeddingUrBlockRouting


class EmbeddingUrBlockRouting(BaseModel):
    """Response shape ``EmbeddingUrBlockRouting``."""

    engine: str | None = None

    fallback_used: bool

    mode: str


class EmbeddingUsage(BaseModel):
    """Response shape ``EmbeddingUsage``."""

    prompt_tokens: int

    total_tokens: int


class FlywheelCandidateList(BaseModel):
    """The workspace Improvements-inbox candidates with their offline deciding axis."""

    candidates: list[FlywheelCandidate]

    object: str
    """Known values: ``flywheel_candidates``."""

    workspace_id: str


class FlywheelCandidate(BaseModel):
    """One inbox candidate with its offline deciding reading — metadata only, never a body."""

    call_type_id: str | None
    """The call type the candidate is measured on."""

    epoch: int
    """The measurement epoch the candidate is bound to."""

    lever_key: str
    """The lever family (e.g. `learned_context` / `hosted_prompt`)."""

    live_verdict: str
    """The live-confirmation verdict (`not_run` until a confirmation opens)."""

    module_id: str | None
    """The candidate module/version id, or null."""

    module_version: str | None
    """The candidate module version (recipe hash), or null."""

    offline: FlywheelCandidateOffline | None
    """The deciding reading (contract + intervals + deciding axes), or null before the screen ran.
    """

    offline_verdict: str
    """The offline screening verdict for this candidate.

    Known values: ``none``, ``screening``, ``screened``, ``rejected``, ``parked``.
    """

    provenance: str
    """WHERE the proposal came from — DERIVED from the run’s trigger evidence, never a prop.

    Known values: ``corrections``, ``eval_set``, ``human_draft``, ``unknown``.
    """

    run_id: str
    """The screening run id (the evidence trace)."""

    started_at: str
    """When the screening run opened (ISO)."""


class FlywheelCandidateOffline(BaseModel):
    """The deciding reading (contract + intervals + deciding axes), or null before the screen ran."""

    contract: str
    """The decision intent the screen was decided under (e.g. `product_improvement`)."""

    cost: FlywheelCandidateOfflineCost
    """The cost (savings / budget) interval."""

    deciding: list[str]
    """The conjunct axes whose state made the outcome — EMPTY on a screened pass.

    Known values: ``quality``, ``cost``, ``guardrail``, ``evidence``.
    """

    economics: FlywheelCandidateOfflineEconomics | None
    """The ABSOLUTE economics beside the ratio; null when the screen measured no absolute cost."""

    quality: FlywheelCandidateOfflineCost
    """The quality (non-inferiority / superiority) interval."""


class FlywheelCandidateOfflineCost(BaseModel):
    """The cost (savings / budget) interval."""

    high: float
    """The upper confidence bound."""

    low: float
    """The lower confidence bound."""

    point: float
    """The point estimate."""

    state: str
    """The tri-state for this axis — a labelled tier, never a claim.

    Known values: ``pass``, ``fail``, ``inconclusive``.
    """


class FlywheelCandidateOfflineEconomics(BaseModel):
    """The ABSOLUTE economics beside the ratio; null when the screen measured no absolute cost."""

    cost_per_avoided_error_micro_usd: FlywheelCandidateOfflineEconomicsCostPerAvoidedErrorMicroUsd
    """$ per AVOIDED ERROR, µUSD — `unavailable` whenever the errors-avoided interval crosses zero.
    """

    design: str
    """`paired` for an offline contrast on the same clusters; `independent` for live arms.

    Known values: ``paired``, ``independent``.
    """

    errors_avoided_per_1000: FlywheelCandidateOfflineEconomicsErrorsAvoidedPer1000
    """ERRORS AVOIDED per 1,000 requests (the treated − baseline success-rate gap, scaled)."""

    extra_cost_per_1000_micro_usd: FlywheelCandidateOfflineEconomicsErrorsAvoidedPer1000
    """EXTRA cost per 1,000 requests, µUSD (treated − baseline). Negative ⇒ the lever is CHEAPER."""

    n_clusters_baseline: int

    n_clusters_treated: int

    net_value_per_1000_micro_usd: (
        FlywheelCandidateOfflineEconomicsCostPerAvoidedErrorMicroUsd | None
    )
    """The JOINT `value × Δsuccess − Δcost` per 1,000 requests — null when no value was preregistered.
    """

    value_per_avoided_error_micro_usd: float | None
    """The PREREGISTERED value the joint bound was computed with (null when none)."""

    version: int
    """The absolute-economics derivation version."""


class FlywheelCandidateOfflineEconomicsCostPerAvoidedErrorMicroUsd(BaseModel):
    """$ per AVOIDED ERROR, µUSD — `unavailable` whenever the errors-avoided interval crosses zero."""

    high: float | None
    """The upper bound (null when unavailable)."""

    low: float | None
    """The lower bound (null when unavailable)."""

    point: float | None
    """The point estimate (null when unavailable)."""

    reason: str | None
    """The NAMED reason the figure is unavailable (null when measured)."""

    status: str
    """`unavailable` ⇒ the ratio is undefined/unbounded; there is no number to show.

    Known values: ``measured``, ``unavailable``.
    """


class FlywheelCandidateOfflineEconomicsErrorsAvoidedPer1000(BaseModel):
    """ERRORS AVOIDED per 1,000 requests (the treated − baseline success-rate gap, scaled)."""

    high: float

    low: float

    point: float


class ConfirmationStatus(BaseModel):
    """The live-confirmation state for a candidate — status, the one-look result, adoptability, and the recorded interval + n."""

    adopt_refusal: str | None
    """The NAMED reason adoption is unavailable (e.g. not_yet_confirmed_live), or null."""

    adoptable: bool
    """True ONLY when the confirmation is open AND its live result is confirmed."""

    adopted_by: str | None
    """Who adopted this confirmation — `system:autopilot` for the platform auto path, `human:<userId>` for a dashboard press — or null when not adopted.
    """

    auto_adopt: ConfirmationStatusAutoAdopt
    """The autopilot decision for this confirmation (read-time, from the current config)."""

    candidate_ref: str

    epoch: int | None

    lift: ConfirmationLift | None
    """The recorded live lift (interval + n), or null before a result is recorded."""

    module_id: str | None
    """The servable learned-context module id (`candidate_id`) of this confirmation, or null. A non-proxied customer reads this + `module_version` to inject exactly what the platform is confirming/adopted.
    """

    module_version: str | None
    """The recipe-hash module version of the confirmation candidate, or null."""

    object: str
    """Known values: ``flywheel_confirmation_status``."""

    present: bool
    """Whether a confirmation exists for this candidate reference."""

    result_outcome: str | None
    """The one-look live result: pending | confirmed | refuted | inconclusive, or null."""

    self_improve_mode: str
    """The call type's self-improve mode (off | assist | autopilot)."""

    status: str | None
    """The lifecycle (open | adopted | rolled_back | invalidated | closed), or null."""


class ConfirmationStatusAutoAdopt(BaseModel):
    """The autopilot decision for this confirmation (read-time, from the current config)."""

    eligible: bool
    """Whether autopilot WOULD auto-adopt this confirmed confirmation under the current mode + guardrails (recomputed at read time).
    """

    refusals: list[str]
    """The NAMED failed guard(s) when not eligible (e.g. mode_not_autopilot, cost_over_budget, surface_disabled) — so a customer can see WHY autopilot did not fire.
    """


class ConfirmationLift(BaseModel):
    """The live lift — the contrast interval + n per arm + cost per successful artifact."""

    aa_status: str
    """The A/A instrument status: unknown | passing | parked."""

    cost_per_success_micro_usd: int | None
    """OUR treated-arm cost per successful artifact (micro-USD), or null (no successes)."""

    interval: ConfirmationLiftInterval
    """The treated − lever_holdout contrast interval (fractions)."""

    n_lever_holdout: int

    n_treated: int


class ConfirmationLiftInterval(BaseModel):
    """The treated − lever_holdout contrast interval (fractions)."""

    high: float

    low: float

    point: float


class CandidateDecisionParams(TypedDict, total=False):
    """Human decision callback: accept/reject/revert with actor + mandatory reason (audit-only)."""

    actor_id: Required[str]

    callback_id: Required[str]

    candidate_ref: Required[str]

    decided_at: Required[str]

    decision: Required[Literal["accept", "reject", "revert"]]

    evidence_hash: Required[str]

    kind: Required[Literal["decision"]]

    reason: Required[str]

    schema: Required[Literal["ur.appci.callback.v1"]]

    surface: Required[Literal["pull_request", "dashboard", "cli"]]

    workspace_id: Required[str]


class CandidateDecisionResult(BaseModel):
    """Decision verdict: accepted or a visible duplicate no-op (a replay). Never a learning label."""

    callback_id: str

    learning_use: str
    """Known values: ``audit``."""

    status: str
    """Known values: ``accepted``, ``duplicate``."""


class CandidateRolloutParams(TypedDict, total=False):
    """Rollout-gate request: the CI-observed facts the server decides the unlock from."""

    application_headline: Required[str | None]

    candidate_ref: Required[str]

    candidate_state: Required[str]

    change_shape: Required[str]

    observed_identity: Required[CandidateRolloutIdentityParams]
    """The bound application-evidence identity (matches the SDK `EvidenceContract`)."""

    requires_repository_write: Required[bool]

    schema: Required[Literal["ur.flywheel.rollout.request.v1"]]


class CandidateRolloutIdentityParams(TypedDict, total=False):
    """The bound application-evidence identity (matches the SDK `EvidenceContract`)."""

    baseSha: Required[str]

    candidateRef: str

    configHash: Required[str]

    datasetSplit: Required[str]

    evaluatorVersion: Required[str]

    evidenceEpoch: Required[str]

    harnessHash: Required[str]

    headSha: Required[str]

    lockDigest: Required[str]

    objective: Required[str]

    repository: Required[str]

    workflowId: Required[str]


class CandidateRolloutResult(BaseModel):
    """Rollout gate: the full blocker list + the immutable evidence address. Never pressed."""

    blockers: list[CandidateRolloutBlocker]

    candidate_ref: str

    evidence_hash: str

    pressed: bool
    """Known values: ``False``."""

    unlocked: bool


class CandidateRolloutBlocker(BaseModel):
    """A named rollout precondition failure + the family it belongs to."""

    detail: str | None = None

    family: str

    message: str

    reason: str


class ConfirmationList(BaseModel):
    """The workspace confirmations ledger — the discovery surface for what to adopt."""

    confirmations: list[Confirmation]

    object: str
    """Known values: ``flywheel_confirmations``."""

    workspace_id: str


class Confirmation(BaseModel):
    """One confirmation in the workspace ledger — metadata only, never a body."""

    adoptable: bool
    """True ONLY when the confirmation is open AND its live result is confirmed."""

    call_type_id: str | None
    """The call type this confirmation is measured on."""

    candidate_ref: str
    """The candidate reference — the id a decision route (adopt/reject) takes."""

    epoch: int
    """The measurement epoch the candidate is bound to."""

    lever_key: str
    """The lever family (e.g. `learned_context`)."""

    module_id: str
    """The servable learned-context module id of this confirmation candidate."""

    module_version: str
    """The recipe-hash module version."""

    opened_at: str | None
    """When the confirmation was opened (ISO), or null on a legacy row."""

    result_outcome: str
    """The one-look live result: pending | confirmed | refuted | inconclusive."""

    status: str
    """The lifecycle: open | adopted | rolled_back | invalidated | closed."""


class ExperimentEnrolParams(TypedDict, total=False):
    """Enrol one execution slot — the gateway decides the arm."""

    pair_key: Required[str]
    """The pair — one idea family frozen in the preregistration's screen or test split."""

    phase: Required[Literal["screen", "test"]]
    """The fundable phase the execution runs in: `screen` (the historical screen pairs) or `test`.
    """

    slot: Required[float]
    """One of the pair’s two slots: 0 or 1 (anything else is refused `slot_invalid`)."""


class ExperimentExecution(BaseModel):
    """One enrolled experiment execution — ids / arm / hashes only."""

    arm: str
    """Decided by the sealed assignment — never by the caller.

    Known values: ``control``, ``treated``.
    """

    assignment_version: str
    """The sealed assignment rule version."""

    candidate_hash: str
    """The frozen candidate this execution is bound to (every call re-checks it)."""

    created: bool
    """False when the same {phase, pair_key, slot} was already enrolled (idempotent)."""

    created_at: str

    execution_id: str
    """Send as the `X-UR-Experiment-Execution` header on every call of this execution."""

    experiment_id: str

    object: str
    """Known values: ``flywheel_experiment_execution``."""

    pair_key: str

    phase: str
    """Known values: ``screen``, ``test``."""

    slot: int


class ExperimentOutcomeParams(TypedDict, total=False):
    """One live execution outcome — ids, hashes and numbers only, never a body."""

    final_content_hash: Required[str]
    """The hash of the final content (the delivered post, or the last draft when held)."""

    reason_codes: Required[list[str]]
    """The typed reason codes (empty for a clean delivery)."""

    reason_vocab: Required[str]
    """The reason vocabulary id — must be the frozen verifier’s."""

    receipts: Required[list[ExperimentReceiptParams]]

    request_ids: Required[list[str]]
    """Every gateway request id the execution made — members and failed attempts alike."""

    terminal: Required[Literal["delivered", "held"]]


class ExperimentReceiptParams(TypedDict, total=False):
    """One member-call receipt — numbers, hashes and ids only, never a body."""

    call_type: Required[str]

    extractor_version: Required[str]
    """The receipt-extraction recipe version — must be the experiment verifier’s."""

    numbers: Required[dict[str, float]]
    """The stage-aware body-free numbers (e.g. `post_length`, `line_count`, `distinct`, `usefulness`).
    """

    ordinal: Required[int]
    """The call’s position in the execution."""

    parsed_hash: str | None

    quote_ids: list[str]

    request_id: Required[str]
    """The gateway request id of this member call (must be listed in `request_ids`)."""

    response_hash: str | None

    response_len: int

    stage: Required[str]
    """The stage (as the call declared it in `X-UR-Trace`)."""

    system_hash: str | None

    system_len: int

    user_hash: str | None

    user_len: int


class ExperimentExecutionOutcome(BaseModel):
    """The recorded outcome, or — with `?dry_run=true` — the dry-run answer."""

    cost: ExperimentExecutionOutcomeCost | None = None
    """The execution’s cost reconciliation — an ambiguous, pending or unexplained one is incomplete.
    """

    created: bool | None = None
    """False when the same outcome was already recorded (an idempotent repeat)."""

    execution_id: str

    experiment_id: str

    experiment_state: str | None = None
    """Known values: ``admitted``, ``refused``, ``candidate_frozen``, ``screening``, ``screen_passed``, ``screen_failed``, ``screen_incomplete``, ``awaiting_test_funding``, ``test_open``, ``test_passed``, ``test_failed``, ``test_incomplete``, ``closed``, ``expired``, ``abandoned``.
    """

    missing_request_ids: list[str]

    object: str

    outcome_hash: str

    status: str
    """pending_rows: a call’s row has not landed yet — it completes when the rows land."""

    trusted_recorded: list[str]
    """Reason codes the verifier cannot reconstruct — listed, never silently passed."""

    detail: str | None = None

    open_holds: list[ExperimentExecutionOutcomeOpenHold] | None = None
    """The execution’s holds still reserved or ambiguous."""

    recorded_outcome: str | None = None
    """Whether an outcome is already recorded and this payload would converge on it or conflict.

    Known values: ``none``, ``converges``, ``conflicts``.
    """

    refusal: str | None = None
    """The named refusal (e.g. `verifier_mismatch:<gate>`, `receipt_missing:<stage>`), or null."""

    unlisted_request_ids: list[str] | None = None
    """The execution’s own landed calls the payload does NOT list (e.g. a failed attempt the client lost).
    """


class ExperimentExecutionOutcomeCost(BaseModel):
    """The execution’s cost reconciliation — an ambiguous, pending or unexplained one is incomplete."""

    ambiguous_micro_usd: int

    complete: bool
    """True only when every hold is settled, released before dispatch or reconciled, no open hold awaits its row, no unpriced row is unreconciled and the difference is fully explained.
    """

    difference_micro_usd: int
    """rows_measured − settled — non-zero while a hold is unsettled or ambiguous, or settled at its reserve.
    """

    holds: int

    holds_reconciled: int
    """Holds the owner reconciled (settle, settle_at_reserve or release) — each counts as resolved.
    """

    holds_released_after_dispatch: int
    """Holds released after their call was sent without a reconciliation — incomplete."""

    reserved_micro_usd: int

    rowless_resolved_holds: int
    """Reconciled holds whose request row never landed (a stale claim)."""

    rows: int

    rows_measured_micro_usd: int

    rows_unpriced: int

    rows_unpriced_unresolved: int
    """Unpriced rows whose hold the owner has not reconciled — each keeps the cost incomplete."""

    settled_micro_usd: int

    unexplained_micro_usd: int
    """The difference NOT accounted for by an owner reconciliation (over the holds the gateway settled) — must be 0.
    """

    unlanded_holds: int
    """Open holds whose request row has not landed yet."""


class ExperimentExecutionOutcomeOpenHold(BaseModel):
    """Response shape ``ExperimentExecutionOutcomeOpenHold``."""

    amount_micro_usd: int

    hold_key: str

    state: str
    """Known values: ``reserved``, ``ambiguous``."""


class ExperimentScreenEvaluation(BaseModel):
    """The screen after an explicit evaluation (counts only until the verdict)."""

    computed: bool
    """True only for the ONE call that computed and stored the verdict."""

    experiment_id: str

    experiment_state: str
    """Known values: ``admitted``, ``refused``, ``candidate_frozen``, ``screening``, ``screen_passed``, ``screen_failed``, ``screen_incomplete``, ``awaiting_test_funding``, ``test_open``, ``test_passed``, ``test_failed``, ``test_incomplete``, ``closed``, ``expired``, ``abandoned``.
    """

    object: str
    """Known values: ``flywheel_experiment_screen_evaluation``."""

    screen: ExperimentScreenEvaluationScreen
    """The screen: barrier counts (no peeking) and, once computed, the verdict."""


class ExperimentScreenEvaluationScreen(BaseModel):
    """The screen: barrier counts (no peeking) and, once computed, the verdict."""

    executions: list[ExperimentScreenEvaluationScreenExecution]

    progress: ExperimentScreenEvaluationScreenProgress
    """The screen completion-barrier counts (complete / incomplete only — no per-arm outcome)."""

    verdict: ExperimentScreenEvaluationScreenVerdict | None
    """Null until the completion barrier is met and the verdict is stored."""


class ExperimentScreenEvaluationScreenExecution(BaseModel):
    """One enrolled screen execution — ids, arm and standing only."""

    arm: str
    """Known values: ``control``, ``treated``."""

    execution_id: str

    pair_key: str

    slot: int

    status: str
    """no_outcome: none recorded yet; pending_rows: recorded, a call’s row has not landed; cost_unsettled: a hold is still reserved or ambiguous; invalid: the recorded outcome fails now that its rows landed; complete.

    Known values: ``no_outcome``, ``pending_rows``, ``cost_unsettled``, ``invalid``, ``complete``.
    """


class ExperimentScreenEvaluationScreenProgress(BaseModel):
    """The screen completion-barrier counts (complete / incomplete only — no per-arm outcome)."""

    cap_stopped: bool
    """True once a call of the phase was refused for want of money — incomplete forever."""

    executions_complete: int

    executions_cost_unsettled: int

    executions_enrolled: int

    executions_incomplete: int

    executions_invalid: int

    executions_pending_rows: int

    holds_ambiguous: int

    holds_reserved: int

    judgements_recorded: int

    judges_required: int

    outcomes_recorded: int

    pairs_complete: int

    pairs_total: int


class ExperimentScreenEvaluationScreenVerdict(BaseModel):
    """Null until the completion barrier is met and the verdict is stored."""

    candidate_hash: str

    clauses: list[ExperimentScreenEvaluationScreenVerdictClause]
    """Every clause with its counts (empty when incomplete — nothing is analysed)."""

    created_at: str

    failing_clauses: list[str]
    """Every failing clause (screen_fail); empty otherwise."""

    incomplete_reasons: list[str]
    """Why the screen can never complete (screen_incomplete): cap_stop, candidate_withdrawn, outcome_invalid:<execution>:<refusal>, pair_arms_not_opposite:<pair>, judging_not_preregistered, judgement_manifest_mismatch:<judge>.
    """

    inputs: ExperimentScreenEvaluationScreenVerdictInputs
    """The verdict inputs: each execution’s identity, arm, standing, outcome hash and cost reconciliation, the output manifest, and each judgement’s hash and reviewed manifest.
    """

    inputs_hash: str

    prereg_hash: str

    progress: ExperimentScreenEvaluationScreenProgress
    """The screen completion-barrier counts (complete / incomplete only — no per-arm outcome)."""

    rule: ExperimentScreenEvaluationScreenVerdictRule
    """The frozen rule the verdict applied."""

    rule_version: str

    verdict: str
    """Known values: ``screen_pass``, ``screen_fail``, ``screen_incomplete``."""


class ExperimentScreenEvaluationScreenVerdictClause(BaseModel):
    """One screen-rule clause and its counts."""

    clause: str
    """Known values: ``a_feature_moved``, ``b_first_pass_rescue``, ``c_no_net_delivery_loss``, ``d_no_serious_treated_defect``, ``e_judges_no_degradation``.
    """

    detail: ExperimentScreenEvaluationScreenVerdictClauseDetail
    """The clause counts (each clause fills its own members; never a body)."""

    holds: bool


class ExperimentScreenEvaluationScreenVerdictClauseDetail(BaseModel):
    """The clause counts (each clause fills its own members; never a body)."""

    control_delivered: int | None = None

    features: list[ExperimentScreenEvaluationScreenVerdictClauseDetailFeature] | None = None
    """(a) each predicted feature, on the treated vs the control first drafts."""

    min_margin: int | None = None

    min_rescues: int | None = None

    rescues: int | None = None

    treated_delivered: int | None = None

    treated_deliveries_judge_flagged: int | None = None

    treated_deliveries_with_unsupported_claim: int | None = None

    verdicts: list[ExperimentScreenEvaluationScreenVerdictClauseDetailVerdict] | None = None
    """(e) each preregistered judge’s verdict."""


class ExperimentScreenEvaluationScreenVerdictClauseDetailFeature(BaseModel):
    """Response shape ``ExperimentScreenEvaluationScreenVerdictClauseDetailFeature``."""

    attribute: str

    control_first_drafts_with_value: int | None = None

    first_drafts_unmeasured: int | None = None

    focus_value: str

    measurable: bool

    moved: bool | None = None

    reason: str | None = None

    treated_first_drafts_with_value: int | None = None


class ExperimentScreenEvaluationScreenVerdictClauseDetailVerdict(BaseModel):
    """Response shape ``ExperimentScreenEvaluationScreenVerdictClauseDetailVerdict``."""

    judge: str

    verdict: str | None
    """Known values: ``no_evident_degradation``, ``evident_degradation``."""


class ExperimentScreenEvaluationScreenVerdictInputs(BaseModel):
    """The verdict inputs: each execution’s identity, arm, standing, outcome hash and cost reconciliation, the output manifest, and each judgement’s hash and reviewed manifest."""

    candidate_withdrawn: bool

    cap_stopped: bool

    executions: list[ExperimentScreenEvaluationScreenVerdictInputsExecution]

    judgements: list[ExperimentScreenEvaluationScreenVerdictInputsJudgement]

    observations: list[ExperimentScreenEvaluationScreenVerdictInputsObservation]

    output_manifest_hash: str | None
    """The content address of the screen’s output manifest (every screen execution’s final-content hash).
    """

    pairs: list[str]

    phase_holds: ExperimentScreenEvaluationScreenVerdictInputsPhaseHolds


class ExperimentScreenEvaluationScreenVerdictInputsExecution(BaseModel):
    """Response shape ``ExperimentScreenEvaluationScreenVerdictInputsExecution``."""

    arm: str
    """Known values: ``control``, ``treated``."""

    cost: ExperimentExecutionOutcomeCost | None

    execution_id: str

    outcome_hash: str | None

    pair_key: str

    slot: int

    state: str
    """no_outcome: none recorded yet; pending_rows: recorded, a call’s row has not landed; cost_unsettled: a hold is still reserved or ambiguous; invalid: the recorded outcome fails now that its rows landed; complete.

    Known values: ``no_outcome``, ``pending_rows``, ``cost_unsettled``, ``invalid``, ``complete``.
    """


class ExperimentScreenEvaluationScreenVerdictInputsJudgement(BaseModel):
    """Response shape ``ExperimentScreenEvaluationScreenVerdictInputsJudgement``."""

    judge: str

    judgement_hash: str

    manifest_hash: str
    """The output manifest the judge reviewed."""


class ExperimentScreenEvaluationScreenVerdictInputsObservation(BaseModel):
    """Response shape ``ExperimentScreenEvaluationScreenVerdictInputsObservation``."""

    attribute: str

    focus_value: str


class ExperimentScreenEvaluationScreenVerdictInputsPhaseHolds(BaseModel):
    """Response shape ``ExperimentScreenEvaluationScreenVerdictInputsPhaseHolds``."""

    ambiguous: int

    reserved: int


class ExperimentScreenEvaluationScreenVerdictRule(BaseModel):
    """The frozen rule the verdict applied."""

    feature_min_margin: int

    min_first_pass_rescues: int

    unsupported_claim_codes: list[str]


class ExperimentTestEvaluation(BaseModel):
    """The test after an explicit evaluation (counts only until the verdict)."""

    computed: bool
    """True only for the ONE call that computed and stored the decision."""

    experiment_id: str

    experiment_state: str
    """Known values: ``admitted``, ``refused``, ``candidate_frozen``, ``screening``, ``screen_passed``, ``screen_failed``, ``screen_incomplete``, ``awaiting_test_funding``, ``test_open``, ``test_passed``, ``test_failed``, ``test_incomplete``, ``closed``, ``expired``, ``abandoned``.
    """

    object: str
    """Known values: ``flywheel_experiment_test_evaluation``."""

    test: ExperimentTestEvaluationTest
    """The prospective test: barrier counts (no peeking) and, once computed, the decision."""


class ExperimentTestEvaluationTest(BaseModel):
    """The prospective test: barrier counts (no peeking) and, once computed, the decision."""

    executions: list[ExperimentScreenEvaluationScreenExecution]

    manifest_committed: bool

    manifest_hash: str | None

    n: int

    progress: ExperimentTestEvaluationTestProgress
    """The test completion-barrier counts (no per-arm outcome before the verdict)."""

    verdict: ExperimentTestEvaluationTestVerdict | None
    """Null until the completion barrier is met and the decision is stored."""


class ExperimentTestEvaluationTestProgress(BaseModel):
    """The test completion-barrier counts (no per-arm outcome before the verdict)."""

    cap_stopped: bool

    executions_complete: int

    executions_cost_unsettled: int

    executions_enrolled: int

    executions_incomplete: int

    executions_invalid: int

    executions_pending_rows: int

    holds_ambiguous: int

    holds_reserved: int

    judgements_recorded: int

    judges_required: int

    n: int

    outcomes_recorded: int

    pairs_complete: int

    pairs_total: int


class ExperimentTestEvaluationTestVerdict(BaseModel):
    """Null until the completion barrier is met and the decision is stored."""

    candidate_hash: str

    claim_text: str | None
    """The frozen claim text (a pass only) — never more than it is licensed to say."""

    created_at: str

    economics: ExperimentTestEvaluationTestVerdictEconomics | None

    economics_permutations: int

    economics_seed: int

    failing_parts: list[str]
    """Every failing part (test_failed); empty otherwise."""

    goodhart: ExperimentTestEvaluationTestVerdictGoodhart | None

    incomplete_reasons: list[str]
    """Why it can never complete (test_incomplete); else empty."""

    inputs_hash: str

    prereg_hash: str

    primary: ExperimentTestEvaluationTestVerdictPrimary | None

    progress: ExperimentTestEvaluationTestProgress
    """The test completion-barrier counts (no per-arm outcome before the verdict)."""

    quality: ExperimentTestEvaluationTestVerdictQuality | None

    rule: ExperimentTestEvaluationTestVerdictRule

    rule_version: str

    verdict: str
    """Known values: ``test_passed``, ``test_failed``, ``test_incomplete``."""


class ExperimentTestEvaluationTestVerdictEconomics(BaseModel):
    """Response shape ``ExperimentTestEvaluationTestVerdictEconomics``."""

    control_cost_micro_usd: int

    control_deliveries: int

    inconclusive: bool

    min_ratio: float

    pass_: bool = Field(..., alias="pass")

    permutation_p_value: float | None

    permutations: int

    ratio: float | None

    seed: int

    treated_cost_micro_usd: int

    treated_deliveries: int


class ExperimentTestEvaluationTestVerdictGoodhart(BaseModel):
    """Response shape ``ExperimentTestEvaluationTestVerdictGoodhart``."""

    arms: list[ExperimentTestEvaluationTestVerdictGoodhartArm]


class ExperimentTestEvaluationTestVerdictGoodhartArm(BaseModel):
    """Response shape ``ExperimentTestEvaluationTestVerdictGoodhartArm``."""

    arm: str
    """Known values: ``control``, ``treated``."""

    first_draft_cited_quotes_band: dict[str, int]

    first_draft_length_band: dict[str, int]

    repair_count: dict[str, int]

    stranger_usefulness: dict[str, int]


class ExperimentTestEvaluationTestVerdictPrimary(BaseModel):
    """Response shape ``ExperimentTestEvaluationTestVerdictPrimary``."""

    alpha: float

    control_delivered: int

    losses: int

    p_value: float

    pairs_analysed: int

    pass_: bool = Field(..., alias="pass")

    treated_delivered: int

    wins: int


class ExperimentTestEvaluationTestVerdictQuality(BaseModel):
    """Response shape ``ExperimentTestEvaluationTestVerdictQuality``."""

    min_delta: float

    pass_: bool = Field(..., alias="pass")

    per_judge: list[ExperimentTestEvaluationTestVerdictQualityPerJudgeItem]


class ExperimentTestEvaluationTestVerdictQualityPerJudgeItem(BaseModel):
    """Response shape ``ExperimentTestEvaluationTestVerdictQualityPerJudgeItem``."""

    clears: bool

    control_deliveries: int

    control_publishable: int

    control_publishable_rate: float | None

    delta: float | None

    judge: str

    recorded: bool

    serious_treated_defects: int

    treated_deliveries: int

    treated_publishable: int

    treated_publishable_rate: float | None


class ExperimentTestEvaluationTestVerdictRule(BaseModel):
    """Response shape ``ExperimentTestEvaluationTestVerdictRule``."""

    alpha: float

    economics_min_ratio: float

    economics_permutations: int

    economics_seed: int

    n: int

    quality_min_delta: float

    version: str


class ExposureGrantParams(TypedDict, total=False):
    """Mint the deterministic exposure grant for a non-proxied call (never cached)."""

    artifact_key: str
    """The declared artifact key — the cluster key (REQUIRED unless `trace_id` is given)."""

    call_type: str
    """The call type the grant is for (resolves the lever state + the recommended pin)."""

    trace_id: str
    """The trace id — the cluster key when no artifact is declared (REQUIRED unless `artifact_key`).
    """


class ExposureGrant(BaseModel):
    """The exposure grant for a non-proxied call (the arm is assigned by the server, never the caller)."""

    arm: str
    """The exposure arm the grant assigns (the SAME assignment the gateway stamps at dispatch).

    Known values: ``treated``, ``holdout``, ``lever_holdout``, ``pre_lever``.
    """

    epoch: int
    """The assignment epoch (lift is never pooled across epochs)."""

    grant_id: str
    """Deterministic: hash of workspace + cluster key + epoch (idempotent)."""

    lever_id: str | None
    """The lever family when the arm is lever-derived, else null."""

    object: str
    """Known values: ``exposure_grant``."""

    request_id: str
    """The zero-cost `status=preflight` served-record id (the served proof)."""

    valid_until_epoch_close: str
    """A conservative ISO validity horizon; re-mint on a newer epoch (never cached)."""


class MoatNext(BaseModel):
    """What your moat needs next — per-unit readiness + the missing-precondition sentence."""

    experiment: MoatNextExperiment | None
    """The current bounded experiment, or null — benchmarkable is always false."""

    items: list[MoatNextItem]

    object: str
    """Known values: ``flywheel_moat_next``."""

    workspace_id: str


class MoatNextExperiment(BaseModel):
    """The current bounded experiment, or null — benchmarkable is always false."""

    admission: MoatNextExperimentAdmission | None
    """The frozen admission verdict — admitted + the rules applied + the evidence (the owner receipt).
    """

    benchmarkable: bool
    """Known values: ``False``."""

    budget: MoatNextExperimentBudget
    """The experiment budget caps + running spend (micro-USD)."""

    expires_at: str | None

    id: str

    prereg_hash: str

    reservations: MoatNextExperimentReservations | None = None
    """The atomic per-call reservation ledger: the experiment total + each phase (micro-USD)."""

    state: str
    """Known values: ``admitted``, ``refused``, ``candidate_frozen``, ``screening``, ``screen_passed``, ``screen_failed``, ``screen_incomplete``, ``awaiting_test_funding``, ``test_open``, ``test_passed``, ``test_failed``, ``test_incomplete``, ``closed``, ``expired``, ``abandoned``.
    """

    verifier_version: str


class MoatNextExperimentAdmission(BaseModel):
    """The frozen admission verdict — admitted + the rules applied + the evidence (the owner receipt)."""

    admitted: bool

    applied: MoatNextExperimentAdmissionApplied
    """The frozen thresholds the admission applied."""

    evidence: MoatNextExperimentAdmissionEvidence
    """The mechanical evidence the admission weighed (verifier verdict + the fit-split counts)."""

    refusals: list[str]
    """Every failing admission rule, by name (empty ⇒ admitted)."""


class MoatNextExperimentAdmissionApplied(BaseModel):
    """The frozen thresholds the admission applied."""

    budget_cap_micro_usd: int

    expiry_days: int

    min_contrast_ideas: int

    min_delivered_fit: int

    min_held_fit: int

    min_resolved_fit: int

    screen_subcap_micro_usd: int

    verifier_version: str


class MoatNextExperimentAdmissionEvidence(BaseModel):
    """The mechanical evidence the admission weighed (verifier verdict + the fit-split counts)."""

    contrast_ideas_fit: int

    delivered_fit: int

    held_fit: int

    resolved_fit_executions: int

    verifier_refusals: list[str]

    verifier_version: str


class MoatNextExperimentBudget(BaseModel):
    """The experiment budget caps + running spend (micro-USD)."""

    cap_micro_usd: int

    screen_subcap_micro_usd: int

    spend_micro_usd: int


class MoatNextExperimentReservations(BaseModel):
    """The atomic per-call reservation ledger: the experiment total + each phase (micro-USD)."""

    ambiguous_micro_usd: int

    phases: list[MoatNextExperimentReservationsPhase]

    remaining_micro_usd: int

    reserved_micro_usd: int

    spent_micro_usd: int


class MoatNextExperimentReservationsPhase(BaseModel):
    """One phase of the atomic reservation ledger (micro-USD)."""

    ambiguous_micro_usd: int
    """Reserve held for an interrupted/unknown-outcome call, still counted against the cap."""

    cap_micro_usd: int

    funded: bool
    """Whether the phase has a funded cap (the prospective-test phase starts unfunded)."""

    phase: str
    """Known values: ``screen``, ``test``."""

    remaining_micro_usd: int

    reserved_micro_usd: int

    spent_micro_usd: int


class MoatNextItem(BaseModel):
    """What one unit of the moat needs next: ready + verdict, or the named missing precondition."""

    call_type_id: str | None

    lever_family: str

    missing: list[MoatNextPrecondition]
    """Every unmet precondition; empty when ready."""

    next_action: str
    """The customer next-action SENTENCE — always present (never a bare boolean)."""

    primary_missing: MoatNextPrecondition | None
    """The primary missing precondition (the first blocker), or null when ready."""

    ready: bool

    scheduled: bool
    """True when the unit was actually scheduled to run."""

    situation_class: str

    verdict: str
    """Known values: ``run``, ``below_hurdle``, ``cost_exceeds_budget``, ``not_ready``."""


class MoatNextPrecondition(BaseModel):
    """An unmet readiness precondition — the code + the customer sentence."""

    message: str
    """The customer sentence naming exactly what is missing. For the `below_benchmarkable` lifecycle blocker it reports resolved CLAIMS and resolved TASK OUTCOMES as separate counts (a task-only unit reads "needs N more resolved task outcomes (n/200). Failure location may still be unknown."). A claim-less artifact contributes at most one resolved task outcome.
    """

    precondition: str
    """The closed readiness-precondition code."""

    reason: str
    """The machine reason code (stable)."""


class OracleRegisterParams(TypedDict, total=False):
    """Register a check (a platform-evaluated kind, or a push / pull check you host)."""

    kind: Required[
        Literal["label_set", "schema_rules", "test_endpoint", "reconciliation", "customer_ci"]
    ]
    """`label_set` / `schema_rules` = platform checks (in-process, no egress); `test_endpoint` = a PUSH endpoint; `reconciliation` = push or pull; `customer_ci` = a PULL harness.
    """

    oracle_id: str
    """Append a new VERSION of this workspace’s existing oracle (same kind + transport). Absent ⇒ a new `orc_` id.
    """

    spec: Required[dict[str, Any]]
    """The check definition (strict — an unknown key is refused). `label_set`: `{labels[], field?, case_insensitive?}`. `schema_rules`: `{schema, rules[]}` (rules over `equals | within_tolerance | ge | le`). Push (`test_endpoint` / push `reconciliation`): `{url, contract_version}` — the URL must pass the SSRF egress guard (https; never a private / metadata / link-local host). Pull `reconciliation`: `{contract_version}`. `customer_ci`: `{harness_identity}`. The VERSION is the sha256 of the canonical definition: a new spec is a new version (its qualification starts from nothing).
    """

    transport: Literal["platform", "push", "pull"]
    """Default: the kind’s first transport."""


class OracleRegistration(BaseModel):
    """A registered oracle version."""

    cancelled_jobs: int
    """Open jobs of a superseded version this registration cancelled."""

    inserted: bool
    """False when the spec equals the current version (a no-op)."""

    kind: str
    """`label_set` / `schema_rules` = platform checks (in-process, no egress); `test_endpoint` = a PUSH endpoint; `reconciliation` = push or pull; `customer_ci` = a PULL harness.

    Known values: ``label_set``, ``schema_rules``, ``test_endpoint``, ``reconciliation``, ``customer_ci``.
    """

    object: str
    """Known values: ``oracle_registration``."""

    oracle_id: str
    """The platform-minted `orc_…` id (a receipt’s verifier id)."""

    secret: str | None
    """The push / pull HMAC SIGNING SECRET — returned exactly ONCE, when a new push / pull oracle is registered (null otherwise). Store it now: it is never shown again (rotate it with `…/rotate-secret`).
    """

    secret_last4: str | None
    """The last 4 characters of a newly minted secret."""

    source: str
    """The verdict source the version is qualified as: `oracle:<id>@<version>`."""

    superseded_version_hash: str | None
    """The version this one superseded (its receipts stop admitting), or null."""

    transport: str
    """`platform` = evaluated in-process; `push` = the platform POSTs each job to your HTTPS endpoint (SSRF-guarded); `pull` = your worker / CI claims jobs and posts signed verdicts.

    Known values: ``platform``, ``push``, ``pull``.
    """

    version_hash: str
    """The content hash of the canonical definition."""

    version_id: str


class Oracle(BaseModel):
    """An oracle and the role its current version earned."""

    current: OracleCurrent

    kind: str
    """`label_set` / `schema_rules` = platform checks (in-process, no egress); `test_endpoint` = a PUSH endpoint; `reconciliation` = push or pull; `customer_ci` = a PULL harness.

    Known values: ``label_set``, ``schema_rules``, ``test_endpoint``, ``reconciliation``, ``customer_ci``.
    """

    object: str
    """Known values: ``oracle``."""

    oracle_id: str

    revoked: bool

    role: OracleRole

    source: str

    transport: str
    """`platform` = evaluated in-process; `push` = the platform POSTs each job to your HTTPS endpoint (SSRF-guarded); `pull` = your worker / CI claims jobs and posts signed verdicts.

    Known values: ``platform``, ``push``, ``pull``.
    """

    transport_state: OracleTransportState | None
    """Push / pull only (null for a platform check). Never a secret, a salt or a body."""

    versions: list[OracleVersion]


class OracleCurrent(BaseModel):
    """Response shape ``OracleCurrent``."""

    created_at: str

    created_by: str

    spec: Any = None
    """The canonical spec (configuration — never a secret)."""

    version_hash: str

    version_id: str


class OracleRole(BaseModel):
    """Response shape ``OracleRole``."""

    certifier_refusal: str | None
    """Known values: ``false_pass_observed``, ``not_certified``."""

    false_passes_observed: int

    measurements: int

    qualified: bool

    reason: str
    """Known values: ``certifier``, ``detector``, ``not_qualified``, ``revoked``."""

    role: str | None
    """`detector` = the source-health bars (planted recall ≥ 0.8, control specificity ≥ 0.9); `certifier` = those bars + ZERO false passes over ≥ 73 planted probes (Wilson 95 % upper ≤ 5 %) and no false pass ever observed on this version; null = not qualified (or revoked / failed / a canary false pass).

    Known values: ``detector``, ``certifier``.
    """


class OracleTransportState(BaseModel):
    """Push / pull only (null for a platform check). Never a secret, a salt or a body."""

    canaries: OracleTransportStateCanaries
    """RESOLVED canary outcomes only."""

    canary_pool: OracleTransportStateCanaryPool

    jobs: OracleTransportStateJobs

    qualification: OracleTransportStateQualification | None

    secret_last4: str

    secret_rotated_at: str | None


class OracleTransportStateCanaries(BaseModel):
    """RESOLVED canary outcomes only."""

    caught: int

    false_passes: int

    unanswered: int


class OracleTransportStateCanaryPool(BaseModel):
    """Response shape ``OracleTransportStateCanaryPool``."""

    available: bool

    examples: int

    stored_at: str | None


class OracleTransportStateJobs(BaseModel):
    """Response shape ``OracleTransportStateJobs``."""

    answered: int

    cancelled: int

    claimed: int

    failed: int

    lapsed_leases: int

    pending: int


class OracleTransportStateQualification(BaseModel):
    """Response shape ``OracleTransportStateQualification``."""

    answered: int

    check_id: str

    dead: int

    open: int

    total: int


class OracleVersion(BaseModel):
    """Response shape ``OracleVersion``."""

    created_at: str

    version_hash: str

    version_id: str


class OracleClaimParams(TypedDict, total=False):
    """Claim pull jobs."""

    lease_seconds: int
    """The lease (default 900 s): a verdict after it is refused `lease_expired`."""

    max: int
    """At most this many jobs (default 10)."""


class OracleJobList(BaseModel):
    """Claimed jobs — the payloads are returned ONCE and deleted; judge each and post a verdict."""

    data: list[OracleJob]

    lease_until: str

    object: str
    """Known values: ``list``."""

    oracle_id: str

    unavailable: int
    """Due jobs whose payload was already swept (failed `payload_unavailable`)."""


class OracleJob(BaseModel):
    """One oracle job (the push request body / a pull claim entry)."""

    candidate_sha256: str
    """sha256 of `output` — your verdict must echo it (binds the verdict to this candidate)."""

    due_at: str

    input: str
    """The task input."""

    issued_at: str

    job_id: str
    """The server-issued job id your verdict must echo."""

    object: str
    """Known values: ``oracle_job``."""

    oracle_id: str

    oracle_version: str
    """The oracle version your verdict must ECHO (a mismatch is refused)."""

    output: str
    """The candidate output to judge."""

    schema_: str = Field(..., alias="schema")
    """Known values: ``ur.oracle.v1``."""


class OracleQualifyParams(TypedDict, total=False):
    """Qualify an oracle (the role is EARNED in the tenant ledger)."""

    examples: Required[list[OracleExampleParams]]
    """≥ 10 DISTINCT known-good examples (duplicates collapse; ≤ 50 are used). Each yields TWO planted failures (omission / wrong value / truncation / instruction loss) and ONE valid rewrite. The certifier bar needs ≥ 73 planted probes, so ≥ 37 distinct examples.
    """


class OracleExampleParams(TypedDict, total=False):
    """A known-good example: the platform plants failures into it and keeps it as a control."""

    input: Required[str]

    output: Required[str]


class OracleQualification(BaseModel):
    """An oracle qualification."""

    bar: str | None
    """Known values: ``source_health``, ``certifier``."""

    certifier: OracleQualificationCertifier | None
    """The certifier bar (null until graded)."""

    check_id: str

    controls: int

    delivery_errors: dict[str, int]
    """Push only: failed deliveries by closed transport-error code."""

    detector: OracleQualificationDetector | None
    """The source-health detector bars (null until graded)."""

    examples: OracleQualificationExamples

    jobs: OracleQualificationJobs
    """The probe jobs (a platform qualification has none — all zero)."""

    object: str
    """Known values: ``oracle_qualification``."""

    oracle_id: str

    planted: int

    result: str | None
    """Known values: ``passed``, ``failed``."""

    role: str | None
    """`detector` = the source-health bars (planted recall ≥ 0.8, control specificity ≥ 0.9); `certifier` = those bars + ZERO false passes over ≥ 73 planted probes (Wilson 95 % upper ≤ 5 %) and no false pass ever observed on this version; null = not qualified (or revoked / failed / a canary false pass).

    Known values: ``detector``, ``certifier``.
    """

    source: str

    status: str
    """`graded` = one ledger event recorded; `pending` = pull probes await your worker (graded when the last is answered); `incomplete` = a push probe errored (timeout / refusal / bad signature …) — nothing recorded, fix the endpoint and qualify again (an error is never a pass).

    Known values: ``graded``, ``pending``, ``incomplete``.
    """

    transport: str
    """`platform` = evaluated in-process; `push` = the platform POSTs each job to your HTTPS endpoint (SSRF-guarded); `pull` = your worker / CI claims jobs and posts signed verdicts.

    Known values: ``platform``, ``push``, ``pull``.
    """

    version_hash: str


class OracleQualificationCertifier(BaseModel):
    """The certifier bar (null until graded)."""

    errors: list[str]

    false_pass_upper: float

    false_passes: int

    pass_: bool = Field(..., alias="pass")

    planted: int


class OracleQualificationDetector(BaseModel):
    """The source-health detector bars (null until graded)."""

    recall: float

    specificity: float


class OracleQualificationExamples(BaseModel):
    """Response shape ``OracleQualificationExamples``."""

    skipped: dict[str, int]

    supplied: int

    used: int


class OracleQualificationJobs(BaseModel):
    """The probe jobs (a platform qualification has none — all zero)."""

    answered: int

    failed: int

    open: int

    total: int


class OracleRevokeParams(TypedDict, total=False):
    """Revoke an oracle (terminal) — no fields."""


class OracleRevocation(BaseModel):
    """A revoked oracle: every receipt of every version stops admitting; open jobs are cancelled."""

    already_revoked: bool

    cancelled_jobs: int

    object: str
    """Known values: ``oracle_revocation``."""

    oracle_id: str

    revoked_sources: list[str]
    """The version sources newly revoked."""


class OracleTestParams(TypedDict, total=False):
    """Send test — prove the check end to end; nothing is graded."""

    probe: OracleProbeParams
    """PLATFORM checks only: the probe to evaluate in-process (default: the synthetic test probe). A push / pull test always carries the platform’s synthetic probe (400 `test_probe_not_allowed` otherwise).
    """


class OracleProbeParams(TypedDict, total=False):
    """PLATFORM checks only: the probe to evaluate in-process (default: the synthetic test probe). A push / pull test always carries the platform’s synthetic probe (400 `test_probe_not_allowed` otherwise)."""

    input: Required[str]

    output: Required[str]


class OracleTestResult(BaseModel):
    """A send-test result (logged as a `test` run; never graded)."""

    error: str | None
    """A closed transport-error code when the call failed."""

    job_id: str | None

    latency_ms: int | None

    object: str
    """Known values: ``oracle_test``."""

    oracle_id: str

    reasons: list[str]

    request: OracleTestResultRequest | None
    """The EXACT job payload sent (push) / queued (pull) — the synthetic probe; null in-process."""

    status: str
    """`pending` = a pull test job awaits your worker (claim + answer it like any job).

    Known values: ``answered``, ``error``, ``pending``.
    """

    transport: str
    """`platform` = evaluated in-process; `push` = the platform POSTs each job to your HTTPS endpoint (SSRF-guarded); `pull` = your worker / CI claims jobs and posts signed verdicts.

    Known values: ``platform``, ``push``, ``pull``.
    """

    verdict: str | None
    """`pass` = the candidate is right; `fail` = it is wrong. An error is never a pass.

    Known values: ``pass``, ``fail``.
    """

    version_hash: str


class OracleTestResultRequest(BaseModel):
    """The EXACT job payload sent (push) / queued (pull) — the synthetic probe; null in-process."""

    body: OracleJob
    """One oracle job (the push request body / a pull claim entry)."""

    url: str | None


class OracleVerdictsParams(TypedDict, total=False):
    """Post verdicts for claimed jobs."""

    verdicts: Required[list[OracleVerdictParams]]


class OracleVerdictParams(TypedDict, total=False):
    """One verdict, bound to its server-issued job (id + echoed version + candidate hash)."""

    candidate_sha256: Required[str]

    job_id: Required[str]

    oracle_version: Required[str]

    reasons: list[
        Literal[
            "wrong_value",
            "missing_field",
            "extra_field",
            "format_invalid",
            "schema_invalid",
            "rule_failed",
            "execution_failed",
            "truncated",
            "off_task",
            "mismatch",
            "other",
        ]
    ]
    """Closed reason codes for a `fail` (a `pass` carries none)."""

    verdict: Required[Literal["pass", "fail"]]
    """`pass` = the candidate is right; `fail` = it is wrong. An error is never a pass."""


class OracleVerdictsResult(BaseModel):
    """The recorded verdicts (a replay of the same verdict is `duplicate` — a visible no-op)."""

    accepted: int

    conflict: int

    data: list[OracleVerdictResult]

    duplicate: int

    object: str
    """Known values: ``list``."""

    oracle_id: str

    qualification: list[OracleQualificationOutcome]
    """Qualification checks this post completed (graded now)."""

    refused: int


class OracleVerdictResult(BaseModel):
    """Response shape ``OracleVerdictResult``."""

    job_id: str

    reason: str | None
    """The NAMED refusal: `job_not_found` | `job_not_claimed` | `job_closed` | `lease_expired` | `version_mismatch` | `candidate_mismatch` | `malformed_reply` | `conflict`.
    """

    status: str
    """Known values: ``accepted``, ``duplicate``, ``conflict``, ``refused``."""


class OracleQualificationOutcome(BaseModel):
    """Response shape ``OracleQualificationOutcome``."""

    bar: str
    """Known values: ``source_health``, ``certifier``."""

    check_id: str

    result: str
    """Known values: ``passed``, ``failed``."""

    role: str | None
    """`detector` = the source-health bars (planted recall ≥ 0.8, control specificity ≥ 0.9); `certifier` = those bars + ZERO false passes over ≥ 73 planted probes (Wilson 95 % upper ≤ 5 %) and no false pass ever observed on this version; null = not qualified (or revoked / failed / a canary false pass).

    Known values: ``detector``, ``certifier``.
    """


class LearningPlanEnvelope(BaseModel):
    """The learning plan for a workflow (null while collecting)."""

    object: str
    """Known values: ``learning_plan_envelope``."""

    plan: LearningPlan | None
    """One learning-plan version (metadata + the compiled program, never a body)."""

    workflow_id: str


class LearningPlan(BaseModel):
    """One learning-plan version (metadata + the compiled program, never a body)."""

    artifact_type_version_id: str

    call_type_bindings: list[LearningPlanCallTypeBinding]

    created_at: str

    fields_: list[dict[str, Any]] = Field(..., alias="fields")

    id: str

    object: str
    """Known values: ``learning_plan``."""

    plan_input_digest: str

    proposal_version: int

    review_state: str
    """The learning-plan lifecycle state.

    Known values: ``proposed``, ``confirmed``, ``declined``, ``deferred``, ``stale``.
    """

    spec_hash: str

    version: int

    workflow_id: str


class LearningPlanCallTypeBinding(BaseModel):
    """A derived call-type role binding + its label-field proposal / confirmed field."""

    call_type_id: str

    label_field: str | None = None

    label_field_origin: str | None = None
    """Known values: ``plan_confirmed``, ``schema_convention``."""

    label_field_proposal: LearningPlanCallTypeBindingLabelFieldProposal | None = None
    """The structurally-proposed reference-agreement label field for a bound call type."""

    role: str
    """Known values: ``intermediate``, ``terminal``, ``reviewer``."""


class LearningPlanCallTypeBindingLabelFieldProposal(BaseModel):
    """The structurally-proposed reference-agreement label field for a bound call type."""

    basis: str
    """Known values: ``corrections``, ``convention``, ``none``."""

    candidates: list[LearningPlanCallTypeBindingLabelFieldProposalCandidate]

    path: str | None


class LearningPlanCallTypeBindingLabelFieldProposalCandidate(BaseModel):
    """A candidate reference-agreement label field + its change evidence (counts only)."""

    changed: int

    path: str

    total: int


class LearningPlanList(BaseModel):
    """The workspace's learning-plan proposals — the discovery surface for what to confirm."""

    object: str
    """Known values: ``learning_plan_list``."""

    plans: list[LearningPlanProposal]

    workspace_id: str


class LearningPlanProposal(BaseModel):
    """One learning-plan proposal in the discovery list (metadata only, never a body)."""

    created_at: str

    id: str
    """The plan id — the id `POST /v1/flywheel/plan/{id}/confirm` accepts."""

    object: str
    """Known values: ``learning_plan_proposal``."""

    provenance: str
    """inferred = derived from the inferred site brief (a zero-traffic seed); declared = derived from the workspace's OWN traffic. Declared, inferred and gateway provenance are never conflated.

    Known values: ``inferred``, ``declared``.
    """

    review_state: str
    """The learning-plan lifecycle state.

    Known values: ``proposed``, ``confirmed``, ``declined``, ``deferred``, ``stale``.
    """

    workflow_id: str


class PromptCandidateList(BaseModel):
    """The workspace hosted-prompt candidates — the inbox discovery surface."""

    candidates: list[PromptCandidate]

    object: str
    """Known values: ``hosted_prompt_candidates``."""

    workspace_id: str


class PromptCandidate(BaseModel):
    """One customer-drafted hosted-prompt candidate in the ONE Improvements inbox."""

    approve_refusal: str | None
    """The NAMED approve gate (`not_confirmed_live` until the live confirmation is confirmed), or null (approvable).
    """

    call_type_id: str | None

    content_sha256: str
    """The candidate template content sha (the diff-as-shas — never the template text)."""

    epoch: int
    """The learned_context measurement epoch the run is bound to."""

    is_active_version: bool
    """True when this version is ALREADY the call type’s active version (approved)."""

    live_result: str | None
    """The live confirmation’s one-look result (pending | confirmed | refuted | inconclusive), or null.
    """

    live_status: str | None
    """The candidate’s live-confirmation status (open | adopted | closed | …), or null when none opened.
    """

    object: str
    """Known values: ``hosted_prompt_candidate``."""

    provenance: str
    """Always "your draft" — a customer-drafted version, neither correction- nor eval-derived.

    Known values: ``human_draft``.
    """

    run_id: str
    """The screening run id — the id a decision (approve/reject) takes."""

    started_at: str

    status: str
    """The DERIVED run status: screening | screened | confirming | rejected | parked | …"""

    version_id: str
    """The candidate hosted-prompt VERSION id (the diff-as-ids identity)."""


class ReviewerEventsParams(TypedDict, total=False):
    """A signed batch of reviewer decisions."""

    backfill: ReviewerBackfillParams
    """A declared backfill window."""

    events: Required[list[ReviewerEvent]]
    """1..500 reviewer decisions."""

    reviewer_system: str
    """A label for the reviewer system (metadata only; shown in health)."""


class ReviewerBackfillParams(TypedDict, total=False):
    """A declared backfill window."""

    complete: bool
    """Mark the backfill finished. We NEVER infer completion from counts."""

    id: Required[str]
    """The customer’s id for this backfill run."""

    total: int
    """The total the client expects to send (progress denominator; optional)."""


class ReviewerEvent(TypedDict, total=False):
    """One reviewer decision. Provenance + learning use are the server’s."""

    artifact_id: str
    """The artifact id this review is about (or send `artifact_key`)."""

    artifact_key: str
    """The stable artifact key this review is about (or send `artifact_id`)."""

    artifact_version: Required[int]
    """The EXACT draft version the human reviewed. A mismatch is HELD for repair, never guessed."""

    decision: Required[Literal["approved", "approved_with_edits", "rejected", "regenerated"]]
    """The reviewer’s verdict (closed vocabulary)."""

    effective_at: Required[str]
    """When the decision happened in the customer’s world (ISO-8601)."""

    event_id: Required[str]
    """The reviewer system’s own stable event id — the idempotency key. A replay is a no-op."""

    final: ReviewerFinalParams
    """The optional, consented final the reviewer approved."""

    reviewer_id: str
    """An opaque reviewer identifier — an id, never a name or email."""


class ReviewerFinalParams(TypedDict, total=False):
    """The optional, consented final the reviewer approved."""

    diff_stats: DiffStatsParams
    """CLIENT-computed diff stats (the no-consent path)."""

    draft: str
    """The draft the reviewer edited — used ONLY to compute server-side diff stats."""

    hash: str
    """The final content hash (never a body)."""

    text: str
    """The approved final body — stored ONLY under corrections_consent."""


class ReviewerEventsResponse(BaseModel):
    """The per-event reviewer verdicts + a rollup."""

    accepted: int

    adapter: str
    """The pinned adapter contract version (e.g. `reviewer.v1`)."""

    data: list[ReviewerEventResult]

    duplicate: int

    object: str
    """Known values: ``reviewer_events``."""

    rejected: int

    unsupported: int


class ReviewerEventResult(BaseModel):
    """One reviewer event’s verdict."""

    artifact_id: str | None

    artifact_version: int | None

    channel: str | None
    """The mapped outcome channel (always `correction`)."""

    event_id: str

    final_version: int | None
    """The appended final version, when one was sent."""

    kind: str | None
    """The mapped outcome kind."""

    latency_class: str | None
    """Known values: ``instant``, ``delayed``."""

    learning_use: list[str] | None
    """The SERVER-derived learning use — echoed so it is visibly not the caller’s to set."""

    outcome_event_id: str | None

    reason: str
    """The NAMED refusal, or the accepted marker set (`delayed`, `final_absent`, …)."""

    repairable: bool
    """Whether re-driving this same event id can fix it."""

    status: str
    """accepted | duplicate (a replay — a visible no-op) | rejected | unsupported.

    Known values: ``accepted``, ``duplicate``, ``rejected``, ``unsupported``.
    """


class ReviewerHealth(BaseModel):
    """Reviewer-integration health: the six named states + the next repair action."""

    adapter: str

    backfills: list[ReviewerBackfillProgress]
    """(6) Backfill progress, per declared id."""

    dead_letter_total: int

    dead_letters: list[ReviewerDeadLetter]

    events: ReviewerHealthEventCounts
    """The named integration states (counts only — NEVER a body)."""

    last_success_at: str | None
    """(1) The last successful event — null until one lands."""

    last_success_event_id: str | None

    next_repair: ReviewerHealthNextRepair
    """The ONE next repair action. An unnameable dead letter is never `none`."""

    object: str
    """Known values: ``reviewer_health``."""


class ReviewerBackfillProgress(BaseModel):
    """One backfill’s progress."""

    accepted: int

    complete: bool
    """Declared by the client — never inferred from counts."""

    declared_total: int | None

    id: str

    received: int

    rejected: int


class ReviewerDeadLetter(BaseModel):
    """A dead-lettered reviewer event awaiting repair."""

    created_at: str

    event_id: str

    reason: str
    """The NAMED refusal (e.g. `version_mismatch:claimed=2,current=3`)."""


class ReviewerHealthEventCounts(BaseModel):
    """The named integration states (counts only — NEVER a body)."""

    accepted: int

    delayed: int
    """(4) Accepted events the ledger classed `delayed`."""

    duplicate: int
    """(2) Replays absorbed as visible no-ops."""

    rejected: int
    """(5) Events refused for another named reason."""

    unmatched: int
    """(3) Events whose artifact link did not resolve here."""

    unsupported: int
    """Events this deployment cannot act on at all."""


class ReviewerHealthNextRepair(BaseModel):
    """The ONE next repair action. An unnameable dead letter is never `none`."""

    action: str
    """Known values: ``none``, ``send_test_event``, ``repair_version``, ``create_artifact``, ``grant_consent``, ``contact_support``.
    """

    detail: str

    event_id: str | None


class ReviewerRepairParams(TypedDict, total=False):
    """Repair ONE dead-lettered reviewer event."""

    event: Required[ReviewerEvent]
    """The FULL original event (your durable queue still holds it — we keep receipts, not payloads).
    """

    repin_to_current_version: bool
    """Re-pin to the artifact’s CURRENT version. OPT-IN: a stale pin is never silently corrected."""

    reviewer_system: str


class ReviewerRepairResult(BaseModel):
    """The dead-letter repair result."""

    before: ReviewerRepairBefore
    """The receipt’s status + named refusal before the repair."""

    event_id: str

    object: str
    """Known values: ``reviewer_repair``."""

    result: ReviewerEventResult | None
    """The verdict after re-driving; null when the receipt was already accepted (never rewritten).
    """


class ReviewerRepairBefore(BaseModel):
    """The receipt’s status + named refusal before the repair."""

    reason: str

    status: str


class ReviewerSetup(BaseModel):
    """The guided-setup payload for the reviewer adapter."""

    adapter: str

    corrections_consent: bool
    """Whether a final BODY may be stored. Off ⇒ send diff_stats/final_hash only."""

    endpoint: str
    """The path to POST signed reviewer events to."""

    events_received: int
    """Reviewer events this producer has delivered so far."""

    mapping: list[ReviewerMappingRow]

    object: str
    """Known values: ``reviewer_setup``."""

    required_scope: str

    signature: ReviewerSignatureRecipe
    """The signed-webhook recipe. The secret itself is never echoed."""

    test_artifact_key: str
    """The reserved key the guided-setup test event uses."""


class ReviewerMappingRow(BaseModel):
    """What one reviewer decision becomes in the ledger (a mapping preview)."""

    accepts_final: bool

    channel: str

    decision: str
    """The reviewer’s verdict (closed vocabulary).

    Known values: ``approved``, ``approved_with_edits``, ``rejected``, ``regenerated``.
    """

    kind: str

    note: str


class ReviewerSignatureRecipe(BaseModel):
    """The signed-webhook recipe. The secret itself is never echoed."""

    algorithm: str
    """`HMAC-SHA256 over "<unix-seconds>.<raw body>"`."""

    header: str

    key: str
    """WHICH secret signs: your ultrarouter API key. Never returned here — you already hold it."""

    timestamp_header: str

    tolerance_seconds: int


class ReviewerTestParams(TypedDict, total=False):
    """Run one guided-setup reviewer scenario."""

    scenario: Literal["happy", "replay", "version_mismatch"]
    """`happy` (default) sends the pair; `replay` re-sends it; `version_mismatch` dead-letters."""


class ReviewerTestResult(BaseModel):
    """The guided-setup test result."""

    artifact: Artifact
    """The reserved test artifact (lifecycle `test`)."""

    excluded_from_invoicing: bool
    """Test data never enters invoicing: the setup path is unmetered."""

    excluded_from_learning: bool
    """Test data never enters learning: no exposure arm ⇒ excluded from the attribution and calibration rollups.
    """

    object: str
    """Known values: ``reviewer_test``."""

    result: ReviewerEventResult
    """The review event that landed on it — the joined pair."""

    scenario: str
    """Known values: ``happy``, ``replay``, ``version_mismatch``."""


class VerdictSourceCheckParams(TypedDict, total=False):
    """Issue a planted-failure check to the calling verdict source."""

    call_type_id: Required[str]
    """The call type whose GOLDEN SET supplies the known-good references: up to 50 distinct golden references, each yielding ONE planted failure (an omission / wrong value / truncation / instruction-loss mutation) and ONE valid alternative, shuffled. The source never supplies its own references — a legacy `items` field is refused (400).
    """


class VerdictSourceCheck(BaseModel):
    """An issued planted-failure check — the probes are returned ONCE and never stored."""

    call_type_id: str
    """The call type whose golden set supplied the references."""

    created_at: str

    golden_set_id: str
    """The golden set the known-good references were drawn from."""

    id: str
    """The check id (`vsc_…`) the verdicts are posted to."""

    object: str
    """Known values: ``verdict_source_check``."""

    probe_count: int

    probes: list[VerdictSourceProbe]

    status: str
    """Known values: ``open``."""

    verdict_source: str
    """The verdict source under test — the server-assigned producer of the issuing credential (`api_key:<id>` | `session:<user>`). Only this source may answer the check.
    """


class VerdictSourceProbe(BaseModel):
    """One planted-failure-check probe (its planted/control truth is hidden)."""

    input: str
    """The task input (verbatim from the supplied item)."""

    output: str
    """The probe output to judge (a planted failure OR a valid alternative)."""

    probe_id: str
    """The opaque probe id (shuffled order — reveals nothing)."""


class VerdictSourceGradeParams(TypedDict, total=False):
    """The source’s verdicts on a planted-failure check."""

    verdicts: Required[list[VerdictSourceVerdictParams]]
    """Exactly ONE verdict per probe. A missing, duplicate or unknown probe is a 400 and records NOTHING.
    """


class VerdictSourceVerdictParams(TypedDict, total=False):
    """The source’s verdict on one probe (the outcome-event resolution vocabulary, binary)."""

    kind: Required[Literal["resolved_true", "resolved_false"]]
    """`resolved_true` = the probe output meets the objective; `resolved_false` = it fails it."""

    probe_id: Required[str]


class VerdictSourceCheckResult(BaseModel):
    """A graded planted-failure check — an append-only, versioned qualification event."""

    check_id: str

    errors: list[str]
    """Machine-readable reasons a check did not pass."""

    graded_at: str

    object: str
    """Known values: ``verdict_source_check_result``."""

    per_family: list[VerdictSourceCheckResultPerFamilyItem]
    """Recall per planted-failure family (diagnostic)."""

    qualified: bool
    """Whether the source is qualified AFTER this grade."""

    recall: VerdictSourceCheckResultRecall
    """Planted failures reported `resolved_false` (bar = the per-family recall bar 0.8)."""

    result: str
    """`passed` qualifies (or clears) the source; `failed` REVOKES its qualification.

    Known values: ``passed``, ``failed``.
    """

    specificity: VerdictSourceCheckResultRecall
    """Valid alternatives reported `resolved_true` (bar = the specificity bar 0.9)."""

    verdict_source: str


class VerdictSourceCheckResultPerFamilyItem(BaseModel):
    """Response shape ``VerdictSourceCheckResultPerFamilyItem``."""

    caught: int

    family: str

    planted: int


class VerdictSourceCheckResultRecall(BaseModel):
    """Planted failures reported `resolved_false` (bar = the per-family recall bar 0.8)."""

    applicable: int

    bar: float

    hits: int

    min_applicable: int

    pass_: bool = Field(..., alias="pass")

    value: float


class VerdictSourceList(BaseModel):
    """The workspace’s verdict sources and their health."""

    data: list[VerdictSource]

    object: str
    """Known values: ``list``."""


class VerdictSource(BaseModel):
    """One verdict source’s health."""

    admitted_until: str | None
    """The newest verdict time a passed ADMISSION audit vouches for — verdicts recorded at or before it count (retrospective only); null when no admission passed.
    """

    eligible: bool
    """Whether this source’s NEW task verdicts count toward readiness now."""

    eligible_task_verdicts: int
    """Of those, how many count toward readiness now (the SAME rule the readiness count applies)."""

    last_admission: VerdictSourceLastAdmission | None
    """The latest graded ADMISSION audit."""

    last_audit: VerdictSourceLastAdmission | None
    """The latest graded CLEARANCE audit."""

    last_check: VerdictSourceLastAdmission | None
    """The latest graded check or audit of a verdict source."""

    last_clearance_at: str | None
    """The newest verdict time a passed check or blind audit vouches for."""

    qualified: bool

    qualified_since: str | None
    """When the current qualified period began."""

    reason: str
    """`not_qualified` = no passed planted-failure check (or a failed one revoked it); `review_flag` = ≥ 99 % success over ≥ 200 task outcomes since the last clearance (held, not rejected — clear it with a re-run check or a 40-task blind audit); `revoked` = the source’s credential was deleted (terminal — none of its verdicts count any more).

    Known values: ``eligible``, ``not_qualified``, ``review_flag``, ``revoked``.
    """

    review_flag: VerdictSourceReviewFlag
    """The review flag over the task outcomes recorded since the last clearance."""

    revoked: bool
    """The source’s credential was deleted — terminal."""

    task_verdicts: int
    """Resolved task verdicts this source reported (one per artifact)."""

    verdict_source: str


class VerdictSourceLastAdmission(BaseModel):
    """The latest graded ADMISSION audit."""

    at: str

    id: str

    metrics: dict[str, Any]
    """The graded metrics (never a body)."""

    result: str
    """Known values: ``passed``, ``failed``."""


class VerdictSourceReviewFlag(BaseModel):
    """The review flag over the task outcomes recorded since the last clearance."""

    flagged: bool

    min_outcomes: int

    outcomes: int

    success_rate: float | None

    success_rate_bar: float


class FlywheelStatus(BaseModel):
    """Flywheel status: capture counts + integration health + unavailable learning fields."""

    channels: list[FlywheelChannelHealth]
    """Channels detected (integration health)."""

    experiment: MoatNextExperiment | None
    """The current bounded experiment, or null — benchmarkable is always false."""

    imports: FlywheelStatusImports
    """History-import integration health."""

    learning: FlywheelStatusLearning
    """Learning fields — explicitly unavailable; a collecting state never implies observed lift."""

    object: str
    """Known values: ``flywheel_status``."""

    usage: FlywheelUsageBlock
    """The four SEPARATED Flywheel usage quantities + caps + storage + COGS."""

    workspace_id: str


class FlywheelChannelHealth(BaseModel):
    """One channel detected (integration health)."""

    accepted_outcomes: int

    channel: str

    last_observed_at: str | None


class FlywheelStatusImports(BaseModel):
    """History-import integration health."""

    completed: int

    failed: int

    last_import_at: str | None

    running: int

    total: int


class FlywheelStatusLearning(BaseModel):
    """Learning fields — explicitly unavailable; a collecting state never implies observed lift."""

    active_levers: list[str]
    """Empty on this status surface — no lift is claimed while collecting."""

    calibration_available: bool
    """Known values: ``False``."""

    flywheel_class: str
    """Explicitly UNAVAILABLE on this status surface (the class is not computed here).

    Known values: ``unavailable``.
    """

    flywheel_class_reason: str
    """Known values: ``collecting``."""


class FlywheelUsageBlock(BaseModel):
    """The four SEPARATED Flywheel usage quantities + caps + storage + COGS."""

    accepted_outcomes: int
    """OPERATIONAL — accepted outcome events this period (not an invoice line)."""

    actual_cogs: FlywheelUsageBlockActualCogs
    """OUR actual COGS for margin (settled analysis + failed attempts); never billed to the customer.
    """

    analysis_units: FlywheelUsageBlockAnalysisUnits
    """PAID — bounded analysis units (billed by unique artifact version × recipe)."""

    evaluation_compute_usd: FlywheelUsageBlockEvaluationComputeUsd
    """PAID — approved evaluation compute (the platform-spend evaluation counters; one money source).
    """

    metadata_artifacts_monthly_cap: int | None

    overage_paused: bool
    """Default overage is paused — no unpriced automatic overage."""

    period: str
    """The current UTC month bucket (YYYY-MM-DD)."""

    storage: FlywheelUsageBlockStorage
    """The finite storage quotas + lifetime byte counters."""

    tracked_artifacts: int
    """OPERATIONAL — new artifacts captured this period (not an invoice line)."""


class FlywheelUsageBlockActualCogs(BaseModel):
    """OUR actual COGS for margin (settled analysis + failed attempts); never billed to the customer."""

    analysis_micro_usd: int

    failed_attempt_micro_usd: int


class FlywheelUsageBlockAnalysisUnits(BaseModel):
    """PAID — bounded analysis units (billed by unique artifact version × recipe)."""

    lifetime_cap: int | None
    """Lifetime analysis-unit cap; null = unlimited."""

    lifetime_used: int
    """Committed analysis units across the account lifetime."""

    monthly_cap: int | None
    """Monthly analysis-unit cap; null = lifetime governs."""

    reserved: int
    """Open analysis-unit holds this period."""

    settled: int
    """Billed analysis units this period."""


class FlywheelUsageBlockEvaluationComputeUsd(BaseModel):
    """PAID — approved evaluation compute (the platform-spend evaluation counters; one money source)."""

    cap_micro_usd: int
    """The approved monthly evaluation-compute cap."""

    reserved_micro_usd: int

    settled_micro_usd: int


class FlywheelUsageBlockStorage(BaseModel):
    """The finite storage quotas + lifetime byte counters."""

    ledger_index_bytes: int

    ledger_index_bytes_cap: int | None

    paused: bool
    """True when the storage quota is exhausted (new storage paused; export/deletion preserved)."""

    retained_payload_bytes: int

    retained_payload_bytes_cap: int | None


class GenerationStats(BaseModel):
    """Post-hoc stats for one request (GET /v1/generation)."""

    byok: bool
    """Whether a workspace BYOK key served the request."""

    call_type: str | None
    """Resolved call type (`ct_…`), or null."""

    compression: dict[str, Any]
    """Compression summary — the applied compression safety tier + savings provenance."""

    contract_digest: str | None
    """The request's declared-contract digest (json_schema / tools / tool_choice / response_format); the distinguished empty-contract digest for a plain-text request, null on a request recorded before contract digests existed.
    """

    cost: GenerationStatsCost
    """Cost accounting (money is integer micro-USD)."""

    created_at: str
    """ISO-8601 timestamp the request was recorded."""

    error_class: str | None
    """The gateway error code (see `GatewayError.error.code`) when status != ok, else null."""

    exposure: GenerationStatsExposure
    """The immutable pre-dispatch exposure stamp (read-back; never a decision input)."""

    id: str
    """The `req_…` id these stats describe."""

    lever: GenerationStatsLever
    """The learned-context lever stamp for this request."""

    model_requested: str
    """The logical model the caller asked for."""

    model_served: str | None
    """The model actually served, or null on failure."""

    outcomes: list[GenerationStatsOutcome]
    """Outcome events bound to this request — gateway-native (`source:gateway`) mechanical events plus any declared request-shortcut outcomes. Empty when none recorded.
    """

    provider: str | None
    """The provider that served it, or null."""

    routing_decision: dict[str, Any]
    """The full routing trail (mode/sort/attempts/skipped/config_sources) — why this request used the model it did.
    """

    status: str
    """Terminal request status.

    Known values: ``ok``, ``error``, ``cancelled``.
    """

    timing: GenerationStatsTiming
    """Timing."""

    tokens: GenerationStatsTokens
    """Token accounting (incl. cached-prompt tokens)."""


class GenerationStatsCost(BaseModel):
    """Cost accounting (money is integer micro-USD)."""

    cost_basis: str | None
    """Provenance of the cost: `priced` (the offer’s own catalog price), `derived` (a price derived from the logical model it serves), `verified_memory` (answered from verified memory at $0), or `unpriced` (served with no usable price — metered at $0 only where the unpriced-model override is enabled; null on a non-ok row).

    Known values: ``priced``, ``derived``, ``unpriced``, ``verified_memory``.
    """

    total_micro_usd: int
    """Total cost in integer micro-USD."""

    total_usd: float
    """Total cost in USD (float, for readability)."""


class GenerationStatsExposure(BaseModel):
    """The immutable pre-dispatch exposure stamp (read-back; never a decision input)."""

    arm: str | None
    """Standing-holdout arm assigned at dispatch (null when unstamped)."""

    epoch: int | None
    """The assignment epoch the arm was assigned under."""


class GenerationStatsLever(BaseModel):
    """The learned-context lever stamp for this request."""

    epoch: int | None
    """The measurement epoch the injection was bound to."""

    injection: dict[str, Any] | None
    """The serve-time retrieval provenance (`module_id`, `item_ids[]`, `served_rank[]`, `propensity[]`) when injected, or the NAMED refusal that withheld the lever (`holdout`, `candidate_unknown`, `pack_hash_mismatch`, …). Propensity is computable only at serve time and is never backfilled. Ids and numbers only — never a body.
    """

    lever_id: str | None
    """The lever family injected (`learned_context`), or null when none was."""

    module_version: str | None
    """The injected module’s PINNED version — its recipe hash."""

    pack_hash: str | None
    """The content address of the ORDERED item set actually served."""


class GenerationStatsOutcome(BaseModel):
    """One request-bound outcome event."""

    artifact_id: str
    """The artifact the outcome landed on."""

    channel: str
    """The outcome channel (e.g. `mechanical`)."""

    kind: str
    """The closed-vocab kind (e.g. `schema_valid`, `tool_error`)."""

    latency_class: str
    """`instant` | `delayed` (server-derived)."""

    learning_use: list[str]
    """Server-derived learning-use set (`train`/`calibrate`/`rank`/`audit`)."""

    observed_at: str
    """ISO-8601 effective time of the outcome."""

    source: str
    """Server-assigned provenance (`gateway` for gateway-native events)."""

    value: dict[str, Any]
    """Typed value payload — reasons / indices / counts only (never a body)."""


class GenerationStatsTiming(BaseModel):
    """Timing."""

    latency_ms: int | None
    """Total request latency in ms."""

    ttfb_ms: int | None
    """Time-to-first-byte in ms (null when N/A)."""


class GenerationStatsTokens(BaseModel):
    """Token accounting (incl. cached-prompt tokens)."""

    cached: int
    """Cached prompt tokens (subset of input)."""

    input: int

    output: int

    total: int


class ImportList(BaseModel):
    """A keyset-paginated page of imports (never offset-paginated)."""

    data: list[Import]

    next_cursor: str | None

    object: str
    """Known values: ``list``."""


class Import(BaseModel):
    """A history import (metadata + capability report; NEVER a body)."""

    accepted_count: int

    artifact_type_version_id: str | None
    """The call type’s CONFIRMED objective version the batch was bound to (insert-only); null = unbound.
    """

    call_type_id: str | None
    """The call type this batch is bound to (insert-only); null = an unbound batch whose verdicts never count toward readiness.
    """

    corrections_consent: bool

    created_at: str

    duplicate_count: int

    format: str

    format_version: str

    id: str

    import_class: str
    """The import class (pinned by the adapter): usage_only (summaries) | intact_trace (bodies).

    Known values: ``usage_only``, ``intact_trace``.
    """

    key_mode: str
    """Known values: ``test``, ``live``."""

    object: str
    """Known values: ``import``."""

    record_count: int

    rejected_count: int

    report: ImportReport
    """The capability report (may be `{}` while running)."""

    status: str
    """Known values: ``preview``, ``running``, ``completed``, ``cancelled``, ``failed``."""

    unsupported_count: int

    updated_at: str


class ImportReport(BaseModel):
    """The capability report (may be `{}` while running)."""

    accepted: int | None = None

    binding_truth: str | None = None
    """Intact traces only: the honest binding sentence — the call type + confirmed objective the batch is bound to and what still gates its verdicts (a blind admission audit of THIS batch), or that an unbound batch’s verdicts can never count toward readiness.
    """

    bodies_stored: int | None = None
    """Replayable request/response bodies stored (consented intact only)."""

    class_truth: str | None = None
    """The honest one-sentence class truth (usage-only vs consented/unconsented intact)."""

    duplicate: int | None = None

    format: str | None = None

    format_version: str | None = None

    import_class: str | None = None
    """The import class (pinned by the adapter): usage_only (summaries) | intact_trace (bodies).

    Known values: ``usage_only``, ``intact_trace``.
    """

    missing_lineage: int | None = None

    parse_errors: list[ImportParseError] | None = None

    reasons: dict[str, int] | None = None
    """Rejection/unsupported reason → count."""

    record_count: int | None = None

    redacted: int | None = None
    """How many stored records had PII redacted on ingest."""

    rejected: int | None = None

    replayable: bool | None = None
    """Whether any record supports replay (consented intact + a body)."""

    spend_micro_usd: int | None = None
    """Usage-only: total spend (micro-USD)."""

    unsupported: int | None = None

    unsupported_fields: list[str] | None = None

    usage_exposure: list[UsageExposureRow] | None = None
    """Usage-only: per-model exposure rows."""

    workflow: ImportReportWorkflow | None = None
    """Workflow (workflow_execution_jsonl) only: the execution counts (delivered / held), the orphan/interrupted calls kept apart, and the per-execution cost reconciliation.
    """


class ImportParseError(BaseModel):
    """A malformed JSONL line."""

    line: int

    message: str


class UsageExposureRow(BaseModel):
    """A per-model exposure/spend summary row (usage-only import)."""

    cost_micro_usd: int

    input_tokens: int

    model: str

    output_tokens: int

    requests: int


class ImportReportWorkflow(BaseModel):
    """Workflow (workflow_execution_jsonl) only: the execution counts (delivered / held), the orphan/interrupted calls kept apart, and the per-execution cost reconciliation."""

    cost_reconciliation: list[ImportReportWorkflowCostReconciliationItem]

    delivered: int

    executions: int

    held: int

    orphan_calls: int
    """Calls not members of a terminal execution (orphan/interrupted) — kept apart, never dropped.
    """


class ImportReportWorkflowCostReconciliationItem(BaseModel):
    """One execution’s cost reconciliation (gateway summed vs the client figure vs the difference)."""

    client_cost_micro_usd: int | None

    cost_diff_micro_usd: int | None

    execution_key: str

    gateway_cost_micro_usd: int

    pending_charges: int


class ImportCreateParams(TypedDict, total=False):
    """Create or resume a history import (consent-gated; owner/admin or outcomes:write)."""

    call_type_id: str
    """The call type (a `ct_*` id from `GET /v1/call-types`) this history belongs to, and so its CONFIRMED objective. Intact traces only. Every accepted record’s artifact is stamped with the call type, its confirmed objective version and its situation at assembly (insert-only), so the batch’s task verdicts count toward that call type’s readiness once a blind ADMISSION audit of the batch passes. Refused by name: an unknown call type (404 `call_type_not_found`), one without a confirmed objective (409 `call_type_unconfirmed`), a usage-only file (400 `binding_requires_intact_trace`), a resume naming another call type or binding an unbound batch (409 `binding_conflict`), a resume after the confirmed objective changed (409 `binding_stale`). Omitted on a resume ⇒ the batch keeps the binding it was created with; omitted on a new import ⇒ an UNBOUND batch whose verdicts never count toward readiness.
    """

    format: Required[str]
    """The pinned adapter format id (e.g. `usage_summary`, `openai_chat_jsonl`)."""

    format_version: str
    """The pinned adapter version (defaults to the latest for the format)."""

    import_id: str
    """Resume an existing import (idempotent per record content hash)."""

    jsonl: str
    """The uploaded records as JSONL (newline-delimited JSON). Alternative to `records`."""

    mode: Literal["preview", "commit"]
    """preview = capability report only (nothing stored); commit = ingest. Defaults to commit."""

    reason_vocabulary: ImportCreateParamsReasonVocabulary
    """workflow_execution_jsonl only: the typed hold-reason codes this batch’s executions may use (`{ id, codes[] }`). Registered ONCE at the batch creation (insert-only; a resume inherits it). An execution whose terminal names an unregistered code is refused `reason_code_unregistered`. Required for a workflow import (409 `workflow_requires_reason_vocabulary` otherwise).
    """

    records: list[Any]
    """The uploaded records (array form). Intact-trace records may carry request/response bodies — the ONLY import field that does; stored ONLY under corrections_consent, redacted on ingest. A workflow_execution_jsonl record groups the EXISTING gateway request rows its `calls` name into one artifact with one terminal outcome.
    """


class ImportCreateParamsReasonVocabulary(TypedDict, total=False):
    """workflow_execution_jsonl only: the typed hold-reason codes this batch’s executions may use (`{ id, codes[] }`). Registered ONCE at the batch creation (insert-only; a resume inherits it). An execution whose terminal names an unregistered code is refused `reason_code_unregistered`. Required for a workflow import (409 `workflow_requires_reason_vocabulary` otherwise)."""

    codes: Required[list[str]]

    id: Required[str]


class ImportEnvelope(BaseModel):
    """A single import, wrapped in the `import` envelope."""

    import_: Import = Field(..., alias="import")
    """A history import (metadata + capability report; NEVER a body)."""


class ImprovementReads(BaseModel):
    """The multi-goal improvement reads for every call type the workspace has."""

    call_types: list[CallTypeImprovementReads]

    object: str
    """Known values: ``improvement_reads``."""

    workspace_id: str


class CallTypeImprovementReads(BaseModel):
    """The multi-goal improvement reads for one call type + the north-star holdout gap."""

    call_type_id: str

    get_better: ImprovementRead
    """The "quality can improve here" read (Flywheel candidate + plan)."""

    holdout_gap: CallTypeImprovementReadsHoldoutGap
    """The north-star holdout gap for this call type (unavailable until a lever earns live confirmation).
    """

    slug: str | None

    spend_less: ImprovementRead
    """The "a cheaper model is enough here" read (from the eval recommendations)."""


class ImprovementRead(BaseModel):
    """One improvement read (spend-less OR get-better) for one call type."""

    collecting: ImprovementCollecting | None
    """The collecting progress (collecting state only; else null)."""

    deciding: list[str]
    """The deciding axes for a get-better screen (empty for a spend-less recommendation).

    Known values: ``quality``, ``cost``, ``guardrail``, ``evidence``.
    """

    estimate: bool
    """True ONLY when the surfaced figure is an ESTIMATE (a projected saving), never realized."""

    goal: str
    """Which goal this read is for.

    Known values: ``spend_less``, ``get_better``.
    """

    intent: str
    """The decision intent this half reports — cost_optimization for spend-less; the get-better default is product_improvement, a customer-stated intent is reported and never overridden.

    Known values: ``cost_optimization``, ``required_migration``, ``product_improvement``.
    """

    next_action: str
    """The customer’s next action — always a sentence, never a bare state."""

    reason: str | None
    """The NAMED reason (unavailable state only; else null)."""

    source_id: str | None
    """The source row id for evidence / keep_incumbent / needs_confirmation (a rec / run / plan id), else null.
    """

    state: str
    """The closed state this half resolved to.

    Known values: ``evidence``, ``collecting``, ``needs_confirmation``, ``keep_incumbent``, ``unavailable``.
    """

    tier: str | None
    """The evidence tier in the engine’s own vocabulary (evidence state only; else null)."""


class ImprovementCollecting(BaseModel):
    """Progress toward a NAMED engine floor (the collecting state)."""

    floor: int
    """The floor value the owning engine sets (never a new floor)."""

    floor_name: str
    """The NAME of the engine that owns the floor (e.g. golden_set.min_activate)."""

    n: int | None
    """The count toward the floor, or null when the owning engine exposes no per-call-type count."""


class CallTypeImprovementReadsHoldoutGap(BaseModel):
    """The north-star holdout gap for this call type (unavailable until a lever earns live confirmation)."""

    cost_ratio: float | None
    """The live $ per successful task ratio (treated ÷ holdout), null when inconclusive."""

    cost_ratio_ci_high: float | None
    """The cost-ratio CI upper bound."""

    cost_ratio_ci_low: float | None
    """The cost-ratio CI lower bound."""

    gap_ci_high: float | None
    """The gap two-sided CI upper bound (per 1,000)."""

    gap_ci_low: float | None
    """The gap two-sided CI lower bound (per 1,000)."""

    gap_per_1000: float | None
    """The holdout gap per 1,000 tasks (null when no measurement)."""

    reason: str | None
    """The NAMED reason when the tier is not measured (no_measurement / no_confirmed_lever / under_powered / aa_parked / cost_ratio_inconclusive), else null.
    """

    tier: str
    """The evidence tier the holdout gap resolved to.

    Known values: ``measured``, ``inconclusive``, ``unavailable``.
    """


class KeyInfo(BaseModel):
    """Current-key introspection (GET /v1/key)."""

    created_at: str
    """ISO-8601 creation timestamp."""

    expires_at: str | None
    """ISO-8601 expiry, or null when non-expiring."""

    flywheel: FlywheelUsageBlock | None = None
    """The four SEPARATED Flywheel usage quantities for this workspace this period — operational capture counters vs the PAID analysis units + evaluation compute — plus caps, storage quota and our actual COGS. Never merged. Null/absent when the workspace has no Flywheel usage.
    """

    limits: KeyInfoLimits
    """Enforced limits on this key."""

    mode: str
    """Key mode.

    Known values: ``live``, ``test``.
    """

    name: str
    """Human-readable key name."""

    object: str
    """Known values: ``api_key``."""

    prefix: str
    """Display prefix (`ur_sk_<mode>_` + 8 chars) — safe to show."""

    scopes: list[str]
    """The key's closed-vocabulary scopes."""

    usage: KeyInfoUsage
    """Usage this period (from the live spend counters — never a scan of requests)."""

    workspace_id: str


class KeyInfoLimits(BaseModel):
    """Enforced limits on this key."""

    rps_limit: int | None
    """Per-key requests-per-second cap; null = the gateway-key default."""

    spend_cap_micro_usd: int | None
    """Per-key monthly hard cap in micro-USD; null = uncapped."""


class KeyInfoUsage(BaseModel):
    """Usage this period (from the live spend counters — never a scan of requests)."""

    key_spent_micro_usd: int
    """This key's spend this period (from the live spend counters)."""

    period: str
    """The current spend period (UTC calendar month, YYYY-MM-DD)."""

    workspace_spend_cap_micro_usd: int | None
    """The per-workspace monthly hard cap; null = uncapped."""

    workspace_spent_micro_usd: int
    """The workspace's total spend this period."""


class CreateMessageParams(TypedDict, total=False):
    """Anthropic Messages API request, forwarded verbatim to Anthropic. Every field beyond `model` (system, messages, tools, output_config, cache_control, continuation blocks, …) is passed through unchanged. Auth may be the ur key via `Authorization: Bearer` or `x-api-key`; the caller's key is never forwarded upstream (the platform/BYOK key is injected server-side)."""

    model: Required[str]
    """The Anthropic model id to call (e.g. "claude-opus-5-5"). This exact model is the model called.
    """


class CreateMessageResponse(BaseModel):
    """The Anthropic Message object, returned byte-for-byte. Usage is metered from `usage` (input_tokens + cache_read_input_tokens + cache_creation_input_tokens + output_tokens); the ur request id and booked cost ride the `X-UR-Request-Id` / `X-UR-Cost-Micro-USD` headers."""


class ModelList(BaseModel):
    """Active model catalog."""

    data: list[Model]

    object: str
    """Known values: ``list``."""


class Model(BaseModel):
    """A catalog model with pricing + capabilities + provenance (of the logical model) and hosting (of this offer)."""

    active: bool

    capabilities: dict[str, Any]

    context_length: int | None

    hosting_jurisdiction: str
    """HOSTING — where THIS offer RUNS (ISO 3166-1 alpha-2), or "unknown". A CN-origin open-weight model HOSTED in the US shows origin_jurisdiction "CN" + hosting_jurisdiction "US".
    """

    hosting_region: str | None
    """HOSTING — the provider-published serving region (e.g. us-east-1), or null."""

    id: str

    name: str

    object: str
    """Known values: ``model``."""

    origin_jurisdiction: str
    """PROVENANCE — the developing lab's ISO 3166-1 alpha-2 jurisdiction (e.g. US/CN/FR/CA), RESOLVED for this row (an offer inherits it from the logical model it serves), or "unknown".
    """

    pricing: ModelPricing
    """List pricing in integer micro-USD per 1M tokens (money is integer micro-USD)."""

    provider: str

    weights: str
    """Whether the LOGICAL model weights are downloadable — open | closed | unknown (fail-closed).

    Known values: ``open``, ``closed``, ``unknown``.
    """

    workspace_custom: bool | None = None
    """True on a WORKSPACE custom-provider model — tenant-scoped, visible only to the owning workspace's keys; absent on global catalog rows.
    """


class ModelPricing(BaseModel):
    """List pricing in integer micro-USD per 1M tokens (money is integer micro-USD)."""

    cached_input_micro_usd_per_1m: int | None

    input_micro_usd_per_1m: int

    input_usd_per_1m: float

    output_micro_usd_per_1m: int

    output_usd_per_1m: float


class ModelDetail(BaseModel):
    """A catalog model with its per-provider offers. Provenance (origin/weights) is a top-level LOGICAL-model fact; hosting is per-offer."""

    capabilities: dict[str, Any]

    context_length: int | None

    id: str

    name: str

    object: str
    """Known values: ``model``."""

    offers: list[ModelOffer]
    """Every active provider offer, INCLUDING the workspace custom-provider offers routing merges in. Each offer carries its OWN hosting.
    """

    origin_jurisdiction: str
    """PROVENANCE — the LOGICAL model's origin jurisdiction (ISO alpha-2), or "unknown"."""

    weights: str
    """Whether the LOGICAL model weights are downloadable — open | closed | unknown (fail-closed).

    Known values: ``open``, ``closed``, ``unknown``.
    """

    workspace_custom: bool | None = None
    """True when the id resolves ONLY via the workspace custom providers."""


class ModelOffer(BaseModel):
    """One provider offer of a logical model, incl. its per-offer hosting."""

    context_length: int | None

    data_policy: str | None
    """Provider data policy ('strict' = ZDR), or null."""

    hosting_jurisdiction: str
    """HOSTING — where THIS offer RUNS (ISO 3166-1 alpha-2), or "unknown"."""

    hosting_region: str | None
    """HOSTING — the provider-published serving region (e.g. us-east-1), or null."""

    model_id: str
    """The offer's own catalog id (may mirror the logical id)."""

    pricing: ModelPricing
    """List pricing in integer micro-USD per 1M tokens (money is integer micro-USD)."""

    provider: str
    """Provider slug serving this offer."""

    quantization: str | None
    """Offer quantization (e.g. fp8), or null."""

    throughput_rank: int | None
    """Static throughput rank (lower = faster)."""


class OutcomeReceiptRecord(BaseModel):
    """A durable receipt for one reported outcome."""

    applied_at: str | None
    """When the outcome was recorded."""

    artifact_id: str | None
    """The artifact the outcome landed on, once applied."""

    attempts: int
    """Recording attempts that hit an internal error (bounded; then `failed`)."""

    channel: str
    """The outcome channel as sent."""

    created_at: str
    """When the outcome was accepted."""

    episode: OutcomeReceiptRecordEpisode
    """The episode association of an applied teaching outcome."""

    expires_at: str
    """The receipt’s next deadline: while `pending`, when it expires; while its episode association is `pending`, when that becomes `not_recorded`; once settled, when the receipt itself is deleted (30 days).
    """

    id: str
    """The receipt id (`ocr_…`)."""

    kind: str
    """The outcome kind as sent."""

    object: str
    """Known values: ``outcome_receipt``."""

    outcome_event_id: str | None
    """The recorded outcome event (`oev_…`) once applied."""

    outcome_status: str | None
    """Whether applying recorded the event for the first time (`accepted`) or found it (`duplicate`).

    Known values: ``accepted``, ``duplicate``.
    """

    reason: str | None
    """A stable machine reason when not applied: `request_not_found`, `idempotency_conflict`, `apply_failed`, or the validation reason.
    """

    request_id: str
    """The request the outcome names."""

    source_event_id: str
    """Your idempotency discriminator, or a server-minted one when none was sent (then a retry is a new outcome).
    """

    status: str
    """`pending` — the request has not been recorded yet; `applied` — the outcome is recorded; `rejected` — it failed validation once the request was known (see `reason`); `failed` — recording kept hitting an internal error; `expired` — no request with this id appeared in your workspace within 15 minutes (`reason: request_not_found`).

    Known values: ``pending``, ``applied``, ``rejected``, ``failed``, ``expired``.
    """

    updated_at: str


class OutcomeReceiptRecordEpisode(BaseModel):
    """The episode association of an applied teaching outcome."""

    status: str
    """`associated` — the episode holding this request carries a verdict; `pending` — a teaching outcome waiting for its episode to be recorded; `not_recorded` — the persisted request was held out and recording was intentionally suppressed, or no episode held the request within 15 minutes (episode memory or recording off, no consent); `not_applicable` — the outcome does not teach (a proxy, behavioral or mechanical signal) or was not applied.

    Known values: ``associated``, ``pending``, ``not_recorded``, ``not_applicable``.
    """

    trace_id: str | None
    """The episode (`ept_…`) the outcome was associated with, once associated."""

    verdict: str | None
    """What the outcome did to the episode: `recorded` — it is the episode verdict; `kept_earlier` — the episode already had a verdict (the first verdict wins); `revised` — it superseded the verdict (`supersedes_event_id`) before any learned version used the episode, so the verdict was replaced; `revised_after_incorporation` — the superseded verdict was already used by a learned version: the revision is recorded and counted, the episode is not silently unlearned.

    Known values: ``recorded``, ``kept_earlier``, ``revised``, ``revised_after_incorporation``.
    """


class BatchOutcomesParams(TypedDict, total=False):
    """Record ≤ 1,000 outcome events keyed by target."""

    outcomes: Required[list[BatchOutcomeParams]]


class BatchOutcomeParams(TypedDict, total=False):
    """A batch outcome keyed by request_id | artifact_id | artifact_key."""

    alternative_id: str
    """A computable-comparison alternative id."""

    artifact_id: str
    """Target an artifact by id."""

    artifact_key: str
    """Target an artifact by its canonical key."""

    artifact_version: int
    """The pinned artifact version (defaults to the artifact’s current version)."""

    channel: Required[
        Literal["mechanical", "correction", "behavioral", "resolution", "computable", "proxy"]
    ]
    """The outcome channel (closed vocabulary)."""

    claim_id: str
    """Target a specific claim by id (else the artifact)."""

    claim_key: str
    """Target a claim by its customer key — the key’s ACTIVE claim (else the artifact)."""

    confidence: float
    """An optional confidence ∈ (0,1)."""

    evidence_hash: str
    """A content hash of supporting evidence (never a body)."""

    kind: Required[str]
    """The channel `kind` (a closed vocabulary per channel)."""

    observed_at: str
    """The effective time (ISO-8601; must be ≥ the artifact occurred_at). Defaults to now."""

    request_id: str
    """Target via the request shortcut (one-request artifact)."""

    source_event_id: str
    """The caller idempotency discriminator (ULID at enqueue). Defaults to a server ULID."""

    supersedes_event_id: str
    """The event this one supersedes."""

    tool_error_class: Literal["model", "infra", "unclassified"]
    """For mechanical:tool_error — refines learning_use (only model-class teaches)."""

    value: dict[str, Any]
    """The typed numeric/diff-stats payload — never a body."""


class BatchOutcomesResponse(BaseModel):
    """The per-row batch results + a verdict rollup."""

    accepted: int

    conflict: int

    data: list[BatchOutcomeResult]

    duplicate: int

    object: str
    """Known values: ``list``."""

    pending: int
    """Rows whose request has not been recorded yet (durable pending receipts)."""

    rejected: int


class BatchOutcomeResult(BaseModel):
    """One batch outcome’s result."""

    artifact_version: int | None

    canonical_target_id: str | None

    id: str | None
    """The outcome-event id when accepted/duplicate; else null."""

    key: str | None
    """The input target key echoed (request_id/artifact_id/artifact_key)."""

    latency_class: str | None
    """Known values: ``instant``, ``delayed``."""

    learning_use: list[str] | None
    """Known values: ``train``, ``calibrate``, ``rank``, ``audit``."""

    reason: str | None
    """The rejection/conflict reason when not accepted."""

    receipt: OutcomeReceiptRecord | None
    """The durable receipt of a `request_id` row (the same receipt the request-outcome route returns for the same `source_event_id`); null for an `artifact_id` / `artifact_key` row or a row refused before one.
    """

    source: str | None
    """Known values: ``declared``, ``inferred``, ``gateway``, ``imported``."""

    source_event_id: str | None

    status: str
    """Per-row acceptance: accepted | duplicate (no-op) | conflict | rejected | pending — a `request_id` row whose request has not been recorded yet: stored durably and applied when it is (see `receipt`).

    Known values: ``accepted``, ``duplicate``, ``conflict``, ``rejected``, ``pending``.
    """

    target_kind: str | None
    """Known values: ``artifact``, ``claim``."""


class PendingClaimList(BaseModel):
    """A keyset-paginated page of claims awaiting resolution (cursor-based; never offset)."""

    data: list[PendingClaim]

    next_cursor: str | None

    object: str
    """Known values: ``list``."""


class PendingClaim(BaseModel):
    """A claim awaiting resolution."""

    archetype: str
    """The artifact archetype (closed vocabulary).

    Known values: ``forecast``, ``recommendation``, ``draft``, ``extraction``, ``answer``, ``action``.
    """

    artifact_id: str

    artifact_key: str

    claim_key: str

    claim_type: str

    created_at: str

    id: str

    occurred_at: str

    resolves_by: str | None

    state: str
    """The current claim state (derived from the claim’s outcome events). `superseded` is terminal: a later customer-declared claim took this claim’s claim_key (only ever listed under `superseded_claims`).

    Known values: ``pending``, ``overdue``, ``resolved``, ``censored``, ``voided``, ``disputed``, ``superseded``.
    """

    stated_confidence: float | None


class PreflightParams(TypedDict, total=False):
    """Preflight request — a call type + an OPTIONAL cluster key (artifact_key | trace_id) + budget + the OPTIONAL messages a per-request case module is rendered for."""

    artifact_key: str
    """The declared artifact cluster key the exposure grant is minted on (supply it to receive a grant).
    """

    budget: PreflightBudgetParams
    """Optional pre-call budget hints."""

    call_type: Required[str]
    """The call type (slug or `ct_*` id) whose profile to preflight."""

    messages: list[ChatMessageParam]
    """The messages the non-proxied call is about to send. Used ONLY when the learned module is a per-request CASE module (a classification call type learns verified cases, not a static list): the gateway renders the verified cases nearest THIS input (the last user message) — exactly what the chat path would inject for the same messages. Never stored, never logged. Omitted for a case module ⇒ `knowledge: null` with `knowledge_reason: "case_query_missing"`; a static module ignores it.
    """

    trace_id: str
    """The trace-id cluster key (alternative to `artifact_key`; supply it to receive a grant)."""


class PreflightBudgetParams(TypedDict, total=False):
    """Optional pre-call budget hints."""

    max_latency_ms: int
    """Ceiling on the recommended offer p95 latency (the live health input already resolved for candidates/auto). An excluded pin ⇒ `provisional:true, reason:"budget"`. Not evaluated in off/pinned mode (no health is resolved there).
    """

    max_usd: float
    """Ceiling on the recommended offer NET-EFFECTIVE input price per 1M tokens, in USD. Preflight has NO request tokens to price a per-request budget against, so it filters on the rate-card input already in the policy decision (never a token estimator); an unpriceable offer is budget-excluded fail-closed. An excluded pin ⇒ `provisional:true, reason:"budget"`.
    """


class PreflightResponse(BaseModel):
    """Preflight response — the routing decision + the learned knowledge + placement + the exposure grant."""

    config_version: int
    """The config version this decision was resolved on."""

    grant: PreflightGrant | None
    """The exposure grant (present when a cluster key was given; null otherwise). NEVER cached — also served on the `X-UR-Grant` header, which a 304 revalidation still carries.
    """

    grant_reason: str | None
    """The NAMED reason `grant` is null (`no_cluster_key` when neither artifact_key nor trace_id was given). Null when a grant WAS minted.
    """

    knowledge: PreflightKnowledge | None
    """The learned knowledge preflight would inject + where + how it is delivered."""

    knowledge_reason: str | None
    """The NAMED refusal when `knowledge` is null (the inject seam refusal, e.g. `holdout` / `candidate_unknown` / `module_version_mismatch`; `fell_back` when the learned module could not be resolved within the hot-path `learned`-slot budget; or `no_learned_module` when none is configured). Null only when a module WAS injected.
    """

    object: str
    """Known values: ``preflight``."""

    prompt: PreflightPrompt | None
    """The ACTIVE hosted prompt version, or null when code-owned. Config-versioned (part of the ETag).
    """

    provisional: bool
    """Whether this advice is provisional (a confirmed plan / benchmarkable / budget caveat)."""

    reason: str | None = None
    """Why the advice is provisional (present only when `provisional` is true).

    Known values: ``plan_unconfirmed``, ``not_benchmarkable``, ``budget``.
    """

    routing: PreflightRouting
    """The routing decision preflight would have made."""


class PreflightGrant(BaseModel):
    """The exposure grant (present when a cluster key was given; null otherwise). NEVER cached — also served on the `X-UR-Grant` header, which a 304 revalidation still carries."""

    arm: str
    """The exposure arm the grant assigns (the SAME assignment the gateway stamps at dispatch).

    Known values: ``treated``, ``holdout``, ``lever_holdout``, ``pre_lever``.
    """

    epoch: int
    """The assignment epoch (lift is never pooled across epochs)."""

    grant_id: str
    """Deterministic: hash of workspace + cluster key + epoch (idempotent; never cached)."""

    lever_id: str | None
    """The lever family when the arm is lever-derived, else null."""

    request_id: str
    """The zero-cost `status=preflight` served-record id (the served proof)."""

    valid_until_epoch_close: str
    """A conservative ISO validity horizon; re-mint on a newer epoch (never cached)."""


class PreflightKnowledge(BaseModel):
    """The learned knowledge preflight would inject + where + how it is delivered."""

    delivery: str
    """HOW this module reaches the call for the call type. `gateway_inject_after_stable_prefix` — a PROXIED request has the gateway inject it (this advisory is informational). `off` — the gateway does NOT inject; a NON-proxied SDK/preflight consumer MUST inject the returned module itself (at `placement`). Either way preflight returns the module so the SDK knows exactly what to inject; a flip to `off` starts a new learned_context epoch.

    Known values: ``gateway_inject_after_stable_prefix``, ``off``.
    """

    module: PreflightKnowledgeModule
    """The learned-context module preflight would inject (config-versioned; max_age_s 5 + ETag)."""

    placement: str
    """Known values: ``after_stable_prefix``."""


class PreflightKnowledgeModule(BaseModel):
    """The learned-context module preflight would inject (config-versioned; max_age_s 5 + ETag)."""

    content: str
    """The rendered module body (derived statistics only — never a body/PII)."""

    content_hash: str
    """sha256 of the rendered body — the byte identity of what is injected."""

    id: str

    kind: str
    """Known values: ``ur:learned``."""

    lineage: PreflightLineage
    """The learned-module lineage (the pinned recipe the pack was frozen over)."""

    slot: str
    """Known values: ``learned``."""

    state: str
    """The SERVING lifecycle state of the module the gateway would inject — `screened` (passed offline screening), `confirming` (a live confirmation is running; served to the treated arm) or `adopted` (a leased, adopted module). So a non-proxied customer can see WHAT the platform adopted and is serving.
    """

    tokens: int

    version: str
    """The recipe-hash module version."""


class PreflightLineage(BaseModel):
    """The learned-module lineage (the pinned recipe the pack was frozen over)."""

    epoch: int

    item_ids: list[str]

    k: int

    key_spec: str

    pack_hash: str

    ranker_version: str

    source_snapshot: str


class PreflightPrompt(BaseModel):
    """The ACTIVE hosted prompt version, or null when code-owned. Config-versioned (part of the ETag)."""

    sha256: str
    """sha256 of the template — the byte identity of the active version."""

    template: str
    """The prompt template (`{{name}}` variables the caller fills)."""

    variables: list[PreflightPromptVariable]
    """The declared template variables (name + required flag)."""

    version: int
    """The active hosted prompt version number."""


class PreflightPromptVariable(BaseModel):
    """Response shape ``PreflightPromptVariable``."""

    name: str

    required: bool


class PreflightRouting(BaseModel):
    """The routing decision preflight would have made."""

    fallbacks: list[PreflightFallback]
    """Health-ordered fallbacks (the 30 s live part)."""

    max_age_s: float
    """The LIVE (health-ordered fallbacks) part max age in seconds — the 30 s regime.

    Known values: ``30``.
    """

    mode: str
    """The EFFECTIVE router mode the gateway would run.

    Known values: ``off``, ``pinned``, ``candidates``, ``auto``.
    """

    model: PreflightModel | None
    """The recommended model, or null when none resolves."""

    why: PreflightWhy | None
    """The serialised policy decision (null in off/pinned)."""


class PreflightFallback(BaseModel):
    """A fallback offer (live, health-ordered; max_age_s 30)."""

    id: str
    """The fallback logical model id."""

    score: PreflightOfferScore | None
    """One offer policy score (the routing-policy decision evidence; ranking prices only)."""

    skipped_reason: str | None = None
    """Why this candidate was skipped (`capability:*`, `pref:*`, `not_in_list`, `model:unknown`)."""


class PreflightOfferScore(BaseModel):
    """One offer policy score (the routing-policy decision evidence; ranking prices only)."""

    commit_mode: str | None = None
    """Known values: ``sunk``, ``discounted``, ``list``."""

    eligible: bool

    health_score: float

    marginal_micro_usd_per_1m: float | None

    model: str

    net_effective_micro_usd_per_1m: float | None

    offer_id: str

    policy_score: float | None

    provider: str

    reason: str | None = None


class PreflightModel(BaseModel):
    """The recommended model — honest: the pin in off/pinned, the ranked offer in candidates/auto."""

    evidence: str
    """Whether qualified evals back this choice. `qualified` ONLY when the policy input already carries qualified evidence for the pin (a rec-backed migration baseline); else `none`. No $/task or quality-bar language is implied.

    Known values: ``none``, ``qualified``.
    """

    id: str
    """The recommended logical model id."""

    score: PreflightOfferScore | None
    """The chosen offer policy score (candidates/auto), or null in off/pinned mode."""


class PreflightWhy(BaseModel):
    """The serialised routing-policy decision (byte-compatible with `routing_decision.policy` in the generation stats)."""

    canary_bucket: float | None = None

    chain: list[str]

    chosen: PreflightWhyChosen | None

    config_mode: str

    downgraded: bool

    kill_switch: bool

    lever_suppressed: str | None = None

    mode: str

    scores: list[PreflightOfferScore]

    upgrade_ignored: bool


class PreflightWhyChosen(BaseModel):
    """Response shape ``PreflightWhyChosen``."""

    model: str

    offer_id: str

    provider: str


class FeedbackCreateParams(TypedDict, total=False):
    """Human feedback on a prior request."""

    comment: str
    """Optional free-text comment."""

    rating: Required[Literal[1] | Literal[-1]]
    """Thumbs up (1) or thumbs down (-1) — the human feedback signal evals consume."""

    tags: list[str]
    """Optional free-form tags (e.g. "hallucination", "great")."""


class FeedbackEnvelope(BaseModel):
    """A stored feedback row, wrapped in the `feedback` envelope."""

    feedback: Feedback
    """A stored feedback row."""


class Feedback(BaseModel):
    """A stored feedback row."""

    comment: str | None

    created_at: str

    id: str

    object: str
    """Known values: ``request_feedback``."""

    rating: float

    request_id: str

    tags: list[str]


class OutcomeReceiptRecordList(BaseModel):
    """Every outcome receipt for one request in your workspace, oldest first."""

    data: list[OutcomeReceiptRecord]

    object: str
    """Known values: ``list``."""


class RequestOutcomeResult(BaseModel):
    """One request-shortcut outcome result with its durable receipt."""

    artifact_id: str | None
    """The artifact the outcome landed on (null while `pending`)."""

    artifact_version: int | None

    canonical_target_id: str | None

    id: str | None
    """The outcome-event id when accepted/duplicate; else null."""

    latency_class: str | None
    """Known values: ``instant``, ``delayed``."""

    learning_use: list[str] | None
    """Known values: ``train``, ``calibrate``, ``rank``, ``audit``."""

    object: str
    """Known values: ``outcome``."""

    reason: str | None
    """The rejection/conflict reason when not accepted."""

    receipt: OutcomeReceiptRecord
    """A durable receipt for one reported outcome."""

    source: str | None
    """Known values: ``declared``, ``inferred``, ``gateway``, ``imported``."""

    source_event_id: str | None

    status: str
    """`accepted` — recorded now; `duplicate` — a retry of an outcome already recorded (no-op); `pending` — the request has not been recorded yet: the outcome is stored durably and applied when it is (poll the `receipt`). A conflict is answered 409 and a rejection 400 on this route.

    Known values: ``accepted``, ``duplicate``, ``conflict``, ``rejected``, ``pending``.
    """

    target_kind: str | None
    """Known values: ``artifact``, ``claim``."""


for _model in (
    ArtifactTypeEnvelope,
    ArtifactType,
    ArtifactObjective,
    ArtifactList,
    Artifact,
    ArtifactClaim,
    ArtifactEnvelope,
    ArtifactFinal,
    RecordOutcomesResponse,
    OutcomeResult,
    AuditReadiness,
    AuditReadinessCallType,
    AuditReadinessCallTypeCapture,
    AuditReadinessCallTypeCostProvenance,
    AuditReadinessCoverage,
    AuditReadinessEmergingShape,
    AuditReadinessInventory,
    AuditReadinessOpportunity,
    BenchRun,
    BenchAllowance,
    BenchDisposition,
    BenchPowerAdvisory,
    BenchEvalRun,
    BenchEvalRunArm,
    BenchEvidenceClass,
    BenchBaseline,
    BenchCompareGate,
    BenchCompareGateCallType,
    BenchCompareGateCallTypeCostCeiling,
    BenchInterval,
    BenchCompareGateCallTypePairing,
    BenchEntitlement,
    BenchOutcomes,
    BenchRecordedOutcome,
    BenchReport,
    BenchReportCallType,
    BenchReportCallTypeArm,
    BenchReportCallTypeArmCostView,
    BenchDatasetCard,
    BenchDatasetExclusion,
    BenchPowerPlan,
    BenchDatasetStaleness,
    BenchDatasetStratum,
    BenchReportCallTypeInversion,
    BenchReportCallTypePower,
    BenchReportCallTypeProjection,
    BenchReportCallTypeProjectionBasis,
    BenchReportCallTypeTaskViewItem,
    BenchReportCallTypeVerdict,
    BenchReportExport,
    BenchReportReproducibility,
    BenchExpectations,
    BenchAttachedExpectation,
    BenchDatasetFreeze,
    BenchDatasetFreezeDataset,
    BenchDatasetFreezeDatasetEvaluator,
    BenchDatasetFreezeDatasetEvaluatorAssertion,
    BenchDatasetFreezeWarning,
    BenchRunTrigger,
    BenchSuiteStatus,
    BenchSuiteStatusCallType,
    BenchSuiteStatusCallTypeQualified,
    BenchSuiteStatusCapture,
    CallTypeList,
    CallType,
    CallTypeConfigVersion,
    EpisodeMemoryStatus,
    EpisodeMemoryStatusMemory,
    EpisodeMemoryStatusPlaybook,
    EpisodeMemoryStatusSetting,
    EpisodeMemoryStatusSettingLessons,
    EpisodeMemoryStatusSettingLessonsRecipe,
    EpisodeMemoryStatusTraces,
    EpisodeMemoryDisableResult,
    EpisodeMemoryEnableResult,
    EvalRunList,
    EvalRun,
    EvalRunCandidate,
    EvalRunJudge,
    EvalRunSpec,
    EvalRunSpecCandidate,
    EvalRunSpecHypothesis,
    EvalRunSpecProfile,
    EvalRunSpecProfileEvaluatorSuite,
    EvalRunSpecProfileEvaluatorSuiteJudge,
    EvalRunSpecProfileEvaluatorSuiteScorerInstance,
    EnqueueEvalResponse,
    LearningStatus,
    LearningVersionRef,
    LearningStatusBudget,
    LearningEvaluation,
    LearningEvaluationArms,
    LearningEvaluationArm,
    LearningEvaluationDecidedBy,
    LearningEvaluationDifference,
    LearningEvaluationRule,
    LearningStatusEvidence,
    LearningStatusOutcomeReceipts,
    LearningPromotionPolicy,
    LearningStatusRecipe,
    LearningStatusReflection,
    LearningStatusReflectionNext,
    LearningStatusReflectionProvider,
    LearningStatusUsage,
    LearningControl,
    LearningEvaluationList,
    LearningToolDocumentation,
    LearningToolDocumentationTool,
    LearningToolDocumentationToolDocumentedItem,
    LearningVersionList,
    LearningVersion,
    LearningVersionCohort,
    LearningVersionDetail,
    LearningVersionDetailDistiller,
    LearningVersionDetailLesson,
    LearningVersionDetailTransition,
    HostedPromptList,
    HostedPrompt,
    HostedPromptVariable,
    HostedPromptActivation,
    HostedPromptProposal,
    VerifiedMemoryStatus,
    VerifiedMemoryStatusLivePool,
    VerifiedMemoryStatusPostPin,
    VerifiedMemoryStatusServable,
    VerifiedMemoryStatusSetting,
    VerifiedMemoryStatusSettingCalibration,
    VerifiedMemoryStatusSettingOperatingPoint,
    VerifiedMemoryStatusSettingPool,
    VerifiedMemoryStatusSettingPoolDropped,
    VerifiedMemoryDisableResult,
    VerifiedMemoryEnableResult,
    VerifiedMemoryEnableResultCalibration,
    VerifiedMemoryEnableResultPool,
    VerifiedMemoryEnableResultPoolAdmission,
    VerifiedMemoryEnableResultPoolContent,
    ChatCompletion,
    ChatCompletionChoice,
    ChatCompletionMessage,
    UrBlock,
    UrBlockBench,
    UrBlockCompression,
    UrBlockRouting,
    UrBlockVerifiedMemory,
    ChatCompletionUsage,
    ChatCompletionUsagePromptTokensDetails,
    CreateEmbeddingResponse,
    Embedding,
    EmbeddingUrBlock,
    EmbeddingUrBlockRouting,
    EmbeddingUsage,
    FlywheelCandidateList,
    FlywheelCandidate,
    FlywheelCandidateOffline,
    FlywheelCandidateOfflineCost,
    FlywheelCandidateOfflineEconomics,
    FlywheelCandidateOfflineEconomicsCostPerAvoidedErrorMicroUsd,
    FlywheelCandidateOfflineEconomicsErrorsAvoidedPer1000,
    ConfirmationStatus,
    ConfirmationStatusAutoAdopt,
    ConfirmationLift,
    ConfirmationLiftInterval,
    CandidateDecisionResult,
    CandidateRolloutResult,
    CandidateRolloutBlocker,
    ConfirmationList,
    Confirmation,
    ExperimentExecution,
    ExperimentExecutionOutcome,
    ExperimentExecutionOutcomeCost,
    ExperimentExecutionOutcomeOpenHold,
    ExperimentScreenEvaluation,
    ExperimentScreenEvaluationScreen,
    ExperimentScreenEvaluationScreenExecution,
    ExperimentScreenEvaluationScreenProgress,
    ExperimentScreenEvaluationScreenVerdict,
    ExperimentScreenEvaluationScreenVerdictClause,
    ExperimentScreenEvaluationScreenVerdictClauseDetail,
    ExperimentScreenEvaluationScreenVerdictClauseDetailFeature,
    ExperimentScreenEvaluationScreenVerdictClauseDetailVerdict,
    ExperimentScreenEvaluationScreenVerdictInputs,
    ExperimentScreenEvaluationScreenVerdictInputsExecution,
    ExperimentScreenEvaluationScreenVerdictInputsJudgement,
    ExperimentScreenEvaluationScreenVerdictInputsObservation,
    ExperimentScreenEvaluationScreenVerdictInputsPhaseHolds,
    ExperimentScreenEvaluationScreenVerdictRule,
    ExperimentTestEvaluation,
    ExperimentTestEvaluationTest,
    ExperimentTestEvaluationTestProgress,
    ExperimentTestEvaluationTestVerdict,
    ExperimentTestEvaluationTestVerdictEconomics,
    ExperimentTestEvaluationTestVerdictGoodhart,
    ExperimentTestEvaluationTestVerdictGoodhartArm,
    ExperimentTestEvaluationTestVerdictPrimary,
    ExperimentTestEvaluationTestVerdictQuality,
    ExperimentTestEvaluationTestVerdictQualityPerJudgeItem,
    ExperimentTestEvaluationTestVerdictRule,
    ExposureGrant,
    MoatNext,
    MoatNextExperiment,
    MoatNextExperimentAdmission,
    MoatNextExperimentAdmissionApplied,
    MoatNextExperimentAdmissionEvidence,
    MoatNextExperimentBudget,
    MoatNextExperimentReservations,
    MoatNextExperimentReservationsPhase,
    MoatNextItem,
    MoatNextPrecondition,
    OracleRegistration,
    Oracle,
    OracleCurrent,
    OracleRole,
    OracleTransportState,
    OracleTransportStateCanaries,
    OracleTransportStateCanaryPool,
    OracleTransportStateJobs,
    OracleTransportStateQualification,
    OracleVersion,
    OracleJobList,
    OracleJob,
    OracleQualification,
    OracleQualificationCertifier,
    OracleQualificationDetector,
    OracleQualificationExamples,
    OracleQualificationJobs,
    OracleRevocation,
    OracleTestResult,
    OracleTestResultRequest,
    OracleVerdictsResult,
    OracleVerdictResult,
    OracleQualificationOutcome,
    LearningPlanEnvelope,
    LearningPlan,
    LearningPlanCallTypeBinding,
    LearningPlanCallTypeBindingLabelFieldProposal,
    LearningPlanCallTypeBindingLabelFieldProposalCandidate,
    LearningPlanList,
    LearningPlanProposal,
    PromptCandidateList,
    PromptCandidate,
    ReviewerEventsResponse,
    ReviewerEventResult,
    ReviewerHealth,
    ReviewerBackfillProgress,
    ReviewerDeadLetter,
    ReviewerHealthEventCounts,
    ReviewerHealthNextRepair,
    ReviewerRepairResult,
    ReviewerRepairBefore,
    ReviewerSetup,
    ReviewerMappingRow,
    ReviewerSignatureRecipe,
    ReviewerTestResult,
    VerdictSourceCheck,
    VerdictSourceProbe,
    VerdictSourceCheckResult,
    VerdictSourceCheckResultPerFamilyItem,
    VerdictSourceCheckResultRecall,
    VerdictSourceList,
    VerdictSource,
    VerdictSourceLastAdmission,
    VerdictSourceReviewFlag,
    FlywheelStatus,
    FlywheelChannelHealth,
    FlywheelStatusImports,
    FlywheelStatusLearning,
    FlywheelUsageBlock,
    FlywheelUsageBlockActualCogs,
    FlywheelUsageBlockAnalysisUnits,
    FlywheelUsageBlockEvaluationComputeUsd,
    FlywheelUsageBlockStorage,
    GenerationStats,
    GenerationStatsCost,
    GenerationStatsExposure,
    GenerationStatsLever,
    GenerationStatsOutcome,
    GenerationStatsTiming,
    GenerationStatsTokens,
    ImportList,
    Import,
    ImportReport,
    ImportParseError,
    UsageExposureRow,
    ImportReportWorkflow,
    ImportReportWorkflowCostReconciliationItem,
    ImportEnvelope,
    ImprovementReads,
    CallTypeImprovementReads,
    ImprovementRead,
    ImprovementCollecting,
    CallTypeImprovementReadsHoldoutGap,
    KeyInfo,
    KeyInfoLimits,
    KeyInfoUsage,
    CreateMessageResponse,
    ModelList,
    Model,
    ModelPricing,
    ModelDetail,
    ModelOffer,
    OutcomeReceiptRecord,
    OutcomeReceiptRecordEpisode,
    BatchOutcomesResponse,
    BatchOutcomeResult,
    PendingClaimList,
    PendingClaim,
    PreflightResponse,
    PreflightGrant,
    PreflightKnowledge,
    PreflightKnowledgeModule,
    PreflightLineage,
    PreflightPrompt,
    PreflightPromptVariable,
    PreflightRouting,
    PreflightFallback,
    PreflightOfferScore,
    PreflightModel,
    PreflightWhy,
    PreflightWhyChosen,
    FeedbackEnvelope,
    Feedback,
    OutcomeReceiptRecordList,
    RequestOutcomeResult,
):
    _model.model_rebuild()

#: The in-scope operations: operationId -> (method, path, params class, response class).
OPERATIONS: dict[str, tuple[str, str, str | None, str | None]] = {
    "upsertArtifactType": (
        "POST",
        "/v1/artifact-types",
        "ArtifactTypeUpsertParams",
        "ArtifactTypeEnvelope",
    ),
    "listArtifacts": ("GET", "/v1/artifacts", None, "ArtifactList"),
    "createArtifact": ("POST", "/v1/artifacts", "ArtifactCreateParams", "ArtifactEnvelope"),
    "getArtifact": ("GET", "/v1/artifacts/{id}", None, "ArtifactEnvelope"),
    "recordArtifactFinal": (
        "POST",
        "/v1/artifacts/{id}/final",
        "ArtifactFinalParams",
        "ArtifactFinal",
    ),
    "recordArtifactOutcomes": (
        "POST",
        "/v1/artifacts/{id}/outcomes",
        "RecordOutcomesParams",
        "RecordOutcomesResponse",
    ),
    "getAuditReadiness": ("GET", "/v1/audit/readiness", None, "AuditReadiness"),
    "getBenchRun": ("GET", "/v1/bench/runs/{id}", None, "BenchRun"),
    "pinBenchBaseline": ("POST", "/v1/bench/runs/{id}/baseline", None, "BenchBaseline"),
    "getBenchCompareGate": ("GET", "/v1/bench/runs/{id}/gate", None, "BenchCompareGate"),
    "recordBenchRunOutcomes": (
        "POST",
        "/v1/bench/runs/{id}/outcomes",
        "BenchOutcomesParams",
        "BenchOutcomes",
    ),
    "getBenchRunReport": ("GET", "/v1/bench/runs/{id}/report", None, "BenchReport"),
    "attachBenchExpectations": (
        "POST",
        "/v1/bench/suites/{slug}/expectations",
        "BenchExpectationsParams",
        "BenchExpectations",
    ),
    "freezeBenchSuite": (
        "POST",
        "/v1/bench/suites/{slug}/freeze",
        "BenchFreezeParams",
        "BenchDatasetFreeze",
    ),
    "recordBenchSuiteOutcomes": (
        "POST",
        "/v1/bench/suites/{slug}/outcomes",
        "BenchOutcomesParams",
        "BenchOutcomes",
    ),
    "triggerBenchRun": (
        "POST",
        "/v1/bench/suites/{slug}/runs",
        "BenchRunParams",
        "BenchRunTrigger",
    ),
    "getBenchSuiteStatus": ("GET", "/v1/bench/suites/{slug}/status", None, "BenchSuiteStatus"),
    "listCallTypes": ("GET", "/v1/call-types", None, "CallTypeList"),
    "createCallType": ("POST", "/v1/call-types", "CallTypeCreateParams", "CallType"),
    "getCallType": ("GET", "/v1/call-types/{id}", None, "CallType"),
    "updateCallType": ("PATCH", "/v1/call-types/{id}", "CallTypeConfigParams", "CallType"),
    "getEpisodeMemory": ("GET", "/v1/call-types/{id}/episode-memory", None, "EpisodeMemoryStatus"),
    "disableEpisodeMemory": (
        "POST",
        "/v1/call-types/{id}/episode-memory/disable",
        None,
        "EpisodeMemoryDisableResult",
    ),
    "enableEpisodeMemory": (
        "POST",
        "/v1/call-types/{id}/episode-memory/enable",
        "EpisodeMemoryEnableParams",
        "EpisodeMemoryEnableResult",
    ),
    "listCallTypeEvals": ("GET", "/v1/call-types/{id}/evals", None, "EvalRunList"),
    "enqueueCallTypeEval": (
        "POST",
        "/v1/call-types/{id}/evals",
        "EnqueueEvalParams",
        "EnqueueEvalResponse",
    ),
    "getLearningStatus": ("GET", "/v1/call-types/{id}/learning", None, "LearningStatus"),
    "disableLearning": ("POST", "/v1/call-types/{id}/learning/disable", None, "LearningControl"),
    "enableLearning": (
        "POST",
        "/v1/call-types/{id}/learning/enable",
        "LearningEnableParams",
        "LearningControl",
    ),
    "listLearningEvaluations": (
        "GET",
        "/v1/call-types/{id}/learning/evaluations",
        None,
        "LearningEvaluationList",
    ),
    "pauseLearning": ("POST", "/v1/call-types/{id}/learning/pause", None, "LearningControl"),
    "resumeLearning": ("POST", "/v1/call-types/{id}/learning/resume", None, "LearningControl"),
    "rollbackLearning": (
        "POST",
        "/v1/call-types/{id}/learning/rollback",
        "LearningRollbackParams",
        "LearningControl",
    ),
    "getLearningToolDocumentation": (
        "GET",
        "/v1/call-types/{id}/learning/tool-documentation",
        None,
        "LearningToolDocumentation",
    ),
    "putLearningToolDocumentation": (
        "PUT",
        "/v1/call-types/{id}/learning/tool-documentation",
        "PutLearningToolDocumentationParams",
        "LearningToolDocumentation",
    ),
    "listLearningVersions": (
        "GET",
        "/v1/call-types/{id}/learning/versions",
        None,
        "LearningVersionList",
    ),
    "getLearningVersion": (
        "GET",
        "/v1/call-types/{id}/learning/versions/{version_id}",
        None,
        "LearningVersionDetail",
    ),
    "promoteLearningVersion": (
        "POST",
        "/v1/call-types/{id}/learning/versions/{version_id}/promote",
        None,
        "LearningControl",
    ),
    "rejectLearningVersion": (
        "POST",
        "/v1/call-types/{id}/learning/versions/{version_id}/reject",
        None,
        "LearningControl",
    ),
    "listHostedPrompts": ("GET", "/v1/call-types/{id}/prompts", None, "HostedPromptList"),
    "createHostedPrompt": (
        "POST",
        "/v1/call-types/{id}/prompts",
        "HostedPromptCreateParams",
        "HostedPrompt",
    ),
    "deactivateHostedPrompt": (
        "POST",
        "/v1/call-types/{id}/prompts/deactivate",
        None,
        "HostedPromptActivation",
    ),
    "getHostedPromptProposal": (
        "GET",
        "/v1/call-types/{id}/prompts/proposal",
        None,
        "HostedPromptProposal",
    ),
    "getHostedPrompt": ("GET", "/v1/call-types/{id}/prompts/{version}", None, "HostedPrompt"),
    "activateHostedPrompt": (
        "POST",
        "/v1/call-types/{id}/prompts/{version}/activate",
        "HostedPromptActivateParams",
        "HostedPromptActivation",
    ),
    "listCallTypeRecommendations": ("GET", "/v1/call-types/{id}/recommendations", None, None),
    "getVerifiedMemory": (
        "GET",
        "/v1/call-types/{id}/verified-memory",
        None,
        "VerifiedMemoryStatus",
    ),
    "disableVerifiedMemory": (
        "POST",
        "/v1/call-types/{id}/verified-memory/disable",
        None,
        "VerifiedMemoryDisableResult",
    ),
    "enableVerifiedMemory": (
        "POST",
        "/v1/call-types/{id}/verified-memory/enable",
        "VerifiedMemoryEnableParams",
        "VerifiedMemoryEnableResult",
    ),
    "createChatCompletion": (
        "POST",
        "/v1/chat/completions",
        "ChatCompletionCreateParams",
        "ChatCompletion",
    ),
    "createEmbeddings": (
        "POST",
        "/v1/embeddings",
        "EmbeddingCreateParams",
        "CreateEmbeddingResponse",
    ),
    "listFlywheelCandidates": ("GET", "/v1/flywheel/candidates", None, "FlywheelCandidateList"),
    "getCandidateConfirmation": (
        "GET",
        "/v1/flywheel/candidates/{ref}/confirmation",
        None,
        "ConfirmationStatus",
    ),
    "recordCandidateDecision": (
        "POST",
        "/v1/flywheel/candidates/{ref}/decisions",
        "CandidateDecisionParams",
        "CandidateDecisionResult",
    ),
    "evaluateCandidateRollout": (
        "POST",
        "/v1/flywheel/candidates/{ref}/rollout",
        "CandidateRolloutParams",
        "CandidateRolloutResult",
    ),
    "listConfirmations": ("GET", "/v1/flywheel/confirmations", None, "ConfirmationList"),
    "enrolFlywheelExperimentExecution": (
        "POST",
        "/v1/flywheel/experiments/{id}/executions",
        "ExperimentEnrolParams",
        "ExperimentExecution",
    ),
    "recordFlywheelExperimentExecutionOutcome": (
        "POST",
        "/v1/flywheel/experiments/{id}/executions/{execution_id}/outcome",
        "ExperimentOutcomeParams",
        "ExperimentExecutionOutcome",
    ),
    "evaluateFlywheelExperimentScreen": (
        "POST",
        "/v1/flywheel/experiments/{id}/screen/evaluate",
        None,
        "ExperimentScreenEvaluation",
    ),
    "evaluateFlywheelExperimentTest": (
        "POST",
        "/v1/flywheel/experiments/{id}/test/evaluate",
        None,
        "ExperimentTestEvaluation",
    ),
    "mintExposureGrant": ("POST", "/v1/flywheel/grants", "ExposureGrantParams", "ExposureGrant"),
    "getMoatNext": ("GET", "/v1/flywheel/moat-next", None, "MoatNext"),
    "registerOracle": (
        "POST",
        "/v1/flywheel/oracles",
        "OracleRegisterParams",
        "OracleRegistration",
    ),
    "getOracle": ("GET", "/v1/flywheel/oracles/{id}", None, "Oracle"),
    "claimOracleJobs": (
        "POST",
        "/v1/flywheel/oracles/{id}/jobs/claim",
        "OracleClaimParams",
        "OracleJobList",
    ),
    "qualifyOracle": (
        "POST",
        "/v1/flywheel/oracles/{id}/qualify",
        "OracleQualifyParams",
        "OracleQualification",
    ),
    "revokeOracle": (
        "POST",
        "/v1/flywheel/oracles/{id}/revoke",
        "OracleRevokeParams",
        "OracleRevocation",
    ),
    "testOracle": (
        "POST",
        "/v1/flywheel/oracles/{id}/test",
        "OracleTestParams",
        "OracleTestResult",
    ),
    "submitOracleVerdicts": (
        "POST",
        "/v1/flywheel/oracles/{id}/verdicts",
        "OracleVerdictsParams",
        "OracleVerdictsResult",
    ),
    "getLearningPlan": ("GET", "/v1/flywheel/plan", None, "LearningPlanEnvelope"),
    "listLearningPlans": ("GET", "/v1/flywheel/plans", None, "LearningPlanList"),
    "listPromptCandidates": ("GET", "/v1/flywheel/prompt-candidates", None, "PromptCandidateList"),
    "recordReviewerEvents": (
        "POST",
        "/v1/flywheel/reviewer/events",
        "ReviewerEventsParams",
        "ReviewerEventsResponse",
    ),
    "getReviewerHealth": ("GET", "/v1/flywheel/reviewer/health", None, "ReviewerHealth"),
    "repairReviewerEvent": (
        "POST",
        "/v1/flywheel/reviewer/repair",
        "ReviewerRepairParams",
        "ReviewerRepairResult",
    ),
    "getReviewerSetup": ("GET", "/v1/flywheel/reviewer/setup", None, "ReviewerSetup"),
    "runReviewerTest": (
        "POST",
        "/v1/flywheel/reviewer/test",
        "ReviewerTestParams",
        "ReviewerTestResult",
    ),
    "issueVerdictSourceCheck": (
        "POST",
        "/v1/flywheel/source-checks",
        "VerdictSourceCheckParams",
        "VerdictSourceCheck",
    ),
    "gradeVerdictSourceCheck": (
        "POST",
        "/v1/flywheel/source-checks/{id}/verdicts",
        "VerdictSourceGradeParams",
        "VerdictSourceCheckResult",
    ),
    "listVerdictSources": ("GET", "/v1/flywheel/sources", None, "VerdictSourceList"),
    "getFlywheelStatus": ("GET", "/v1/flywheel/status", None, "FlywheelStatus"),
    "getGeneration": ("GET", "/v1/generation", None, "GenerationStats"),
    "listImports": ("GET", "/v1/imports", None, "ImportList"),
    "createImport": ("POST", "/v1/imports", "ImportCreateParams", "ImportEnvelope"),
    "getImport": ("GET", "/v1/imports/{id}", None, "ImportEnvelope"),
    "cancelImport": ("POST", "/v1/imports/{id}/cancel", None, "ImportEnvelope"),
    "listImprovementReads": ("GET", "/v1/improvement-reads", None, "ImprovementReads"),
    "getKey": ("GET", "/v1/key", None, "KeyInfo"),
    "createMessage": ("POST", "/v1/messages", "CreateMessageParams", "CreateMessageResponse"),
    "listModels": ("GET", "/v1/models", None, "ModelList"),
    "getModel": ("GET", "/v1/models/{id}", None, "ModelDetail"),
    "getOutcomeReceipt": ("GET", "/v1/outcome-receipts/{id}", None, "OutcomeReceiptRecord"),
    "recordOutcomesBatch": (
        "POST",
        "/v1/outcomes/batch",
        "BatchOutcomesParams",
        "BatchOutcomesResponse",
    ),
    "listPendingOutcomes": ("GET", "/v1/outcomes/pending", None, "PendingClaimList"),
    "preflight": ("POST", "/v1/preflight", "PreflightParams", "PreflightResponse"),
    "submitFeedback": (
        "POST",
        "/v1/requests/{id}/feedback",
        "FeedbackCreateParams",
        "FeedbackEnvelope",
    ),
    "listRequestOutcomeReceipts": (
        "GET",
        "/v1/requests/{id}/outcome-receipts",
        None,
        "OutcomeReceiptRecordList",
    ),
    "recordRequestOutcome": (
        "POST",
        "/v1/requests/{id}/outcomes",
        "OutcomeParams",
        "RequestOutcomeResult",
    ),
    "createResponse": ("POST", "/v1/responses", "CreateMessageParams", "CreateMessageResponse"),
}
