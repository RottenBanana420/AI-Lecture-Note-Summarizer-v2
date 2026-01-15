# Backend Application

FastAPI backend for AI Lecture Note Summarizer with PostgreSQL, pgvector, and RAG pipeline.

## Features

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

- **97 integration tests** with 77% code coverage
- **Optimized test execution** with parallel processing
- **TDD approach** - tests never modified, only code
- **Deterministic behavior** - no flaky tests
- **Aggressive failure testing** to ensure robustness
- **Fast feedback loop** - optimized for developer productivity

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
├── repositories/      # Data access layer
├── services/          # Business logic layer
└── api/               # API endpoints
    └── v1/            # API version 1

tests/
├── integration/       # Integration tests
│   ├── test_data_model_integrity.py      # Data model tests (30 tests)
│   ├── test_validation_failures.py       # Validation tests (43 tests)
│   └── test_error_handling.py            # Error handling tests (24 tests)
├── unit/              # Unit tests
└── conftest.py        # Shared test fixtures
```

## Running Tests

```bash
# Run all tests
pytest

# Run specific test suite
pytest tests/integration/test_validation_failures.py -v

# Run with coverage
pytest --cov=app --cov-report=html

# Current status: 97 tests passing, 77% coverage
```

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

### Retry Configuration

Configured in `app/core/config.py`:

```python
MAX_RETRY_ATTEMPTS = 3
RETRY_BACKOFF_FACTOR = 2.0
RETRY_MAX_DELAY = 30  # seconds
DATABASE_TIMEOUT = 30  # seconds
```

## Development

### Adding New Validators

```python
from app.core.validators import validate_email, validate_uuid

# Use existing validators
email = validate_email(user_input)
user_id = validate_uuid(id_string, field_name="user_id")
```

### Custom Exception Handling

```python
from app.core.exceptions import ValidationError, ResourceNotFoundError

# Raise custom exceptions
raise ValidationError(
    message="Invalid input",
    field="username",
    details={"min_length": 3}
)

# Exceptions are automatically caught and formatted by FastAPI handlers
```

### Database Operations with Retry

```python
from app.db.db_utils import retry_on_transient_error

@retry_on_transient_error(max_attempts=3)
async def fetch_user(user_id: UUID):
    # Automatically retries on transient database errors
    return await db.query(User).filter(User.id == user_id).first()
```

## Code Coverage

Current coverage: **77%**

```text
app/core/exceptions.py      91%
app/core/validators.py      80%
app/db/db_utils.py          74%
app/models/models.py        95%
app/core/config.py          97%
```

## Next Steps

- [ ] Implement API endpoints for document upload and processing
- [ ] Add PDF processing pipeline with text extraction
- [ ] Integrate AI models for embeddings and summarization
- [ ] Implement RAG pipeline for context-aware summarization
- [ ] Add authentication and authorization
- [ ] Create comprehensive API documentation
