"""Manifest parser and validator for Block 31 third-party integrations."""

import os
import re
from typing import Any, Dict, List, Optional
import yaml
from pydantic import Field, ValidationError

from infuse.contracts.common import InfuseBaseModel
from infuse.integrations.contracts import (
    IntegrationCategory,
    IntegrationComponentInfo,
    VerificationStatus,
)


class ReuseManifest(InfuseBaseModel):
    """Canonical model for REUSE_MANIFEST.yaml."""
    schema_version: str = Field(default="1.0.1")
    generated_at: str = Field(default="")
    project: str = Field(default="INFUSE")
    maintainer: str = Field(default="")
    manifest_rules: List[str] = Field(default_factory=list)
    components: List[IntegrationComponentInfo] = Field(default_factory=list)


def load_manifest(path: Optional[str] = None) -> ReuseManifest:
    """Load and parse REUSE_MANIFEST.yaml from disk."""
    manifest_path = path or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "REUSE_MANIFEST.yaml",
    )
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"Reuse manifest not found at: {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        raw_data = yaml.safe_load(f)

    if not isinstance(raw_data, dict):
        raise ValueError("Invalid manifest format: Root must be a dictionary.")

    return ReuseManifest.model_validate(raw_data)


def validate_manifest(manifest: ReuseManifest) -> List[str]:
    """Validate manifest rules and return any violation warnings/errors."""
    errors: List[str] = []

    if not manifest.components:
        errors.append("Manifest contains no component entries.")

    disallowed_version_tokens = ["latest", "main", "master", "current", "head", "*", ">= "]

    for comp in manifest.components:
        # Check repository URL
        if not comp.repository or not comp.repository.startswith("https://github.com/"):
            errors.append(f"Component '{comp.name}' must have a valid GitHub repository URL.")

        # Check unpinned versions
        ver_lower = comp.version.strip().lower()
        if any(tok in ver_lower for tok in disallowed_version_tokens):
            errors.append(f"Component '{comp.name}' has unpinned version: '{comp.version}'")

        # Check commit SHA format (strict 40-character hex SHA required)
        if not comp.commit_sha or not re.match(r"^[0-9a-fA-F]{40}$", comp.commit_sha):
            errors.append(
                f"Component '{comp.name}' must have a valid 40-character commit_sha: '{comp.commit_sha}'"
            )

        # Disallow placeholder SHAs (e.g., containing repeating patterns like 1a2b3c4d5e6f or commit-)
        if comp.commit_sha in ("commit-4f9e2b1029c78d6b", "commit-8c3b7a1290e43df1", "commit-1a2b3c4d5e6f", "commit-7f8e9d0a1b2c"):
            errors.append(f"Component '{comp.name}' has placeholder commit_sha: '{comp.commit_sha}'")

        # Check valid integration category
        if comp.integration_type not in IntegrationCategory:
            errors.append(
                f"Component '{comp.name}' has invalid category: '{comp.integration_type}'"
            )

        # Check license
        if not comp.license or comp.license.strip() == "":
            errors.append(f"Component '{comp.name}' missing license declaration.")

        # Check verification source
        if not comp.verification_source or comp.verification_source.strip() == "":
            errors.append(f"Component '{comp.name}' missing verification_source.")

        # Check unverified status integration
        if comp.verification_status == VerificationStatus.UNVERIFIED:
            if comp.integration_type in (
                IntegrationCategory.DIRECT_DEPENDENCY,
                IntegrationCategory.ADAPTER_INTEGRATION,
            ):
                errors.append(
                    f"Component '{comp.name}' is UNVERIFIED but marked for active integration."
                )

    return errors


__all__ = [
    "ReuseManifest",
    "load_manifest",
    "validate_manifest",
]
