"""Domain exceptions for INFUSE Economics Layer."""


class EconomicsError(Exception):
    """Base exception for all economics layer errors."""
    pass


class PricingNotFoundError(EconomicsError):
    """Raised when required pricing metadata is not registered for a provider/model."""
    pass


class InvalidPricingRateError(EconomicsError):
    """Raised when a pricing rate declaration contains invalid dimensions or rates."""
    pass


class CalculationError(EconomicsError):
    """Raised when an economic calculation cannot be completed deterministically."""
    pass
