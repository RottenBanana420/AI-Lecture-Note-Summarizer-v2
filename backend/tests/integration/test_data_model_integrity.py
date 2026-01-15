"""
Integration tests for data model integrity.

These tests are designed to INTENTIONALLY FAIL and expose weaknesses in the data model.
Tests must NEVER be modified to pass - only the code/schema should be updated.
"""

import pytest
import uuid
import numpy as np
from sqlalchemy.exc import IntegrityError, DataError
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import User, Document, Chunk, Summary


pytestmark = [pytest.mark.integration, pytest.mark.database]


class TestMissingRelations:
    """Test that missing foreign key relations are properly rejected."""
    
    async def test_chunk_without_document_raises_foreign_key_error(self, db_session: AsyncSession):
        """Attempt to create chunk with non-existent document_id."""
        non_existent_id = uuid.uuid4()
        embedding = np.random.rand(384).tolist()
        
        chunk = Chunk(
            document_id=non_existent_id,
            content="Test content",
            embedding=embedding,
            chunk_index=0,
            token_count=10,
        )
        
        db_session.add(chunk)
        
        with pytest.raises(IntegrityError) as exc_info:
            await db_session.flush()
        
        assert "foreign key constraint" in str(exc_info.value).lower()
    
    async def test_document_without_user_raises_foreign_key_error(self, db_session: AsyncSession):
        """Attempt to create document with non-existent user_id."""
        non_existent_id = uuid.uuid4()
        
        document = Document(
            user_id=non_existent_id,
            filename="test.pdf",
            file_path="/test.pdf",
            file_size=1024,
            content_hash="a" * 64,
            mime_type="application/pdf",
            processing_status="pending",
        )
        
        db_session.add(document)
        
        with pytest.raises(IntegrityError) as exc_info:
            await db_session.flush()
        
        assert "foreign key constraint" in str(exc_info.value).lower()
    
    async def test_summary_without_document_raises_foreign_key_error(self, db_session: AsyncSession, sample_user):
        """Attempt to create summary with non-existent document_id."""
        non_existent_id = uuid.uuid4()
        
        summary = Summary(
            document_id=non_existent_id,
            user_id=sample_user.id,
            summary_text="Test summary",
            summary_type="abstractive",
            model_name="test-model",
            chunk_count=5,
        )
        
        db_session.add(summary)
        
        with pytest.raises(IntegrityError) as exc_info:
            await db_session.flush()
        
        assert "foreign key constraint" in str(exc_info.value).lower()
    
    async def test_summary_without_user_raises_foreign_key_error(self, db_session: AsyncSession, sample_document):
        """Attempt to create summary with non-existent user_id."""
        non_existent_id = uuid.uuid4()
        
        summary = Summary(
            document_id=sample_document.id,
            user_id=non_existent_id,
            summary_text="Test summary",
            summary_type="abstractive",
            model_name="test-model",
            chunk_count=5,
        )
        
        db_session.add(summary)
        
        with pytest.raises(IntegrityError) as exc_info:
            await db_session.flush()
        
        assert "foreign key constraint" in str(exc_info.value).lower()


class TestInvalidReferences:
    """Test that invalid data types and NULL values are properly rejected."""
    
    async def test_chunk_with_null_document_id_raises_error(self, db_session: AsyncSession):
        """Attempt to create chunk with NULL document_id."""
        embedding = np.random.rand(384).tolist()
        
        chunk = Chunk(
            document_id=None,
            content="Test content",
            embedding=embedding,
            chunk_index=0,
            token_count=10,
        )
        
        db_session.add(chunk)
        
        with pytest.raises(IntegrityError) as exc_info:
            await db_session.flush()
        
        assert "not null" in str(exc_info.value).lower() or "null value" in str(exc_info.value).lower()
    
    async def test_document_with_null_user_id_raises_error(self, db_session: AsyncSession):
        """Attempt to create document with NULL user_id."""
        document = Document(
            user_id=None,
            filename="test.pdf",
            file_path="/test.pdf",
            file_size=1024,
            content_hash="a" * 64,
            mime_type="application/pdf",
            processing_status="pending",
        )
        
        db_session.add(document)
        
        with pytest.raises(IntegrityError) as exc_info:
            await db_session.flush()
        
        assert "not null" in str(exc_info.value).lower() or "null value" in str(exc_info.value).lower()
    
    async def test_user_with_null_email_raises_error(self, db_session: AsyncSession):
        """Attempt to create user with NULL email."""
        user = User(
            email=None,
            password_hash="hashed_password",
        )
        
        db_session.add(user)
        
        with pytest.raises(IntegrityError) as exc_info:
            await db_session.flush()
        
        assert "not null" in str(exc_info.value).lower() or "null value" in str(exc_info.value).lower()
    
    async def test_chunk_with_null_embedding_raises_error(self, db_session: AsyncSession, sample_document):
        """Attempt to create chunk with NULL embedding."""
        chunk = Chunk(
            document_id=sample_document.id,
            content="Test content",
            embedding=None,
            chunk_index=0,
            token_count=10,
        )
        
        db_session.add(chunk)
        
        with pytest.raises(IntegrityError) as exc_info:
            await db_session.flush()
        
        assert "not null" in str(exc_info.value).lower() or "null value" in str(exc_info.value).lower()


class TestDuplicateRecords:
    """Test that duplicate records are properly rejected."""
    
    async def test_duplicate_email_raises_unique_violation(self, db_session: AsyncSession, sample_user):
        """Attempt to create two users with same email."""
        duplicate_user = User(
            email=sample_user.email,  # Same email
            password_hash="different_hash",
        )
        
        db_session.add(duplicate_user)
        
        with pytest.raises(IntegrityError) as exc_info:
            await db_session.flush()
        
        assert "unique" in str(exc_info.value).lower() or "duplicate" in str(exc_info.value).lower()
    
    async def test_duplicate_chunk_index_raises_unique_violation(self, db_session: AsyncSession, sample_chunk):
        """Attempt to create two chunks with same (document_id, chunk_index)."""
        embedding = np.random.rand(384).tolist()
        
        duplicate_chunk = Chunk(
            document_id=sample_chunk.document_id,
            chunk_index=sample_chunk.chunk_index,  # Same index
            content="Different content",
            embedding=embedding,
            token_count=15,
        )
        
        db_session.add(duplicate_chunk)
        
        with pytest.raises(IntegrityError) as exc_info:
            await db_session.flush()
        
        assert "unique" in str(exc_info.value).lower() or "duplicate" in str(exc_info.value).lower()
    
    async def test_duplicate_user_content_hash_raises_unique_violation(
        self, db_session: AsyncSession, sample_document
    ):
        """Attempt to create two documents with same (user_id, content_hash)."""
        duplicate_document = Document(
            user_id=sample_document.user_id,
            content_hash=sample_document.content_hash,  # Same hash
            filename="different_name.pdf",
            file_path="/different_path.pdf",
            file_size=2048,
            mime_type="application/pdf",
            processing_status="pending",
        )
        
        db_session.add(duplicate_document)
        
        with pytest.raises(IntegrityError) as exc_info:
            await db_session.flush()
        
        assert "unique" in str(exc_info.value).lower() or "duplicate" in str(exc_info.value).lower()


class TestDataIntegrityConstraints:
    """Test that check constraints are properly enforced."""
    
    async def test_invalid_processing_status_raises_error(self, db_session: AsyncSession, sample_user):
        """Attempt to set processing_status to invalid value."""
        document = Document(
            user_id=sample_user.id,
            filename="test.pdf",
            file_path="/test.pdf",
            file_size=1024,
            content_hash="b" * 64,
            mime_type="application/pdf",
            processing_status="invalid_status",  # Invalid
        )
        
        db_session.add(document)
        
        with pytest.raises((IntegrityError, DataError)) as exc_info:
            await db_session.flush()
        
        error_msg = str(exc_info.value).lower()
        assert "check" in error_msg or "constraint" in error_msg or "violates" in error_msg
    
    async def test_negative_file_size_raises_error(self, db_session: AsyncSession, sample_user):
        """Attempt to create document with negative file_size."""
        document = Document(
            user_id=sample_user.id,
            filename="test.pdf",
            file_path="/test.pdf",
            file_size=-1024,  # Negative
            content_hash="c" * 64,
            mime_type="application/pdf",
            processing_status="pending",
        )
        
        db_session.add(document)
        
        with pytest.raises((IntegrityError, DataError)) as exc_info:
            await db_session.flush()
        
        error_msg = str(exc_info.value).lower()
        assert "check" in error_msg or "constraint" in error_msg or "violates" in error_msg
    
    async def test_zero_file_size_raises_error(self, db_session: AsyncSession, sample_user):
        """Attempt to create document with zero file_size."""
        document = Document(
            user_id=sample_user.id,
            filename="test.pdf",
            file_path="/test.pdf",
            file_size=0,  # Zero
            content_hash="d" * 64,
            mime_type="application/pdf",
            processing_status="pending",
        )
        
        db_session.add(document)
        
        with pytest.raises((IntegrityError, DataError)) as exc_info:
            await db_session.flush()
        
        error_msg = str(exc_info.value).lower()
        assert "check" in error_msg or "constraint" in error_msg or "violates" in error_msg
    
    async def test_invalid_page_order_raises_error(self, db_session: AsyncSession, sample_document):
        """Attempt to create chunk with start_page > end_page."""
        embedding = np.random.rand(384).tolist()
        
        chunk = Chunk(
            document_id=sample_document.id,
            content="Test content",
            embedding=embedding,
            chunk_index=5,
            start_page=10,
            end_page=5,  # end_page < start_page
            token_count=10,
        )
        
        db_session.add(chunk)
        
        with pytest.raises((IntegrityError, DataError)) as exc_info:
            await db_session.flush()
        
        error_msg = str(exc_info.value).lower()
        assert "check" in error_msg or "constraint" in error_msg or "violates" in error_msg
    
    async def test_negative_token_count_raises_error(self, db_session: AsyncSession, sample_document):
        """Attempt to create chunk with negative token_count."""
        embedding = np.random.rand(384).tolist()
        
        chunk = Chunk(
            document_id=sample_document.id,
            content="Test content",
            embedding=embedding,
            chunk_index=6,
            token_count=-10,  # Negative
        )
        
        db_session.add(chunk)
        
        with pytest.raises((IntegrityError, DataError)) as exc_info:
            await db_session.flush()
        
        error_msg = str(exc_info.value).lower()
        assert "check" in error_msg or "constraint" in error_msg or "violates" in error_msg
    
    async def test_zero_token_count_raises_error(self, db_session: AsyncSession, sample_document):
        """Attempt to create chunk with zero token_count."""
        embedding = np.random.rand(384).tolist()
        
        chunk = Chunk(
            document_id=sample_document.id,
            content="Test content",
            embedding=embedding,
            chunk_index=7,
            token_count=0,  # Zero
        )
        
        db_session.add(chunk)
        
        with pytest.raises((IntegrityError, DataError)) as exc_info:
            await db_session.flush()
        
        error_msg = str(exc_info.value).lower()
        assert "check" in error_msg or "constraint" in error_msg or "violates" in error_msg
    
    async def test_invalid_summary_type_raises_error(
        self, db_session: AsyncSession, sample_document, sample_user
    ):
        """Attempt to set summary_type to invalid value."""
        summary = Summary(
            document_id=sample_document.id,
            user_id=sample_user.id,
            summary_text="Test summary",
            summary_type="invalid_type",  # Invalid
            model_name="test-model",
            chunk_count=5,
        )
        
        db_session.add(summary)
        
        with pytest.raises((IntegrityError, DataError)) as exc_info:
            await db_session.flush()
        
        error_msg = str(exc_info.value).lower()
        assert "check" in error_msg or "constraint" in error_msg or "violates" in error_msg
    
    async def test_negative_chunk_count_in_summary_raises_error(
        self, db_session: AsyncSession, sample_document, sample_user
    ):
        """Attempt to create summary with negative chunk_count."""
        summary = Summary(
            document_id=sample_document.id,
            user_id=sample_user.id,
            summary_text="Test summary",
            summary_type="abstractive",
            model_name="test-model",
            chunk_count=-5,  # Negative
        )
        
        db_session.add(summary)
        
        with pytest.raises((IntegrityError, DataError)) as exc_info:
            await db_session.flush()
        
        error_msg = str(exc_info.value).lower()
        assert "check" in error_msg or "constraint" in error_msg or "violates" in error_msg
    
    async def test_zero_chunk_count_in_summary_raises_error(
        self, db_session: AsyncSession, sample_document, sample_user
    ):
        """Attempt to create summary with zero chunk_count."""
        summary = Summary(
            document_id=sample_document.id,
            user_id=sample_user.id,
            summary_text="Test summary",
            summary_type="abstractive",
            model_name="test-model",
            chunk_count=0,  # Zero
        )
        
        db_session.add(summary)
        
        with pytest.raises((IntegrityError, DataError)) as exc_info:
            await db_session.flush()
        
        error_msg = str(exc_info.value).lower()
        assert "check" in error_msg or "constraint" in error_msg or "violates" in error_msg


class TestCascadeOperations:
    """Test that cascade delete operations work correctly."""
    
    async def test_delete_user_cascades_to_documents(
        self, db_session: AsyncSession, sample_user, sample_document
    ):
        """Deleting user should delete all their documents."""
        user_id = sample_user.id
        document_id = sample_document.id
        
        # Delete user
        await db_session.delete(sample_user)
        await db_session.flush()
        
        # Verify document is also deleted
        from sqlalchemy import select
        result = await db_session.execute(select(Document).where(Document.id == document_id))
        deleted_document = result.scalar_one_or_none()
        
        assert deleted_document is None, "Document should be deleted when user is deleted"
    
    async def test_delete_document_cascades_to_chunks(
        self, db_session: AsyncSession, sample_document, sample_chunk
    ):
        """Deleting document should delete all its chunks."""
        document_id = sample_document.id
        chunk_id = sample_chunk.id
        
        # Delete document
        await db_session.delete(sample_document)
        await db_session.flush()
        
        # Verify chunk is also deleted
        from sqlalchemy import select
        result = await db_session.execute(select(Chunk).where(Chunk.id == chunk_id))
        deleted_chunk = result.scalar_one_or_none()
        
        assert deleted_chunk is None, "Chunk should be deleted when document is deleted"
    
    async def test_delete_document_cascades_to_summaries(
        self, db_session: AsyncSession, sample_document, sample_summary
    ):
        """Deleting document should delete all its summaries."""
        document_id = sample_document.id
        summary_id = sample_summary.id
        
        # Delete document
        await db_session.delete(sample_document)
        await db_session.flush()
        
        # Verify summary is also deleted
        from sqlalchemy import select
        result = await db_session.execute(select(Summary).where(Summary.id == summary_id))
        deleted_summary = result.scalar_one_or_none()
        
        assert deleted_summary is None, "Summary should be deleted when document is deleted"
    
    async def test_delete_user_cascades_to_summaries(
        self, db_session: AsyncSession, sample_user, sample_summary
    ):
        """Deleting user should delete all their summaries."""
        user_id = sample_user.id
        summary_id = sample_summary.id
        
        # Delete user
        await db_session.delete(sample_user)
        await db_session.flush()
        
        # Verify summary is also deleted
        from sqlalchemy import select
        result = await db_session.execute(select(Summary).where(Summary.id == summary_id))
        deleted_summary = result.scalar_one_or_none()
        
        assert deleted_summary is None, "Summary should be deleted when user is deleted"


class TestJSONBValidation:
    """Test JSONB field operations."""
    
    async def test_valid_jsonb_structure_is_accepted(self, db_session: AsyncSession):
        """Valid JSON should be accepted in metadata fields."""
        user = User(
            email="jsonb_test@example.com",
            password_hash="hashed",
            meta_data={"key": "value", "nested": {"data": [1, 2, 3]}},
        )
        
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)
        
        assert user.meta_data == {"key": "value", "nested": {"data": [1, 2, 3]}}
    
    async def test_empty_jsonb_is_accepted(self, db_session: AsyncSession):
        """Empty dict should be accepted as default."""
        user = User(
            email="empty_jsonb@example.com",
            password_hash="hashed",
        )
        
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)
        
        assert user.meta_data == {}
    
    async def test_jsonb_query_with_missing_key_returns_null(self, db_session: AsyncSession, sample_user):
        """Query JSONB field that doesn't exist should return NULL."""
        from sqlalchemy import select
        
        # Query for a key that doesn't exist
        result = await db_session.execute(
            select(User.meta_data["nonexistent_key"]).where(User.id == sample_user.id)
        )
        value = result.scalar_one_or_none()
        
        assert value is None


class TestVectorOperations:
    """Test vector embedding operations."""
    
    async def test_chunk_with_invalid_vector_dimension_raises_error(
        self, db_session: AsyncSession, sample_document
    ):
        """Attempt to insert vector with wrong dimensions."""
        from sqlalchemy.exc import StatementError
        
        wrong_embedding = np.random.rand(256).tolist()  # Wrong dimension (should be 384)
        
        chunk = Chunk(
            document_id=sample_document.id,
            content="Test content",
            embedding=wrong_embedding,
            chunk_index=10,
            token_count=10,
        )
        
        db_session.add(chunk)
        
        with pytest.raises((IntegrityError, DataError, StatementError, ValueError)) as exc_info:
            await db_session.flush()
        
        error_msg = str(exc_info.value).lower()
        assert "dimension" in error_msg or "vector" in error_msg or "expected" in error_msg
    
    async def test_vector_similarity_search_returns_results(
        self, db_session: AsyncSession, sample_document
    ):
        """Perform cosine similarity search on embeddings."""
        # Create multiple chunks with embeddings
        chunks = []
        for i in range(5):
            embedding = np.random.rand(384).tolist()
            chunk = Chunk(
                document_id=sample_document.id,
                content=f"Test content {i}",
                embedding=embedding,
                chunk_index=i + 20,
                token_count=10,
            )
            chunks.append(chunk)
            db_session.add(chunk)
        
        await db_session.flush()
        
        # Perform similarity search
        query_embedding = np.random.rand(384).tolist()
        
        from sqlalchemy import select, func
        
        # Use pgvector's cosine distance operator
        result = await db_session.execute(
            select(Chunk)
            .where(Chunk.document_id == sample_document.id)
            .order_by(Chunk.embedding.cosine_distance(query_embedding))
            .limit(3)
        )
        
        similar_chunks = result.scalars().all()
        
        assert len(similar_chunks) > 0, "Should return similar chunks"
        assert len(similar_chunks) <= 3, "Should respect limit"
    
    async def test_valid_vector_embedding_is_stored_correctly(
        self, db_session: AsyncSession, sample_chunk
    ):
        """Valid 384-dimensional vector should be stored and retrieved correctly."""
        await db_session.refresh(sample_chunk)
        
        assert sample_chunk.embedding is not None
        assert len(sample_chunk.embedding) == 384
