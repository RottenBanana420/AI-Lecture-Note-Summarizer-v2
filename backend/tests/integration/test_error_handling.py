"""
Aggressive tests for error handling mechanisms.

These tests verify that:
1. SQLAlchemy exceptions are properly translated to custom exceptions
2. Retry logic works correctly for transient errors
3. Error responses follow standardized format
4. Correlation IDs are generated and tracked

Tests must NEVER be modified to pass - only implementation code should be updated.
"""

import pytest
import uuid
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.exc import IntegrityError, OperationalError, TimeoutError as SQLTimeoutError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.db_utils import (
    is_transient_error,
    parse_integrity_error,
    translate_db_error,
    retry_on_transient_error,
)
from app.core.exceptions import (
    ForeignKeyViolationError,
    UniqueConstraintViolationError,
    CheckConstraintViolationError,
    NotNullViolationError,
    DatabaseConnectionError,
    DatabaseTimeoutError,
    IntegrityConstraintError,
)


pytestmark = [pytest.mark.integration]


class TestExceptionTranslation:
    """Test that SQLAlchemy exceptions are properly translated to custom exceptions."""
    
    def test_parse_foreign_key_violation(self):
        """Foreign key IntegrityError should be parsed to ForeignKeyViolationError."""
        # Simulate PostgreSQL foreign key error message
        orig_error = Mock()
        orig_error.__str__ = lambda self: (
            'Key (user_id)=(123e4567-e89b-12d3-4567-426614174000) '
            'is not present in table "users"'
        )
        
        exc = IntegrityError(
            statement="INSERT INTO documents...",
            params={},
            orig=orig_error
        )
        
        result = parse_integrity_error(exc)
        
        assert isinstance(result, ForeignKeyViolationError)
        assert "users" in str(result)
    
    def test_parse_unique_constraint_violation(self):
        """Unique constraint IntegrityError should be parsed to UniqueConstraintViolationError."""
        orig_error = Mock()
        orig_error.__str__ = lambda self: (
            'duplicate key value violates unique constraint "users_email_key"\n'
            'DETAIL:  Key (email)=(test@example.com) already exists.'
        )
        
        exc = IntegrityError(
            statement="INSERT INTO users...",
            params={},
            orig=orig_error
        )
        
        result = parse_integrity_error(exc)
        
        assert isinstance(result, UniqueConstraintViolationError)
        assert "email" in str(result).lower()
    
    def test_parse_check_constraint_violation(self):
        """Check constraint IntegrityError should be parsed to CheckConstraintViolationError."""
        orig_error = Mock()
        orig_error.__str__ = lambda self: (
            'new row for relation "documents" violates check constraint "check_file_size_positive"'
        )
        
        exc = IntegrityError(
            statement="INSERT INTO documents...",
            params={},
            orig=orig_error
        )
        
        result = parse_integrity_error(exc)
        
        assert isinstance(result, CheckConstraintViolationError)
        assert "check_file_size_positive" in str(result)
    
    def test_parse_not_null_violation(self):
        """NOT NULL IntegrityError should be parsed to NotNullViolationError."""
        orig_error = Mock()
        orig_error.__str__ = lambda self: (
            'null value in column "email" of relation "users" violates not-null constraint'
        )
        
        exc = IntegrityError(
            statement="INSERT INTO users...",
            params={},
            orig=orig_error
        )
        
        result = parse_integrity_error(exc)
        
        assert isinstance(result, NotNullViolationError)
        assert "email" in str(result)
    
    def test_translate_operational_error(self):
        """OperationalError should be translated to DatabaseConnectionError."""
        orig_error = Mock()
        orig_error.__str__ = lambda self: "connection refused"
        
        exc = OperationalError(
            statement="SELECT...",
            params={},
            orig=orig_error
        )
        
        result = translate_db_error(exc)
        
        assert isinstance(result, DatabaseConnectionError)
    
    def test_translate_timeout_error(self):
        """TimeoutError should be translated to DatabaseTimeoutError."""
        exc = SQLTimeoutError("Query timeout")
        
        result = translate_db_error(exc)
        
        assert isinstance(result, DatabaseTimeoutError)


class TestTransientErrorDetection:
    """Test that transient errors are correctly identified."""
    
    def test_operational_error_is_transient(self):
        """OperationalError should be identified as transient."""
        exc = OperationalError(statement="", params={}, orig=None)
        assert is_transient_error(exc) is True
    
    def test_timeout_error_is_transient(self):
        """TimeoutError should be identified as transient."""
        exc = SQLTimeoutError("Query timeout")
        assert is_transient_error(exc) is True
    
    def test_integrity_error_is_not_transient(self):
        """IntegrityError should NOT be identified as transient."""
        exc = IntegrityError(statement="", params={}, orig=None)
        assert is_transient_error(exc) is False
    
    def test_value_error_is_not_transient(self):
        """ValueError should NOT be identified as transient."""
        exc = ValueError("test error")
        assert is_transient_error(exc) is False


class TestRetryLogic:
    """Test retry decorator behavior."""
    
    @pytest.mark.asyncio
    async def test_retry_succeeds_on_second_attempt(self):
        """Function should succeed on retry after transient error."""
        call_count = 0
        
        @retry_on_transient_error(max_attempts=3, backoff_factor=0.1, max_delay=1)
        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call fails with transient error
                raise OperationalError(statement="", params={}, orig=None)
            return "success"
        
        result = await flaky_function()
        
        assert result == "success"
        assert call_count == 2  # Failed once, succeeded on retry
    
    @pytest.mark.asyncio
    async def test_retry_exhausts_all_attempts(self):
        """Function should exhaust all retry attempts for persistent transient errors."""
        call_count = 0
        
        @retry_on_transient_error(max_attempts=3, backoff_factor=0.1, max_delay=1)
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise OperationalError(statement="", params={}, orig=None)
        
        with pytest.raises(OperationalError):
            await always_fails()
        
        assert call_count == 3  # All attempts exhausted
    
    @pytest.mark.asyncio
    async def test_retry_does_not_retry_non_transient_errors(self):
        """Non-transient errors should fail immediately without retry."""
        call_count = 0
        
        @retry_on_transient_error(max_attempts=3, backoff_factor=0.1, max_delay=1)
        async def non_transient_failure():
            nonlocal call_count
            call_count += 1
            raise IntegrityError(statement="", params={}, orig=None)
        
        with pytest.raises(IntegrityError):
            await non_transient_failure()
        
        assert call_count == 1  # No retries for non-transient errors
    
    @pytest.mark.asyncio
    async def test_retry_with_exponential_backoff(self):
        """Retry delays should follow exponential backoff pattern."""
        import time
        
        call_times = []
        
        @retry_on_transient_error(max_attempts=3, backoff_factor=2.0, max_delay=10)
        async def track_timing():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise OperationalError(statement="", params={}, orig=None)
            return "success"
        
        await track_timing()
        
        # Verify we made 3 calls
        assert len(call_times) == 3
        
        # Verify delays are increasing (with some tolerance for jitter)
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]
        
        # First delay should be around 1s (2^0 + jitter)
        # Second delay should be around 2s (2^1 + jitter)
        assert 0.5 < delay1 < 2.0
        assert 1.5 < delay2 < 3.5
        assert delay2 > delay1  # Second delay should be longer


class TestErrorResponseFormat:
    """Test that error responses follow standardized format."""
    
    def test_app_exception_to_dict_has_required_fields(self):
        """AppException.to_dict() should include all required fields."""
        from app.core.exceptions import ValidationError
        
        exc = ValidationError(
            message="Test error",
            field="test_field",
        )
        
        error_dict = exc.to_dict()
        
        assert "error" in error_dict
        assert "code" in error_dict["error"]
        assert "message" in error_dict["error"]
        assert "details" in error_dict["error"]
        assert "correlation_id" in error_dict["error"]
        assert "timestamp" in error_dict["error"]
    
    def test_app_exception_has_correlation_id(self):
        """AppException should generate correlation ID if not provided."""
        from app.core.exceptions import ValidationError
        
        exc = ValidationError(message="Test error")
        
        assert exc.correlation_id is not None
        assert len(exc.correlation_id) > 0
        
        # Should be valid UUID
        try:
            uuid.UUID(exc.correlation_id)
        except ValueError:
            pytest.fail("Correlation ID should be a valid UUID")
    
    def test_app_exception_uses_provided_correlation_id(self):
        """AppException should use provided correlation ID."""
        from app.core.exceptions import ValidationError
        
        test_id = str(uuid.uuid4())
        exc = ValidationError(message="Test error", correlation_id=test_id)
        
        assert exc.correlation_id == test_id
    
    def test_app_exception_has_timestamp(self):
        """AppException should include ISO 8601 timestamp."""
        from app.core.exceptions import ValidationError
        from datetime import datetime
        
        exc = ValidationError(message="Test error")
        
        assert exc.timestamp is not None
        assert exc.timestamp.endswith("Z")  # UTC indicator
        
        # Should be parseable as ISO 8601
        try:
            datetime.fromisoformat(exc.timestamp.replace("Z", "+00:00"))
        except ValueError:
            pytest.fail("Timestamp should be valid ISO 8601 format")
    
    def test_validation_error_includes_field_in_details(self):
        """ValidationError should include field name in details."""
        from app.core.exceptions import ValidationError
        
        exc = ValidationError(message="Test error", field="email")
        
        assert "field" in exc.details
        assert exc.details["field"] == "email"
    
    def test_foreign_key_error_includes_table_info(self):
        """ForeignKeyViolationError should include table information."""
        exc = ForeignKeyViolationError(
            table="documents",
            column="user_id",
            referenced_table="users"
        )
        
        assert "documents" in str(exc)
        assert "user_id" in str(exc)
        assert "users" in str(exc)


class TestErrorHandlerIntegration:
    """Test FastAPI error handler integration."""
    
    @pytest.mark.asyncio
    async def test_app_exception_handler_returns_json_response(self):
        """app_exception_handler should return JSONResponse with error dict."""
        from app.core.error_handlers import app_exception_handler
        from app.core.exceptions import ValidationError
        from fastapi import Request
        
        # Create mock request
        request = Mock(spec=Request)
        request.url.path = "/test"
        request.method = "POST"
        
        exc = ValidationError(message="Test error", field="test_field")
        
        response = await app_exception_handler(request, exc)
        
        assert response.status_code == 400  # BAD_REQUEST
        assert "error" in response.body.decode()
    
    @pytest.mark.asyncio
    async def test_integrity_error_handler_translates_error(self):
        """integrity_error_handler should translate IntegrityError to custom exception."""
        from app.core.error_handlers import integrity_error_handler
        from fastapi import Request
        
        request = Mock(spec=Request)
        request.url.path = "/test"
        request.method = "POST"
        
        orig_error = Mock()
        orig_error.__str__ = lambda self: "foreign key constraint"
        
        exc = IntegrityError(statement="", params={}, orig=orig_error)
        
        response = await integrity_error_handler(request, exc)
        
        assert response.status_code == 400  # BAD_REQUEST
        assert "error" in response.body.decode()
        assert "correlation_id" in response.body.decode()


class TestCorrelationIDPropagation:
    """Test that correlation IDs are properly propagated through error handling."""
    
    def test_correlation_id_propagates_through_translation(self):
        """Correlation ID should be preserved when translating errors."""
        test_id = str(uuid.uuid4())
        
        exc = OperationalError(statement="", params={}, orig=None)
        result = translate_db_error(exc, correlation_id=test_id)
        
        assert result.correlation_id == test_id
    
    def test_parsed_integrity_error_has_correlation_id(self):
        """Parsed integrity errors should have correlation IDs."""
        orig_error = Mock()
        orig_error.__str__ = lambda self: "foreign key constraint"
        
        exc = IntegrityError(statement="", params={}, orig=orig_error)
        result = parse_integrity_error(exc)
        
        assert result.correlation_id is not None
        assert len(result.correlation_id) > 0
