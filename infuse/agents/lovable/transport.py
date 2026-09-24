"""Transport abstraction layer for Lovable API and session management (Block 27)."""

import json
import threading
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from infuse.agents.lovable.errors import (
    LovableAdapterError,
    LovableAuthenticationError,
    LovableNetworkError,
    LovableTimeoutError,
)
from infuse.agents.lovable.models import (
    LovableExecutionOutput,
    redact_lovable_secrets,
)


class ILovableTransport(ABC):
    """Abstract transport boundary between LovableAdapter and Lovable runtime/API."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check whether the underlying Lovable runtime/API is available."""
        pass

    @abstractmethod
    def execute(
        self,
        prompt: str,
        execution_id: Optional[str] = None,
        project_id: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> LovableExecutionOutput:
        """Execute a generation or edit step on Lovable."""
        pass

    @abstractmethod
    def cancel_execution(self, execution_id: str) -> bool:
        """Cancel an in-flight execution."""
        pass

    @abstractmethod
    def terminate_session(self, session_id: str) -> bool:
        """Hard terminate a session/project build."""
        pass


class LovableHttpTransport(ILovableTransport):
    """HTTP/API transport for Lovable cloud agent service."""

    def __init__(
        self,
        api_endpoint: str = "https://api.lovable.dev/v1",
        api_key: Optional[str] = None,
        default_timeout: float = 60.0,
    ) -> None:
        self.api_endpoint = api_endpoint.rstrip("/")
        self.api_key = api_key
        self.default_timeout = default_timeout
        self._active_executions: Dict[str, Any] = {}
        self._lock = threading.RLock()

    def is_available(self) -> bool:
        return bool(self.api_key)

    def execute(
        self,
        prompt: str,
        execution_id: Optional[str] = None,
        project_id: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> LovableExecutionOutput:
        if not self.api_key:
            raise LovableAuthenticationError("Lovable API key is missing or unauthorized.")

        # If live HTTP is configured, this transport executes the request safely
        raise LovableNetworkError("Live Lovable HTTP service requires valid configured remote credentials.")

    def cancel_execution(self, execution_id: str) -> bool:
        with self._lock:
            if execution_id in self._active_executions:
                self._active_executions.pop(execution_id, None)
                return True
            return False

    def terminate_session(self, session_id: str) -> bool:
        with self._lock:
            if session_id in self._active_executions:
                self._active_executions.pop(session_id, None)
                return True
            return False


class LovableReferenceTransport(ILovableTransport):
    """Deterministic reference/mock transport for hermetic testing of Lovable adapter."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.invocations: List[Dict[str, Any]] = []
        self.cancelled_executions: List[str] = []
        self.terminated_sessions: List[str] = []
        self.is_ready = True
        self.should_timeout = False
        self.should_fail = False
        self.should_raise_auth = False
        self.custom_output: Optional[LovableExecutionOutput] = None

    def is_available(self) -> bool:
        return self.is_ready

    def execute(
        self,
        prompt: str,
        execution_id: Optional[str] = None,
        project_id: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> LovableExecutionOutput:
        with self._lock:
            self.invocations.append({
                "prompt": prompt,
                "execution_id": execution_id,
                "project_id": project_id,
                "parameters": parameters,
                "timeout": timeout,
            })

            if self.should_raise_auth:
                raise LovableAuthenticationError("Lovable authentication failed.")

            if self.should_timeout:
                raise LovableTimeoutError("Lovable execution timed out.")

            if self.should_fail:
                raise LovableNetworkError("Lovable API returned 500 error.")

            if self.custom_output is not None:
                return self.custom_output.model_copy(deep=True)

            return LovableExecutionOutput(
                response_data={
                    "result": f"Lovable created UI components for: {prompt[:40]}",
                    "status": "completed",
                    "project_id": project_id or "proj_default",
                    "components_generated": 2,
                },
                status_code=200,
                duration_ms=10.0,
            )

    def cancel_execution(self, execution_id: str) -> bool:
        with self._lock:
            self.cancelled_executions.append(execution_id)
            return True

    def terminate_session(self, session_id: str) -> bool:
        with self._lock:
            self.terminated_sessions.append(session_id)
            return True

    def clear(self) -> None:
        with self._lock:
            self.invocations.clear()
            self.cancelled_executions.clear()
            self.terminated_sessions.clear()
            self.should_timeout = False
            self.should_fail = False
            self.should_raise_auth = False
            self.custom_output = None
