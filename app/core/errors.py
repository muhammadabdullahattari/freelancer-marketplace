from pydantic import BaseModel
from enum import Enum
from datetime import datetime, timezone
from typing import Optional, Any
import logging

logger = logging.getLogger(__name__)


class ErrorCode(str, Enum):
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    INVALID_TOKEN = "INVALID_TOKEN"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    CONFLICT = "CONFLICT"
    
    DUPLICATE_PROPOSAL = "DUPLICATE_PROPOSAL"
    JOB_NOT_OPEN = "JOB_NOT_OPEN"
    PROPOSAL_NOT_SUBMITTED = "PROPOSAL_NOT_SUBMITTED"
    INVALID_STATE_TRANSITION = "INVALID_STATE_TRANSITION"
    UNAUTHORIZED_ACTION = "UNAUTHORIZED_ACTION"
    INVALID_OPERATION = "INVALID_OPERATION"
    
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

class ErrorDetails(BaseModel):
    code: str
    message: str
    status: int
    timestamp: str
    request_id: Optional[str] = None
    details: Optional[dict[str, Any]] = None


class ErrorResponse(BaseModel):
    error: ErrorDetails

class APIException(Exception):
    
    def __init__(self, code: ErrorCode, message: str, status_code: int, details: Optional[dict] = None, request_id: Optional[str] = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        self.request_id = request_id
        
        logger.error(
            f"[{request_id}] {code.value}: {message}",
            extra={"status_code": status_code, "details": details}
        )
        
        super().__init__(self.message)
    
    def to_dict(self) -> dict:
        return {
            "error": {
                "code": self.code.value,
                "message": self.message,
                "status": self.status_code,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": self.request_id,
                "details": self.details
            }
        }


class ValidationException(APIException):
    def __init__(self, message: str, details: Optional[dict] = None, request_id: Optional[str] = None):
        super().__init__(
            ErrorCode.VALIDATION_ERROR,
            message,
            400,
            details,
            request_id
        )


class AuthenticationException(APIException):
    def __init__(self, message: str = "Invalid credentials", request_id: Optional[str] = None):
        super().__init__(
            ErrorCode.INVALID_CREDENTIALS,
            message,
            401,
            request_id=request_id
        )


class AuthorizationException(APIException):
    def __init__(self, message: str = "Not authorized to perform this action", request_id: Optional[str] = None):
        super().__init__(
            ErrorCode.FORBIDDEN,
            message,
            403,
            request_id=request_id
        )


class ResourceNotFoundException(APIException):
    def __init__(self, resource: str, request_id: Optional[str] = None):
        super().__init__(
            ErrorCode.NOT_FOUND,
            f"{resource} not found",
            404,
            request_id=request_id
        )


class ConflictException(APIException):
    def __init__(self, message: str, details: Optional[dict] = None, request_id: Optional[str] = None):
        super().__init__(
            ErrorCode.CONFLICT,
            message,
            409,
            details,
            request_id
        )


class BusinessLogicException(APIException):
    def __init__(self, code: ErrorCode, message: str, details: Optional[dict] = None, request_id: Optional[str] = None):
        super().__init__(
            code,
            message,
            400,
            details,
            request_id
        )
        
class RateLimitException(APIException):
    def __init__(self, message: str = "Too many requests", request_id: Optional[str] = None):
        super().__init__(
            ErrorCode.RATE_LIMIT_EXCEEDED,
            message,
            429,
            request_id=request_id
        )