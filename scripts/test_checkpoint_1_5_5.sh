#!/bin/bash

# =================================================================
# Test Script for Phase 1.5 Checkpoint 1.5.5
# Auto Cleanup
# =================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo ""
    echo "=========================================="
    echo "$1"
    echo "=========================================="
    echo ""
}

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_header "Phase 1.5 Checkpoint 1.5.5 Tests"
print_status "Testing: Auto Cleanup"

# Check if we're in the project root
if [ ! -f "docker-compose.yml" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

# Check prerequisites
print_status "Checking prerequisites..."
for checkpoint in 1 2 3 4; do
    if [ $checkpoint -eq 1 ]; then
        checkpoint_file="backend/app/api/v1/photos.py"
    elif [ $checkpoint -eq 2 ]; then
        checkpoint_file="backend/app/api/v1/templates_preprocessing.py"
    elif [ $checkpoint -eq 3 ]; then
        checkpoint_file="backend/app/services/face_mapping.py"
    else
        checkpoint_file="backend/app/services/batch_processing.py"
    fi

    if [ ! -f "$checkpoint_file" ]; then
        print_error "Checkpoint 1.5.${checkpoint} not complete. Please complete it first."
        print_error "Run: ./scripts/test_checkpoint_1_5_${checkpoint}.sh"
        exit 1
    fi
done
print_success "All prerequisites complete"

# Check Docker services
print_status "Checking Docker services..."
if ! docker compose ps postgres | grep -q "Up"; then
    print_warning "PostgreSQL not running. Starting services..."
    docker compose up -d postgres redis
    sleep 5
fi

# Check database
print_status "Checking database connection..."
if ! docker exec faceswap_postgres pg_isready -U faceswap_user &> /dev/null; then
    print_error "Database is not ready"
    exit 1
fi
print_success "Database is ready"

# Activate virtual environment
print_status "Activating virtual environment..."
if [ ! -d "venv" ]; then
    print_error "Virtual environment not found. Creating..."
    python3 -m venv venv
fi

source venv/bin/activate
print_success "Virtual environment activated"

# Install dependencies
print_status "Checking dependencies..."
cd backend
if ! python -c "import pytest" &> /dev/null; then
    print_warning "Installing test dependencies..."
    pip install -q pytest pytest-cov
fi
print_success "Dependencies ready"

# Run tests
print_header "Running Checkpoint 1.5.5 Tests"

print_status "Test file: tests/test_phase_1_5_checkpoint_5.py"
echo ""

# Run pytest with verbose output
pytest tests/test_phase_1_5_checkpoint_5.py -v --tb=short --color=yes -x

TEST_EXIT_CODE=$?

echo ""
print_header "Test Results"

if [ $TEST_EXIT_CODE -eq 0 ]; then
    print_success "✅ All Checkpoint 1.5.5 tests passed!"
    echo ""
    print_success "🎉 PHASE 1.5 COMPLETE! 🎉"
    echo ""
    print_status "All Phase 1.5 checkpoints are now complete:"
    print_status "  ✅ Checkpoint 1.5.1: Separated Upload APIs"
    print_status "  ✅ Checkpoint 1.5.2: Template Preprocessing"
    print_status "  ✅ Checkpoint 1.5.3: Flexible Face Mapping"
    print_status "  ✅ Checkpoint 1.5.4: Batch Processing"
    print_status "  ✅ Checkpoint 1.5.5: Auto Cleanup"
    echo ""
    print_status "Phase 1.5 MVP Enhanced Features are ready for production!"
    echo ""
    print_status "Next steps:"
    print_status "  - Run full test suite: pytest backend/tests/"
    print_status "  - Start the application: docker compose up"
    print_status "  - Review API documentation: http://localhost:8000/docs"
    exit 0
else
    print_error "❌ Some tests failed"
    echo ""
    print_status "Please review the errors above and fix them before proceeding."
    print_status "Common issues:"
    print_status "  1. Storage path permissions"
    print_status "  2. Database records not properly cleaned"
    print_status "  3. File system errors"
    echo ""
    print_status "For help, see: docs/CHECKPOINT-1.5.5-COMPLETE.md"
    exit 1
fi
