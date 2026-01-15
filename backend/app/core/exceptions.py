"""Custom exception hierarchy for the application.

This module defines domain-specific exceptions that provide:
- Consistent error handling across the application
- HTTP status codes for API responses
- Error codes for client-side handling
- Correlation IDs for request tracing
- User-friendly messages and developer details
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from http import HTTPStatus


class AppException(Exception):
    """Base exception for all application errors.
    
    All custom exceptions should inherit from this class to ensure
    consistent error handling and response formatting.
    """
    
    def __init__(
        self,
        message: str,
        status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ):
        """Initialize application exception.
        
        Args:
            message: User-friendly error message
            status_code: HTTP status code for API response
            error_code: Machine-readable error code
            details: Additional error details for debugging
            correlation_id: Request correlation ID for tracing
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.timestamp = datetime.utcnow().isoformat() + "Z"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON serialization."""
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details,
                "correlation_id": self.correlation_id,
                "timestamp": self.timestamp,
            }
        }


# ============================================================================
# Validation Errors
# ============================================================================

class ValidationError(AppException):
    """Exception raised for input validation failures.
    
    This includes Pydantic validation errors, custom business rule
    violations, and any other input validation failures.
    """
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ):
        """Initialize validation error.
        
        Args:
            message: User-friendly error message
            field: Field name that failed validation
            details: Additional validation error details
            correlation_id: Request correlation ID
        """
        error_details = details or {}
        if field:
            error_details["field"] = field
        
        super().__init__(
            message=message,
            status_code=HTTPStatus.BAD_REQUEST,
            error_code="VALIDATION_ERROR",
            details=error_details,
            correlation_id=correlation_id,
        )


class InvalidUUIDError(ValidationError):
    """Exception raised for malformed UUID values."""
    
    def __init__(
        self,
        field: str,
        value: Any,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(
            message=f"Invalid UUID format for field '{field}'",
            field=field,
            details={"value": str(value), "expected_format": "UUID v4"},
            correlation_id=correlation_id,
        )


class InvalidEmailError(ValidationError):
    """Exception raised for invalid email addresses."""
    
    def __init__(
        self,
        email: str,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(
            message="Invalid email address format",
            field="email",
            details={"value": email},
            correlation_id=correlation_id,
        )


class InvalidVectorDimensionError(ValidationError):
    """Exception raised for incorrect vector embedding dimensions."""
    
    def __init__(
        self,
        expected: int,
        actual: int,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(
            message=f"Invalid vector dimension: expected {expected}, got {actual}",
            field="embedding",
            details={"expected_dimension": expected, "actual_dimension": actual},
            correlation_id=correlation_id,
        )


class InvalidFileError(ValidationError):
    """Exception raised for invalid file uploads."""
    
    def __init__(
        self,
        message: str,
        filename: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ):
        error_details = details or {}
        if filename:
            error_details["filename"] = filename
        
        super().__init__(
            message=message,
            field="file",
            details=error_details,
            correlation_id=correlation_id,
        )


# ============================================================================
# Database Errors
# ============================================================================

class DatabaseError(AppException):
    """Base exception for database-related errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "DATABASE_ERROR",
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            error_code=error_code,
            details=details,
            correlation_id=correlation_id,
        )


class DatabaseConnectionError(DatabaseError):
    """Exception raised when database connection fails."""
    
    def __init__(
        self,
        message: str = "Failed to connect to database",
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            error_code="DATABASE_CONNECTION_ERROR",
            details=details,
            correlation_id=correlation_id,
        )


class DatabaseTimeoutError(DatabaseError):
    """Exception raised when database operation times out."""
    
    def __init__(
        self,
        operation: str,
        timeout_seconds: int,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(
            message=f"Database operation '{operation}' timed out after {timeout_seconds}s",
            error_code="DATABASE_TIMEOUT",
            details={"operation": operation, "timeout_seconds": timeout_seconds},
            correlation_id=correlation_id,
        )


class TransactionError(DatabaseError):
    """Exception raised for transaction-related failures."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            error_code="TRANSACTION_ERROR",
            details=details,
            correlation_id=correlation_id,
        )


# ============================================================================
# Resource Errors
# ============================================================================

class ResourceNotFoundError(AppException):
    """Exception raised when a requested resource is not found."""
    
    def __init__(
        self,
        resource_type: str,
        resource_id: Any,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(
            message=f"{resource_type} with ID '{resource_id}' not found",
            status_code=HTTPStatus.NOT_FOUND,
            error_code="RESOURCE_NOT_FOUND",
            details={"resource_type": resource_type, "resource_id": str(resource_id)},
            correlation_id=correlation_id,
        )


class DuplicateResourceError(AppException):
    """Exception raised when attempting to create a duplicate resource."""
    
    def __init__(
        self,
        resource_type: str,
        field: str,
        value: Any,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(
            message=f"{resource_type} with {field}='{value}' already exists",
            status_code=HTTPStatus.CONFLICT,
            error_code="DUPLICATE_RESOURCE",
            details={
                "resource_type": resource_type,
                "field": field,
                "value": str(value),
            },
            correlation_id=correlation_id,
        )


# ============================================================================
# Constraint Errors
# ============================================================================

class IntegrityConstraintError(AppException):
    """Base exception for database integrity constraint violations."""
    
    def __init__(
        self,
        message: str,
        constraint_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ):
        error_details = details or {}
        if constraint_name:
            error_details["constraint"] = constraint_name
        
        super().__init__(
            message=message,
            status_code=HTTPStatus.BAD_REQUEST,
            error_code="INTEGRITY_CONSTRAINT_VIOLATION",
            details=error_details,
            correlation_id=correlation_id,
        )


class ForeignKeyViolationError(IntegrityConstraintError):
    """Exception raised for foreign key constraint violations."""
    
    def __init__(
        self,
        table: str,
        column: str,
        referenced_table: str,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(
            message=f"Foreign key violation: {table}.{column} references non-existent {referenced_table}",
            details={
                "table": table,
                "column": column,
                "referenced_table": referenced_table,
            },
            correlation_id=correlation_id,
        )


class UniqueConstraintViolationError(IntegrityConstraintError):
    """Exception raised for unique constraint violations."""
    
    def __init__(
        self,
        table: str,
        columns: list[str],
        correlation_id: Optional[str] = None,
    ):
        columns_str = ", ".join(columns)
        super().__init__(
            message=f"Unique constraint violation on {table}({columns_str})",
            details={"table": table, "columns": columns},
            correlation_id=correlation_id,
        )


class CheckConstraintViolationError(IntegrityConstraintError):
    """Exception raised for check constraint violations."""
    
    def __init__(
        self,
        table: str,
        constraint: str,
        message: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ):
        error_message = message or f"Check constraint '{constraint}' violated on table '{table}'"
        super().__init__(
            message=error_message,
            constraint_name=constraint,
            details={"table": table},
            correlation_id=correlation_id,
        )


class NotNullViolationError(IntegrityConstraintError):
    """Exception raised for NOT NULL constraint violations."""
    
    def __init__(
        self,
        table: str,
        column: str,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(
            message=f"NULL value not allowed for {table}.{column}",
            details={"table": table, "column": column},
            correlation_id=correlation_id,
        )


# ============================================================================
# External Service Errors
# ============================================================================

class ExternalServiceError(AppException):
    """Exception raised when external service calls fail."""
    
    def __init__(
        self,
        service_name: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ):
        error_details = details or {}
        error_details["service"] = service_name
        
        super().__init__(
            message=f"External service '{service_name}' error: {message}",
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            error_code="EXTERNAL_SERVICE_ERROR",
            details=error_details,
            correlation_id=correlation_id,
        )


class CircuitBreakerOpenError(ExternalServiceError):
    """Exception raised when circuit breaker is open."""
    
    def __init__(
        self,
        service_name: str,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(
            service_name=service_name,
            message="Service temporarily unavailable due to repeated failures",
            details={"circuit_state": "OPEN"},
            correlation_id=correlation_id,
        )


# ============================================================================
# Partial Failure Errors
# ============================================================================

class PartialFailureError(AppException):
    """Exception raised when operation partially succeeds."""
    
    def __init__(
        self,
        message: str,
        successful_items: int,
        failed_items: int,
        failures: list[Dict[str, Any]],
        correlation_id: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            status_code=HTTPStatus.MULTI_STATUS,
            error_code="PARTIAL_FAILURE",
            details={
                "successful_count": successful_items,
                "failed_count": failed_items,
                "failures": failures,
            },
            correlation_id=correlation_id,
        )
