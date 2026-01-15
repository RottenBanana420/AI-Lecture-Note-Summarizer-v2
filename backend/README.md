# Backend Application

FastAPI backend for AI Lecture Note Summarizer with PostgreSQL, pgvector, and RAG pipeline.

## Features

### ✅ PDF Processing & Normalization

- **Robust PDF Extraction** using PyMuPDF (primary) and pdfplumber (fallback)
- **Reading Order Preservation** for complex multi-column layouts
- **Advanced Text Normalization** (whitespace, unicode NFC, smart quotes, dashes)
- **Metadata Tracking** (word counts, processing time, success rates, warnings)
- **Graceful Error Recovery** for corrupted or partially extractable documents

### ✅ Data Model & Validation

- **Relational data model** with PostgreSQL + pgvector
- **Comprehensive validation** for all input data
- **Custom exception hierarchy** with correlation IDs
- **Standardized error responses** across all endpoints

### ✅ Error Handling & Resilience

- **Retry logic** with exponential backoff for transient errors
- **Circuit breaker pattern** ready for external services
- **Graceful degradation** under failure conditions
- **Request tracing** via correlation IDs

### ✅ Testing Infrastructure

- **142 tests passing** (97 integration, 45 unit)
- **89% code coverage** for core and service layers
- **TDD approach** - tests never modified, only code
- **Deterministic behavior** - no flaky tests
- **Aggressive failure testing** to ensure robustness
- **Fast feedback loop** - optimized for developer productivity
- **Comprehensive PDF fixtures** covering edge cases (multi-column, encoding, etc.)

## Structure

```text
app/
├── core/              # Core configuration and utilities
│   ├── config.py      # Application configuration
│   ├── exceptions.py  # Custom exception hierarchy
│   ├── error_handlers.py  # FastAPI error handlers
│   └── validators.py  # Reusable validation functions
├── db/                # Database layer
│   ├── session.py     # Database session management
│   └── db_utils.py    # Error handling & retry logic
├── models/            # SQLAlchemy models
│   └── models.py      # User, Document, Chunk, Summary
├── schemas/           # Pydantic schemas
│   └── extraction_result.py  # PDF extraction result schemas
├── repositories/      # Data access layer
├── services/          # Business logic layer
│   ├── pdf_extractor.py  # PDF text extraction service
│   └── pdf_normalizer.py # Text normalization utilities
└── api/               # API endpoints
    └── v1/            # API version 1

tests/
├── integration/       # Integration tests
│   ├── test_data_model_integrity.py      # Data model tests (30 tests)
│   ├── test_validation_failures.py       # Validation tests (43 tests)
│   └── test_error_handling.py            # Error handling tests (24 tests)
├── unit/              # Unit tests
│   ├── test_pdf_extraction.py            # 27 extraction tests
│   └── test_pdf_normalization.py         # 18 normalization tests
├── fixtures/          # Test fixtures
│   ├── pdfs/          # Sample PDF fixtures for testing
│   └── generate_test_pdfs.py  # Fixture generation script
├── conftest.py        # Shared test fixtures
└── pytest.ini         # Testing configuration
```

## Running Tests

```bash
# Run all tests
pytest

# Run specific test suite
pytest tests/unit/test_pdf_extraction.py -v

# Run with coverage
pytest --cov=app --cov-report=term-missing

# Current status: 142 tests passing, 89% coverage
```

## PDF Processing Pipeline

The system uses a multi-strategy approach for text extraction:

1. **PyMuPDF (fitz)**: Primary extraction method for high-performance and coordinate-based block analysis.
2. **pdfplumber**: Fallback method for complex layouts or when PyMuPDF fails to extract structured text.
3. **Normalizer**: Pipeline for cleaning text:
   - Unicode NFC normalization
   - Smart quote & dash normalization
   - Whitespace and paragraph break management

## Error Handling

### Exception Hierarchy

All exceptions inherit from `AppException` with built-in:

- Correlation IDs for request tracing
- ISO 8601 timestamps
- HTTP status code mapping
- Structured error details

**Exception Types:**

- `ValidationError` - Input validation failures
- `DatabaseError` - Database operation failures
- `IntegrityConstraintError` - Constraint violations
- `ResourceNotFoundError` - Entity not found (404)
- `ExternalServiceError` - Third-party service failures

### Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "User-friendly error message",
    "details": {
      "field": "email",
      "reason": "Invalid email format"
    },
    "correlation_id": "uuid-v4",
    "timestamp": "2026-01-15T05:28:46Z"
  }
}
```

## Code Coverage

Current coverage: **89%**

```text
app/core/exceptions.py      91%
app/core/validators.py      80%
app/models/models.py        95%
app/services/pdf_extractor  85%
app/services/pdf_normalizer 83%
app/schemas/extraction_result 98%
```

## Next Steps

- [ ] Implement API endpoints for document upload and processing
- [x] Add PDF processing pipeline with text extraction
- [ ] Integrate AI models for embeddings and summarization
- [ ] Implement RAG pipeline for context-aware summarization
- [ ] Add authentication and authorization
- [ ] Create comprehensive API documentation
