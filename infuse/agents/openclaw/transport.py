"""Transport abstraction layer for OpenClaw CLI and process management (Block 27)."""

import json
import os
import shutil
import subprocess
import threading
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from infuse.agents.openclaw.errors import (
    OpenClawCLINotFoundError,
    OpenClawProcessError,
    OpenClawTimeoutError,
)
from infuse.agents.openclaw.models import (
    OpenClawExecutionOutput,
    redact_openclaw_secrets,
)


class IOpenClawTransport(ABC):
    """Abstract transport boundary between OpenClawAdapter and OpenClaw runtime."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check whether the underlying OpenClaw runtime is available."""
        pass

    @abstractmethod
    def execute(
        self,
        args: List[str],
        execution_id: Optional[str] = None,
        cwd: Optional[str] = None,
        timeout: Optional[float] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> OpenClawExecutionOutput:
        """Execute an OpenClaw CLI command with arguments."""
        pass

    @abstractmethod
    def cancel_execution(self, execution_id: str) -> bool:
        """Cancel an in-flight execution process."""
        pass

    @abstractmethod
    def terminate_session(self, session_id: str) -> bool:
        """Hard terminate a session process."""
        pass


class OpenClawSubprocessTransport(IOpenClawTransport):
    """Subprocess-based transport communicating with local OpenClaw CLI."""

    def __init__(self, cli_path: Optional[str] = None, default_timeout: float = 60.0) -> None:
        self._cli_path = cli_path or self._discover_cli()
        self._default_timeout = default_timeout
        self._active_processes: Dict[str, subprocess.Popen] = {}
        self._lock = threading.RLock()

    def _discover_cli(self) -> Optional[str]:
        common_candidates = [
            os.path.expanduser("~/.local/bin/openclaw"),
            "/usr/local/bin/openclaw",
            "/opt/homebrew/bin/openclaw",
            "openclaw",
            "open-claw",
        ]
        for candidate in common_candidates:
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
            which_path = shutil.which(candidate)
            if which_path:
                return which_path
        return None

    def is_available(self) -> bool:
        cli = self._cli_path or self._discover_cli()
        return bool(cli and os.path.isfile(cli) and os.access(cli, os.X_OK))

    def execute(
        self,
        args: List[str],
        execution_id: Optional[str] = None,
        cwd: Optional[str] = None,
        timeout: Optional[float] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> OpenClawExecutionOutput:
        cli = self._cli_path or self._discover_cli()
        if not cli:
            raise OpenClawCLINotFoundError("OpenClaw executable ('openclaw') not found on system PATH.")

        cmd = [cli] + list(args)
        exec_timeout = timeout or self._default_timeout

        clean_env = os.environ.copy()
        if env:
            clean_env.update(env)

        start_time = time.perf_counter()
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
                env=clean_env,
                shell=False,
                text=True,
            )

            if execution_id:
                with self._lock:
                    self._active_processes[execution_id] = proc

            try:
                stdout, stderr = proc.communicate(timeout=exec_timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate()
                raise OpenClawTimeoutError(
                    f"OpenClaw process timed out after {exec_timeout} seconds for execution '{execution_id}'."
                )

            duration_ms = (time.perf_counter() - start_time) * 1000.0

            parsed_json = None
            if stdout:
                try:
                    parsed_json = json.loads(stdout.strip())
                except Exception:
                    pass

            if proc.returncode != 0:
                redacted_err = redact_openclaw_secrets(stderr)
                raise OpenClawProcessError(
                    f"OpenClaw process exited with return code {proc.returncode}: {redacted_err}"
                )

            return OpenClawExecutionOutput(
                stdout=stdout or "",
                stderr=stderr or "",
                return_code=proc.returncode,
                parsed_json=parsed_json,
                duration_ms=duration_ms,
            )
        finally:
            if execution_id:
                with self._lock:
                    self._active_processes.pop(execution_id, None)

    def cancel_execution(self, execution_id: str) -> bool:
        with self._lock:
            proc = self._active_processes.get(execution_id)
            if proc and proc.poll() is None:
                proc.terminate()
                return True
            return False

    def terminate_session(self, session_id: str) -> bool:
        with self._lock:
            proc = self._active_processes.get(session_id)
            if proc and proc.poll() is None:
                proc.kill()
                return True
            return False


class OpenClawReferenceTransport(IOpenClawTransport):
    """Deterministic reference/mock transport for hermetic testing of OpenClaw adapter."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.invocations: List[Dict[str, Any]] = []
        self.cancelled_executions: List[str] = []
        self.terminated_sessions: List[str] = []
        self.is_ready = True
        self.should_timeout = False
        self.should_fail = False
        self.should_raise_not_found = False
        self.custom_output: Optional[OpenClawExecutionOutput] = None

    def is_available(self) -> bool:
        return self.is_ready

    def execute(
        self,
        args: List[str],
        execution_id: Optional[str] = None,
        cwd: Optional[str] = None,
        timeout: Optional[float] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> OpenClawExecutionOutput:
        with self._lock:
            self.invocations.append({
                "args": list(args),
                "execution_id": execution_id,
                "cwd": cwd,
                "timeout": timeout,
                "env": env,
            })

            if self.should_raise_not_found:
                raise OpenClawCLINotFoundError("OpenClaw executable not found.")

            if self.should_timeout:
                raise OpenClawTimeoutError("OpenClaw reference execution timed out.")

            if self.should_fail:
                raise OpenClawProcessError("OpenClaw reference process exited with error.")

            if self.custom_output is not None:
                return self.custom_output.model_copy(deep=True)

            prompt_str = " ".join(args)
            return OpenClawExecutionOutput(
                stdout=f"OpenClaw execution completed for: {prompt_str[:40]}",
                stderr="",
                return_code=0,
                parsed_json={
                    "result": f"OpenClaw execution completed for: {prompt_str[:40]}",
                    "status": "completed",
                },
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
            self.should_raise_not_found = False
            self.custom_output = None
