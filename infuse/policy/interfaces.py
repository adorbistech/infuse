"""Policy Manager interface definitions."""

from abc import ABC, abstractmethod
from typing import List, Optional

from infuse.contracts.policy import GovernancePolicy


class IPolicyManager(ABC):
    """Abstract interface for governance policy lifecycle management."""

    @abstractmethod
    def create_policy(self, policy: GovernancePolicy, activate: bool = False) -> GovernancePolicy:
        """Validate, normalize, version, and persist a new governance policy."""
        raise NotImplementedError

    @abstractmethod
    def get_policy(self, policy_id: str, version: Optional[str] = None) -> Optional[GovernancePolicy]:
        """Retrieve a policy revision by policy_id and optional version."""
        raise NotImplementedError

    @abstractmethod
    def get_active_policy(self) -> Optional[GovernancePolicy]:
        """Retrieve the currently active governance policy revision."""
        raise NotImplementedError

    @abstractmethod
    def update_policy(
        self,
        policy_id: str,
        policy: GovernancePolicy,
        bump_version: bool = True
    ) -> GovernancePolicy:
        """Validate, normalize, create a new revision, and persist the updated policy."""
        raise NotImplementedError

    @abstractmethod
    def activate_policy(self, policy_id: str, version: Optional[str] = None) -> GovernancePolicy:
        """Activate a specific policy revision and deactivate previous active policy."""
        raise NotImplementedError

    @abstractmethod
    def list_policies(self, include_historical: bool = False) -> List[GovernancePolicy]:
        """List all policy envelopes, optionally including historical revisions."""
        raise NotImplementedError

    @abstractmethod
    def get_policy_history(self, policy_id: str) -> List[GovernancePolicy]:
        """Retrieve the chronological immutable revision history for a policy."""
        raise NotImplementedError
