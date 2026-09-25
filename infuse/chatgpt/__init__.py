"""INFUSE ChatGPT App Integration Package.

Provides OpenAPI 3.1.0 Action endpoints, curated tool catalogs, authentication
boundaries, multi-tenant isolation, and structured UI rendering for ChatGPT.
"""

from infuse.chatgpt.auth import AuthenticatedContext, ChatGptAuthService
from infuse.chatgpt.config import AuthMode, ChatGptAppConfig
from infuse.chatgpt.models import (
    ControlExecutionInput,
    ExecuteTaskInput,
    GetExecutionInput,
    GetPolicyInput,
    ListExecutionsInput,
    ToolCategory,
    ToolResponseEnvelope,
)
from infuse.chatgpt.router import create_chatgpt_router
from infuse.chatgpt.schema import generate_openapi_schema
from infuse.chatgpt.tools import ChatGptToolRegistry

__all__ = [
    "AuthMode",
    "AuthenticatedContext",
    "ChatGptAppConfig",
    "ChatGptAuthService",
    "ChatGptToolRegistry",
    "ControlExecutionInput",
    "ExecuteTaskInput",
    "GetExecutionInput",
    "GetPolicyInput",
    "ListExecutionsInput",
    "ToolCategory",
    "ToolResponseEnvelope",
    "create_chatgpt_router",
    "generate_openapi_schema",
]
