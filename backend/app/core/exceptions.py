"""
Centralized exception handling for the Stock Analysis API
"""
from enum import Enum
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import logging
import uuid

logger = logging.getLogger(__name__)


class ErrorCategory(str, Enum):
    """Error categories for classification"""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NOT_FOUND = "not_found"
    EXTERNAL_API = "external_api"
    DATABASE = "database"
    CACHE = "cache"
    INTERNAL = "internal"
    BUSINESS_LOGIC = "business_logic"


class AppException(Exception):
    """Base application exception with structured error information"""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ):
        self.message = message
        self.category = category
        self.status_code = status_code
        self.details = details or {}
        self.correlation_id = correlation_id or str(uuid.uuid4())
        super().__init__(message)


class ValidationError(AppException):
    """Validation error with field-specific information"""
    
    def __init__(self, message: str, field: str, value: Any, correlation_id: Optional[str] = None):
        super().__init__(
            message=message,
            category=ErrorCategory.VALIDATION,
            status_code=400,
            details={"field": field, "value": str(value)},
            correlation_id=correlation_id
        )


class ExternalAPIError(AppException):
    """External API error with service information"""
    
    def __init__(self, message: str, service: str, status_code: int = 502, correlation_id: Optional[str] = None):
        super().__init__(
            message=message,
            category=ErrorCategory.EXTERNAL_API,
            status_code=status_code,
            details={"service": service},
            correlation_id=correlation_id
        )


class DatabaseError(AppException):
    """Database operation error"""
    
    def __init__(self, message: str, operation: str, correlation_id: Optional[str] = None):
        super().__init__(
            message=message,
            category=ErrorCategory.DATABASE,
            status_code=500,
            details={"operation": operation},
            correlation_id=correlation_id
        )


class BusinessLogicError(AppException):
    """Business logic validation error"""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None, correlation_id: Optional[str] = None):
        super().__init__(
            message=message,
            category=ErrorCategory.BUSINESS_LOGIC,
            status_code=422,
            details=context or {},
            correlation_id=correlation_id
        )


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Global exception handler for AppException and its subclasses"""
    correlation_id = exc.correlation_id or request.headers.get("x-correlation-id", str(uuid.uuid4()))
    
    # Log error with structured context
    logger.error(
        "Application error occurred",
        extra={
            "correlation_id": correlation_id,
            "error_category": exc.category.value,
            "error_message": exc.message,
            "status_code": exc.status_code,
            "request_path": str(request.url.path),
            "request_method": request.method,
            "details": exc.details,
            "user_agent": request.headers.get("user-agent"),
            "client_ip": request.client.host if request.client else None
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.message,
                "category": exc.category.value,
                "correlation_id": correlation_id,
                "details": exc.details
            }
        },
        headers={"x-correlation-id": correlation_id}
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handler for FastAPI HTTPException"""
    correlation_id = request.headers.get("x-correlation-id", str(uuid.uuid4()))
    
    logger.warning(
        "HTTP exception occurred",
        extra={
            "correlation_id": correlation_id,
            "status_code": exc.status_code,
            "detail": exc.detail,
            "request_path": str(request.url.path),
            "request_method": request.method
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.detail,
                "category": "http_error",
                "correlation_id": correlation_id,
                "details": {}
            }
        },
        headers={"x-correlation-id": correlation_id}
    )


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handler for Pydantic validation errors"""
    correlation_id = request.headers.get("x-correlation-id", str(uuid.uuid4()))
    
    # Extract validation error details
    details = {}
    if hasattr(exc, 'errors'):
        details = {"validation_errors": exc.errors()}
    
    logger.warning(
        "Validation error occurred",
        extra={
            "correlation_id": correlation_id,
            "request_path": str(request.url.path),
            "request_method": request.method,
            "validation_details": details
        }
    )
    
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "message": "Validation failed",
                "category": "validation",
                "correlation_id": correlation_id,
                "details": details
            }
        },
        headers={"x-correlation-id": correlation_id}
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handler for unhandled exceptions"""
    correlation_id = request.headers.get("x-correlation-id", str(uuid.uuid4()))
    
    logger.error(
        "Unhandled exception occurred",
        extra={
            "correlation_id": correlation_id,
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "request_path": str(request.url.path),
            "request_method": request.method
        },
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": "Internal server error",
                "category": "internal",
                "correlation_id": correlation_id,
                "details": {}
            }
        },
        headers={"x-correlation-id": correlation_id}
    )