"""Interface definitions for Block 16 Economics Engine."""

from abc import ABC, abstractmethod
from typing import List, Optional

from infuse.economics.models import ExecutionEconomicSummary, ModelPricingRate
from infuse.observer.models import ExecutionTokenSummary


class IPricingRegistry(ABC):
    """Abstract catalog interface for model and provider pricing rates."""

    @abstractmethod
    def register_rate(self, rate: ModelPricingRate) -> ModelPricingRate:
        """Register or update a pricing rate for a provider/model target."""
        pass

    @abstractmethod
    def get_rate(self, provider_id: str, model_id: str) -> Optional[ModelPricingRate]:
        """Retrieve the pricing rate for a specific provider and model."""
        pass

    @abstractmethod
    def list_rates(self) -> List[ModelPricingRate]:
        """List all registered pricing rates."""
        pass

    @abstractmethod
    def delete_rate(self, provider_id: str, model_id: str) -> bool:
        """Remove a pricing rate from the catalog."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all registered rates in memory."""
        pass


class IEconomicsEngine(ABC):
    """Abstract interface for execution economics calculation."""

    @abstractmethod
    def calculate(self, summary: ExecutionTokenSummary) -> ExecutionEconomicSummary:
        """Deterministically calculate economic cost from an ExecutionTokenSummary."""
        pass

    @abstractmethod
    def get_summary(self, execution_id: str) -> Optional[ExecutionEconomicSummary]:
        """Retrieve the latest cached economic summary for an execution."""
        pass

    @abstractmethod
    def list_summaries(self) -> List[ExecutionEconomicSummary]:
        """List all active execution economic summaries."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear cached economic calculation state."""
        pass
