"""FastAPI exception handlers for consistent error responses.

This module provides centralized error handling for the application,
ensuring all errors return a consistent JSON format with proper HTTP
status codes and correlation IDs for request tracing.
"""

import logging
from typing import Union
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, OperationalError, TimeoutError as SQLTimeoutError
from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import (
    AppException,
    DatabaseError,
    DatabaseConnectionError,
    DatabaseTimeoutError,
    ForeignKeyViolationError,
    UniqueConstraintViolationError,
    CheckConstraintViolationError,
    NotNullViolationError,
)

logger = logging.getLogger(__name__)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle custom application exceptions.
    
    Args:
        request: FastAPI request object
        exc: Application exception instance
        
    Returns:
        JSON response with error details
    """
    logger.error(
        f"Application error: {exc.error_code}",
        extra={
            "correlation_id": exc.correlation_id,
            "error_code": exc.error_code,
            "error_message": exc.message,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method,
        },
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors.
    
    Converts Pydantic validation errors to a standardized format
    consistent with other application errors.
    
    Args:
        request: FastAPI request object
        exc: Pydantic validation error
        
    Returns:
        JSON response with validation error details
    """
    import uuid
    from datetime import datetime
    
    correlation_id = str(uuid.uuid4())
    
    # Extract validation errors
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"],
        })
    
    logger.warning(
        "Validation error",
        extra={
            "correlation_id": correlation_id,
            "errors": errors,
            "path": request.url.path,
            "method": request.method,
        },
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": {"validation_errors": errors},
                "correlation_id": correlation_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        },
    )


async def integrity_error_handler(
    request: Request, exc: IntegrityError
) -> JSONResponse:
    """Handle SQLAlchemy IntegrityError.
    
    Translates database integrity errors into user-friendly error messages
    with appropriate HTTP status codes.
    
    Args:
        request: FastAPI request object
        exc: SQLAlchemy IntegrityError
        
    Returns:
        JSON response with error details
    """
    import uuid
    from datetime import datetime
    
    correlation_id = str(uuid.uuid4())
    error_msg = str(exc.orig).lower() if exc.orig else str(exc).lower()
    
    # Parse the error message to determine the specific constraint violation
    if "foreign key" in error_msg or "fk_" in error_msg:
        # Extract table and column information if possible
        app_exc = ForeignKeyViolationError(
            table="unknown",
            column="unknown",
            referenced_table="unknown",
            correlation_id=correlation_id,
        )
        app_exc.details["original_error"] = str(exc.orig) if exc.orig else str(exc)
        
    elif "unique" in error_msg or "duplicate" in error_msg:
        # Extract constraint name if possible
        app_exc = UniqueConstraintViolationError(
            table="unknown",
            columns=["unknown"],
            correlation_id=correlation_id,
        )
        app_exc.details["original_error"] = str(exc.orig) if exc.orig else str(exc)
        
    elif "check constraint" in error_msg or "violates check" in error_msg:
        app_exc = CheckConstraintViolationError(
            table="unknown",
            constraint="unknown",
            correlation_id=correlation_id,
        )
        app_exc.details["original_error"] = str(exc.orig) if exc.orig else str(exc)
        
    elif "not null" in error_msg or "null value" in error_msg:
        app_exc = NotNullViolationError(
            table="unknown",
            column="unknown",
            correlation_id=correlation_id,
        )
        app_exc.details["original_error"] = str(exc.orig) if exc.orig else str(exc)
        
    else:
        # Generic integrity error
        from app.core.exceptions import IntegrityConstraintError
        app_exc = IntegrityConstraintError(
            message="Database integrity constraint violated",
            details={"original_error": str(exc.orig) if exc.orig else str(exc)},
            correlation_id=correlation_id,
        )
    
    logger.error(
        f"Database integrity error: {app_exc.error_code}",
        extra={
            "correlation_id": correlation_id,
            "error_code": app_exc.error_code,
            "error_message": app_exc.message,
            "details": app_exc.details,
            "path": request.url.path,
            "method": request.method,
        },
    )
    
    return JSONResponse(
        status_code=app_exc.status_code,
        content=app_exc.to_dict(),
    )


async def operational_error_handler(
    request: Request, exc: OperationalError
) -> JSONResponse:
    """Handle SQLAlchemy OperationalError.
    
    These are typically connection-related errors that may be transient.
    
    Args:
        request: FastAPI request object
        exc: SQLAlchemy OperationalError
        
    Returns:
        JSON response with error details
    """
    import uuid
    
    correlation_id = str(uuid.uuid4())
    
    app_exc = DatabaseConnectionError(
        message="Database connection error",
        details={"original_error": str(exc.orig) if exc.orig else str(exc)},
        correlation_id=correlation_id,
    )
    
    logger.error(
        f"Database operational error: {app_exc.error_code}",
        extra={
            "correlation_id": correlation_id,
            "error_code": app_exc.error_code,
            "error_message": app_exc.message,
            "details": app_exc.details,
            "path": request.url.path,
            "method": request.method,
        },
    )
    
    return JSONResponse(
        status_code=app_exc.status_code,
        content=app_exc.to_dict(),
    )


async def timeout_error_handler(
    request: Request, exc: SQLTimeoutError
) -> JSONResponse:
    """Handle SQLAlchemy TimeoutError.
    
    Args:
        request: FastAPI request object
        exc: SQLAlchemy TimeoutError
        
    Returns:
        JSON response with error details
    """
    import uuid
    
    correlation_id = str(uuid.uuid4())
    
    app_exc = DatabaseTimeoutError(
        operation="database_query",
        timeout_seconds=30,  # Default timeout
        correlation_id=correlation_id,
    )
    app_exc.details["original_error"] = str(exc)
    
    logger.error(
        f"Database timeout error: {app_exc.error_code}",
        extra={
            "correlation_id": correlation_id,
            "error_code": app_exc.error_code,
            "error_message": app_exc.message,
            "details": app_exc.details,
            "path": request.url.path,
            "method": request.method,
        },
    )
    
    return JSONResponse(
        status_code=app_exc.status_code,
        content=app_exc.to_dict(),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions.
    
    This is a catch-all handler for any exceptions not handled by
    more specific handlers. It ensures no sensitive information is
    leaked to clients.
    
    Args:
        request: FastAPI request object
        exc: Any unhandled exception
        
    Returns:
        JSON response with generic error message
    """
    import uuid
    from datetime import datetime
    
    correlation_id = str(uuid.uuid4())
    
    # Log the full exception for debugging
    logger.exception(
        "Unhandled exception",
        extra={
            "correlation_id": correlation_id,
            "exception_type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method,
        },
    )
    
    # Return generic error to client (don't leak internal details)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred. Please try again later.",
                "details": {},
                "correlation_id": correlation_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        },
    )


def register_exception_handlers(app) -> None:
    """Register all exception handlers with the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    # Custom application exceptions
    app.add_exception_handler(AppException, app_exception_handler)
    
    # Pydantic validation errors
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    
    # SQLAlchemy errors
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(OperationalError, operational_error_handler)
    app.add_exception_handler(SQLTimeoutError, timeout_error_handler)
    
    # Catch-all for unexpected errors
    app.add_exception_handler(Exception, generic_exception_handler)
    
    logger.info("Exception handlers registered successfully")
