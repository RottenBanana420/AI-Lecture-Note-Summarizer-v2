# AI Lecture Note Summarizer v2

Smart study companion that cuts review time by 70% with AI-powered summarization using Retrieval-Augmented Generation (RAG).

## Project Status

🟢 **Environment Ready** - Configured and ready for implementation

## Quick Start

### Automated Setup (Recommended)

```bash
./scripts/setup.sh
```

This will check prerequisites, create `.env` file, set up Python environment, start Docker services, and install all dependencies.

### Manual Setup

**Prerequisites:**

- Python 3.11+
- Docker Desktop
- Node.js 18+ (for frontend)

**Steps:**

1. **Create environment file**:

   ```bash
   cp .env.example .env
   # Edit .env and update POSTGRES_PASSWORD and SECRET_KEY
   ```

2. **Start Docker services**:

   ```bash
   docker-compose up -d
   ```

3. **Install dependencies**:

   ```bash
   pip install -r backend/requirements.txt
   python -m spacy download en_core_web_sm
   cd frontend && npm install
   ```

4. **Verify environment**:

   ```bash
   ./scripts/verify_environment.sh
   ```

## Architecture

- **Backend**: FastAPI with async support
- **Database**: PostgreSQL 16 with pgvector extension
- **Cache**: Redis 7
- **Frontend**: React 18 + TypeScript + Vite
- **AI Pipeline**: RAG with sentence-transformers

See [system_architecture.md](docs/system_architecture.md) for detailed design.

## Development

### Environment

- Python virtual environment auto-activates in project directory
- Docker services managed via docker-compose
- All configuration in `.env` (copy from `.env.example`)

### Testing Philosophy

- **Break-first approach**: Tests are never modified, only code
- **TDD workflow**: Red → Green → Refactor
- **Correctness first, speed second**

See [testing_strategy.md](docs/testing_strategy.md) for complete guide.

## Documentation

- [Environment Setup Guide](docs/environment_setup.md)
- [System Architecture](docs/system_architecture.md)
- [Testing Strategy](docs/testing_strategy.md)
- [Implementation Plan](docs/implementation_plan.md)

## Project Structure

```
.
├── backend/              # FastAPI application
│   ├── requirements.txt  # Python dependencies
│   └── init.sql         # Database initialization
├── frontend/            # React application
│   └── package.json     # Node dependencies
├── docs/                # Documentation
├── scripts/             # Helper scripts
│   ├── setup.sh         # One-command setup
│   └── verify_environment.sh # Environment verification
├── docker-compose.yml   # Service orchestration
└── .env.example         # Environment template
```

## License

See [LICENSE](LICENSE) file for details.
