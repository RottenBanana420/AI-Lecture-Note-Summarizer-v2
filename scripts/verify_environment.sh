#!/bin/bash
# Environment Verification Script for AI Lecture Note Summarizer

echo "=========================================="
echo "Environment Verification"
echo "=========================================="
echo ""

# Check Python Environment
echo "=== Python Environment ==="
python --version
echo "Virtual Environment: $(pyenv version-name)"
echo ""

# Check Docker Services
echo "=== Docker Services ==="
docker-compose ps
echo ""

# Check PostgreSQL
echo "=== PostgreSQL ==="
docker-compose exec -T postgres psql -U postgres -c "SELECT version();" | head -3
echo ""

# Check pgvector Extension
echo "=== pgvector Extension ==="
docker-compose exec -T postgres psql -U postgres -d lecture_notes -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
echo ""

# Check Redis
echo "=== Redis ==="
echo "Redis ping: $(docker-compose exec -T redis redis-cli ping)"
echo ""

# Check Project Structure
echo "=== Project Structure ==="
echo "Backend directory: $([ -d backend ] && echo '✓ exists' || echo '✗ missing')"
echo "Frontend directory: $([ -d frontend ] && echo '✓ exists' || echo '✗ missing')"
echo "requirements.txt: $([ -f backend/requirements.txt ] && echo '✓ exists' || echo '✗ missing')"
echo "docker-compose.yml: $([ -f docker-compose.yml ] && echo '✓ exists' || echo '✗ missing')"
echo ""

echo "=========================================="
echo "Environment Check Complete!"
echo "=========================================="
