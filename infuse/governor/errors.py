"""Domain exceptions for INFUSE Governor Engine."""


class GovernorError(Exception):
    """Base exception for all Governor engine errors."""
    pass


class GovernorEvaluationError(GovernorError):
    """Raised when Governor decision evaluation encounters invalid or contradictory inputs."""
    pass


class GovernorPolicyError(GovernorError):
    """Raised when policy configuration is invalid or unresolvable."""
    pass
