"""Workload Classifier contract definitions and models."""

from enum import Enum
from typing import List
from pydantic import Field

from infuse.contracts.common import InfuseBaseModel
from infuse.version import SCHEMA_VERSION


class WorkloadCategory(str, Enum):
    """Canonical categorization of agent workloads."""
    CONVERSATIONAL = "CONVERSATIONAL"
    REASONING = "REASONING"
    CODING = "CODING"
    STRUCTURED_GENERATION = "STRUCTURED_GENERATION"
    TOOL_USE = "TOOL_USE"
    WEB_ENABLED = "WEB_ENABLED"
    MULTIMODAL = "MULTIMODAL"
    EXTRACTION = "EXTRACTION"
    TRANSFORMATION = "TRANSFORMATION"
    WORKFLOW_EXECUTION = "WORKFLOW_EXECUTION"
    UNKNOWN = "UNKNOWN"


class ComplexityLevel(str, Enum):
    """Categorical complexity band derived from execution context dimensions."""
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class IntensityLevel(str, Enum):
    """Discrete intensity levels for resource dimensions."""
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class WorkloadDimensions(InfuseBaseModel):
    """Normalized multi-dimensional execution characteristics."""
    requires_tools: bool = Field(
        default=False,
        description="Whether tool/function calling is required for execution."
    )
    requires_web: bool = Field(
        default=False,
        description="Whether external web access/search is required."
    )
    requires_vision: bool = Field(
        default=False,
        description="Whether multimodal vision input processing is required."
    )
    requires_structured_output: bool = Field(
        default=False,
        description="Whether structured JSON output is required."
    )
    context_intensity: IntensityLevel = Field(
        default=IntensityLevel.LOW,
        description="Magnitude of context window demands."
    )
    tool_intensity: IntensityLevel = Field(
        default=IntensityLevel.NONE,
        description="Magnitude of tool calling complexity."
    )
    latency_sensitivity: IntensityLevel = Field(
        default=IntensityLevel.LOW,
        description="Latency urgency demanded by the execution context."
    )
    estimated_context_tokens: int = Field(
        default=0,
        ge=0,
        description="Estimated token context requirement."
    )
    message_count: int = Field(
        default=0,
        ge=0,
        description="Message history depth."
    )
    tool_count: int = Field(
        default=0,
        ge=0,
        description="Total tool interfaces attached."
    )


class WorkloadClassification(InfuseBaseModel):
    """Canonical classification result characterizing an ExecutionContext."""
    category: WorkloadCategory = Field(
        default=WorkloadCategory.UNKNOWN,
        description="Primary canonical workload category."
    )
    secondary_categories: List[WorkloadCategory] = Field(
        default_factory=list,
        description="Secondary workload characteristics."
    )
    complexity_level: ComplexityLevel = Field(
        default=ComplexityLevel.LOW,
        description="Categorical complexity level."
    )
    complexity_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Deterministic complexity score bounded between 0.0 and 1.0."
    )
    dimensions: WorkloadDimensions = Field(
        default_factory=WorkloadDimensions,
        description="Multi-dimensional execution characteristics."
    )
    evidence: List[str] = Field(
        default_factory=list,
        description="Deterministic explainability evidence and rationale for classification."
    )
    schema_version: str = Field(
        default=SCHEMA_VERSION,
        description="Schema contract version."
    )
