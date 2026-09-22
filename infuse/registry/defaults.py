"""Standard reference provider and model records for testing and default bootstrapping."""

from typing import List, Tuple

from infuse.registry.models import (
    ModelCapabilityDeclaration,
    ModelModality,
    ModelRecord,
    ProviderCapabilityDeclaration,
    ProviderRecord,
    RegistryLifecycleStatus,
)


def get_default_catalog_records() -> Tuple[List[ProviderRecord], List[ModelRecord]]:
    """Return standard catalog fixtures for reference providers and models."""
    providers = [
        ProviderRecord(
            provider_id="anthropic",
            name="Anthropic",
            description="Anthropic Claude model provider.",
            provider_type="cloud",
            capabilities=ProviderCapabilityDeclaration(
                supports_streaming=True,
                supports_tool_calling=True,
                supports_caching=True,
                supports_vision=True,
                supports_structured_output=True,
                supported_protocols=["http", "sse"]
            ),
            status=RegistryLifecycleStatus.ACTIVE
        ),
        ProviderRecord(
            provider_id="openai",
            name="OpenAI",
            description="OpenAI GPT & Reasoning model provider.",
            provider_type="cloud",
            capabilities=ProviderCapabilityDeclaration(
                supports_streaming=True,
                supports_tool_calling=True,
                supports_caching=True,
                supports_vision=True,
                supports_structured_output=True,
                supported_protocols=["http", "sse"]
            ),
            status=RegistryLifecycleStatus.ACTIVE
        ),
        ProviderRecord(
            provider_id="google",
            name="Google Gemini",
            description="Google Gemini multimodal model provider.",
            provider_type="cloud",
            capabilities=ProviderCapabilityDeclaration(
                supports_streaming=True,
                supports_tool_calling=True,
                supports_caching=True,
                supports_vision=True,
                supports_structured_output=True,
                supported_protocols=["http", "grpc"]
            ),
            status=RegistryLifecycleStatus.ACTIVE
        ),
        ProviderRecord(
            provider_id="deepseek",
            name="DeepSeek",
            description="DeepSeek AI models.",
            provider_type="cloud",
            capabilities=ProviderCapabilityDeclaration(
                supports_streaming=True,
                supports_tool_calling=True,
                supports_caching=False,
                supports_vision=False,
                supports_structured_output=True,
                supported_protocols=["http"]
            ),
            status=RegistryLifecycleStatus.ACTIVE
        ),
    ]

    models = [
        ModelRecord(
            model_id="claude-3-7-sonnet",
            provider_id="anthropic",
            name="Claude 3.7 Sonnet",
            family="claude-3",
            description="Hybrid reasoning and agentic coding flagship model.",
            context_window=200000,
            max_output_tokens=8192,
            capabilities=ModelCapabilityDeclaration(
                supports_tools=True,
                supports_vision=True,
                supports_structured_output=True,
                supports_streaming=True,
                supports_caching=True,
                supports_reasoning=True,
                modalities=[ModelModality.TEXT, ModelModality.VISION],
                declared_capabilities=["tools", "vision", "caching", "reasoning", "coding"]
            ),
            status=RegistryLifecycleStatus.ACTIVE
        ),
        ModelRecord(
            model_id="gpt-4o",
            provider_id="openai",
            name="GPT-4o",
            family="gpt-4",
            description="High-speed flagship omni-modal model.",
            context_window=128000,
            max_output_tokens=4096,
            capabilities=ModelCapabilityDeclaration(
                supports_tools=True,
                supports_vision=True,
                supports_structured_output=True,
                supports_streaming=True,
                supports_caching=True,
                supports_reasoning=False,
                modalities=[ModelModality.TEXT, ModelModality.VISION],
                declared_capabilities=["tools", "vision", "json", "streaming"]
            ),
            status=RegistryLifecycleStatus.ACTIVE
        ),
        ModelRecord(
            model_id="gemini-2.0-flash",
            provider_id="google",
            name="Gemini 2.0 Flash",
            family="gemini-2",
            description="Next-generation multimodal performance model.",
            context_window=1000000,
            max_output_tokens=8192,
            capabilities=ModelCapabilityDeclaration(
                supports_tools=True,
                supports_vision=True,
                supports_structured_output=True,
                supports_streaming=True,
                supports_caching=True,
                supports_reasoning=False,
                modalities=[ModelModality.TEXT, ModelModality.VISION, ModelModality.AUDIO],
                declared_capabilities=["tools", "vision", "audio", "long_context"]
            ),
            status=RegistryLifecycleStatus.ACTIVE
        ),
        ModelRecord(
            model_id="deepseek-v3",
            provider_id="deepseek",
            name="DeepSeek V3",
            family="deepseek",
            description="Efficient open-weights MoE model.",
            context_window=64000,
            max_output_tokens=4096,
            capabilities=ModelCapabilityDeclaration(
                supports_tools=True,
                supports_vision=False,
                supports_structured_output=True,
                supports_streaming=True,
                supports_caching=False,
                supports_reasoning=False,
                modalities=[ModelModality.TEXT],
                declared_capabilities=["tools", "coding", "json"]
            ),
            status=RegistryLifecycleStatus.ACTIVE
        ),
    ]

    return providers, models
