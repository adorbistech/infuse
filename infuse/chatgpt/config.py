"""Configuration models for INFUSE ChatGPT App Integration."""

import os
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class AuthMode(str, Enum):
    """Supported authentication modes for ChatGPT App."""
    BEARER = "bearer"
    OAUTH2 = "oauth2"
    NONE = "none"  # Used only in explicit local dev / test mock mode


class ChatGptAppConfig(BaseModel):
    """Configuration settings for the INFUSE ChatGPT App integration."""

    enabled: bool = Field(default=True, description="Enables the ChatGPT App router and tools")
    auth_mode: AuthMode = Field(default=AuthMode.BEARER, description="Authentication mechanism")
    api_key_secret: Optional[str] = Field(
        default=None,
        description="Master shared secret or comma-separated valid API tokens for Bearer auth"
    )
    oauth2_issuer: Optional[str] = Field(
        default=None,
        description="OAuth2 authorization issuer URL for token validation"
    )
    oauth2_audience: Optional[str] = Field(
        default="infuse-chatgpt-app",
        description="Expected OAuth2 audience claim"
    )
    allowed_tenants: List[str] = Field(
        default_factory=list,
        description="Optional list of permitted tenant IDs. If empty, all valid authenticated tenants are allowed"
    )
    max_execution_limit: int = Field(
        default=100,
        description="Max execution records returned to ChatGPT in a single query"
    )
    public_url: str = Field(
        default="https://api.infuse.adorbistech.com",
        description="Canonical public URL where the ChatGPT App action endpoints are hosted"
    )

    @classmethod
    def from_env(cls) -> "ChatGptAppConfig":
        """Load configuration from environment variables."""
        enabled_val = os.getenv("INFUSE_CHATGPT_ENABLED", "true").lower() in ("true", "1", "yes")
        auth_mode_val = os.getenv("INFUSE_CHATGPT_AUTH_MODE", "bearer").lower()
        try:
            auth_mode = AuthMode(auth_mode_val)
        except ValueError:
            auth_mode = AuthMode.BEARER

        raw_tenants = os.getenv("INFUSE_CHATGPT_ALLOWED_TENANTS", "")
        tenants = [t.strip() for t in raw_tenants.split(",") if t.strip()]

        return cls(
            enabled=enabled_val,
            auth_mode=auth_mode,
            api_key_secret=os.getenv("INFUSE_CHATGPT_API_KEY", None),
            oauth2_issuer=os.getenv("INFUSE_CHATGPT_OAUTH2_ISSUER", None),
            oauth2_audience=os.getenv("INFUSE_CHATGPT_OAUTH2_AUDIENCE", "infuse-chatgpt-app"),
            allowed_tenants=tenants,
            max_execution_limit=int(os.getenv("INFUSE_CHATGPT_MAX_LIMIT", "100")),
            public_url=os.getenv("INFUSE_PUBLIC_URL", "https://api.infuse.adorbistech.com").rstrip("/"),
        )
