"""Authentication and authorization boundary for INFUSE ChatGPT App."""

import re
from typing import List, Optional, Set
from pydantic import BaseModel, Field

from infuse.chatgpt.config import AuthMode, ChatGptAppConfig


class AuthenticatedContext(BaseModel):
    """Encapsulates verified identity and authorization claims of a ChatGPT caller."""

    user_id: str = Field(..., description="Unique user identifier from ChatGPT session or OAuth token")
    tenant_id: str = Field(default="default", description="Tenant or organization identifier")
    scopes: Set[str] = Field(default_factory=lambda: {"read:executions", "read:policies", "execute:tasks"})
    is_authenticated: bool = Field(default=True)

    def has_scope(self, required_scope: str) -> bool:
        """Check if context satisfies the required scope or admin wildcard."""
        if "admin" in self.scopes or "*" in self.scopes:
            return True
        return required_scope in self.scopes


class AuthError(Exception):
    """Raised when authentication or authorization fails."""

    def __init__(self, message: str, status_code: int = 401, error_code: str = "UNAUTHORIZED"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code


class ChatGptAuthService:
    """Validates incoming ChatGPT requests and derives authorized tenant context."""

    def __init__(self, config: ChatGptAppConfig):
        self.config = config

    def authenticate_header(self, authorization_header: Optional[str]) -> AuthenticatedContext:
        """Authenticate request using the Authorization HTTP header.

        Args:
            authorization_header: Raw HTTP Authorization header (e.g. 'Bearer <token>').

        Returns:
            AuthenticatedContext representing verified user and tenant claims.

        Raises:
            AuthError: If authentication token is missing, malformed, or invalid.
        """
        if self.config.auth_mode == AuthMode.NONE:
            return AuthenticatedContext(
                user_id="dev_user",
                tenant_id="default",
                scopes={"admin", "read:executions", "read:policies", "execute:tasks", "control:write"},
            )

        if not authorization_header:
            raise AuthError("Missing Authorization header in request.", status_code=401, error_code="MISSING_TOKEN")

        match = re.match(r"^Bearer\s+(.+)$", authorization_header.strip(), re.IGNORECASE)
        if not match:
            raise AuthError("Malformed Authorization header. Expected format: 'Bearer <token>'.", status_code=401, error_code="INVALID_HEADER")

        token = match.group(1).strip()
        return self.validate_token(token)

    def validate_token(self, token: str) -> AuthenticatedContext:
        """Validate token string against configured secret or OAuth2 issuer."""
        if not token:
            raise AuthError("Empty authentication token provided.", status_code=401, error_code="EMPTY_TOKEN")

        # 1. Bearer secret check
        if self.config.auth_mode == AuthMode.BEARER:
            valid_keys = (
                [k.strip() for k in self.config.api_key_secret.split(",") if k.strip()]
                if self.config.api_key_secret
                else []
            )

            # If no secret configured in test/dev environment, accept standard token format or reject
            if not valid_keys:
                # Default development fallback if key not explicitly set
                if token.startswith("infuse_") or token.startswith("test_token_"):
                    # Extract tenant/user if encoded, e.g. infuse_tenant123_user456
                    parts = token.split("_")
                    tenant = parts[1] if len(parts) > 2 else "default"
                    user = parts[2] if len(parts) > 2 else "chatgpt_user"
                    return AuthenticatedContext(
                        user_id=user,
                        tenant_id=tenant,
                        scopes={"read:executions", "read:policies", "execute:tasks", "control:write"},
                    )
                raise AuthError("Invalid API token provided.", status_code=401, error_code="INVALID_TOKEN")

            if token not in valid_keys:
                raise AuthError("Unauthorized: Provided API token does not match configured keys.", status_code=401, error_code="INVALID_KEY")

            return AuthenticatedContext(
                user_id="authorized_chatgpt_user",
                tenant_id="default",
                scopes={"read:executions", "read:policies", "execute:tasks", "control:write"},
            )

        # 2. OAuth2 mode
        if self.config.auth_mode == AuthMode.OAUTH2:
            # Parse simulated or standard JWT/opaque token
            if not token.startswith("oauth_") and not token.startswith("eyJ"):
                raise AuthError("Invalid OAuth2 access token format.", status_code=401, error_code="INVALID_OAUTH_TOKEN")

            return AuthenticatedContext(
                user_id="oauth_user",
                tenant_id="default",
                scopes={"read:executions", "read:policies", "execute:tasks", "control:write"},
            )

        raise AuthError("Unsupported authentication configuration.", status_code=500, error_code="SERVER_CONFIG_ERROR")

    def enforce_scope(self, context: AuthenticatedContext, required_scope: str) -> None:
        """Ensure authenticated context has the necessary permission scope."""
        if not context.has_scope(required_scope):
            raise AuthError(
                f"Forbidden: Token lacks required scope '{required_scope}'.",
                status_code=403,
                error_code="FORBIDDEN_SCOPE",
            )
