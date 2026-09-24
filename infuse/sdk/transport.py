"""Transport abstraction layer for the INFUSE SDK (Block 28).

Decouples the SDK client surface from the underlying HTTP transport,
allowing seamless use of standard HTTP, ASGI in-memory apps, or deterministic
reference test transports.
"""

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from infuse.sdk.config import ClientConfig
from infuse.sdk.errors import (
    AuthenticationError,
    ConflictError,
    InfuseSdkError,
    MalformedResponseError,
    NotFoundError,
    ServerError,
    TimeoutError,
    TransportError,
    ValidationError,
    redact_sdk_secrets,
)


class TransportResponse:
    """Normalized response envelope returned by ITransport."""

    def __init__(self, status_code: int, data: Any, headers: Optional[Dict[str, str]] = None) -> None:
        self.status_code = status_code
        self.data = data
        self.headers = headers or {}


class ITransport(ABC):
    """Abstract transport boundary for INFUSE API communication."""

    @abstractmethod
    def send_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> TransportResponse:
        """Send a synchronous request to the INFUSE backend API."""
        pass


class HttpTransport(ITransport):
    """Standard HTTP transport using Python's standard library urllib.request."""

    def __init__(self, config: Optional[ClientConfig] = None) -> None:
        self.config = config or ClientConfig()
        self.base_url = self.config.base_url.rstrip("/")

    def send_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> TransportResponse:
        clean_path = path if path.startswith("/") else f"/{path}"
        url = f"{self.base_url}{clean_path}"

        if params:
            # Filter None query values
            filtered_params = {k: v for k, v in params.items() if v is not None}
            if filtered_params:
                query_str = urllib.parse.urlencode(filtered_params)
                url = f"{url}?{query_str}"

        req_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.config.api_key:
            req_headers["Authorization"] = f"Bearer {self.config.api_key}"
        req_headers.update(self.config.custom_headers)
        if headers:
            req_headers.update(headers)

        body_bytes: Optional[bytes] = None
        if json_data is not None:
            body_bytes = json.dumps(json_data).encode("utf-8")

        req = urllib.request.Request(
            url=url,
            data=body_bytes,
            headers=req_headers,
            method=method.upper(),
        )

        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout_seconds) as response:
                status_code = response.getcode()
                raw_bytes = response.read()
                resp_headers = dict(response.headers.items())
                
                if not raw_bytes:
                    return TransportResponse(status_code=status_code, data=None, headers=resp_headers)

                try:
                    parsed_json = json.loads(raw_bytes.decode("utf-8"))
                except Exception as exc:
                    raise MalformedResponseError(
                        message=f"Failed to parse server response as JSON: {exc}",
                        status_code=status_code,
                    ) from exc

                return TransportResponse(status_code=status_code, data=parsed_json, headers=resp_headers)

        except urllib.error.HTTPError as exc:
            status_code = exc.code
            raw_err = exc.read().decode("utf-8", errors="replace")
            err_data: Dict[str, Any] = {}
            err_msg = f"HTTP {status_code} error from server"
            
            try:
                err_data = json.loads(raw_err)
                if isinstance(err_data, dict):
                    err_msg = err_data.get("message") or err_msg
            except Exception:
                err_msg = raw_err or err_msg

            if status_code == 400:
                raise ValidationError(message=err_msg, status_code=400, details=err_data)
            elif status_code == 401 or status_code == 403:
                raise AuthenticationError(message=err_msg, status_code=status_code, details=err_data)
            elif status_code == 404:
                raise NotFoundError(message=err_msg, status_code=404, details=err_data)
            elif status_code == 409:
                raise ConflictError(message=err_msg, status_code=409, details=err_data)
            elif status_code == 422:
                raise ValidationError(message=err_msg, status_code=422, details=err_data)
            elif status_code == 504:
                raise TimeoutError(message=err_msg, status_code=504, details=err_data)
            elif status_code >= 500:
                raise ServerError(message=err_msg, status_code=status_code, details=err_data)
            else:
                raise TransportError(message=err_msg, status_code=status_code, details=err_data)

        except urllib.error.URLError as exc:
            reason_str = str(exc.reason)
            if "timed out" in reason_str.lower():
                raise TimeoutError(message=f"Request to {url} timed out: {reason_str}") from exc
            raise TransportError(message=f"Connection failure to {url}: {reason_str}") from exc

        except TimeoutError:
            raise
        except InfuseSdkError:
            raise
        except Exception as exc:
            raise TransportError(message=f"Unexpected transport failure: {exc}") from exc


class ReferenceTransport(ITransport):
    """Deterministic in-memory reference transport for unit and integration testing."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.invocations: List[Dict[str, Any]] = []
        self._mock_routes: Dict[Tuple[str, str], TransportResponse] = {}
        self.should_raise: Optional[Exception] = None

    def register_route(
        self,
        method: str,
        path: str,
        status_code: int = 200,
        data: Any = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """Register a canned response for a specific method and path."""
        with self._lock:
            key = (method.upper(), path.rstrip("/"))
            self._mock_routes[key] = TransportResponse(status_code=status_code, data=data, headers=headers)

    def send_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> TransportResponse:
        with self._lock:
            clean_path = path.rstrip("/")
            self.invocations.append({
                "method": method.upper(),
                "path": clean_path,
                "params": params or {},
                "json_data": json_data,
                "headers": headers or {},
            })

            if self.should_raise is not None:
                raise self.should_raise

            key = (method.upper(), clean_path)
            if key in self._mock_routes:
                resp = self._mock_routes[key]
                if resp.status_code == 400 or resp.status_code == 422:
                    msg = (resp.data.get("message") if isinstance(resp.data, dict) else str(resp.data)) or "Validation error"
                    raise ValidationError(message=msg, status_code=resp.status_code, details=resp.data)
                elif resp.status_code == 401 or resp.status_code == 403:
                    msg = (resp.data.get("message") if isinstance(resp.data, dict) else str(resp.data)) or "Unauthorized"
                    raise AuthenticationError(message=msg, status_code=resp.status_code, details=resp.data)
                elif resp.status_code == 404:
                    msg = (resp.data.get("message") if isinstance(resp.data, dict) else str(resp.data)) or "Not found"
                    raise NotFoundError(message=msg, status_code=404, details=resp.data)
                elif resp.status_code == 409:
                    msg = (resp.data.get("message") if isinstance(resp.data, dict) else str(resp.data)) or "Conflict"
                    raise ConflictError(message=msg, status_code=409, details=resp.data)
                elif resp.status_code >= 500:
                    msg = (resp.data.get("message") if isinstance(resp.data, dict) else str(resp.data)) or "Server error"
                    raise ServerError(message=msg, status_code=resp.status_code, details=resp.data)
                return resp

            # Default fallback 404
            raise NotFoundError(message=f"No route registered for {method.upper()} {clean_path}", status_code=404)

    def clear(self) -> None:
        """Clear recorded invocations and mock routes."""
        with self._lock:
            self.invocations.clear()
            self._mock_routes.clear()
            self.should_raise = None


__all__ = [
    "ITransport",
    "TransportResponse",
    "HttpTransport",
    "ReferenceTransport",
]
