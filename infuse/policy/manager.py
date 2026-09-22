"""Policy Manager implementation.

Authority for governance policy lifecycle, validation, normalization, versioning,
active policy resolution, and revision history.
"""

from typing import List, Optional
import re

from infuse.api.repositories.interfaces import IPolicyRepository
from infuse.api.repositories.memory import InMemoryPolicyRepository
from infuse.contracts.policy import GovernancePolicy
from infuse.policy.errors import (
    PolicyConflictError,
    PolicyNotFoundError,
    PolicyValidationError,
)
from infuse.policy.interfaces import IPolicyManager
from infuse.policy.normalization import normalize_policy
from infuse.policy.validation import validate_policy


def _bump_version(version: str) -> str:
    """Deterministically increment a version string (semver or integer)."""
    v = (version or "1.0.0").strip()
    parts = v.split(".")
    
    if len(parts) == 3 and all(p.isdigit() for p in parts):
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
        return f"{major}.{minor}.{patch + 1}"
    elif len(parts) == 2 and all(p.isdigit() for p in parts):
        major, minor = int(parts[0]), int(parts[1])
        return f"{major}.{minor + 1}"
    elif len(parts) == 1 and parts[0].isdigit():
        return str(int(parts[0]) + 1)
    
    # Fallback for arbitrary revision string
    match = re.search(r"(\d+)$", v)
    if match:
        num = int(match.group(1))
        prefix = v[:match.start(1)]
        return f"{prefix}{num + 1}"
    return f"{v}.1"


class PolicyManager(IPolicyManager):
    """Lifecycle authority for INFUSE governance policies."""

    def __init__(self, repository: Optional[IPolicyRepository] = None) -> None:
        self._repository = repository or InMemoryPolicyRepository()

    def create_policy(self, policy: GovernancePolicy, activate: bool = False) -> GovernancePolicy:
        """Validate, normalize, version, and persist a new governance policy."""
        # 1. Structural and logical validation
        validate_policy(policy)

        # 2. Deterministic normalization
        norm_policy = normalize_policy(policy)

        # 3. Check collision
        existing = self._repository.get_by_id(norm_policy.policy_id)
        if existing is not None:
            raise PolicyConflictError(
                f"Policy with ID '{norm_policy.policy_id}' already exists. Use update_policy() to create a new revision."
            )

        if activate:
            norm_policy.is_active = True

        # 4. Save into repository
        return self._repository.save(norm_policy)

    def get_policy(self, policy_id: str, version: Optional[str] = None) -> Optional[GovernancePolicy]:
        """Retrieve a policy revision by ID and optional version."""
        if version:
            return self._repository.get_revision(policy_id, version)
        return self._repository.get_by_id(policy_id)

    def get_active_policy(self) -> Optional[GovernancePolicy]:
        """Retrieve the currently active governance policy revision."""
        return self._repository.get_active()

    def update_policy(
        self,
        policy_id: str,
        policy: GovernancePolicy,
        bump_version: bool = True
    ) -> GovernancePolicy:
        """Validate, normalize, create a new revision, and persist the updated policy."""
        existing = self._repository.get_by_id(policy_id)
        if existing is None:
            raise PolicyNotFoundError(f"Cannot update non-existent policy '{policy_id}'.")

        # Ensure ID consistency
        if policy.policy_id != policy_id:
            policy = policy.model_copy(update={"policy_id": policy_id})

        # Version incrementation
        existing_history = self._repository.get_history(policy_id)
        existing_versions = {h.version for h in existing_history}

        if bump_version or policy.version in existing_versions or policy.version == "1.0.0":
            if policy.version in existing_versions or policy.version == existing.version or policy.version == "1.0.0":
                new_ver = _bump_version(existing.version)
                policy = policy.model_copy(update={"version": new_ver})

        # 1. Validation
        validate_policy(policy)

        # 2. Normalization
        norm_policy = normalize_policy(policy)

        # 3. Save new revision (repository maintains historical snapshots)
        return self._repository.save(norm_policy)

    def activate_policy(self, policy_id: str, version: Optional[str] = None) -> GovernancePolicy:
        """Activate a specific policy revision and deactivate previous active policy."""
        try:
            return self._repository.set_active(policy_id, version)
        except KeyError as exc:
            raise PolicyNotFoundError(str(exc)) from exc

    def list_policies(self, include_historical: bool = False) -> List[GovernancePolicy]:
        """List all policy envelopes, optionally including historical revisions."""
        return self._repository.list_all(include_historical=include_historical)

    def get_policy_history(self, policy_id: str) -> List[GovernancePolicy]:
        """Retrieve the chronological immutable revision history for a policy."""
        history = self._repository.get_history(policy_id)
        if not history:
            raise PolicyNotFoundError(f"Policy '{policy_id}' has no revision history or does not exist.")
        return history
