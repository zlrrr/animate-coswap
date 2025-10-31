#!/usr/bin/env bash
#
# Database Connection Diagnostic Script
# Checks all aspects of database connectivity
#

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
echo "║         Database Connection Diagnostic Tool                     ║"
echo "║                                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

ERRORS=0

# Check 1: Docker daemon
echo -e "\n${BLUE}[1/8] Checking Docker daemon...${NC}"
if docker info &> /dev/null; then
    echo -e "${GREEN}✓ Docker is running${NC}"
else
    echo -e "${RED}✗ Docker is not running${NC}"
    echo -e "${YELLOW}   → Start Docker Desktop${NC}"
    ERRORS=$((ERRORS+1))
    exit 1
fi

# Check 2: Docker containers
echo -e "\n${BLUE}[2/8] Checking Docker containers...${NC}"

POSTGRES_RUNNING=$(docker ps --filter "name=faceswap_postgres" --format "{{.Names}}")
REDIS_RUNNING=$(docker ps --filter "name=faceswap_redis" --format "{{.Names}}")

if [ -n "$POSTGRES_RUNNING" ]; then
    echo -e "${GREEN}✓ PostgreSQL container is running${NC}"
else
    echo -e "${RED}✗ PostgreSQL container is NOT running${NC}"
    echo -e "${YELLOW}   → Run: docker-compose up -d postgres${NC}"
    ERRORS=$((ERRORS+1))
fi

if [ -n "$REDIS_RUNNING" ]; then
    echo -e "${GREEN}✓ Redis container is running${NC}"
else
    echo -e "${RED}✗ Redis container is NOT running${NC}"
    echo -e "${YELLOW}   → Run: docker-compose up -d redis${NC}"
    ERRORS=$((ERRORS+1))
fi

# Check 3: PostgreSQL readiness
echo -e "\n${BLUE}[3/8] Testing PostgreSQL connection...${NC}"
if [ -n "$POSTGRES_RUNNING" ]; then
    if docker exec faceswap_postgres pg_isready -U faceswap_user &> /dev/null; then
        echo -e "${GREEN}✓ PostgreSQL is accepting connections${NC}"
    else
        echo -e "${RED}✗ PostgreSQL is not ready${NC}"
        echo -e "${YELLOW}   → Wait a few seconds and try again${NC}"
        ERRORS=$((ERRORS+1))
    fi
fi

# Check 4: Redis readiness
echo -e "\n${BLUE}[4/8] Testing Redis connection...${NC}"
if [ -n "$REDIS_RUNNING" ]; then
    REDIS_RESPONSE=$(docker exec faceswap_redis redis-cli ping 2>&1)
    if [ "$REDIS_RESPONSE" = "PONG" ]; then
        echo -e "${GREEN}✓ Redis is responding${NC}"
    else
        echo -e "${RED}✗ Redis is not responding${NC}"
        ERRORS=$((ERRORS+1))
    fi
fi

# Check 5: Environment file
echo -e "\n${BLUE}[5/8] Checking environment configuration...${NC}"

if [ -f "backend/.env" ]; then
    echo -e "${GREEN}✓ backend/.env exists${NC}"

    # Extract DATABASE_URL
    DB_URL=$(grep "^DATABASE_URL=" backend/.env | cut -d'=' -f2-)

    if [ -n "$DB_URL" ]; then
        echo -e "${BLUE}   DATABASE_URL: ${DB_URL}${NC}"

        # Parse credentials
        if [[ $DB_URL =~ postgresql://([^:]+):([^@]+)@([^:]+):([^/]+)/(.+) ]]; then
            DB_USER="${BASH_REMATCH[1]}"
            DB_PASS="${BASH_REMATCH[2]}"
            DB_HOST="${BASH_REMATCH[3]}"
            DB_PORT="${BASH_REMATCH[4]}"
            DB_NAME="${BASH_REMATCH[5]}"

            echo -e "${BLUE}   User: ${DB_USER}${NC}"
            echo -e "${BLUE}   Host: ${DB_HOST}:${DB_PORT}${NC}"
            echo -e "${BLUE}   Database: ${DB_NAME}${NC}"

            # Verify against docker-compose.yml
            EXPECTED_USER="faceswap_user"
            EXPECTED_PASS="faceswap_password"
            EXPECTED_DB="faceswap"

            if [ "$DB_USER" != "$EXPECTED_USER" ]; then
                echo -e "${RED}✗ User mismatch! Expected: $EXPECTED_USER, Got: $DB_USER${NC}"
                echo -e "${YELLOW}   → Update DATABASE_URL in backend/.env${NC}"
                ERRORS=$((ERRORS+1))
            fi

            if [ "$DB_PASS" != "$EXPECTED_PASS" ]; then
                echo -e "${RED}✗ Password mismatch! Expected: $EXPECTED_PASS${NC}"
                echo -e "${YELLOW}   → Update DATABASE_URL in backend/.env${NC}"
                ERRORS=$((ERRORS+1))
            fi

            if [ "$DB_NAME" != "$EXPECTED_DB" ]; then
                echo -e "${RED}✗ Database name mismatch! Expected: $EXPECTED_DB, Got: $DB_NAME${NC}"
                echo -e "${YELLOW}   → Update DATABASE_URL in backend/.env${NC}"
                ERRORS=$((ERRORS+1))
            fi

            if [ "$ERRORS" -eq 0 ] || [ "$DB_USER" = "$EXPECTED_USER" ]; then
                echo -e "${GREEN}✓ Credentials match docker-compose.yml${NC}"
            fi
        else
            echo -e "${RED}✗ Invalid DATABASE_URL format${NC}"
            ERRORS=$((ERRORS+1))
        fi
    else
        echo -e "${RED}✗ DATABASE_URL not found in .env${NC}"
        ERRORS=$((ERRORS+1))
    fi
else
    echo -e "${RED}✗ backend/.env does NOT exist${NC}"
    echo -e "${YELLOW}   → Run: cp backend/.env.example backend/.env${NC}"
    ERRORS=$((ERRORS+1))
fi

# Check 6: Database existence
echo -e "\n${BLUE}[6/8] Checking database existence...${NC}"
if [ -n "$POSTGRES_RUNNING" ]; then
    DB_EXISTS=$(docker exec faceswap_postgres psql -U faceswap_user -lqt | cut -d \| -f 1 | grep -w faceswap)
    if [ -n "$DB_EXISTS" ]; then
        echo -e "${GREEN}✓ Database 'faceswap' exists${NC}"
    else
        echo -e "${RED}✗ Database 'faceswap' does NOT exist${NC}"
        echo -e "${YELLOW}   → Recreate containers: docker-compose down && docker-compose up -d postgres redis${NC}"
        ERRORS=$((ERRORS+1))
    fi
fi

# Check 7: Database tables
echo -e "\n${BLUE}[7/8] Checking database tables...${NC}"
if [ -n "$POSTGRES_RUNNING" ] && [ -n "$DB_EXISTS" ]; then
    TABLES=$(docker exec faceswap_postgres psql -U faceswap_user -d faceswap -c "\dt" 2>&1)

    if echo "$TABLES" | grep -q "images"; then
        echo -e "${GREEN}✓ Table 'images' exists${NC}"
    else
        echo -e "${YELLOW}⚠  Table 'images' does NOT exist${NC}"
        echo -e "${YELLOW}   → Run migrations: cd backend && alembic upgrade head${NC}"
    fi

    if echo "$TABLES" | grep -q "tasks"; then
        echo -e "${GREEN}✓ Table 'tasks' exists${NC}"
    else
        echo -e "${YELLOW}⚠  Table 'tasks' does NOT exist${NC}"
        echo -e "${YELLOW}   → Run migrations: cd backend && alembic upgrade head${NC}"
    fi

    echo -e "\n${BLUE}   All tables:${NC}"
    echo "$TABLES" | grep -E "^\s(public|Schema)" | sed 's/^/   /'
fi

# Check 8: Test actual connection from backend
echo -e "\n${BLUE}[8/8] Testing Python database connection...${NC}"

if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate

    # Create a temporary test script
    cat > /tmp/test_db_conn.py <<'EOF'
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from sqlalchemy import create_engine, text
    from app.core.config import settings

    print(f"Testing connection to: {settings.DATABASE_URL.split('@')[1]}")  # Hide password

    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        version = result.fetchone()[0]
        print(f"✓ Connection successful!")
        print(f"  PostgreSQL version: {version.split(',')[0]}")
except Exception as e:
    print(f"✗ Connection failed: {str(e)}")
    sys.exit(1)
EOF

    if python /tmp/test_db_conn.py; then
        echo -e "${GREEN}✓ Backend can connect to database${NC}"
    else
        echo -e "${RED}✗ Backend cannot connect to database${NC}"
        ERRORS=$((ERRORS+1))
    fi

    rm -f /tmp/test_db_conn.py
else
    echo -e "${YELLOW}⚠  Virtual environment not found${NC}"
    echo -e "${YELLOW}   → Run: python3 -m venv venv${NC}"
fi

# Summary
echo -e "\n${BLUE}"
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                         Diagnostic Summary                       ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed! Database is properly configured.${NC}"
    echo ""
    echo -e "${BLUE}You can now start the backend:${NC}"
    echo "  cd backend"
    echo "  source ../venv/bin/activate"
    echo "  uvicorn app.main:app --reload --port 8000"
    exit 0
else
    echo -e "${RED}❌ Found $ERRORS issue(s). Please fix them before starting the backend.${NC}"
    echo ""
    echo -e "${BLUE}Quick fixes:${NC}"
    echo ""
    echo -e "${YELLOW}1. If Docker is not running:${NC}"
    echo "   → Start Docker Desktop"
    echo ""
    echo -e "${YELLOW}2. If containers are not running:${NC}"
    echo "   → docker-compose up -d postgres redis"
    echo ""
    echo -e "${YELLOW}3. If .env file is missing:${NC}"
    echo "   → cp backend/.env.example backend/.env"
    echo ""
    echo -e "${YELLOW}4. If credentials don't match:${NC}"
    echo "   → Edit backend/.env to use:"
    echo "     DATABASE_URL=postgresql://faceswap_user:faceswap_password@localhost:5432/faceswap"
    echo ""
    echo -e "${YELLOW}5. If tables are missing:${NC}"
    echo "   → cd backend && source ../venv/bin/activate && alembic upgrade head"
    echo ""
    echo -e "${BLUE}Or run the automated setup:${NC}"
    echo "   → ./scripts/setup_local_dev.sh"
    echo ""
    exit 1
fi
