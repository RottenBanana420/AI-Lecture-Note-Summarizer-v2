#!/bin/bash
# One-Command Setup Script for AI Lecture Note Summarizer
# This script automates the complete environment setup process

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    local all_good=true
    
    # Check Python
    if command -v python &> /dev/null; then
        PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
        print_success "Python $PYTHON_VERSION installed"
    else
        print_error "Python not found"
        all_good=false
    fi
    
    # Check pyenv
    if command -v pyenv &> /dev/null; then
        PYENV_VERSION=$(pyenv --version | awk '{print $2}')
        print_success "pyenv $PYENV_VERSION installed"
    else
        print_error "pyenv not found - install with: brew install pyenv pyenv-virtualenv"
        all_good=false
    fi
    
    # Check Docker
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version | awk '{print $3}' | sed 's/,//')
        print_success "Docker $DOCKER_VERSION installed"
    else
        print_error "Docker not found - install Docker Desktop"
        all_good=false
    fi
    
    # Check Node.js
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        print_success "Node.js $NODE_VERSION installed"
    else
        print_warning "Node.js not found - install with: brew install node"
        print_info "Frontend setup will be skipped"
    fi
    
    if [ "$all_good" = false ]; then
        print_error "Missing required prerequisites. Please install them and try again."
        exit 1
    fi
}

# Create .env file if it doesn't exist
setup_env_file() {
    print_header "Setting Up Environment File"
    
    if [ -f .env ]; then
        print_warning ".env file already exists - skipping"
    else
        cp .env.example .env
        print_success "Created .env file from .env.example"
        print_warning "IMPORTANT: Edit .env and update the following:"
        print_info "  - POSTGRES_PASSWORD (change from default)"
        print_info "  - SECRET_KEY (generate a secure key)"
        print_info "  - DATABASE_URL (update password to match POSTGRES_PASSWORD)"
    fi
}

# Setup Python virtual environment
setup_python_env() {
    print_header "Setting Up Python Environment"
    
    # Check if virtual environment exists
    if pyenv virtualenvs | grep -q "lecture-summarizer-backend"; then
        print_success "Virtual environment 'lecture-summarizer-backend' already exists"
    else
        print_info "Creating virtual environment..."
        PYTHON_VERSION=$(cat .python-version 2>/dev/null || echo "3.11.14")
        
        # Install Python version if not available
        if ! pyenv versions | grep -q "$PYTHON_VERSION"; then
            print_info "Installing Python $PYTHON_VERSION..."
            pyenv install $PYTHON_VERSION
        fi
        
        pyenv virtualenv $PYTHON_VERSION lecture-summarizer-backend
        print_success "Created virtual environment"
    fi
    
    # Activate and install dependencies
    print_info "Installing Python dependencies (this may take 5-10 minutes)..."
    eval "$(pyenv init -)"
    eval "$(pyenv virtualenv-init -)"
    pyenv activate lecture-summarizer-backend
    
    pip install --upgrade pip --quiet
    pip install -r backend/requirements.txt --quiet
    
    print_success "Python dependencies installed"
    
    # Download SpaCy model
    print_info "Downloading SpaCy language model..."
    python -m spacy download en_core_web_sm --quiet
    print_success "SpaCy model downloaded"
}

# Start Docker services
setup_docker_services() {
    print_header "Starting Docker Services"
    
    # Check if Docker is running
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker Desktop and try again."
        exit 1
    fi
    
    print_info "Starting PostgreSQL and Redis..."
    docker-compose up -d
    
    # Wait for services to be healthy
    print_info "Waiting for services to be ready..."
    sleep 5
    
    # Check PostgreSQL
    if docker-compose exec -T postgres pg_isready -U postgres &> /dev/null; then
        print_success "PostgreSQL is ready"
    else
        print_error "PostgreSQL failed to start"
        exit 1
    fi
    
    # Check Redis
    if docker-compose exec -T redis redis-cli ping &> /dev/null; then
        print_success "Redis is ready"
    else
        print_error "Redis failed to start"
        exit 1
    fi
    
    # Verify pgvector extension
    print_info "Verifying pgvector extension..."
    if docker-compose exec -T postgres psql -U postgres -d lecture_notes -c "SELECT extname FROM pg_extension WHERE extname = 'vector';" | grep -q "vector"; then
        print_success "pgvector extension installed"
    else
        print_error "pgvector extension not found"
        exit 1
    fi
}

# Setup frontend
setup_frontend() {
    print_header "Setting Up Frontend"
    
    if command -v npm &> /dev/null; then
        print_info "Installing frontend dependencies..."
        cd frontend
        npm install --silent
        cd ..
        print_success "Frontend dependencies installed"
    else
        print_warning "npm not found - skipping frontend setup"
    fi
}

# Run verification
run_verification() {
    print_header "Running Environment Verification"
    
    if [ -f scripts/verify_environment.sh ]; then
        chmod +x scripts/verify_environment.sh
        ./scripts/verify_environment.sh
    else
        print_warning "Verification script not found - skipping"
    fi
}

# Main execution
main() {
    echo -e "${GREEN}"
    echo "╔═══════════════════════════════════════════════════════╗"
    echo "║   AI Lecture Note Summarizer - Setup Script          ║"
    echo "╚═══════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    check_prerequisites
    setup_env_file
    setup_python_env
    setup_docker_services
    setup_frontend
    run_verification
    
    print_header "Setup Complete!"
    print_success "Environment is ready for development"
    echo ""
    print_info "Next steps:"
    echo "  1. Edit .env file with your configuration"
    echo "  2. Start backend: cd backend && uvicorn app.main:app --reload"
    echo "  3. Start frontend: cd frontend && npm run dev"
    echo ""
    print_info "For more information, see: docs/environment_setup.md"
}

# Run main function
main
