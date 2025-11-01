#!/bin/bash

# =================================================================
# Test Script for Phase 1.5 Checkpoint 1.5.3
# Flexible Face Mapping
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

print_header "Phase 1.5 Checkpoint 1.5.3 Tests"
print_status "Testing: Flexible Face Mapping"

# Check if we're in the project root
if [ ! -f "docker-compose.yml" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

# Check prerequisites
print_status "Checking prerequisites..."
for checkpoint in 1 2; do
    checkpoint_file="backend/app/api/v1/$([ $checkpoint -eq 1 ] && echo 'photos.py' || echo 'templates_preprocessing.py')"
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

# Check faceswap_tasks table has task_id and face_mappings columns
print_status "Checking faceswap_tasks schema..."
if ! docker exec faceswap_postgres psql -U faceswap_user -d faceswap -c "\d faceswap_tasks" | grep -q "task_id"; then
    print_error "faceswap_tasks table missing task_id column. Please run migration:"
    print_error "./scripts/apply_phase_1_5_migration.sh"
    exit 1
fi
if ! docker exec faceswap_postgres psql -U faceswap_user -d faceswap -c "\d faceswap_tasks" | grep -q "face_mappings"; then
    print_error "faceswap_tasks table missing face_mappings column. Please run migration:"
    print_error "./scripts/apply_phase_1_5_migration.sh"
    exit 1
fi
print_success "faceswap_tasks schema is correct"

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
print_header "Running Checkpoint 1.5.3 Tests"

print_status "Test file: tests/test_phase_1_5_checkpoint_3.py"
echo ""

# Run pytest with verbose output
pytest tests/test_phase_1_5_checkpoint_3.py -v --tb=short --color=yes -x

TEST_EXIT_CODE=$?

echo ""
print_header "Test Results"

if [ $TEST_EXIT_CODE -eq 0 ]; then
    print_success "✅ All Checkpoint 1.5.3 tests passed!"
    echo ""
    print_status "Checkpoint 1.5.3 is complete. You can now proceed to:"
    print_status "  Checkpoint 1.5.4: Batch Processing"
    echo ""
    print_status "To continue:"
    print_status "  ./scripts/test_checkpoint_1_5_4.sh"
    exit 0
else
    print_error "❌ Some tests failed"
    echo ""
    print_status "Please review the errors above and fix them before proceeding."
    print_status "Common issues:"
    print_status "  1. Database not properly migrated (missing task_id or face_mappings)"
    print_status "  2. Preprocessing data not available (run Checkpoint 1.5.2 first)"
    print_status "  3. API schema validation errors"
    echo ""
    print_status "For help, see: docs/CHECKPOINT-1.5.3-COMPLETE.md"
    exit 1
fi
