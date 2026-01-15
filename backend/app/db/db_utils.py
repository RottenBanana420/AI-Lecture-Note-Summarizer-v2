"""Database utility functions for error handling and resilience.

This module provides utilities for:
- Retrying transient database errors
- Translating SQLAlchemy exceptions to custom exceptions
- Parsing integrity errors for specific constraint violations
"""

import time
import logging
import re
from typing import Callable, TypeVar, Any, Optional
from functools import wraps
from sqlalchemy.exc import (
    IntegrityError,
    OperationalError,
    TimeoutError as SQLTimeoutError,
    DatabaseError as SQLDatabaseError,
    DisconnectionError,
)

from app.core.config import settings
from app.core.exceptions import (
    DatabaseError,
    DatabaseConnectionError,
    DatabaseTimeoutError,
    TransactionError,
    ForeignKeyViolationError,
    UniqueConstraintViolationError,
    CheckConstraintViolationError,
    NotNullViolationError,
    IntegrityConstraintError,
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


def is_transient_error(exc: Exception) -> bool:
    """Determine if a database error is transient and retryable.
    
    Transient errors include:
    - Connection errors
    - Timeout errors
    - Deadlock errors
    - Serialization failures
    
    Args:
        exc: Exception to check
        
    Returns:
        True if error is transient and should be retried
    """
    if isinstance(exc, (OperationalError, DisconnectionError, SQLTimeoutError)):
        return True
    
    if isinstance(exc, SQLDatabaseError):
        error_msg = str(exc).lower()
        transient_patterns = [
            "connection",
            "timeout",
            "deadlock",
            "serialization failure",
            "could not serialize",
            "connection reset",
            "broken pipe",
        ]
        return any(pattern in error_msg for pattern in transient_patterns)
    
    return False


def retry_on_transient_error(
    max_attempts: Optional[int] = None,
    backoff_factor: Optional[float] = None,
    max_delay: Optional[int] = None,
):
    """Decorator to retry database operations on transient errors.
    
    Implements exponential backoff with jitter to avoid thundering herd.
    
    Args:
        max_attempts: Maximum number of retry attempts (default from config)
        backoff_factor: Exponential backoff multiplier (default from config)
        max_delay: Maximum delay between retries in seconds (default from config)
        
    Returns:
        Decorated function that retries on transient errors
    """
    if max_attempts is None:
        max_attempts = settings.MAX_RETRY_ATTEMPTS
    if backoff_factor is None:
        backoff_factor = settings.RETRY_BACKOFF_FACTOR
    if max_delay is None:
        max_delay = settings.RETRY_MAX_DELAY
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:
                    last_exception = exc
                    
                    # Check if error is transient
                    if not is_transient_error(exc):
                        # Non-transient error, fail immediately
                        raise
                    
                    # Last attempt, don't retry
                    if attempt == max_attempts - 1:
                        break
                    
                    # Calculate delay with exponential backoff and jitter
                    import random
                    delay = min(
                        backoff_factor ** attempt + random.uniform(0, 1),
                        max_delay
                    )
                    
                    logger.warning(
                        f"Transient database error on attempt {attempt + 1}/{max_attempts}. "
                        f"Retrying in {delay:.2f}s",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "max_attempts": max_attempts,
                            "delay": delay,
                            "error": str(exc),
                        },
                    )
                    
                    await asyncio.sleep(delay)
            
            # All retries exhausted
            logger.error(
                f"All {max_attempts} retry attempts exhausted for {func.__name__}",
                extra={
                    "function": func.__name__,
                    "max_attempts": max_attempts,
                    "last_error": str(last_exception),
                },
            )
            raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_exception = exc
                    
                    if not is_transient_error(exc):
                        raise
                    
                    if attempt == max_attempts - 1:
                        break
                    
                    import random
                    delay = min(
                        backoff_factor ** attempt + random.uniform(0, 1),
                        max_delay
                    )
                    
                    logger.warning(
                        f"Transient database error on attempt {attempt + 1}/{max_attempts}. "
                        f"Retrying in {delay:.2f}s",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "max_attempts": max_attempts,
                            "delay": delay,
                            "error": str(exc),
                        },
                    )
                    
                    time.sleep(delay)
            
            logger.error(
                f"All {max_attempts} retry attempts exhausted for {func.__name__}",
                extra={
                    "function": func.__name__,
                    "max_attempts": max_attempts,
                    "last_error": str(last_exception),
                },
            )
            raise last_exception
        
        # Return appropriate wrapper based on function type
        import asyncio
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def parse_integrity_error(exc: IntegrityError) -> IntegrityConstraintError:
    """Parse SQLAlchemy IntegrityError and return specific custom exception.
    
    Analyzes the error message to determine the specific type of constraint
    violation and extracts relevant details.
    
    Args:
        exc: SQLAlchemy IntegrityError
        
    Returns:
        Specific custom exception based on constraint type
    """
    error_msg = str(exc.orig).lower() if exc.orig else str(exc).lower()
    original_error = str(exc.orig) if exc.orig else str(exc)
    
    # Foreign key constraint violation
    # Patterns: "foreign key", "fk_", or "is not present in table"
    if ("foreign key" in error_msg or "fk_" in error_msg or 
        "is not present in table" in error_msg or "not present in table" in error_msg):
        # Try to extract table and column names
        # Pattern: DETAIL:  Key (column_name)=(value) is not present in table "table_name"
        # Also handle: violates foreign key constraint "fk_table_column_fkey"
        
        # Extract referenced table
        referenced_table = "unknown"
        table_pattern = r'table "(\w+)"'
        table_match = re.search(table_pattern, error_msg)
        if table_match:
            referenced_table = table_match.group(1)
        
        # Extract column
        column = "unknown"
        column_pattern = r'key \((\w+)\)'
        column_match = re.search(column_pattern, error_msg)
        if column_match:
            column = column_match.group(1)
        
        # Extract source table from constraint name or relation
        table = "unknown"
        # Try constraint pattern: fk_documents_user_id
        constraint_pattern = r'constraint "fk_(\w+)_'
        constraint_match = re.search(constraint_pattern, error_msg)
        if constraint_match:
            table = constraint_match.group(1)
        else:
            # Try relation pattern
            relation_pattern = r'relation "(\w+)"'
            relation_match = re.search(relation_pattern, error_msg)
            if relation_match:
                table = relation_match.group(1)
        
        return ForeignKeyViolationError(
            table=table,
            column=column,
            referenced_table=referenced_table,
        )
    
    # Unique constraint violation
    elif "unique" in error_msg or "duplicate" in error_msg:
        # Pattern: DETAIL:  Key (column1, column2)=(value1, value2) already exists
        unique_pattern = r'key \(([\w, ]+)\)'
        match = re.search(unique_pattern, error_msg)
        
        columns = []
        if match:
            columns_str = match.group(1)
            columns = [col.strip() for col in columns_str.split(',')]
        
        # Try to extract table name
        table_pattern = r'relation "(\w+)"'
        table_match = re.search(table_pattern, error_msg)
        table = table_match.group(1) if table_match else "unknown"
        
        return UniqueConstraintViolationError(
            table=table,
            columns=columns if columns else ["unknown"],
        )
    
    # Check constraint violation
    elif "check constraint" in error_msg or "violates check" in error_msg:
        # Pattern: violates check constraint "constraint_name"
        constraint_pattern = r'constraint "(\w+)"'
        match = re.search(constraint_pattern, error_msg)
        constraint = match.group(1) if match else "unknown"
        
        # Try to extract table name
        table_pattern = r'relation "(\w+)"'
        table_match = re.search(table_pattern, error_msg)
        table = table_match.group(1) if table_match else "unknown"
        
        return CheckConstraintViolationError(
            table=table,
            constraint=constraint,
        )
    
    # NOT NULL constraint violation
    elif "not null" in error_msg or "null value" in error_msg:
        # Pattern: null value in column "column_name" violates not-null constraint
        column_pattern = r'column "(\w+)"'
        match = re.search(column_pattern, error_msg)
        column = match.group(1) if match else "unknown"
        
        # Try to extract table name
        table_pattern = r'relation "(\w+)"'
        table_match = re.search(table_pattern, error_msg)
        table = table_match.group(1) if table_match else "unknown"
        
        return NotNullViolationError(
            table=table,
            column=column,
        )
    
    # Generic integrity error
    return IntegrityConstraintError(
        message="Database integrity constraint violated",
        details={"original_error": original_error},
    )


def translate_db_error(exc: Exception, correlation_id: Optional[str] = None) -> Exception:
    """Translate SQLAlchemy exceptions to custom application exceptions.
    
    Args:
        exc: SQLAlchemy exception
        correlation_id: Optional correlation ID for request tracing
        
    Returns:
        Custom application exception
    """
    # IntegrityError - constraint violations
    if isinstance(exc, IntegrityError):
        return parse_integrity_error(exc)
    
    # OperationalError - connection issues
    elif isinstance(exc, (OperationalError, DisconnectionError)):
        return DatabaseConnectionError(
            message="Database connection error",
            details={"original_error": str(exc.orig) if hasattr(exc, 'orig') and exc.orig else str(exc)},
            correlation_id=correlation_id,
        )
    
    # TimeoutError - query timeout
    elif isinstance(exc, SQLTimeoutError):
        return DatabaseTimeoutError(
            operation="database_query",
            timeout_seconds=settings.DATABASE_TIMEOUT,
            correlation_id=correlation_id,
        )
    
    # Generic database error
    elif isinstance(exc, SQLDatabaseError):
        return DatabaseError(
            message="Database operation failed",
            details={"original_error": str(exc.orig) if hasattr(exc, 'orig') and exc.orig else str(exc)},
            correlation_id=correlation_id,
        )
    
    # Unknown error, return as-is
    return exc


async def handle_db_operation(
    operation: Callable[..., T],
    *args,
    **kwargs
) -> T:
    """Execute a database operation with error handling and translation.
    
    This is a convenience function that combines retry logic and error
    translation for database operations.
    
    Args:
        operation: Async callable to execute
        *args: Positional arguments for operation
        **kwargs: Keyword arguments for operation
        
    Returns:
        Result of the operation
        
    Raises:
        Custom application exception if operation fails
    """
    @retry_on_transient_error()
    async def _execute():
        try:
            return await operation(*args, **kwargs)
        except Exception as exc:
            # Translate database errors to custom exceptions
            if isinstance(exc, (IntegrityError, OperationalError, SQLTimeoutError, SQLDatabaseError)):
                raise translate_db_error(exc)
            raise
    
    return await _execute()
