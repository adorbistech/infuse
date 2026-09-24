"""Domain exceptions for INFUSE Universal Agent Adapter Layer."""


class AgentAdapterError(Exception):
    """Base exception for all agent adapter operations."""
    pass


class AgentUnavailableError(AgentAdapterError):
    """Raised when an agent runtime is unreachable or not attached."""
    pass


class UnsupportedAgentOperationError(AgentAdapterError):
    """Raised when an operation is requested that the agent does not declare capability for."""
    pass


class AgentExecutionError(AgentAdapterError):
    """Raised when an agent execution step fails during execution."""
    pass


class AgentControlError(AgentAdapterError):
    """Raised when a control operation (cancel/throttle/switch/terminate) fails in the agent adapter."""
    pass
