"""
Aggressive failure-oriented tests for validation layer.

These tests are designed to INTENTIONALLY FAIL and expose weaknesses in validation.
Tests must NEVER be modified to pass - only the implementation code should be updated.

Test Categories:
1. Invalid Data - Malformed inputs, wrong types, invalid formats
2. Missing Dependencies - NULL values, missing foreign keys, missing config
3. Edge Cases - Boundary values, special characters, precision issues
"""

import pytest
import uuid
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, DataError

from app.models.models import User, Document, Chunk, Summary
from app.core.validators import (
    validate_uuid,
    validate_email,
    validate_file_size,
    validate_mime_type,
    validate_vector_dimension,
    validate_jsonb_structure,
    validate_positive_integer,
    validate_string_length,
    validate_enum_value,
)
from app.core.exceptions import (
    ValidationError,
    InvalidUUIDError,
    InvalidEmailError,
    InvalidVectorDimensionError,
    InvalidFileError,
)


pytestmark = [pytest.mark.integration, pytest.mark.database]


class TestInvalidUUIDs:
    """Test that malformed UUIDs are properly rejected."""
    
    def test_validate_uuid_with_invalid_string(self):
        """Malformed UUID string should raise InvalidUUIDError."""
        with pytest.raises(InvalidUUIDError) as exc_info:
            validate_uuid("not-a-uuid", "test_field")
        
        assert "test_field" in str(exc_info.value)
    
    def test_validate_uuid_with_integer(self):
        """Integer value should raise InvalidUUIDError."""
        with pytest.raises(InvalidUUIDError):
            validate_uuid(12345, "test_field")
    
    def test_validate_uuid_with_none(self):
        """None value should raise InvalidUUIDError."""
        with pytest.raises(InvalidUUIDError):
            validate_uuid(None, "test_field")
    
    def test_validate_uuid_with_empty_string(self):
        """Empty string should raise InvalidUUIDError."""
        with pytest.raises(InvalidUUIDError):
            validate_uuid("", "test_field")
    
    def test_validate_uuid_with_partial_uuid(self):
        """Partial UUID should raise InvalidUUIDError."""
        with pytest.raises(InvalidUUIDError):
            validate_uuid("123e4567-e89b-12d3", "test_field")


class TestInvalidEmails:
    """Test that invalid email formats are properly rejected."""
    
    def test_validate_email_without_at_symbol(self):
        """Email without @ should raise InvalidEmailError."""
        with pytest.raises(InvalidEmailError):
            validate_email("invalidemail.com")
    
    def test_validate_email_without_domain(self):
        """Email without domain should raise InvalidEmailError."""
        with pytest.raises(InvalidEmailError):
            validate_email("user@")
    
    def test_validate_email_without_tld(self):
        """Email without TLD should raise InvalidEmailError."""
        with pytest.raises(InvalidEmailError):
            validate_email("user@domain")
    
    def test_validate_email_with_spaces(self):
        """Email with spaces should raise InvalidEmailError."""
        with pytest.raises(InvalidEmailError):
            validate_email("user name@domain.com")
    
    def test_validate_email_with_multiple_at_symbols(self):
        """Email with multiple @ symbols should raise InvalidEmailError."""
        with pytest.raises(InvalidEmailError):
            validate_email("user@@domain.com")
    
    def test_validate_email_empty_string(self):
        """Empty email should raise InvalidEmailError."""
        with pytest.raises(InvalidEmailError):
            validate_email("")
    
    def test_validate_email_none(self):
        """None email should raise InvalidEmailError."""
        with pytest.raises(InvalidEmailError):
            validate_email(None)


class TestInvalidNumericalValues:
    """Test that negative/zero values are properly rejected for positive-only fields."""
    
    async def test_document_with_negative_file_size(self, db_session: AsyncSession, sample_user):
        """Document with negative file_size should raise IntegrityError."""
        document = Document(
            user_id=sample_user.id,
            filename="test.pdf",
            file_path="/test.pdf",
            file_size=-1000,  # NEGATIVE
            content_hash="x" * 64,
            mime_type="application/pdf",
            processing_status="pending",
        )
        
        db_session.add(document)
        
        with pytest.raises((IntegrityError, DataError)) as exc_info:
            await db_session.flush()
        
        error_msg = str(exc_info.value).lower()
        assert "check" in error_msg or "constraint" in error_msg or "violates" in error_msg
    
    async def test_document_with_zero_file_size(self, db_session: AsyncSession, sample_user):
        """Document with zero file_size should raise IntegrityError."""
        document = Document(
            user_id=sample_user.id,
            filename="test.pdf",
            file_path="/test.pdf",
            file_size=0,  # ZERO
            content_hash="y" * 64,
            mime_type="application/pdf",
            processing_status="pending",
        )
        
        db_session.add(document)
        
        with pytest.raises((IntegrityError, DataError)) as exc_info:
            await db_session.flush()
        
        error_msg = str(exc_info.value).lower()
        assert "check" in error_msg or "constraint" in error_msg or "violates" in error_msg
    
    async def test_chunk_with_negative_token_count(self, db_session: AsyncSession, sample_document):
        """Chunk with negative token_count should raise IntegrityError."""
        embedding = np.random.rand(384).tolist()
        
        chunk = Chunk(
            document_id=sample_document.id,
            content="Test content",
            embedding=embedding,
            chunk_index=100,
            token_count=-50,  # NEGATIVE
        )
        
        db_session.add(chunk)
        
        with pytest.raises((IntegrityError, DataError)) as exc_info:
            await db_session.flush()
        
        error_msg = str(exc_info.value).lower()
        assert "check" in error_msg or "constraint" in error_msg or "violates" in error_msg
    
    async def test_chunk_with_zero_token_count(self, db_session: AsyncSession, sample_document):
        """Chunk with zero token_count should raise IntegrityError."""
        embedding = np.random.rand(384).tolist()
        
        chunk = Chunk(
            document_id=sample_document.id,
            content="Test content",
            embedding=embedding,
            chunk_index=101,
            token_count=0,  # ZERO
        )
        
        db_session.add(chunk)
        
        with pytest.raises((IntegrityError, DataError)) as exc_info:
            await db_session.flush()
        
        error_msg = str(exc_info.value).lower()
        assert "check" in error_msg or "constraint" in error_msg or "violates" in error_msg
    
    def test_validate_positive_integer_with_negative(self):
        """Negative integer should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_positive_integer(-5, "test_field")
        
        assert "test_field" in str(exc_info.value)
    
    def test_validate_positive_integer_with_zero_not_allowed(self):
        """Zero should raise ValidationError when not allowed."""
        with pytest.raises(ValidationError):
            validate_positive_integer(0, "test_field", allow_zero=False)
    
    def test_validate_positive_integer_with_float(self):
        """Float value should raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_positive_integer(5.5, "test_field")


class TestInvalidEnumValues:
    """Test that invalid enum values are properly rejected."""
    
    async def test_document_with_invalid_processing_status(self, db_session: AsyncSession, sample_user):
        """Document with invalid processing_status should raise error."""
        document = Document(
            user_id=sample_user.id,
            filename="test.pdf",
            file_path="/test.pdf",
            file_size=1024,
            content_hash="z" * 64,
            mime_type="application/pdf",
            processing_status="INVALID_STATUS",  # INVALID
        )
        
        db_session.add(document)
        
        with pytest.raises((IntegrityError, DataError)) as exc_info:
            await db_session.flush()
        
        error_msg = str(exc_info.value).lower()
        assert "check" in error_msg or "constraint" in error_msg or "violates" in error_msg
    
    async def test_summary_with_invalid_type(self, db_session: AsyncSession, sample_document, sample_user):
        """Summary with invalid summary_type should raise error."""
        summary = Summary(
            document_id=sample_document.id,
            user_id=sample_user.id,
            summary_text="Test summary",
            summary_type="INVALID_TYPE",  # INVALID
            model_name="test-model",
            chunk_count=5,
        )
        
        db_session.add(summary)
        
        with pytest.raises((IntegrityError, DataError)) as exc_info:
            await db_session.flush()
        
        error_msg = str(exc_info.value).lower()
        assert "check" in error_msg or "constraint" in error_msg or "violates" in error_msg
    
    def test_validate_enum_value_with_invalid_value(self):
        """Invalid enum value should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_enum_value("invalid", "status", ["pending", "processing", "completed"])
        
        assert "status" in str(exc_info.value)
        assert "invalid" in str(exc_info.value).lower()


class TestInvalidVectorDimensions:
    """Test that incorrect vector dimensions are properly rejected."""
    
    async def test_chunk_with_wrong_dimension_vector(self, db_session: AsyncSession, sample_document):
        """Chunk with wrong embedding dimension should raise error."""
        from sqlalchemy.exc import StatementError
        
        wrong_embedding = np.random.rand(256).tolist()  # WRONG: should be 384
        
        chunk = Chunk(
            document_id=sample_document.id,
            content="Test content",
            embedding=wrong_embedding,
            chunk_index=200,
            token_count=10,
        )
        
        db_session.add(chunk)
        
        with pytest.raises((IntegrityError, DataError, StatementError, ValueError)) as exc_info:
            await db_session.flush()
        
        error_msg = str(exc_info.value).lower()
        assert "dimension" in error_msg or "vector" in error_msg or "expected" in error_msg
    
    async def test_chunk_with_oversized_vector(self, db_session: AsyncSession, sample_document):
        """Chunk with oversized embedding should raise error."""
        from sqlalchemy.exc import StatementError
        
        oversized_embedding = np.random.rand(512).tolist()  # TOO LARGE
        
        chunk = Chunk(
            document_id=sample_document.id,
            content="Test content",
            embedding=oversized_embedding,
            chunk_index=201,
            token_count=10,
        )
        
        db_session.add(chunk)
        
        with pytest.raises((IntegrityError, DataError, StatementError, ValueError)) as exc_info:
            await db_session.flush()
        
        error_msg = str(exc_info.value).lower()
        assert "dimension" in error_msg or "vector" in error_msg or "expected" in error_msg
    
    async def test_chunk_with_undersized_vector(self, db_session: AsyncSession, sample_document):
        """Chunk with undersized embedding should raise error."""
        from sqlalchemy.exc import StatementError
        
        undersized_embedding = np.random.rand(128).tolist()  # TOO SMALL
        
        chunk = Chunk(
            document_id=sample_document.id,
            content="Test content",
            embedding=undersized_embedding,
            chunk_index=202,
            token_count=10,
        )
        
        db_session.add(chunk)
        
        with pytest.raises((IntegrityError, DataError, StatementError, ValueError)) as exc_info:
            await db_session.flush()
        
        error_msg = str(exc_info.value).lower()
        assert "dimension" in error_msg or "vector" in error_msg or "expected" in error_msg
    
    def test_validate_vector_dimension_with_wrong_size(self):
        """Vector with wrong dimension should raise InvalidVectorDimensionError."""
        embedding = [0.1] * 256  # Wrong size
        
        with pytest.raises(InvalidVectorDimensionError) as exc_info:
            validate_vector_dimension(embedding, expected_dimension=384)
        
        assert "384" in str(exc_info.value)
        assert "256" in str(exc_info.value)
    
    def test_validate_vector_dimension_with_non_list(self):
        """Non-list embedding should raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_vector_dimension("not a list", expected_dimension=384)


class TestInvalidFileData:
    """Test that invalid file data is properly rejected."""
    
    def test_validate_file_size_negative(self):
        """Negative file size should raise InvalidFileError."""
        with pytest.raises(InvalidFileError) as exc_info:
            validate_file_size(-1000, max_size=1024*1024, filename="test.pdf")
        
        assert "test.pdf" in str(exc_info.value) or "file" in str(exc_info.value).lower()
    
    def test_validate_file_size_zero(self):
        """Zero file size should raise InvalidFileError."""
        with pytest.raises(InvalidFileError):
            validate_file_size(0, max_size=1024*1024, filename="test.pdf")
    
    def test_validate_file_size_exceeds_maximum(self):
        """File size exceeding maximum should raise InvalidFileError."""
        max_size = 10 * 1024 * 1024  # 10MB
        oversized = 20 * 1024 * 1024  # 20MB
        
        with pytest.raises(InvalidFileError) as exc_info:
            validate_file_size(oversized, max_size=max_size, filename="large.pdf")
        
        assert "exceeds" in str(exc_info.value).lower()
    
    def test_validate_mime_type_invalid(self):
        """Invalid MIME type should raise InvalidFileError."""
        with pytest.raises(InvalidFileError) as exc_info:
            validate_mime_type("application/exe", filename="virus.exe")
        
        assert "not allowed" in str(exc_info.value).lower()
    
    def test_validate_mime_type_empty(self):
        """Empty MIME type should raise InvalidFileError."""
        with pytest.raises(InvalidFileError):
            validate_mime_type("", filename="test.pdf")
    
    def test_validate_mime_type_none(self):
        """None MIME type should raise InvalidFileError."""
        with pytest.raises(InvalidFileError):
            validate_mime_type(None, filename="test.pdf")


class TestInvalidJSONBStructures:
    """Test that malformed JSONB structures are properly rejected."""
    
    def test_validate_jsonb_with_non_dict(self):
        """Non-dictionary JSONB should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_jsonb_structure("not a dict")
        
        assert "dictionary" in str(exc_info.value).lower()
    
    def test_validate_jsonb_with_list(self):
        """List JSONB should raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_jsonb_structure([1, 2, 3])
    
    def test_validate_jsonb_missing_required_keys(self):
        """JSONB missing required keys should raise ValidationError."""
        data = {"key1": "value1"}
        
        with pytest.raises(ValidationError) as exc_info:
            validate_jsonb_structure(data, required_keys=["key1", "key2"])
        
        assert "missing" in str(exc_info.value).lower()
        assert "key2" in str(exc_info.value).lower()
    
    def test_validate_jsonb_with_invalid_keys(self):
        """JSONB with invalid keys should raise ValidationError."""
        data = {"key1": "value1", "invalid_key": "value"}
        
        with pytest.raises(ValidationError) as exc_info:
            validate_jsonb_structure(data, allowed_keys=["key1", "key2"])
        
        assert "invalid" in str(exc_info.value).lower()


class TestInvalidStringLengths:
    """Test that string length violations are properly rejected."""
    
    def test_validate_string_length_too_short(self):
        """String shorter than minimum should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            validate_string_length("ab", "name", min_length=3)
        
        assert "at least" in str(exc_info.value).lower()
    
    def test_validate_string_length_too_long(self):
        """String longer than maximum should raise ValidationError."""
        long_string = "a" * 300
        
        with pytest.raises(ValidationError) as exc_info:
            validate_string_length(long_string, "description", max_length=255)
        
        assert "exceed" in str(exc_info.value).lower()
    
    def test_validate_string_length_with_non_string(self):
        """Non-string value should raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_string_length(12345, "name")


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    async def test_chunk_with_start_page_greater_than_end_page(
        self, db_session: AsyncSession, sample_document
    ):
        """Chunk with start_page > end_page should raise error."""
        embedding = np.random.rand(384).tolist()
        
        chunk = Chunk(
            document_id=sample_document.id,
            content="Test content",
            embedding=embedding,
            chunk_index=300,
            start_page=10,
            end_page=5,  # INVALID: end < start
            token_count=10,
        )
        
        db_session.add(chunk)
        
        with pytest.raises((IntegrityError, DataError)) as exc_info:
            await db_session.flush()
        
        error_msg = str(exc_info.value).lower()
        assert "check" in error_msg or "constraint" in error_msg or "violates" in error_msg
    
    async def test_user_with_extremely_long_email(self, db_session: AsyncSession):
        """User with extremely long email should be handled properly."""
        from sqlalchemy.exc import DBAPIError
        
        # Email longer than typical database field
        long_email = "a" * 300 + "@example.com"
        
        user = User(
            email=long_email,
            password_hash="hashed",
        )
        
        db_session.add(user)
        
        # Should either raise validation error or database error
        with pytest.raises((ValidationError, IntegrityError, DataError, DBAPIError)):
            await db_session.flush()
    
    async def test_document_with_negative_page_count(self, db_session: AsyncSession, sample_user):
        """Document with negative page_count should raise error."""
        document = Document(
            user_id=sample_user.id,
            filename="test.pdf",
            file_path="/test.pdf",
            file_size=1024,
            content_hash="w" * 64,
            mime_type="application/pdf",
            processing_status="pending",
            page_count=-10,  # NEGATIVE
        )
        
        db_session.add(document)
        
        with pytest.raises((IntegrityError, DataError)) as exc_info:
            await db_session.flush()
        
        error_msg = str(exc_info.value).lower()
        assert "check" in error_msg or "constraint" in error_msg or "violates" in error_msg
