"""API Error taxonomy and exception classes."""

from enum import Enum
from typing import Any, Dict, Optional
from starlette.responses import JSONResponse

from infuse.api.schemas.errors import ApiErrorResponse
from infuse.version import SCHEMA_VERSION


class ErrorCode(str, Enum):
    """Canonical error codes for the Universal HTTP API."""
    BAD_REQUEST = "BAD_REQUEST"
    MALFORMED_JSON = "MALFORMED_JSON"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ApiError(Exception):
    """Base API exception class."""
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details

    def to_response(self, correlation_id: Optional[str] = None) -> JSONResponse:
        error_dto = ApiErrorResponse(
            code=self.code.value if isinstance(self.code, Enum) else str(self.code),
            message=self.message,
            details=self.details,
            correlation_id=correlation_id,
            schema_version=SCHEMA_VERSION
        )
        return JSONResponse(
            content=error_dto.model_dump(),
            status_code=self.status_code
        )


class BadRequestError(ApiError):
    """400 Bad Request error."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=message,
            code=ErrorCode.BAD_REQUEST,
            status_code=400,
            details=details
        )


class MalformedJsonError(ApiError):
    """400 Malformed JSON error."""
    def __init__(self, message: str = "Request body must be valid JSON.", details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=message,
            code=ErrorCode.MALFORMED_JSON,
            status_code=400,
            details=details
        )


class RequestValidationError(ApiError):
    """422 Validation error for schema mismatches."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=message,
            code=ErrorCode.VALIDATION_ERROR,
            status_code=422,
            details=details
        )


class NotFoundError(ApiError):
    """404 Resource not found error."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=message,
            code=ErrorCode.NOT_FOUND,
            status_code=404,
            details=details
        )


class ConflictError(ApiError):
    """409 Conflict error."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=message,
            code=ErrorCode.CONFLICT,
            status_code=409,
            details=details
        )
