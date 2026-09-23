"""Deterministic In-Memory Economics Engine for Block 16."""

import threading
from typing import Dict, List, Optional

from infuse.economics.calculator import calculate_execution_economics
from infuse.economics.interfaces import IEconomicsEngine, IPricingRegistry
from infuse.economics.models import ExecutionEconomicSummary
from infuse.economics.pricing_registry import InMemoryPricingRegistry
from infuse.observer.models import ExecutionTokenSummary


class EconomicsEngine(IEconomicsEngine):
    """Deterministic engine for converting normalized token usage facts into economic cost facts.

    Calculates execution-level costs using registered pricing rates without performing
    governance, routing, customer billing, or lifecycle mutations.
    """

    def __init__(self, pricing_registry: Optional[IPricingRegistry] = None) -> None:
        self._lock = threading.RLock()
        self._registry = pricing_registry or InMemoryPricingRegistry()
        self._summaries: Dict[str, ExecutionEconomicSummary] = {}

    @property
    def pricing_registry(self) -> IPricingRegistry:
        """Access the backing pricing rate registry."""
        return self._registry

    def calculate(self, summary: ExecutionTokenSummary) -> ExecutionEconomicSummary:
        """Deterministically calculate economic cost from an ExecutionTokenSummary."""
        if not summary or not summary.execution_id:
            raise ValueError("ExecutionTokenSummary with valid execution_id is required.")

        pricing_rate = None
        if summary.provider_id and summary.model_id:
            pricing_rate = self._registry.get_rate(summary.provider_id, summary.model_id)

        economic_summary = calculate_execution_economics(summary, pricing_rate)

        with self._lock:
            self._summaries[summary.execution_id] = economic_summary
            return economic_summary.model_copy(deep=True)

    def get_summary(self, execution_id: str) -> Optional[ExecutionEconomicSummary]:
        """Retrieve a deep copy of the latest cached economic summary for an execution."""
        if not execution_id:
            return None
        with self._lock:
            res = self._summaries.get(execution_id.strip())
            return res.model_copy(deep=True) if res else None

    def list_summaries(self) -> List[ExecutionEconomicSummary]:
        """List deep copies of all active execution economic summaries."""
        with self._lock:
            return [s.model_copy(deep=True) for s in self._summaries.values()]

    def clear(self) -> None:
        """Clear cached economic calculation state."""
        with self._lock:
            self._summaries.clear()
