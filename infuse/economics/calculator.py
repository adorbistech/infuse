"""Exact Deterministic Cost Calculation Core for Block 16 Economics Engine."""

from decimal import Decimal
from typing import List, Optional, Tuple

from infuse.economics.models import (
    CostComponent,
    EconomicCompleteness,
    ExecutionEconomicSummary,
    ModelPricingRate,
    PricingUnit,
)
from infuse.observer.models import ExecutionTokenSummary


UNIT_FACTORS = {
    PricingUnit.PER_TOKEN: Decimal(1),
    PricingUnit.PER_1K_TOKENS: Decimal(1000),
    PricingUnit.PER_1M_TOKENS: Decimal(1000000),
}


def calculate_dimension_cost(
    tokens: Optional[int],
    rate: Optional[Decimal],
    unit: PricingUnit
) -> Optional[Decimal]:
    """Calculate exact cost for a single token dimension using Decimal arithmetic."""
    if tokens is None or rate is None:
        return None
    factor = UNIT_FACTORS.get(unit, Decimal(1000000))
    # (tokens * rate) / factor ensures high precision without intermediate float conversion
    return (Decimal(tokens) * rate) / factor


def calculate_execution_economics(
    summary: ExecutionTokenSummary,
    pricing_rate: Optional[ModelPricingRate] = None
) -> ExecutionEconomicSummary:
    """Deterministically compute normalized economic facts from an ExecutionTokenSummary."""
    execution_id = summary.execution_id
    provider_id = summary.provider_id
    model_id = summary.model_id

    # If no pricing metadata is available, return UNKNOWN completeness without fabricating costs
    if pricing_rate is None:
        return ExecutionEconomicSummary(
            execution_id=execution_id,
            provider_id=provider_id,
            model_id=model_id,
            input_tokens=summary.input_tokens,
            output_tokens=summary.output_tokens,
            cached_tokens=summary.cached_tokens,
            total_tokens=summary.total_tokens,
            input_cost=None,
            output_cost=None,
            cached_cost=None,
            total_cost=None,
            currency=None,
            completeness=EconomicCompleteness.UNKNOWN,
            is_authoritative=summary.is_authoritative,
            is_finalized=summary.is_finalized,
            pricing_source=None,
            events_count=summary.events_count,
            last_sequence=summary.last_sequence,
            components=[]
        )

    unit = pricing_rate.unit
    currency = pricing_rate.currency
    pricing_source = f"{pricing_rate.provider_id}/{pricing_rate.model_id}"

    # Calculate individual components
    input_cost = calculate_dimension_cost(summary.input_tokens, pricing_rate.input_rate, unit)
    output_cost = calculate_dimension_cost(summary.output_tokens, pricing_rate.output_rate, unit)
    cached_cost = calculate_dimension_cost(summary.cached_tokens, pricing_rate.cached_rate, unit)

    components: List[CostComponent] = []

    if summary.input_tokens is not None or pricing_rate.input_rate is not None:
        components.append(CostComponent(
            dimension="input",
            tokens=summary.input_tokens,
            unit_rate=pricing_rate.input_rate,
            unit=unit,
            cost=input_cost,
            currency=currency
        ))

    if summary.output_tokens is not None or pricing_rate.output_rate is not None:
        components.append(CostComponent(
            dimension="output",
            tokens=summary.output_tokens,
            unit_rate=pricing_rate.output_rate,
            unit=unit,
            cost=output_cost,
            currency=currency
        ))

    if summary.cached_tokens is not None or pricing_rate.cached_rate is not None:
        components.append(CostComponent(
            dimension="cached",
            tokens=summary.cached_tokens,
            unit_rate=pricing_rate.cached_rate,
            unit=unit,
            cost=cached_cost,
            currency=currency
        ))

    # Evaluate completeness
    # Dimensions that were present in token summary
    observed_dimensions = []
    if summary.input_tokens is not None:
        observed_dimensions.append((summary.input_tokens, pricing_rate.input_rate, input_cost))
    if summary.output_tokens is not None:
        observed_dimensions.append((summary.output_tokens, pricing_rate.output_rate, output_cost))
    if summary.cached_tokens is not None:
        observed_dimensions.append((summary.cached_tokens, pricing_rate.cached_rate, cached_cost))

    known_costs = [c for c in [input_cost, output_cost, cached_cost] if c is not None]

    if not observed_dimensions and not known_costs:
        completeness = EconomicCompleteness.UNKNOWN
        total_cost = None
    elif all(rate is not None for _, rate, _ in observed_dimensions) and observed_dimensions:
        completeness = EconomicCompleteness.COMPLETE
        total_cost = sum(known_costs, Decimal(0))
    elif known_costs:
        completeness = EconomicCompleteness.PARTIAL
        total_cost = sum(known_costs, Decimal(0))
    else:
        completeness = EconomicCompleteness.UNKNOWN
        total_cost = None

    return ExecutionEconomicSummary(
        execution_id=execution_id,
        provider_id=provider_id or pricing_rate.provider_id,
        model_id=model_id or pricing_rate.model_id,
        input_tokens=summary.input_tokens,
        output_tokens=summary.output_tokens,
        cached_tokens=summary.cached_tokens,
        total_tokens=summary.total_tokens,
        input_cost=input_cost,
        output_cost=output_cost,
        cached_cost=cached_cost,
        total_cost=total_cost,
        currency=currency,
        completeness=completeness,
        is_authoritative=summary.is_authoritative,
        is_finalized=summary.is_finalized,
        pricing_source=pricing_source,
        events_count=summary.events_count,
        last_sequence=summary.last_sequence,
        components=components
    )
