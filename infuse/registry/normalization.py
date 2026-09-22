"""Deterministic normalization for Provider and Model Registry records."""

from typing import List, Optional

from infuse.registry.models import ModelRecord, ProviderRecord
from infuse.version import SCHEMA_VERSION


def _clean_str(val: Optional[str]) -> Optional[str]:
    if val is None:
        return None
    trimmed = val.strip()
    return trimmed if trimmed else None


def _clean_list(items: List[str], lowercase: bool = False) -> List[str]:
    seen = set()
    result = []
    for item in items:
        if not item or not item.strip():
            continue
        cleaned = item.strip().lower() if lowercase else item.strip()
        if cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result


def normalize_provider_record(provider: ProviderRecord) -> ProviderRecord:
    """Deterministically normalize ProviderRecord strings and lists."""
    prov_id = provider.provider_id.strip()
    name = provider.name.strip()
    desc = _clean_str(provider.description)
    ptype = provider.provider_type.strip().lower()
    endpoint = _clean_str(provider.endpoint_reference)
    version = provider.version.strip() if provider.version else "1.0.0"

    norm_caps = provider.capabilities.model_copy(
        update={
            "supported_protocols": _clean_list(provider.capabilities.supported_protocols, lowercase=True)
        }
    )

    return provider.model_copy(
        update={
            "provider_id": prov_id,
            "name": name,
            "description": desc,
            "provider_type": ptype,
            "endpoint_reference": endpoint,
            "version": version,
            "capabilities": norm_caps,
            "schema_version": SCHEMA_VERSION
        }
    )


def normalize_model_record(model: ModelRecord) -> ModelRecord:
    """Deterministically normalize ModelRecord strings and lists."""
    model_id = model.model_id.strip()
    provider_id = model.provider_id.strip()
    name = model.name.strip()
    family = _clean_str(model.family)
    desc = _clean_str(model.description)
    version = model.version.strip() if model.version else "1.0.0"

    norm_caps = model.capabilities.model_copy(
        update={
            "declared_capabilities": _clean_list(model.capabilities.declared_capabilities, lowercase=True)
        }
    )

    return model.model_copy(
        update={
            "model_id": model_id,
            "provider_id": provider_id,
            "name": name,
            "family": family,
            "description": desc,
            "version": version,
            "capabilities": norm_caps,
            "schema_version": SCHEMA_VERSION
        }
    )
