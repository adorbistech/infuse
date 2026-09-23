"""Thread-safe In-Memory Pricing Registry for Block 16 Economics Engine."""

import threading
from typing import Dict, List, Optional, Tuple

from infuse.economics.errors import InvalidPricingRateError
from infuse.economics.interfaces import IPricingRegistry
from infuse.economics.models import ModelPricingRate


class InMemoryPricingRegistry(IPricingRegistry):
    """In-memory thread-safe registry catalog for model and provider pricing rates."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._rates: Dict[Tuple[str, str], ModelPricingRate] = {}

    def _make_key(self, provider_id: str, model_id: str) -> Tuple[str, str]:
        return (provider_id.strip().lower(), model_id.strip().lower())

    def register_rate(self, rate: ModelPricingRate) -> ModelPricingRate:
        """Register or update a pricing rate for a provider/model target."""
        if not rate or not rate.provider_id or not rate.provider_id.strip():
            raise InvalidPricingRateError("Pricing rate must specify a non-empty provider_id.")
        if not rate.model_id or not rate.model_id.strip():
            raise InvalidPricingRateError("Pricing rate must specify a non-empty model_id.")

        if rate.input_rate is not None and rate.input_rate < 0:
            raise InvalidPricingRateError(f"input_rate must be non-negative, got {rate.input_rate}")
        if rate.output_rate is not None and rate.output_rate < 0:
            raise InvalidPricingRateError(f"output_rate must be non-negative, got {rate.output_rate}")
        if rate.cached_rate is not None and rate.cached_rate < 0:
            raise InvalidPricingRateError(f"cached_rate must be non-negative, got {rate.cached_rate}")

        key = self._make_key(rate.provider_id, rate.model_id)
        with self._lock:
            stored = rate.model_copy(deep=True)
            self._rates[key] = stored
            return stored.model_copy(deep=True)

    def get_rate(self, provider_id: str, model_id: str) -> Optional[ModelPricingRate]:
        """Retrieve the pricing rate for a specific provider and model."""
        if not provider_id or not model_id:
            return None
        key = self._make_key(provider_id, model_id)
        with self._lock:
            rate = self._rates.get(key)
            return rate.model_copy(deep=True) if rate else None

    def list_rates(self) -> List[ModelPricingRate]:
        """List all registered pricing rates."""
        with self._lock:
            return [r.model_copy(deep=True) for r in self._rates.values()]

    def delete_rate(self, provider_id: str, model_id: str) -> bool:
        """Remove a pricing rate from the catalog."""
        if not provider_id or not model_id:
            return False
        key = self._make_key(provider_id, model_id)
        with self._lock:
            return self._rates.pop(key, None) is not None

    def clear(self) -> None:
        """Clear all registered rates in memory."""
        with self._lock:
            self._rates.clear()
