#!/usr/bin/env bash
#
# Database Initialization Script
# Creates database schema using Alembic migrations
#

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                                                                  ║"
echo "║              Database Initialization Script                     ║"
echo "║                                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Step 1: Check Docker services
echo -e "\n${BLUE}[1/6] Checking Docker services...${NC}"

if ! docker ps | grep -q faceswap_postgres; then
    echo -e "${RED}✗ PostgreSQL container is not running${NC}"
    echo -e "${YELLOW}   Starting PostgreSQL...${NC}"
    docker-compose up -d postgres

    echo -e "${YELLOW}   Waiting for PostgreSQL to be ready...${NC}"
    for i in {1..30}; do
        if docker exec faceswap_postgres pg_isready -U faceswap_user &> /dev/null; then
            break
        fi
        sleep 1
    done
fi

if docker exec faceswap_postgres pg_isready -U faceswap_user &> /dev/null; then
    echo -e "${GREEN}✓ PostgreSQL is ready${NC}"
else
    echo -e "${RED}✗ PostgreSQL failed to start${NC}"
    exit 1
fi

# Step 2: Check .env file
echo -e "\n${BLUE}[2/6] Checking environment configuration...${NC}"

if [ ! -f "backend/.env" ]; then
    echo -e "${YELLOW}⚠  .env file not found, creating from example...${NC}"
    cp backend/.env.example backend/.env
    echo -e "${GREEN}✓ Created backend/.env${NC}"
else
    echo -e "${GREEN}✓ backend/.env exists${NC}"
fi

# Step 3: Verify database connection
echo -e "\n${BLUE}[3/6] Verifying database connection...${NC}"

DB_EXISTS=$(docker exec faceswap_postgres psql -U faceswap_user -lqt | cut -d \| -f 1 | grep -w faceswap || echo "")

if [ -z "$DB_EXISTS" ]; then
    echo -e "${YELLOW}⚠  Database 'faceswap' does not exist${NC}"
    echo -e "${YELLOW}   Creating database...${NC}"
    docker exec faceswap_postgres psql -U faceswap_user -c "CREATE DATABASE faceswap;" || true
fi

echo -e "${GREEN}✓ Database 'faceswap' exists${NC}"

# Step 4: Create alembic/versions directory if not exists
echo -e "\n${BLUE}[4/6] Checking Alembic configuration...${NC}"

if [ ! -d "backend/alembic/versions" ]; then
    echo -e "${YELLOW}⚠  alembic/versions directory not found${NC}"
    echo -e "${YELLOW}   Creating directory...${NC}"
    mkdir -p backend/alembic/versions
    echo -e "${GREEN}✓ Created alembic/versions directory${NC}"
else
    echo -e "${GREEN}✓ alembic/versions directory exists${NC}"
fi

# Step 5: Check existing migrations
echo -e "\n${BLUE}[5/6] Checking existing migrations...${NC}"

cd backend

# Count migration files (excluding .gitkeep)
MIGRATION_COUNT=$(find alembic/versions -name "*.py" -type f | wc -l)

if [ "$MIGRATION_COUNT" -eq 0 ]; then
    echo -e "${YELLOW}⚠  No migrations found${NC}"
    echo -e "${YELLOW}   Creating initial migration...${NC}"

    # Activate virtual environment if it exists
    if [ -f "../venv/bin/activate" ]; then
        source ../venv/bin/activate
    fi

    # Create initial migration
    alembic revision --autogenerate -m "Initial migration"

    NEW_MIGRATION=$(find alembic/versions -name "*.py" -type f | head -1)
    if [ -n "$NEW_MIGRATION" ]; then
        echo -e "${GREEN}✓ Created migration: $(basename $NEW_MIGRATION)${NC}"
    else
        echo -e "${RED}✗ Failed to create migration${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ Found $MIGRATION_COUNT existing migration(s)${NC}"
fi

# Step 6: Apply migrations
echo -e "\n${BLUE}[6/6] Applying migrations...${NC}"

# Activate virtual environment if it exists
if [ -f "../venv/bin/activate" ]; then
    source ../venv/bin/activate
fi

alembic upgrade head

echo -e "${GREEN}✓ Migrations applied successfully${NC}"

# Verify tables created
echo -e "\n${BLUE}Verifying database tables...${NC}"

cd ..
TABLES=$(docker exec faceswap_postgres psql -U faceswap_user -d faceswap -c "\dt" 2>&1)

if echo "$TABLES" | grep -q "images"; then
    echo -e "${GREEN}✓ Table 'images' created${NC}"
else
    echo -e "${RED}✗ Table 'images' not found${NC}"
fi

if echo "$TABLES" | grep -q "templates"; then
    echo -e "${GREEN}✓ Table 'templates' created${NC}"
else
    echo -e "${RED}✗ Table 'templates' not found${NC}"
fi

if echo "$TABLES" | grep -q "faceswap_tasks"; then
    echo -e "${GREEN}✓ Table 'faceswap_tasks' created${NC}"
else
    echo -e "${RED}✗ Table 'faceswap_tasks' not found${NC}"
fi

echo -e "\n${BLUE}All tables:${NC}"
docker exec faceswap_postgres psql -U faceswap_user -d faceswap -c "\dt"

echo -e "\n${GREEN}"
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                                                                  ║"
echo "║              ✅ Database Initialized Successfully                ║"
echo "║                                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "\n${BLUE}Next steps:${NC}"
echo "  1. Start the backend: cd backend && uvicorn app.main:app --reload --port 8000"
echo "  2. Start the frontend: cd frontend && npm run dev"
echo "  3. Open browser: http://localhost:5173"
echo ""
