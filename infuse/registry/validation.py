"""Validation logic for Provider and Model Registry records."""

import re
from typing import Any, Dict, List

from infuse.registry.errors import RegistryValidationError, SecretDetectedError
from infuse.registry.models import ModelRecord, ProviderRecord
from infuse.version import SCHEMA_VERSION

_FORBIDDEN_SECRET_KEYS = {
    "api_key", "apikey", "secret", "secret_key", "password", "token",
    "access_token", "auth_token", "private_key", "bearer_token", "credentials"
}

_SECRET_PATTERN = re.compile(r"^(sk-[a-zA-Z0-9_\-]{10,}|ghp_[a-zA-Z0-9]{10,}|Bearer\s+[a-zA-Z0-9_\-\.]+)")


def _check_secrets(data: Any, path: str = "") -> None:
    """Recursively inspect dictionaries and lists for credentials or secret patterns."""
    if isinstance(data, dict):
        for k, v in data.items():
            k_lower = str(k).lower().strip()
            current_path = f"{path}.{k}" if path else str(k)
            if k_lower in _FORBIDDEN_SECRET_KEYS:
                raise SecretDetectedError(
                    f"Forbidden credential key '{k}' detected at '{current_path}'. Registry must not contain secrets."
                )
            _check_secrets(v, current_path)
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            _check_secrets(item, f"{path}[{idx}]")
    elif isinstance(data, str):
        if _SECRET_PATTERN.search(data.strip()):
            raise SecretDetectedError(
                f"Secret pattern detected at '{path}'. Registry records must not contain credentials or tokens."
            )


def validate_provider_record(provider: ProviderRecord) -> None:
    """Validate structural constraints and security invariants of a ProviderRecord."""
    violations: List[str] = []

    # 1. Secret / Credential Inspection
    _check_secrets(provider.model_dump())

    # 2. Structural identity checks
    if not provider.provider_id or not provider.provider_id.strip():
        violations.append("provider.provider_id must be a non-empty string.")

    if not provider.name or not provider.name.strip():
        violations.append("provider.name must be a non-empty string.")

    if not provider.version or not provider.version.strip():
        violations.append("provider.version must be a non-empty string.")

    if provider.schema_version != SCHEMA_VERSION:
        violations.append(
            f"provider.schema_version must be '{SCHEMA_VERSION}', got '{provider.schema_version}'."
        )

    if violations:
        raise RegistryValidationError(
            f"ProviderRecord validation failed with {len(violations)} violation(s).",
            violations=violations
        )


def validate_model_record(model: ModelRecord) -> None:
    """Validate structural constraints and security invariants of a ModelRecord."""
    violations: List[str] = []

    # 1. Secret / Credential Inspection
    _check_secrets(model.model_dump())

    # 2. Structural identity checks
    if not model.model_id or not model.model_id.strip():
        violations.append("model.model_id must be a non-empty string.")

    if not model.provider_id or not model.provider_id.strip():
        violations.append("model.provider_id must be a non-empty string.")

    if not model.name or not model.name.strip():
        violations.append("model.name must be a non-empty string.")

    if model.context_window <= 0:
        violations.append(f"model.context_window must be > 0, got {model.context_window}.")

    if model.max_output_tokens <= 0:
        violations.append(f"model.max_output_tokens must be > 0, got {model.max_output_tokens}.")

    if model.schema_version != SCHEMA_VERSION:
        violations.append(
            f"model.schema_version must be '{SCHEMA_VERSION}', got '{model.schema_version}'."
        )

    if violations:
        raise RegistryValidationError(
            f"ModelRecord validation failed with {len(violations)} violation(s).",
            violations=violations
        )
