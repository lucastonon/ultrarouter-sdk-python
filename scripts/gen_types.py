#!/usr/bin/env python3
"""Generate ``src/ultrarouter/types/_generated.py`` from ``openapi/openapi.yaml``.

The generated module holds:

* one pydantic response model per object schema returned by an API-key endpoint the SDK
  covers (nested inline objects become their own classes), and
* one ``TypedDict`` per request body / nested request object, used to type method
  arguments.

Never hand-edit the output. Change the spec (re-sync it) or the naming tables below, then run::

    uv run python scripts/gen_types.py           # rewrite the module
    uv run python scripts/gen_types.py --check   # exit 1 if the committed module is stale

Design rules:

* Response models allow unknown fields (``extra="allow"``) so a newer gateway never breaks an
  older SDK. Enumerated response strings are typed ``str`` (forward compatible) and their known
  values are listed in the attribute docstring; request enums are ``Literal`` types.
* A field the spec marks required is required on the model; a nullable field admits ``None``.
* ``oneOf``/``anyOf`` of objects in a response is merged into one model (a property is required
  only when every variant requires it).
* Structurally identical inline objects share one class (the first name wins), so the module stays
  small and names are stable for a given spec.
"""

from __future__ import annotations

import argparse
import json
import keyword
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "openapi" / "openapi.yaml"
OUT_PATH = ROOT / "src" / "ultrarouter" / "types" / "_generated.py"

HTTP_METHODS = ("get", "post", "put", "patch", "delete")

#: Operations reachable with an API key that the SDK deliberately does not wrap, with the reason
#: (also rendered into docs/api-coverage.md by scripts/gen_coverage.py).
EXCLUDED_OPERATIONS: dict[str, str] = {
    "echo": "Diagnostic auth echo; use client.key.retrieve() to check a key.",
    "enrolFlywheelExperimentExecution": (
        "Bounded-experiment run surface; its outcome route is not in the spec yet. The run methods ship "
        "together once both operations exist."
    ),
}

#: Public names for component schemas (component name -> class name). Unlisted components keep
#: their spec name.
COMPONENT_NAMES: dict[str, str] = {
    "ChatCompletionsResponse": "ChatCompletion",
    "ChatCompletionsRequest": "ChatCompletionCreateParams",
    "EmbeddingsResponse": "CreateEmbeddingResponse",
    "EmbeddingsRequest": "EmbeddingCreateParams",
    "ModelsListResponse": "ModelList",
    "ModelDetailResponse": "ModelDetail",
    "UrResponseBlock": "UrBlock",
    "AuditReadinessResponse": "AuditReadiness",
    "GenerationStats": "GenerationStats",
    "FeedbackResponse": "Feedback",
    "FeedbackRequest": "FeedbackCreateParams",
    "KeyIntrospection": "KeyInfo",
    "PreflightResponse": "PreflightResponse",
    "PreflightRequest": "PreflightParams",
    "CallTypeSummary": "CallType",
    "CallTypeListResponse": "CallTypeList",
    "CreateCallTypeRequest": "CallTypeCreateParams",
    "CallTypeConfigBody": "CallTypeConfigParams",
    "ArtifactSummary": "Artifact",
    "ArtifactListResponse": "ArtifactList",
    "CreateArtifactRequest": "ArtifactCreateParams",
    "UpsertArtifactTypeRequest": "ArtifactTypeUpsertParams",
    "ClaimInput": "ClaimParams",
    "FinalRequest": "ArtifactFinalParams",
    "FinalResponse": "ArtifactFinal",
    "RecordOutcomesRequest": "RecordOutcomesParams",
    "OutcomeInput": "OutcomeParams",
    "BatchOutcomesRequest": "BatchOutcomesParams",
    "BatchOutcomeInput": "BatchOutcomeParams",
    "PendingClaimsResponse": "PendingClaimList",
    "FlywheelStatusResponse": "FlywheelStatus",
    "ImportRequest": "ImportCreateParams",
    "ImportSummary": "Import",
    "ImportListResponse": "ImportList",
    "BenchSuiteStatusResponse": "BenchSuiteStatus",
    "BenchDatasetFreezeResponse": "BenchDatasetFreeze",
    "BenchFreezeRequest": "BenchFreezeParams",
    "BenchRunTriggerRequest": "BenchRunParams",
    "BenchRunTriggerResponse": "BenchRunTrigger",
    "BenchRunResponse": "BenchRun",
    "BenchReportResponse": "BenchReport",
    "BenchExpectationsRequest": "BenchExpectationsParams",
    "BenchExpectationsResponse": "BenchExpectations",
    "BenchOutcomesRequest": "BenchOutcomesParams",
    "BenchOutcomesResponse": "BenchOutcomes",
    "BenchBaselineResponse": "BenchBaseline",
    "BenchCompareGateResponse": "BenchCompareGate",
    "EnqueueEvalRequest": "EnqueueEvalParams",
    "EvalRunListResponse": "EvalRunList",
    "ReviewerEventsRequest": "ReviewerEventsParams",
    "ReviewerEventInput": "ReviewerEvent",
    "ReviewerSetupResponse": "ReviewerSetup",
    "ReviewerHealthResponse": "ReviewerHealth",
    "ReviewerTestRequest": "ReviewerTestParams",
    "ReviewerTestResponse": "ReviewerTestResult",
    "ReviewerRepairRequest": "ReviewerRepairParams",
    "ReviewerRepairResponse": "ReviewerRepairResult",
    "ImprovementReadsResponse": "ImprovementReads",
    "MoatNextResponse": "MoatNext",
    "ConfirmationStatusResponse": "ConfirmationStatus",
}

#: Names for inline (non-component) response bodies, keyed by operationId.
RESPONSE_NAMES: dict[str, str] = {
    "listHostedPrompts": "HostedPromptList",
    "createHostedPrompt": "HostedPrompt",
    "getHostedPrompt": "HostedPrompt",
    "activateHostedPrompt": "HostedPromptActivation",
    "deactivateHostedPrompt": "HostedPromptActivation",
    "getHostedPromptProposal": "HostedPromptProposal",
    "getVerifiedMemory": "VerifiedMemoryStatus",
    "enableVerifiedMemory": "VerifiedMemoryEnableResult",
    "disableVerifiedMemory": "VerifiedMemoryDisableResult",
    "mintExposureGrant": "ExposureGrant",
    "listFlywheelCandidates": "FlywheelCandidateList",
    "recordCandidateDecision": "CandidateDecisionResult",
    "evaluateCandidateRollout": "CandidateRolloutResult",
    "listConfirmations": "ConfirmationList",
    "registerOracle": "OracleRegistration",
    "getOracle": "Oracle",
    "claimOracleJobs": "OracleJobList",
    "qualifyOracle": "OracleQualification",
    "revokeOracle": "OracleRevocation",
    "testOracle": "OracleTestResult",
    "submitOracleVerdicts": "OracleVerdictsResult",
    "getLearningPlan": "LearningPlanEnvelope",
    "listLearningPlans": "LearningPlanList",
    "listPromptCandidates": "PromptCandidateList",
    "issueVerdictSourceCheck": "VerdictSourceCheck",
    "gradeVerdictSourceCheck": "VerdictSourceCheckResult",
    "listVerdictSources": "VerdictSourceList",
}

#: Names for inline (non-component) request bodies, keyed by operationId.
PARAMS_NAMES: dict[str, str] = {
    "createHostedPrompt": "HostedPromptCreateParams",
    "activateHostedPrompt": "HostedPromptActivateParams",
    "enableVerifiedMemory": "VerifiedMemoryEnableParams",
    "mintExposureGrant": "ExposureGrantParams",
    "recordCandidateDecision": "CandidateDecisionParams",
    "evaluateCandidateRollout": "CandidateRolloutParams",
    "registerOracle": "OracleRegisterParams",
    "claimOracleJobs": "OracleClaimParams",
    "qualifyOracle": "OracleQualifyParams",
    "revokeOracle": "OracleRevokeParams",
    "testOracle": "OracleTestParams",
    "submitOracleVerdicts": "OracleVerdictsParams",
    "issueVerdictSourceCheck": "VerdictSourceCheckParams",
    "gradeVerdictSourceCheck": "VerdictSourceGradeParams",
}

#: Renames for automatically-derived nested class names (auto name -> public name).
NESTED_NAMES: dict[str, str] = {
    # chat
    "ChatCompletionCreateParamsMessage": "ChatMessageParam",
    "ChatMessageParamContentItem": "ChatContentPartParam",
    "ChatContentPartParamCacheControl": "CacheControlParam",
    "ChatCompletionCreateParamsProvider": "ProviderPreferencesParam",
    "ChatCompletionCreateParamsReasoning": "ReasoningParam",
    "ChatCompletionCreateParamsCompression": "CompressionParam",
    "ChatCompletionCreateParamsUr": "UrParams",
    "UrParamsBench": "BenchTagParam",
    "UrParamsContextModule": "ContextModuleRefParam",
    "UrParamsManifest": "ManifestWireParam",
    "ManifestWireParamEntry": "ManifestWireEntryParam",
    "ManifestWireEntryParamRange": "ManifestWireRangeParam",
    "UrParamsSegment": "SegmentHintParam",
    "ChatCompletionCreateParamsResponseFormat": "ResponseFormatTextParam",
    "ChatCompletionCreateParamsResponseFormat2": "ResponseFormatJsonObjectParam",
    "ChatCompletionCreateParamsResponseFormat3": "ResponseFormatJsonSchemaParam",
    "ChatCompletionChoiceMessage": "ChatCompletionMessage",
    # embeddings + models
    "CreateEmbeddingResponseItem": "Embedding",
    "CreateEmbeddingResponseUr": "EmbeddingUrBlock",
    "CreateEmbeddingResponseUrRouting": "EmbeddingUrRouting",
    "CreateEmbeddingResponseUsage": "EmbeddingUsage",
    "ModelListItem": "Model",
    "ModelListItemPricing": "ModelPricing",
    "ModelDetailOffer": "ModelOffer",
    # hosted prompts
    "HostedPromptListItem": "HostedPrompt",
    "HostedPromptListItemVariable": "HostedPromptVariable",
    "HostedPromptCreateParamsVariable": "HostedPromptVariableParam",
    # preflight
    "PreflightResponseGrant": "PreflightGrant",
    "PreflightResponseKnowledge": "PreflightKnowledge",
    "PreflightResponsePrompt": "PreflightPrompt",
    "PreflightResponsePromptVariable": "PreflightPromptVariable",
    # artifacts / outcomes
    "ArtifactFinalParamsDiffStats": "DiffStatsParams",
    "DiffStatsParamsLengths": "DiffLengthsParams",
    # bench
    "BenchRunAllowance": "BenchAllowance",
    "BenchRunDisposition": "BenchDisposition",
    "BenchDispositionPower": "BenchPowerAdvisory",
    "BenchRunRun": "BenchEvalRun",
    "BenchEvalRunEvidenceClass": "BenchEvidenceClass",
    "BenchCompareGateCallTypeCostInterval": "BenchInterval",
    "BenchCompareGateEntitlement": "BenchEntitlement",
    "BenchReportCallTypeDatasetCard": "BenchDatasetCard",
    "BenchDatasetCardExclusion": "BenchDatasetExclusion",
    "BenchDatasetCardPowerPlan": "BenchPowerPlan",
    "BenchDatasetCardStaleness": "BenchDatasetStaleness",
    "BenchDatasetCardStratum": "BenchDatasetStratum",
    "BenchOutcomesParamsOutcome": "BenchOutcomeParams",
    "BenchOutcomesRecordedItem": "BenchRecordedOutcome",
    "BenchExpectationsParamsExpectation": "BenchExpectationParams",
    "BenchExpectationsAttachedItem": "BenchAttachedExpectation",
    # call types + evals
    "CallTypeConfigParamsSelfImproveGuardrails": "SelfImproveGuardrailsParams",
    "EvalRunListItem": "EvalRun",
    "EvalRunCandidate": "EvalRunCandidate",
    "EvalRunRunSpec": "EvalRunSpec",
    # reviewer
    "ReviewerRepairResultBefore": "ReviewerRepairBefore",
    "ReviewerHealthEvents": "ReviewerHealthEventCounts",
    "ReviewerSetupSignature": "ReviewerSignatureRecipe",
    # flywheel
    "FlywheelCandidateListCandidate": "FlywheelCandidate",
    "CandidateRolloutParamsObservedIdentity": "CandidateRolloutIdentityParams",
    "CandidateRolloutResultBlocker": "CandidateRolloutBlocker",
    "ConfirmationListConfirmation": "Confirmation",
    "OracleJobListItem": "OracleJob",
    "OracleQualifyParamsExample": "OracleExampleParams",
    "OracleTestParamsProbe": "OracleProbeParams",
    "OracleVerdictsParamsVerdict": "OracleVerdictParams",
    "OracleVerdictsResultItem": "OracleVerdictResult",
    "OracleVerdictsResultQualificationItem": "OracleQualificationOutcome",
    "LearningPlanEnvelopePlan": "LearningPlan",
    "LearningPlanListPlan": "LearningPlanProposal",
    "PromptCandidateListCandidate": "PromptCandidate",
    "VerdictSourceCheckProbe": "VerdictSourceProbe",
    "VerdictSourceGradeParamsVerdict": "VerdictSourceVerdictParams",
    "VerdictSourceListItem": "VerdictSource",
}

#: Response models whose name ends up used by several operations are generated once.

_IRREGULAR_SINGULARS = {
    "data": "Item",
    "entries": "Entry",
    "classes": "Class",
    "statuses": "Status",
    "analyses": "Analysis",
    "aliases": "Alias",
    "matches": "Match",
    "series": "Series",
    "batches": "Batch",
    "properties": "Property",
    "policies": "Policy",
    "strata": "Stratum",
    "criteria": "Criterion",
    "vias": "Via",
}


def pascal(name: str) -> str:
    """``call_types`` -> ``CallTypes``; non-identifier characters split words."""
    parts = re.split(r"[^0-9A-Za-z]+", name)
    out = "".join(p[:1].upper() + p[1:] for p in parts if p)
    if not out or out[0].isdigit():
        out = "X" + out
    return out


def singular(name: str) -> str:
    """Best-effort singular of an array property name, as a PascalCase word."""
    if name in _IRREGULAR_SINGULARS:
        return _IRREGULAR_SINGULARS[name]
    base = name
    if base.endswith("ies") and len(base) > 4:
        base = base[:-3] + "y"
    elif base.endswith("sses"):
        base = base[:-2]
    elif base.endswith("s") and not base.endswith("ss") and len(base) > 3:
        base = base[:-1]
    else:
        return pascal(base) + "Item"
    return pascal(base)


def strip_description(schema: Any) -> Any:
    """A copy of a schema without documentation keys (the structural identity)."""
    if isinstance(schema, dict):
        return {
            k: strip_description(v)
            for k, v in schema.items()
            if k not in ("description", "example", "examples", "title", "default")
        }
    if isinstance(schema, list):
        return [strip_description(v) for v in schema]
    return schema


def structural_key(schema: Any) -> str:
    """The identity of an object schema, ignoring docs and its own (reference-site) nullability."""
    stripped = strip_description(schema)
    if isinstance(stripped, dict):
        stripped.pop("nullable", None)
    return json.dumps(stripped, sort_keys=True)


def clean_doc(text: str | None) -> str | None:
    if text is None:
        return None
    text = text.strip()
    if not text:
        return None
    return text


def is_nullable_marker(schema: Any) -> bool:
    """``{"nullable": true}`` with no type: a value that may be anything (``Any``).

    The spec writes a nullable union as ``anyOf``/``oneOf`` with ``nullable: true`` beside it; a bare
    ``{"nullable": true}`` member of a union is read as its ``null`` branch.
    """
    return isinstance(schema, dict) and schema.get("nullable") is True and len(schema) == 1


@dataclass
class FieldDef:
    name: str  # python attribute name
    wire: str  # JSON property name
    annotation: str
    required: bool
    nullable: bool
    doc: str | None


@dataclass
class ClassDef:
    name: str
    kind: str  # "model" | "params"
    doc: str | None
    fields: list[FieldDef] = field(default_factory=list)
    pointer: str = ""


class Generator:
    """Walks the in-scope operations and accumulates class definitions."""

    def __init__(self, spec: dict[str, Any]) -> None:
        self.spec = spec
        self.schemas: dict[str, Any] = spec["components"]["schemas"]
        self.classes: dict[str, ClassDef] = {}
        self.order: list[str] = []
        # (kind, structural key) -> class name, for dedupe
        self.by_structure: dict[tuple[str, str], str] = {}
        # (kind, component) -> class name
        self.by_component: dict[tuple[str, str], str] = {}
        self.auto_names: set[str] = set()
        self.uses_literal = False
        self.uses_required = False
        self.uses_field = False
        self.operations: list[dict[str, Any]] = []
        # (kind, structural key) -> component name: an inline copy of a component reuses its class
        self.component_structures: dict[tuple[str, str], str] = {}
        for component, schema in self.schemas.items():
            for kind in ("model", "params"):
                body = schema
                if kind == "model":
                    body = self.merged_variants(schema) or schema
                self.component_structures.setdefault((kind, structural_key(body)), component)

    # ── scope ────────────────────────────────────────────────────────────────

    def in_scope_operations(self) -> list[tuple[str, str, dict[str, Any]]]:
        ops: list[tuple[str, str, dict[str, Any]]] = []
        for path, item in self.spec["paths"].items():
            for method in HTTP_METHODS:
                op = item.get(method)
                if op is None:
                    continue
                security = op.get("security")
                if not security or not any("bearerAuth" in s for s in security):
                    continue
                if op["operationId"] in EXCLUDED_OPERATIONS:
                    continue
                ops.append((method, path, op))
        return ops

    def run(self) -> None:
        for method, path, op in self.in_scope_operations():
            op_id = op["operationId"]
            record: dict[str, Any] = {
                "operation_id": op_id,
                "method": method.upper(),
                "path": path,
                "response": None,
                "params": None,
            }
            body = op.get("requestBody")
            if body is not None:
                schema = body.get("content", {}).get("application/json", {}).get("schema")
                if schema is not None:
                    record["params"] = self.top_level(schema, "params", op_id, PARAMS_NAMES)
            for status, response in op.get("responses", {}).items():
                if not status.startswith("2"):
                    continue
                schema = response.get("content", {}).get("application/json", {}).get("schema")
                if schema is not None:
                    record["response"] = self.top_level(schema, "model", op_id, RESPONSE_NAMES)
                    break
            self.operations.append(record)

    def top_level(
        self, schema: dict[str, Any], kind: str, op_id: str, names: dict[str, str]
    ) -> str:
        if "$ref" in schema:
            return self.component(schema["$ref"].split("/")[-1], kind)
        name = names.get(op_id)
        if name is None:
            base = pascal(op_id[:1].upper() + op_id[1:])
            name = base + ("Params" if kind == "params" else "Response")
        return self.object_class(schema, kind, name, pointer=f"operation:{op_id}")

    def component(self, component: str, kind: str) -> str:
        key = (kind, component)
        if key in self.by_component:
            return self.by_component[key]
        name = COMPONENT_NAMES.get(component, component)
        if kind == "params" and not name.endswith("Params"):
            name = name + "Params" if component not in COMPONENT_NAMES else name
        self.by_component[key] = name
        schema = self.schemas[component]
        self.object_class(schema, kind, name, pointer=f"component:{component}", force_name=True)
        return name

    # ── classes ──────────────────────────────────────────────────────────────

    def merged_variants(self, schema: dict[str, Any]) -> dict[str, Any] | None:
        """Merge a oneOf/anyOf whose members are all objects into one object schema."""
        for key in ("oneOf", "anyOf"):
            variants = schema.get(key)
            if not variants:
                continue
            members = [self.deref(v) for v in variants if not is_nullable_marker(v)]
            if not members or not all(
                m.get("type") == "object" and "properties" in m for m in members
            ):
                return None
            properties: dict[str, Any] = {}
            required: set[str] | None = None
            for member in members:
                for prop, prop_schema in member["properties"].items():
                    if prop not in properties:
                        properties[prop] = prop_schema
                    elif structural_key(properties[prop]) != structural_key(prop_schema):
                        existing = properties[prop]
                        alts = (
                            existing["anyOf"]
                            if "anyOf" in existing and existing.get("_merged")
                            else [existing]
                        )
                        if all(structural_key(a) != structural_key(prop_schema) for a in alts):
                            alts = [*alts, prop_schema]
                        properties[prop] = {
                            "anyOf": alts,
                            "_merged": True,
                            "description": existing.get("description"),
                        }
                req = set(member.get("required", []))
                required = req if required is None else required & req
            merged: dict[str, Any] = {
                "type": "object",
                "properties": properties,
                "required": sorted(required or set()),
            }
            if schema.get("description"):
                merged["description"] = schema["description"]
            return merged
        return None

    def deref(self, schema: dict[str, Any]) -> dict[str, Any]:
        if "$ref" in schema:
            return dict(self.schemas[schema["$ref"].split("/")[-1]])
        return schema

    def object_class(
        self,
        schema: dict[str, Any],
        kind: str,
        name: str,
        *,
        pointer: str,
        force_name: bool = False,
    ) -> str:
        if kind == "model":
            merged = self.merged_variants(schema)
            if merged is not None:
                schema = merged
        skey = (kind, structural_key(schema))
        if not force_name and skey in self.by_structure:
            return self.by_structure[skey]
        if not force_name and skey in self.component_structures:
            return self.component(self.component_structures[skey], kind)
        auto = name
        n = 2
        while auto in self.auto_names:
            auto = f"{name}{n}"
            n += 1
        self.auto_names.add(auto)
        name = self.unique_name(NESTED_NAMES.get(auto, auto))
        self.by_structure.setdefault(skey, name)
        cls = ClassDef(
            name=name, kind=kind, doc=clean_doc(schema.get("description")), pointer=pointer
        )
        self.classes[name] = cls
        self.order.append(name)
        required = set(schema.get("required", []))
        for prop, prop_schema in schema.get("properties", {}).items():
            annotation, nullable = self.annotation(prop_schema, kind, name, prop)
            attr = self.attribute_name(prop, kind)
            doc = clean_doc(
                prop_schema.get("description") if isinstance(prop_schema, dict) else None
            )
            enum_values = self.enum_values(prop_schema)
            if kind == "model" and enum_values:
                listing = ", ".join(f"``{v}``" for v in enum_values)
                doc = (doc + "\n\n" if doc else "") + f"Known values: {listing}."
            cls.fields.append(
                FieldDef(
                    name=attr,
                    wire=prop,
                    annotation=annotation,
                    required=prop in required,
                    nullable=nullable,
                    doc=doc,
                )
            )
        return name

    def enum_values(self, schema: Any) -> list[Any]:
        if not isinstance(schema, dict):
            return []
        if "enum" in schema:
            return list(schema["enum"])
        if schema.get("type") == "array" and isinstance(schema.get("items"), dict):
            return list(schema["items"].get("enum", []))
        return []

    def unique_name(self, name: str) -> str:
        if name not in self.classes:
            return name
        n = 2
        while f"{name}{n}" in self.classes:
            n += 1
        return f"{name}{n}"

    def attribute_name(self, prop: str, kind: str) -> str:
        if kind == "params":
            return prop
        attr = re.sub(r"[^0-9A-Za-z_]", "_", prop)
        if attr[:1].isdigit():
            attr = "_" + attr
        if keyword.iskeyword(attr) or attr in {
            "schema",
            "json",
            "dict",
            "copy",
            "validate",
            "construct",
            "fields",
        }:
            attr = attr + "_"
        return attr

    # ── annotations ──────────────────────────────────────────────────────────

    def annotation(self, schema: Any, kind: str, parent: str, prop: str) -> tuple[str, bool]:
        """Return (annotation without None, nullable)."""
        if not isinstance(schema, dict) or not schema:
            return "Any", False
        nullable = bool(schema.get("nullable"))
        if "$ref" in schema:
            return self.component(schema["$ref"].split("/")[-1], kind), nullable
        for key in ("anyOf", "oneOf"):
            if key in schema:
                if kind == "model":
                    merged = self.merged_variants(schema)
                    if merged is not None:
                        name = self.object_class(
                            merged, kind, parent + pascal(prop), pointer=f"{parent}.{prop}"
                        )
                        has_null = any(is_nullable_marker(v) for v in schema[key])
                        return name, nullable or has_null
                parts: list[str] = []
                for variant in schema[key]:
                    if is_nullable_marker(variant):
                        nullable = True
                        continue
                    sub, sub_null = self.annotation(variant, kind, parent, prop)
                    nullable = nullable or sub_null
                    if sub not in parts:
                        parts.append(sub)
                if not parts:
                    return "Any", nullable
                if "Any" in parts:
                    return "Any", nullable
                return (parts[0] if len(parts) == 1 else " | ".join(parts)), nullable
        typ = schema.get("type")
        enum = schema.get("enum")
        if enum is not None and kind == "params":
            self.uses_literal = True
            return "Literal[" + ", ".join(json.dumps(v) for v in enum) + "]", nullable
        if typ == "string":
            return "str", nullable
        if typ == "integer":
            return "int", nullable
        if typ == "number":
            return "float", nullable
        if typ == "boolean":
            return "bool", nullable
        if typ == "array":
            items = schema.get("items", {})
            item_ann, item_null = self.annotation(items, kind, parent, prop + "__item")
            if item_null and item_ann != "Any":
                item_ann = f"{item_ann} | None"
            inner_name = item_ann
            return f"list[{inner_name}]", nullable
        if typ == "object" or "properties" in schema:
            if schema.get("properties"):
                base = parent + (singular(prop[:-6]) if prop.endswith("__item") else pascal(prop))
                name = self.object_class(schema, kind, base, pointer=f"{parent}.{prop}")
                return name, nullable
            extra = schema.get("additionalProperties")
            if isinstance(extra, dict) and extra and not is_nullable_marker(extra):
                value_ann, value_null = self.annotation(extra, kind, parent, prop + "_value")
                if value_null and value_ann != "Any":
                    value_ann = f"{value_ann} | None"
                return f"dict[str, {value_ann}]", nullable
            return "dict[str, Any]", nullable
        return "Any", nullable

    # ── rendering ────────────────────────────────────────────────────────────

    def render(self) -> str:
        body: list[str] = []
        for name in self.order:
            cls = self.classes[name]
            body.append("")
            body.append("")
            if cls.kind == "model":
                body.extend(self.render_model(cls))
            else:
                body.extend(self.render_params(cls))
        body.append("")
        body.append("")
        body.append("for _model in (")
        for name in self.order:
            if self.classes[name].kind == "model":
                body.append(f"    {name},")
        body.append("):")
        body.append("    _model.model_rebuild()")
        body.append("")
        body.append(
            "#: The in-scope operations: operationId -> (method, path, params class, response class)."
        )
        body.append("OPERATIONS: dict[str, tuple[str, str, str | None, str | None]] = {")
        for record in self.operations:
            body.append(
                f'    "{record["operation_id"]}": ("{record["method"]}", "{record["path"]}", '
                f"{record['params']!r}, {record['response']!r}),"
            )
        body.append("}")
        body.append("")

        head: list[str] = []
        head.append('"""Typed API shapes generated from ``openapi/openapi.yaml``.')
        head.append("")
        head.append(
            "Do not edit by hand: run ``python scripts/gen_types.py`` after re-syncing the spec."
        )
        head.append(
            "Response models subclass :class:`ultrarouter.BaseModel` (unknown fields are kept);"
        )
        head.append("request shapes are ``TypedDict`` classes used to type method arguments.")
        head.append('"""')
        head.append("")
        head.append("from __future__ import annotations")
        head.append("")
        typing_names = ["Any"]
        if self.uses_literal:
            typing_names.append("Literal")
        head.append(f"from typing import {', '.join(sorted(typing_names))}")
        head.append("")
        if self.uses_field:
            head.append("from pydantic import Field")
        ext = ["TypedDict"]
        if self.uses_required:
            ext.insert(0, "Required")
        head.append(f"from typing_extensions import {', '.join(ext)}")
        head.append("")
        head.append("from .._models import BaseModel")
        head.append("")
        head.append("__all__ = [")
        head.append('    "OPERATIONS",')
        for n in sorted(self.order):
            head.append(f'    "{n}",')
        head.append("]")
        return "\n".join(head + body)

    def docstring(self, text: str, indent: str) -> list[str]:
        text = text.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
        if "\n" not in text and len(text) + len(indent) + 6 <= 100:
            return [f'{indent}"""{text}"""']
        out = [f'{indent}"""{text.splitlines()[0]}']
        for line in text.splitlines()[1:]:
            out.append(f"{indent}{line}" if line else "")
        out.append(f'{indent}"""')
        return out

    def class_doc(self, cls: ClassDef) -> str:
        if cls.doc:
            return cls.doc
        if cls.kind == "params":
            return f"Request shape ``{cls.name}``."
        return f"Response shape ``{cls.name}``."

    def render_model(self, cls: ClassDef) -> list[str]:
        out = [f"class {cls.name}(BaseModel):"]
        out.extend(self.docstring(self.class_doc(cls), "    "))
        for f in cls.fields:
            out.append("")
            ann = f.annotation
            if f.nullable or not f.required:
                ann = ann if ann == "Any" else f"{ann} | None"
            if f.name != f.wire:
                self.uses_field = True
                default = "..." if f.required else "None"
                out.append(f'    {f.name}: {ann} = Field({default}, alias="{f.wire}")')
            elif f.required:
                out.append(f"    {f.name}: {ann}")
            else:
                out.append(f"    {f.name}: {ann} = None")
            if f.doc:
                out.extend(self.docstring(f.doc, "    "))
        return out

    def render_params(self, cls: ClassDef) -> list[str]:
        functional = any(not f.wire.isidentifier() or keyword.iskeyword(f.wire) for f in cls.fields)
        if functional:
            out = [f'{cls.name} = TypedDict(\n    "{cls.name}",\n    {{']
            for f in cls.fields:
                ann = f.annotation
                if f.nullable:
                    ann = ann if ann == "Any" else f"{ann} | None"
                if f.required:
                    self.uses_required = True
                    ann = f"Required[{ann}]"
                out.append(f'        "{f.wire}": {ann},')
            out.append("    },\n    total=False,\n)")
            out.extend(self.docstring(self.class_doc(cls), ""))
            return out
        out = [f"class {cls.name}(TypedDict, total=False):"]
        out.extend(self.docstring(self.class_doc(cls), "    "))
        for f in cls.fields:
            ann = f.annotation
            if f.nullable:
                ann = ann if ann == "Any" else f"{ann} | None"
            if f.required:
                self.uses_required = True
                ann = f"Required[{ann}]"
            out.append("")
            out.append(f"    {f.wire}: {ann}")
            if f.doc:
                out.extend(self.docstring(f.doc, "    "))
        return out


def generate(spec_path: Path = SPEC_PATH) -> str:
    """Return the formatted module source for the spec at ``spec_path``."""
    text = spec_path.read_text(encoding="utf-8")
    spec = yaml.safe_load(text)
    gen = Generator(spec)
    gen.run()
    source = gen.render()
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "_generated.py"
        target.write_text(source, encoding="utf-8")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "ruff",
                "format",
                "--quiet",
                "--config",
                str(ROOT / "pyproject.toml"),
                str(target),
            ],
            check=True,
        )
        return target.read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check", action="store_true", help="fail if the committed module is stale"
    )
    args = parser.parse_args(argv)
    source = generate()
    if args.check:
        current = OUT_PATH.read_text(encoding="utf-8") if OUT_PATH.exists() else ""
        if current != source:
            print(
                f"{OUT_PATH.relative_to(ROOT)} is stale: run `python scripts/gen_types.py`",
                file=sys.stderr,
            )
            return 1
        print(f"{OUT_PATH.relative_to(ROOT)} is up to date")
        return 0
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(source, encoding="utf-8")
    print(f"wrote {OUT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
