# Environment Setup Guide

Complete guide for establishing isolated development environments for the AI Lecture Note Summarizer project.

## Overview

This project uses a multi-layered isolation strategy:

- **Python Backend**: pyenv-virtualenv for complete Python environment isolation
- **Database & Services**: Docker containers for PostgreSQL with pgvector, Redis
- **Frontend**: Node.js with npm for package management
- **Development Orchestration**: Docker Compose for service coordination

---

## Python Backend Environment (pyenv-virtualenv)

### Prerequisites

**macOS Installation:**

```bash
# Install pyenv and pyenv-virtualenv via Homebrew
brew install pyenv pyenv-virtualenv
```

**Linux Installation:**

```bash
# Install pyenv
curl https://pyenv.run | bash

# pyenv-virtualenv is typically included with pyenv installer
```

### Shell Configuration

Add the following to your shell configuration file (`~/.zshrc` or `~/.bashrc`):

```bash
# pyenv configuration
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init --path)"
eval "$(pyenv init -)"

# pyenv-virtualenv automatic activation
eval "$(pyenv virtualenv-init -)"
```

**Apply changes:**

```bash
source ~/.zshrc  # or ~/.bashrc
```

### Python Version Installation

```bash
# List available Python versions
pyenv install --list | grep "^  3\."

# Install Python 3.11 (recommended for AI workloads)
pyenv install 3.11.7

# Verify installation
pyenv versions
```

### Virtual Environment Creation

```bash
# Navigate to project directory
cd /Users/kusaihajuri/Projects/AI-Lecture-Note-Summarizer-v2

# Create virtual environment
pyenv virtualenv 3.11.7 lecture-summarizer-backend

# Set local Python version for automatic activation
pyenv local lecture-summarizer-backend
```

**Automatic Activation:**
When you enter the project directory, the virtual environment will automatically activate due to the `.python-version` file created by `pyenv local`.

### Dependency Installation

```bash
# Ensure virtual environment is active
cd /Users/kusaihajuri/Projects/AI-Lecture-Note-Summarizer-v2

# Install backend dependencies
pip install --upgrade pip
pip install -r backend/requirements.txt
```

### Environment Verification

```bash
# Verify Python version
python --version  # Should show 3.11.7

# Verify virtual environment
pyenv version  # Should show lecture-summarizer-backend

# Verify pip packages are isolated
pip list
```

---

## Database & Services (Docker)

### Prerequisites

**Install Docker Desktop:**

- macOS: Download from [docker.com](https://www.docker.com/products/docker-desktop)
- Linux: Follow [official installation guide](https://docs.docker.com/engine/install/)

### PostgreSQL with pgvector

The project uses Docker Compose to run PostgreSQL with the pgvector extension for vector similarity search.

**Start services:**

```bash
cd /Users/kusaihajuri/Projects/AI-Lecture-Note-Summarizer-v2
docker-compose up -d
```

**Verify pgvector extension:**

```bash
docker-compose exec postgres psql -U postgres -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

**Connection details:**

- Host: `localhost`
- Port: `5432`
- Database: `lecture_notes`
- User: `postgres`
- Password: (defined in `.env` file)

### Service Management

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f

# Restart specific service
docker-compose restart postgres
```

---

## Frontend Environment (Node.js)

### Prerequisites

**Install Node Version Manager (nvm):**

**macOS/Linux:**

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
```

### Node.js Installation

```bash
# Install Node.js LTS
nvm install --lts

# Use LTS version
nvm use --lts

# Set default
nvm alias default node
```

### Frontend Setup

```bash
# Navigate to frontend directory
cd /Users/kusaihajuri/Projects/AI-Lecture-Note-Summarizer-v2/frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

---

## Complete Environment Verification

### Verification Script

Create a verification script to check all environments:

```bash
#!/bin/bash
# verify_environment.sh

echo "=== Python Environment ==="
python --version
pyenv version
echo ""

echo "=== Docker Services ==="
docker-compose ps
echo ""

echo "=== PostgreSQL + pgvector ==="
docker-compose exec -T postgres psql -U postgres -c "SELECT version();"
docker-compose exec -T postgres psql -U postgres -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
echo ""

echo "=== Node.js Environment ==="
node --version
npm --version
echo ""

echo "=== Environment Check Complete ==="
```

**Run verification:**

```bash
chmod +x scripts/verify_environment.sh
./scripts/verify_environment.sh
```

---

## Environment Isolation Benefits

### Python Backend

- **No Global Pollution**: Dependencies isolated per project
- **Version Control**: Exact Python version per project
- **Automatic Activation**: No manual activation needed
- **Reproducibility**: `.python-version` file ensures consistency

### Docker Services

- **Consistent Database**: Same PostgreSQL version across all environments
- **Extension Management**: pgvector extension pre-configured
- **Easy Reset**: `docker-compose down -v` for clean slate
- **Production Parity**: Development mirrors production setup

### Frontend

- **Package Isolation**: Node modules isolated per project
- **Version Management**: Consistent Node.js version via nvm
- **Fast Iteration**: Hot module replacement for rapid development

---

## Troubleshooting

### Python Environment Not Activating

**Issue**: Virtual environment doesn't activate when entering directory

**Solution**:

```bash
# Verify .python-version file exists
cat .python-version

# Manually activate if needed
pyenv activate lecture-summarizer-backend

# Re-run shell configuration
eval "$(pyenv virtualenv-init -)"
```

### Docker Services Not Starting

**Issue**: PostgreSQL container fails to start

**Solution**:

```bash
# Check Docker Desktop is running
docker ps

# View detailed logs
docker-compose logs postgres

# Remove volumes and restart
docker-compose down -v
docker-compose up -d
```

### pgvector Extension Missing

**Issue**: pgvector extension not available

**Solution**:

```bash
# Recreate containers with fresh image
docker-compose down
docker-compose pull
docker-compose up -d

# Manually install extension
docker-compose exec postgres psql -U postgres -d lecture_notes -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

---

## Next Steps

After environment setup:

1. Review [system_architecture.md](system_architecture.md) for system design
2. Review [testing_strategy.md](testing_strategy.md) for testing approach
3. Begin implementation following TDD principles
