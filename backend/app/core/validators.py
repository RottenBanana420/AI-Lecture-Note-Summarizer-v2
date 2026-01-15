"""Reusable validation functions for the application.

This module provides common validation utilities that can be used
across different layers of the application (API, services, models).
"""

import re
import uuid as uuid_lib
from typing import Any, Optional, Dict, List
from email_validator import validate_email as email_validator_validate, EmailNotValidError

from app.core.exceptions import (
    ValidationError,
    InvalidUUIDError,
    InvalidEmailError,
    InvalidVectorDimensionError,
    InvalidFileError,
)


# Email validation regex (RFC 5322 simplified)
EMAIL_REGEX = re.compile(
    r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
)

# Allowed MIME types for file uploads
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "text/plain",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
}


def validate_uuid(value: Any, field_name: str = "id") -> uuid_lib.UUID:
    """Validate UUID format.
    
    Args:
        value: Value to validate as UUID
        field_name: Name of the field being validated
        
    Returns:
        Validated UUID object
        
    Raises:
        InvalidUUIDError: If value is not a valid UUID
    """
    if isinstance(value, uuid_lib.UUID):
        return value
    
    if not isinstance(value, str):
        raise InvalidUUIDError(field=field_name, value=value)
    
    try:
        return uuid_lib.UUID(value)
    except (ValueError, AttributeError, TypeError) as e:
        raise InvalidUUIDError(field=field_name, value=value)


def validate_email(email: str) -> str:
    """Validate email address format.
    
    Uses both regex and email-validator library for comprehensive validation.
    
    Args:
        email: Email address to validate
        
    Returns:
        Normalized email address
        
    Raises:
        InvalidEmailError: If email format is invalid
    """
    if not email or not isinstance(email, str):
        raise InvalidEmailError(email=str(email))
    
    # Basic regex check
    if not EMAIL_REGEX.match(email):
        raise InvalidEmailError(email=email)
    
    # Comprehensive validation using email-validator
    try:
        validated = email_validator_validate(email, check_deliverability=False)
        return validated.normalized
    except EmailNotValidError as e:
        raise InvalidEmailError(email=email)


def validate_file_size(
    file_size: int,
    max_size: int,
    filename: Optional[str] = None,
) -> int:
    """Validate file size constraints.
    
    Args:
        file_size: File size in bytes
        max_size: Maximum allowed file size in bytes
        filename: Optional filename for error messages
        
    Returns:
        Validated file size
        
    Raises:
        InvalidFileError: If file size exceeds maximum or is invalid
    """
    if file_size <= 0:
        raise InvalidFileError(
            message="File size must be greater than zero",
            filename=filename,
            details={"file_size": file_size},
        )
    
    if file_size > max_size:
        raise InvalidFileError(
            message=f"File size exceeds maximum allowed size of {max_size} bytes",
            filename=filename,
            details={
                "file_size": file_size,
                "max_size": max_size,
                "max_size_mb": max_size / (1024 * 1024),
            },
        )
    
    return file_size


def validate_mime_type(
    mime_type: str,
    allowed_types: Optional[set[str]] = None,
    filename: Optional[str] = None,
) -> str:
    """Validate MIME type against allowed types.
    
    Args:
        mime_type: MIME type to validate
        allowed_types: Set of allowed MIME types (defaults to ALLOWED_MIME_TYPES)
        filename: Optional filename for error messages
        
    Returns:
        Validated MIME type
        
    Raises:
        InvalidFileError: If MIME type is not allowed
    """
    if allowed_types is None:
        allowed_types = ALLOWED_MIME_TYPES
    
    if not mime_type or not isinstance(mime_type, str):
        raise InvalidFileError(
            message="Invalid MIME type",
            filename=filename,
            details={"mime_type": str(mime_type)},
        )
    
    if mime_type not in allowed_types:
        raise InvalidFileError(
            message=f"MIME type '{mime_type}' is not allowed",
            filename=filename,
            details={
                "mime_type": mime_type,
                "allowed_types": list(allowed_types),
            },
        )
    
    return mime_type


def validate_vector_dimension(
    embedding: List[float],
    expected_dimension: int,
) -> List[float]:
    """Validate vector embedding dimensions.
    
    Args:
        embedding: Vector embedding to validate
        expected_dimension: Expected number of dimensions
        
    Returns:
        Validated embedding
        
    Raises:
        InvalidVectorDimensionError: If dimension doesn't match expected
    """
    if not isinstance(embedding, (list, tuple)):
        raise ValidationError(
            message="Embedding must be a list or tuple",
            field="embedding",
            details={"type": type(embedding).__name__},
        )
    
    actual_dimension = len(embedding)
    if actual_dimension != expected_dimension:
        raise InvalidVectorDimensionError(
            expected=expected_dimension,
            actual=actual_dimension,
        )
    
    # Validate all elements are numeric
    try:
        return [float(x) for x in embedding]
    except (ValueError, TypeError) as e:
        raise ValidationError(
            message="All embedding values must be numeric",
            field="embedding",
            details={"error": str(e)},
        )


def validate_jsonb_structure(
    data: Any,
    required_keys: Optional[List[str]] = None,
    allowed_keys: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Validate JSONB data structure.
    
    Args:
        data: Data to validate
        required_keys: List of required keys
        allowed_keys: List of allowed keys (if None, all keys allowed)
        
    Returns:
        Validated dictionary
        
    Raises:
        ValidationError: If structure is invalid
    """
    if data is None:
        return {}
    
    if not isinstance(data, dict):
        raise ValidationError(
            message="JSONB data must be a dictionary",
            field="meta_data",
            details={"type": type(data).__name__},
        )
    
    # Check required keys
    if required_keys:
        missing_keys = set(required_keys) - set(data.keys())
        if missing_keys:
            raise ValidationError(
                message=f"Missing required keys: {', '.join(missing_keys)}",
                field="meta_data",
                details={"missing_keys": list(missing_keys)},
            )
    
    # Check allowed keys
    if allowed_keys is not None:
        invalid_keys = set(data.keys()) - set(allowed_keys)
        if invalid_keys:
            raise ValidationError(
                message=f"Invalid keys: {', '.join(invalid_keys)}",
                field="meta_data",
                details={
                    "invalid_keys": list(invalid_keys),
                    "allowed_keys": allowed_keys,
                },
            )
    
    return data


def validate_positive_integer(
    value: int,
    field_name: str,
    allow_zero: bool = False,
) -> int:
    """Validate that a value is a positive integer.
    
    Args:
        value: Value to validate
        field_name: Name of the field being validated
        allow_zero: Whether to allow zero as a valid value
        
    Returns:
        Validated integer
        
    Raises:
        ValidationError: If value is not a positive integer
    """
    if not isinstance(value, int):
        raise ValidationError(
            message=f"{field_name} must be an integer",
            field=field_name,
            details={"value": value, "type": type(value).__name__},
        )
    
    min_value = 0 if allow_zero else 1
    if value < min_value:
        raise ValidationError(
            message=f"{field_name} must be {'non-negative' if allow_zero else 'positive'}",
            field=field_name,
            details={"value": value, "minimum": min_value},
        )
    
    return value


def validate_string_length(
    value: str,
    field_name: str,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
) -> str:
    """Validate string length constraints.
    
    Args:
        value: String to validate
        field_name: Name of the field being validated
        min_length: Minimum allowed length
        max_length: Maximum allowed length
        
    Returns:
        Validated string
        
    Raises:
        ValidationError: If string length is invalid
    """
    if not isinstance(value, str):
        raise ValidationError(
            message=f"{field_name} must be a string",
            field=field_name,
            details={"type": type(value).__name__},
        )
    
    length = len(value)
    
    if min_length is not None and length < min_length:
        raise ValidationError(
            message=f"{field_name} must be at least {min_length} characters",
            field=field_name,
            details={"length": length, "min_length": min_length},
        )
    
    if max_length is not None and length > max_length:
        raise ValidationError(
            message=f"{field_name} must not exceed {max_length} characters",
            field=field_name,
            details={"length": length, "max_length": max_length},
        )
    
    return value


def validate_enum_value(
    value: str,
    field_name: str,
    allowed_values: List[str],
) -> str:
    """Validate that a value is in the allowed enum values.
    
    Args:
        value: Value to validate
        field_name: Name of the field being validated
        allowed_values: List of allowed values
        
    Returns:
        Validated value
        
    Raises:
        ValidationError: If value is not in allowed values
    """
    if value not in allowed_values:
        raise ValidationError(
            message=f"Invalid value for {field_name}",
            field=field_name,
            details={
                "value": value,
                "allowed_values": allowed_values,
            },
        )
    
    return value
