"""Normalized Data Models for Block 16 Economics Engine."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import Field

from infuse.contracts.common import InfuseBaseModel, utc_now
from infuse.version import SCHEMA_VERSION


class PricingUnit(str, Enum):
    """Normalization unit for token pricing rates."""
    PER_TOKEN = "PER_TOKEN"
    PER_1K_TOKENS = "PER_1K_TOKENS"
    PER_1M_TOKENS = "PER_1M_TOKENS"


class EconomicCompleteness(str, Enum):
    """Categorical status of economic calculation completeness."""
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"


class ModelPricingRate(InfuseBaseModel):
    """Normalized rate declaration for a provider/model target."""
    provider_id: str = Field(..., description="Provider identifier (e.g. 'openai', 'anthropic').")
    model_id: str = Field(..., description="Model identifier (e.g. 'gpt-4o', 'claude-3-5-sonnet').")
    input_rate: Optional[Decimal] = Field(default=None, description="Input/prompt token rate.")
    output_rate: Optional[Decimal] = Field(default=None, description="Output/completion token rate.")
    cached_rate: Optional[Decimal] = Field(default=None, description="Cached prompt token rate.")
    unit: PricingUnit = Field(
        default=PricingUnit.PER_1M_TOKENS,
        description="Base unit for the rate (e.g. per 1M tokens)."
    )
    currency: Optional[str] = Field(
        default=None,
        description="Currency code (e.g. 'USD', 'EUR'). None if unspecified."
    )
    effective_from: Optional[datetime] = Field(
        default=None,
        description="Timestamp when rate becomes effective."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Pricing metadata extensions."
    )


class CostComponent(InfuseBaseModel):
    """Detailed breakdown of a single priced dimension."""
    dimension: str = Field(..., description="Token dimension name (e.g. 'input', 'output', 'cached').")
    tokens: Optional[int] = Field(default=None, ge=0, description="Token count observed.")
    unit_rate: Optional[Decimal] = Field(default=None, description="Unit rate applied.")
    unit: Optional[PricingUnit] = Field(default=None, description="Pricing unit format.")
    cost: Optional[Decimal] = Field(default=None, description="Calculated exact monetary cost.")
    currency: Optional[str] = Field(default=None, description="Monetary currency.")


class ExecutionEconomicSummary(InfuseBaseModel):
    """Normalized, deterministic economic observation for an execution run."""
    execution_id: str = Field(..., description="Execution identifier.")
    provider_id: Optional[str] = Field(default=None, description="Executing provider ID.")
    model_id: Optional[str] = Field(default=None, description="Executing model ID.")
    input_tokens: Optional[int] = Field(default=None, ge=0, description="Observed input tokens.")
    output_tokens: Optional[int] = Field(default=None, ge=0, description="Observed output tokens.")
    cached_tokens: Optional[int] = Field(default=None, ge=0, description="Observed cached tokens.")
    total_tokens: Optional[int] = Field(default=None, ge=0, description="Observed total tokens.")
    input_cost: Optional[Decimal] = Field(default=None, description="Exact calculated input cost.")
    output_cost: Optional[Decimal] = Field(default=None, description="Exact calculated output cost.")
    cached_cost: Optional[Decimal] = Field(default=None, description="Exact calculated cached cost.")
    total_cost: Optional[Decimal] = Field(default=None, description="Exact calculated total cost.")
    currency: Optional[str] = Field(default=None, description="Pricing currency.")
    completeness: EconomicCompleteness = Field(
        default=EconomicCompleteness.UNKNOWN,
        description="Economic calculation completeness state."
    )
    is_authoritative: bool = Field(
        default=False,
        description="True if usage facts were authoritative."
    )
    is_finalized: bool = Field(
        default=False,
        description="True if execution has concluded."
    )
    pricing_source: Optional[str] = Field(
        default=None,
        description="Source identifier of applied pricing rate."
    )
    events_count: int = Field(default=0, ge=0, description="Number of observed usage events.")
    last_sequence: int = Field(default=0, ge=0, description="Highest observed event sequence.")
    calculated_at: datetime = Field(
        default_factory=utc_now,
        description="UTC calculation timestamp."
    )
    components: List[CostComponent] = Field(
        default_factory=list,
        description="Itemized cost components."
    )
    schema_version: str = Field(
        default=SCHEMA_VERSION,
        description="Contract schema version."
    )


__all__ = [
    "PricingUnit",
    "EconomicCompleteness",
    "ModelPricingRate",
    "CostComponent",
    "ExecutionEconomicSummary",
]
