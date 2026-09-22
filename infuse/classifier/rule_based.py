"""Rule-based deterministic Workload Classifier implementation."""

from typing import List, Tuple

from infuse.classifier.interfaces import IWorkloadClassifier
from infuse.classifier.models import (
    ComplexityLevel,
    IntensityLevel,
    WorkloadCategory,
    WorkloadClassification,
    WorkloadDimensions,
)
from infuse.context.models import ExecutionContextRecord
from infuse.version import SCHEMA_VERSION

_HINT_MAP = {
    "code": WorkloadCategory.CODING,
    "coding": WorkloadCategory.CODING,
    "dev": WorkloadCategory.CODING,
    "software": WorkloadCategory.CODING,
    "programming": WorkloadCategory.CODING,
    "reasoning": WorkloadCategory.REASONING,
    "logic": WorkloadCategory.REASONING,
    "math": WorkloadCategory.REASONING,
    "chat": WorkloadCategory.CONVERSATIONAL,
    "conversation": WorkloadCategory.CONVERSATIONAL,
    "fast-chat": WorkloadCategory.CONVERSATIONAL,
    "dialogue": WorkloadCategory.CONVERSATIONAL,
    "tools": WorkloadCategory.TOOL_USE,
    "tool_use": WorkloadCategory.TOOL_USE,
    "agent": WorkloadCategory.TOOL_USE,
    "functions": WorkloadCategory.TOOL_USE,
    "web": WorkloadCategory.WEB_ENABLED,
    "search": WorkloadCategory.WEB_ENABLED,
    "research": WorkloadCategory.WEB_ENABLED,
    "browsing": WorkloadCategory.WEB_ENABLED,
    "vision": WorkloadCategory.MULTIMODAL,
    "image": WorkloadCategory.MULTIMODAL,
    "multimodal": WorkloadCategory.MULTIMODAL,
    "extract": WorkloadCategory.EXTRACTION,
    "extraction": WorkloadCategory.EXTRACTION,
    "scraping": WorkloadCategory.EXTRACTION,
    "transform": WorkloadCategory.TRANSFORMATION,
    "transformation": WorkloadCategory.TRANSFORMATION,
    "translation": WorkloadCategory.TRANSFORMATION,
    "json": WorkloadCategory.STRUCTURED_GENERATION,
    "structured": WorkloadCategory.STRUCTURED_GENERATION,
    "schema": WorkloadCategory.STRUCTURED_GENERATION,
    "workflow": WorkloadCategory.WORKFLOW_EXECUTION,
    "pipeline": WorkloadCategory.WORKFLOW_EXECUTION,
    "step": WorkloadCategory.WORKFLOW_EXECUTION,
}


class RuleBasedWorkloadClassifier(IWorkloadClassifier):
    """Deterministic, explainable rule-based workload classifier."""

    def classify(self, context: ExecutionContextRecord) -> WorkloadClassification:
        evidence: List[str] = []

        # 1. Resolve capability demands
        req_caps = [c.lower() for c in context.constraints.requested_capabilities]
        tools_req = (
            context.constraints.supports_tools
            or context.operation.has_tools
            or context.operation.tool_count > 0
            or "tools" in req_caps
            or "tool_use" in req_caps
        )
        web_req = "web" in req_caps or "search" in req_caps or "browsing" in req_caps
        vision_req = context.constraints.supports_vision or "vision" in req_caps or "multimodal" in req_caps
        structured_req = (
            context.constraints.supports_structured_output
            or "structured_output" in req_caps
            or "json" in req_caps
        )

        # 2. Determine Primary & Secondary Categories
        category, secondary_categories = self._resolve_categories(
            context=context,
            tools_req=tools_req,
            web_req=web_req,
            vision_req=vision_req,
            structured_req=structured_req,
            evidence=evidence
        )

        # 3. Compute Dimensions & Resource Intensities
        dimensions = self._compute_dimensions(
            context=context,
            tools_req=tools_req,
            web_req=web_req,
            vision_req=vision_req,
            structured_req=structured_req,
            evidence=evidence
        )

        # 4. Compute Deterministic Complexity Score & Level
        complexity_level, complexity_score = self._compute_complexity(
            context=context,
            dimensions=dimensions,
            evidence=evidence
        )

        return WorkloadClassification(
            category=category,
            secondary_categories=secondary_categories,
            complexity_level=complexity_level,
            complexity_score=complexity_score,
            dimensions=dimensions,
            evidence=evidence,
            schema_version=SCHEMA_VERSION
        )

    def _resolve_categories(
        self,
        context: ExecutionContextRecord,
        tools_req: bool,
        web_req: bool,
        vision_req: bool,
        structured_req: bool,
        evidence: List[str]
    ) -> Tuple[WorkloadCategory, List[WorkloadCategory]]:
        primary: WorkloadCategory = WorkloadCategory.UNKNOWN
        hint = context.task.workload_hint

        # Check explicit caller workload_hint first
        if hint and hint.strip():
            norm_hint = hint.strip().lower()
            if norm_hint in _HINT_MAP:
                primary = _HINT_MAP[norm_hint]
                evidence.append(f"Category '{primary.value}' mapped from caller workload_hint '{hint}'.")
            else:
                try:
                    primary = WorkloadCategory(hint.strip().upper())
                    evidence.append(f"Category '{primary.value}' matched explicit canonical enum from workload_hint '{hint}'.")
                except ValueError:
                    primary = WorkloadCategory.UNKNOWN

        # If no hint or unknown, infer from capabilities and context
        if primary == WorkloadCategory.UNKNOWN:
            if vision_req:
                primary = WorkloadCategory.MULTIMODAL
                evidence.append("Category inferred as MULTIMODAL from vision capability requirement.")
            elif tools_req:
                primary = WorkloadCategory.TOOL_USE
                evidence.append("Category inferred as TOOL_USE from tool calling requirement.")
            elif web_req:
                primary = WorkloadCategory.WEB_ENABLED
                evidence.append("Category inferred as WEB_ENABLED from web browsing requirement.")
            elif structured_req:
                primary = WorkloadCategory.STRUCTURED_GENERATION
                evidence.append("Category inferred as STRUCTURED_GENERATION from structured output requirement.")
            elif context.runtime.step_index > 0 or (context.runtime.workflow_id and context.runtime.workflow_id.strip()):
                primary = WorkloadCategory.WORKFLOW_EXECUTION
                evidence.append("Category inferred as WORKFLOW_EXECUTION from workflow trajectory signals.")
            elif context.operation.message_count > 0:
                primary = WorkloadCategory.CONVERSATIONAL
                evidence.append("Category inferred as CONVERSATIONAL from message history presence.")
            else:
                primary = WorkloadCategory.UNKNOWN
                evidence.append("Category unclassified (UNKNOWN) due to absence of identifying workload signals.")

        # Resolve secondary categories
        secondaries: List[WorkloadCategory] = []
        if tools_req and primary != WorkloadCategory.TOOL_USE:
            secondaries.append(WorkloadCategory.TOOL_USE)
        if web_req and primary != WorkloadCategory.WEB_ENABLED:
            secondaries.append(WorkloadCategory.WEB_ENABLED)
        if vision_req and primary != WorkloadCategory.MULTIMODAL:
            secondaries.append(WorkloadCategory.MULTIMODAL)
        if structured_req and primary != WorkloadCategory.STRUCTURED_GENERATION:
            secondaries.append(WorkloadCategory.STRUCTURED_GENERATION)
        if (context.runtime.step_index > 0 or context.runtime.workflow_id) and primary != WorkloadCategory.WORKFLOW_EXECUTION:
            secondaries.append(WorkloadCategory.WORKFLOW_EXECUTION)

        return primary, secondaries

    def _compute_dimensions(
        self,
        context: ExecutionContextRecord,
        tools_req: bool,
        web_req: bool,
        vision_req: bool,
        structured_req: bool,
        evidence: List[str]
    ) -> WorkloadDimensions:
        tool_count = context.operation.tool_count
        if tool_count == 0:
            tool_intensity = IntensityLevel.NONE
        elif tool_count <= 2:
            tool_intensity = IntensityLevel.LOW
        elif tool_count <= 5:
            tool_intensity = IntensityLevel.MEDIUM
        else:
            tool_intensity = IntensityLevel.HIGH

        est_tokens = context.constraints.min_context_tokens or 0
        if est_tokens <= 4000:
            context_intensity = IntensityLevel.LOW
        elif est_tokens <= 16000:
            context_intensity = IntensityLevel.MEDIUM
        else:
            context_intensity = IntensityLevel.HIGH

        max_lat = context.constraints.max_latency_ms
        if max_lat is not None and max_lat <= 1000.0:
            latency_sensitivity = IntensityLevel.HIGH
        elif max_lat is not None and max_lat <= 5000.0:
            latency_sensitivity = IntensityLevel.MEDIUM
        else:
            latency_sensitivity = IntensityLevel.LOW

        evidence.append(
            f"Dimensions: tools={tools_req} (intensity={tool_intensity.value}), "
            f"web={web_req}, vision={vision_req}, structured={structured_req}, "
            f"context_intensity={context_intensity.value}, latency_sensitivity={latency_sensitivity.value}."
        )

        return WorkloadDimensions(
            requires_tools=tools_req,
            requires_web=web_req,
            requires_vision=vision_req,
            requires_structured_output=structured_req,
            context_intensity=context_intensity,
            tool_intensity=tool_intensity,
            latency_sensitivity=latency_sensitivity,
            estimated_context_tokens=est_tokens,
            message_count=context.operation.message_count,
            tool_count=tool_count
        )

    def _compute_complexity(
        self,
        context: ExecutionContextRecord,
        dimensions: WorkloadDimensions,
        evidence: List[str]
    ) -> Tuple[ComplexityLevel, float]:
        score = 0.1  # Baseline complexity

        if dimensions.requires_tools:
            score += 0.20
            if dimensions.tool_count > 2:
                score += min(0.15, (dimensions.tool_count - 2) * 0.05)

        if dimensions.requires_web:
            score += 0.15

        if dimensions.requires_vision:
            score += 0.20

        if dimensions.requires_structured_output:
            score += 0.10

        if context.runtime.step_index > 0:
            score += min(0.15, context.runtime.step_index * 0.05)

        if dimensions.estimated_context_tokens > 32000:
            score += 0.20
        elif dimensions.estimated_context_tokens > 8000:
            score += 0.10

        if dimensions.message_count > 10:
            score += 0.15
        elif dimensions.message_count > 4:
            score += 0.08

        # Bound score between 0.0 and 1.0
        score = min(1.0, max(0.0, score))
        score = round(score, 2)

        if score < 0.30:
            level = ComplexityLevel.LOW
        elif score < 0.60:
            level = ComplexityLevel.MODERATE
        elif score < 0.85:
            level = ComplexityLevel.HIGH
        else:
            level = ComplexityLevel.VERY_HIGH

        evidence.append(f"Derived complexity score {score} -> level '{level.value}'.")
        return level, score
