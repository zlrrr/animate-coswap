#!/bin/bash

# =================================================================
# Phase 1.5 Migration Application Script
# =================================================================
# This script applies the initial database migration that includes
# all Phase 1.5 features (preprocessing, batch processing, etc.)
#
# Usage: ./scripts/apply_phase_1_5_migration.sh
# =================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

print_header() {
    echo ""
    echo "=========================================="
    echo "$1"
    echo "=========================================="
    echo ""
}

# =================================================================
# Main Script
# =================================================================

print_header "Phase 1.5 Database Migration"

# Step 1: Check if we're in the right directory
print_status "Checking current directory..."
if [ ! -f "docker-compose.yml" ]; then
    print_error "docker-compose.yml not found. Please run this script from the project root directory."
    exit 1
fi
print_success "In correct directory"

# Step 2: Check if Docker is available
print_status "Checking Docker availability..."
if command -v docker &> /dev/null; then
    print_success "Docker is available"
else
    print_error "Docker is not installed or not in PATH"
    exit 1
fi

# Step 3: Check Docker services
print_status "Checking Docker services..."
if docker compose ps postgres | grep -q "Up"; then
    print_success "PostgreSQL container is running"
else
    print_warning "PostgreSQL container is not running. Starting services..."
    docker compose up -d postgres redis
    print_status "Waiting for PostgreSQL to be ready..."
    sleep 5

    # Wait for PostgreSQL to be ready
    for i in {1..30}; do
        if docker exec faceswap_postgres pg_isready -U faceswap_user &> /dev/null; then
            print_success "PostgreSQL is ready"
            break
        fi
        if [ $i -eq 30 ]; then
            print_error "PostgreSQL failed to start within 30 seconds"
            exit 1
        fi
        echo -n "."
        sleep 1
    done
fi

# Step 4: Check if .env file exists
print_status "Checking .env file..."
if [ ! -f "backend/.env" ]; then
    print_warning ".env file not found. Creating from .env.example..."
    if [ -f "backend/.env.example" ]; then
        cp backend/.env.example backend/.env
        print_success "Created .env file from .env.example"
    else
        print_error ".env.example not found"
        exit 1
    fi
else
    print_success ".env file exists"
fi

# Step 5: Check if migration file exists
print_status "Checking migration file..."
MIGRATION_FILE="backend/alembic/versions/00f2e8fecd91_initial_schema_with_phase_1_5.py"
if [ ! -f "$MIGRATION_FILE" ]; then
    print_error "Migration file not found: $MIGRATION_FILE"
    exit 1
fi
print_success "Migration file found"

# Step 6: Check if alembic_version table exists (indicates existing migrations)
print_status "Checking for existing migrations..."
if docker exec faceswap_postgres psql -U faceswap_user -d faceswap -c "SELECT * FROM alembic_version;" &> /dev/null; then
    print_warning "Database already has migration history"

    # Get current revision
    CURRENT_REV=$(docker exec faceswap_postgres psql -U faceswap_user -d faceswap -t -c "SELECT version_num FROM alembic_version;")
    CURRENT_REV=$(echo $CURRENT_REV | xargs)  # Trim whitespace

    if [ ! -z "$CURRENT_REV" ]; then
        print_warning "Current revision: $CURRENT_REV"
        print_warning "This migration starts fresh with revision: 00f2e8fecd91"
        print_error "Cannot apply this migration to an existing database with different schema"
        echo ""
        echo "Options:"
        echo "  1. Backup and drop the database, then run this script again"
        echo "  2. Create a custom migration that updates from your current schema"
        echo ""
        echo "To reset the database (WARNING: This will delete all data):"
        echo "  docker exec faceswap_postgres psql -U faceswap_user -d faceswap -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'"
        echo "  Then run this script again"
        exit 1
    fi
else
    print_success "No existing migrations found - ready for fresh setup"
fi

# Step 7: Change to backend directory
print_status "Changing to backend directory..."
cd backend

# Step 8: Check if Python virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    print_warning "Python virtual environment not activated"

    # Try to activate if it exists
    if [ -f "../venv/bin/activate" ]; then
        print_status "Activating virtual environment..."
        source ../venv/bin/activate
        print_success "Virtual environment activated"
    else
        print_error "Virtual environment not found at ../venv"
        echo "Please create it with: python3 -m venv venv"
        exit 1
    fi
else
    print_success "Virtual environment is activated: $VIRTUAL_ENV"
fi

# Step 9: Check if alembic is installed
print_status "Checking Alembic installation..."
if ! python -c "import alembic" &> /dev/null; then
    print_warning "Alembic not installed. Installing requirements..."
    pip install -q alembic sqlalchemy psycopg2-binary
    print_success "Requirements installed"
else
    print_success "Alembic is installed"
fi

# Step 10: Stamp database with initial revision (if needed)
print_status "Checking if we need to stamp the database..."
if ! docker exec faceswap_postgres psql -U faceswap_user -d faceswap -c "\dt" | grep -q "alembic_version"; then
    print_status "Creating alembic_version table..."
    alembic stamp 00f2e8fecd91
    print_success "Database stamped with revision 00f2e8fecd91"
fi

# Step 11: Apply migration
print_header "Applying Migration"
print_status "Running: alembic upgrade head"
echo ""

if alembic upgrade head; then
    print_success "Migration applied successfully!"
else
    print_error "Migration failed!"
    echo ""
    echo "To debug, try:"
    echo "  cd backend"
    echo "  alembic current"
    echo "  alembic history"
    exit 1
fi

# Step 12: Verify tables were created
print_header "Verifying Database Schema"

print_status "Checking created tables..."
cd ..  # Back to root directory

TABLES=$(docker exec faceswap_postgres psql -U faceswap_user -d faceswap -t -c "\dt" | awk '{print $3}' | grep -v '^$' | sort)

echo "$TABLES"

# Expected tables
EXPECTED_TABLES="alembic_version batch_tasks crawl_tasks faceswap_tasks images template_preprocessing templates users"

# Count tables
TABLE_COUNT=$(echo "$TABLES" | wc -w)

if [ "$TABLE_COUNT" -ge 7 ]; then
    print_success "Found $TABLE_COUNT tables"

    # Check for essential Phase 1.5 tables
    for table in batch_tasks template_preprocessing; do
        if echo "$TABLES" | grep -q "$table"; then
            print_success "✓ Phase 1.5 table exists: $table"
        else
            print_warning "✗ Phase 1.5 table missing: $table"
        fi
    done
else
    print_error "Only found $TABLE_COUNT tables, expected at least 7"
    exit 1
fi

# Step 13: Verify Phase 1.5 columns
print_header "Verifying Phase 1.5 Schema"

# Check images table for Phase 1.5 columns
print_status "Checking images table for Phase 1.5 columns..."
IMAGES_COLUMNS=$(docker exec faceswap_postgres psql -U faceswap_user -d faceswap -c "\d images" | grep -E "storage_type|expires_at|session_id")
if [ ! -z "$IMAGES_COLUMNS" ]; then
    print_success "✓ Images table has Phase 1.5 columns (storage_type, expires_at, session_id)"
else
    print_warning "✗ Images table missing some Phase 1.5 columns"
fi

# Check templates table for Phase 1.5 columns
print_status "Checking templates table for Phase 1.5 columns..."
TEMPLATES_COLUMNS=$(docker exec faceswap_postgres psql -U faceswap_user -d faceswap -c "\d templates" | grep -E "is_preprocessed|male_face_count|female_face_count")
if [ ! -z "$TEMPLATES_COLUMNS" ]; then
    print_success "✓ Templates table has Phase 1.5 columns (is_preprocessed, male/female counts)"
else
    print_warning "✗ Templates table missing some Phase 1.5 columns"
fi

# Check faceswap_tasks table for Phase 1.5 columns
print_status "Checking faceswap_tasks table for Phase 1.5 columns..."
TASKS_COLUMNS=$(docker exec faceswap_postgres psql -U faceswap_user -d faceswap -c "\d faceswap_tasks" | grep -E "task_id|batch_id|face_mappings|use_preprocessed")
if [ ! -z "$TASKS_COLUMNS" ]; then
    print_success "✓ FaceSwap tasks table has Phase 1.5 columns (task_id, batch_id, face_mappings)"
else
    print_warning "✗ FaceSwap tasks table missing some Phase 1.5 columns"
fi

# Final summary
print_header "Migration Complete!"

echo "✅ Database schema successfully created with Phase 1.5 features"
echo ""
echo "Next Steps:"
echo "  1. Start backend server: cd backend && uvicorn app.main:app --reload"
echo "  2. Run tests: pytest backend/tests/ -v"
echo "  3. Begin implementing Phase 1.5 checkpoints (see docs/PHASE-1.5-QUICK-REFERENCE.md)"
echo ""
echo "Phase 1.5 Features Enabled:"
echo "  ✓ Separated storage (temporary photos / permanent templates)"
echo "  ✓ Template preprocessing (face detection, gender classification, masking)"
echo "  ✓ Batch processing (multiple templates at once)"
echo "  ✓ Flexible face mapping (custom source-to-target mapping)"
echo "  ✓ Auto-cleanup (temporary file expiration)"
echo ""
print_success "Database is ready for Phase 1.5 development!"
