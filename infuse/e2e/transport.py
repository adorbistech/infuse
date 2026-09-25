from typing import Any, Dict, List, Optional
from starlette.testclient import TestClient

from infuse.e2e.environment import EndToEndIntegrationEnvironment
from infuse.sdk.errors import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ServerError,
    ValidationError,
)
from infuse.sdk.transport import ITransport, TransportResponse


class InProcessE2ETransport(ITransport):
    """Direct ASGI test transport connecting SDK to the INFUSE HTTP API."""

    def __init__(
        self,
        environment: Optional[EndToEndIntegrationEnvironment] = None,
        app: Optional[Any] = None,
    ) -> None:
        self.environment = environment or EndToEndIntegrationEnvironment()
        if app is None:
            from infuse.api.app import create_app
            self.app = create_app()
        else:
            self.app = app
        self.client = TestClient(self.app, base_url="http://testserver", raise_server_exceptions=False)
        self.invocations: List[Dict[str, Any]] = []

    def send_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> TransportResponse:
        method_upper = method.upper()
        self.invocations.append({
            "method": method_upper,
            "path": path,
            "params": params,
            "json_data": json_data,
            "headers": headers,
        })

        # Send via starlette TestClient
        response = self.client.request(
            method=method_upper,
            url=path,
            params=params,
            json=json_data,
            headers=headers,
        )

        try:
            resp_data = response.json()
        except Exception:
            resp_data = response.text

        status_code = response.status_code
        if status_code in (400, 422):
            msg = resp_data.get("message", "Validation error") if isinstance(resp_data, dict) else str(resp_data)
            raise ValidationError(message=msg, status_code=status_code, details=resp_data)
        elif status_code in (401, 403):
            msg = resp_data.get("message", "Unauthorized") if isinstance(resp_data, dict) else str(resp_data)
            raise AuthenticationError(message=msg, status_code=status_code, details=resp_data)
        elif status_code == 404:
            msg = resp_data.get("message", "Not found") if isinstance(resp_data, dict) else str(resp_data)
            raise NotFoundError(message=msg, status_code=404, details=resp_data)
        elif status_code == 409:
            msg = resp_data.get("message", "Conflict") if isinstance(resp_data, dict) else str(resp_data)
            raise ConflictError(message=msg, status_code=409, details=resp_data)
        elif status_code >= 500:
            msg = resp_data.get("message", "Server error") if isinstance(resp_data, dict) else str(resp_data)
            raise ServerError(message=msg, status_code=status_code, details=resp_data)

        return TransportResponse(
            status_code=status_code,
            data=resp_data,
            headers=dict(response.headers),
        )


__all__ = [
    "InProcessE2ETransport",
]
