"""Shared test fixtures and configuration.

This module provides pytest fixtures for database testing with proper isolation.

Test Suite Organization
=======================

Integration Tests (tests/integration/):
- test_data_model_integrity.py: Database schema constraints (FK, unique, check constraints)  
- test_error_handling.py: Exception translation, retry logic, transient error detection
- test_validation_failures.py: Validator functions for inputs (UUID, email, files, etc.)

Unit Tests (tests/unit/):
- test_pdf_extraction.py: PDF text extraction logic
- test_pdf_normalization.py: Text normalization (whitespace, unicode)
- test_pdf_cleaning.py: Header/footer removal, noise removal
- test_pdf_segmentation.py: Text segmentation and chunking
- test_performance.py: Performance benchmarks and memory usage
- test_stress.py: Stress testing and edge cases

Fixture Scopes:
- session: Created once per test session (test_engine, event_loop)
- function: Created for each test function (db_session, sample_* fixtures)

Best Practices:
- Use db_session for all database operations to ensure transactional rollback
- Sample fixtures create database records that are automatically cleaned up
- Each test runs in isolation with its own transaction
"""

import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import text
from app.db.session import Base
from app.models.models import User, Document, Chunk, Summary
import numpy as np


# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/lecture_notes_test"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        # Enable pgvector extension
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    
    yield engine
    
    # Drop all tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional database session for tests.
    
    This fixture ensures test isolation by:
    1. Creating a new connection for each test
    2. Starting a transaction before the test
    3. Rolling back the transaction after the test completes
    
    This means all database changes made during a test are automatically
    discarded, ensuring tests don't affect each other.
    
    Scope: function (new session for each test)
    Dependencies: test_engine (session-scoped)
    """
    # Create a connection
    async with test_engine.connect() as connection:
        # Begin a transaction
        async with connection.begin() as transaction:
            # Create session bound to the connection
            TestSessionLocal = async_sessionmaker(
                bind=connection,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            
            async with TestSessionLocal() as session:
                yield session
                # Rollback the transaction after test
                await transaction.rollback()


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqVr/Vf3Hy",  # "password"
        "full_name": "Test User",
        "is_active": True,
        "meta_data": {"preferences": {"theme": "dark"}},
    }


@pytest.fixture
def sample_document_data(sample_user):
    """Sample document data for testing."""
    return {
        "user_id": sample_user.id,
        "filename": "test_lecture.pdf",
        "file_path": "/uploads/test_lecture.pdf",
        "file_size": 1024 * 1024,  # 1MB
        "content_hash": "a" * 64,
        "mime_type": "application/pdf",
        "processing_status": "pending",
        "page_count": 10,
        "word_count": 5000,
        "meta_data": {"title": "Test Lecture", "course": "CS 101"},
    }


@pytest.fixture
def sample_chunk_data(sample_document):
    """Sample chunk data for testing."""
    # Generate a random 384-dimensional vector
    embedding = np.random.rand(384).tolist()
    
    return {
        "document_id": sample_document.id,
        "content": "This is a test chunk of text from the lecture notes.",
        "embedding": embedding,
        "chunk_index": 0,
        "start_page": 1,
        "end_page": 1,
        "token_count": 12,
        "meta_data": {"section": "Introduction"},
    }


@pytest.fixture
def sample_summary_data(sample_document, sample_user):
    """Sample summary data for testing."""
    return {
        "document_id": sample_document.id,
        "user_id": sample_user.id,
        "summary_text": "This is a test summary of the lecture notes.",
        "summary_type": "abstractive",
        "model_name": "gpt-3.5-turbo",
        "model_version": "0613",
        "chunk_count": 5,
        "generation_time_ms": 1500,
        "meta_data": {"confidence_score": 0.95},
    }


@pytest.fixture
async def sample_user(db_session: AsyncSession, sample_user_data):
    """Create a sample user in the database."""
    user = User(**sample_user_data)
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def sample_document(db_session: AsyncSession, sample_user, sample_document_data):
    """Create a sample document in the database."""
    document = Document(**sample_document_data)
    db_session.add(document)
    await db_session.flush()
    await db_session.refresh(document)
    return document


@pytest.fixture
async def sample_chunk(db_session: AsyncSession, sample_document, sample_chunk_data):
    """Create a sample chunk in the database."""
    chunk = Chunk(**sample_chunk_data)
    db_session.add(chunk)
    await db_session.flush()
    await db_session.refresh(chunk)
    return chunk


@pytest.fixture
async def sample_summary(db_session: AsyncSession, sample_document, sample_user, sample_summary_data):
    """Create a sample summary in the database."""
    summary = Summary(**sample_summary_data)
    db_session.add(summary)
    await db_session.flush()
    await db_session.refresh(summary)
    return summary


# ============================================================================
# Summarization Test Fixtures
# ============================================================================

@pytest.fixture
def test_documents():
    """Load test documents from fixtures/test_data directory.
    
    Returns:
        Dictionary mapping document names to their content
    """
    import os
    from pathlib import Path
    
    test_data_dir = Path(__file__).parent / "fixtures" / "test_data"
    documents = {}
    
    document_files = [
        "standard_document.txt",
        "short_document.txt",
        "long_document.txt",
        "empty_document.txt",
        "malformed_document.txt",
        "non_english_document.txt",
    ]
    
    for filename in document_files:
        filepath = test_data_dir / filename
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            # Use filename without extension as key
            key = filename.replace("_document.txt", "")
            documents[key] = content
    
    return documents


@pytest.fixture
def summarization_service():
    """Provide a SummarizationService instance for testing.
    
    This fixture returns the placeholder service that raises NotImplementedError.
    Tests should expect this behavior until actual implementation is added.
    """
    from app.services.summarization_service import SummarizationService
    return SummarizationService()


@pytest.fixture
def quality_metrics():
    """Placeholder fixture for future quality metric calculations.
    
    This will eventually provide functions to calculate:
    - ROUGE scores
    - BERTScore
    - QA-based faithfulness
    - Coverage metrics
    
    For now, returns None to indicate metrics are not yet implemented.
    """
    return None

