#!/usr/bin/env bash
#
# Local Development Setup Script for macOS
# This script sets up the local development environment
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                                                                  ║"
echo "║         Animate-CoSwap Local Development Setup (macOS)          ║"
echo "║                                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Step 1: Check prerequisites
echo -e "\n${BLUE}[1/7] Checking prerequisites...${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    echo "   Please install Docker Desktop from: https://www.docker.com/products/docker-desktop"
    exit 1
fi
echo -e "${GREEN}✓ Docker installed${NC}"

# Check Docker is running
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker is not running${NC}"
    echo "   Please start Docker Desktop"
    exit 1
fi
echo -e "${GREEN}✓ Docker is running${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed${NC}"
    exit 1
fi
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✓ Python ${PYTHON_VERSION} installed${NC}"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo -e "${YELLOW}⚠️  Node.js is not installed${NC}"
    echo "   Frontend will not be available. Install from: https://nodejs.org/"
else
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}✓ Node.js ${NODE_VERSION} installed${NC}"
fi

# Step 2: Create backend .env file
echo -e "\n${BLUE}[2/7] Setting up backend environment...${NC}"

if [ -f "backend/.env" ]; then
    echo -e "${YELLOW}⚠️  backend/.env already exists${NC}"
    read -p "   Overwrite? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}   Keeping existing .env file${NC}"
    else
        cp backend/.env.example backend/.env
        echo -e "${GREEN}✓ Created backend/.env from .env.example${NC}"
    fi
else
    cp backend/.env.example backend/.env
    echo -e "${GREEN}✓ Created backend/.env from .env.example${NC}"
fi

# Step 3: Create frontend .env file
echo -e "\n${BLUE}[3/7] Setting up frontend environment...${NC}"

if [ -f "frontend/.env" ]; then
    echo -e "${YELLOW}⚠️  frontend/.env already exists${NC}"
else
    if [ -f "frontend/.env.example" ]; then
        cp frontend/.env.example frontend/.env
        echo -e "${GREEN}✓ Created frontend/.env from .env.example${NC}"
    else
        # Create default frontend .env
        cat > frontend/.env <<EOF
VITE_API_URL=http://localhost:8000
EOF
        echo -e "${GREEN}✓ Created default frontend/.env${NC}"
    fi
fi

# Step 4: Start Docker services
echo -e "\n${BLUE}[4/7] Starting Docker services (PostgreSQL & Redis)...${NC}"

docker-compose up -d postgres redis

# Wait for PostgreSQL to be ready
echo -e "${YELLOW}   Waiting for PostgreSQL to be ready...${NC}"
for i in {1..30}; do
    if docker exec faceswap_postgres pg_isready -U faceswap_user &> /dev/null; then
        echo -e "${GREEN}✓ PostgreSQL is ready${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ PostgreSQL failed to start${NC}"
        exit 1
    fi
    sleep 1
done

# Wait for Redis to be ready
echo -e "${YELLOW}   Waiting for Redis to be ready...${NC}"
for i in {1..30}; do
    if docker exec faceswap_redis redis-cli ping &> /dev/null; then
        echo -e "${GREEN}✓ Redis is ready${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ Redis failed to start${NC}"
        exit 1
    fi
    sleep 1
done

# Step 5: Setup Python virtual environment
echo -e "\n${BLUE}[5/7] Setting up Python virtual environment...${NC}"

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓ Created virtual environment${NC}"
else
    echo -e "${YELLOW}   Virtual environment already exists${NC}"
fi

# Activate virtual environment and install dependencies
source venv/bin/activate

# Check platform and install appropriate requirements
PLATFORM=$(uname -s)
MACHINE=$(uname -m)

if [ "$PLATFORM" = "Darwin" ] && [ "$MACHINE" = "arm64" ]; then
    echo -e "${BLUE}   Detected: macOS Apple Silicon${NC}"
    if [ -f "backend/requirements-macos-m.txt" ]; then
        pip install -r backend/requirements-macos-m.txt
    else
        pip install -r backend/requirements.txt
    fi
else
    echo -e "${BLUE}   Detected: $PLATFORM $MACHINE${NC}"
    pip install -r backend/requirements.txt
fi

echo -e "${GREEN}✓ Installed Python dependencies${NC}"

# Step 6: Run database migrations
echo -e "\n${BLUE}[6/7] Running database migrations...${NC}"

cd backend

# Check if alembic is initialized
if [ ! -d "alembic/versions" ]; then
    echo -e "${YELLOW}   Initializing Alembic...${NC}"
    mkdir -p alembic/versions
fi

# Run migrations
if command -v alembic &> /dev/null; then
    # Check if there are any migrations
    if [ -z "$(ls -A alembic/versions 2>/dev/null)" ]; then
        echo -e "${YELLOW}   No migrations found, creating initial migration...${NC}"
        alembic revision --autogenerate -m "Initial migration"
    fi

    alembic upgrade head
    echo -e "${GREEN}✓ Database migrations completed${NC}"
else
    echo -e "${YELLOW}⚠️  Alembic not found, skipping migrations${NC}"
fi

cd ..

# Step 7: Install frontend dependencies (if Node.js is available)
echo -e "\n${BLUE}[7/7] Setting up frontend...${NC}"

if command -v npm &> /dev/null; then
    if [ ! -d "frontend/node_modules" ]; then
        cd frontend
        npm install
        cd ..
        echo -e "${GREEN}✓ Installed frontend dependencies${NC}"
    else
        echo -e "${YELLOW}   Frontend dependencies already installed${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Skipping frontend setup (Node.js not available)${NC}"
fi

# Summary
echo -e "\n${GREEN}"
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                                                                  ║"
echo "║                    ✅ Setup Complete!                            ║"
echo "║                                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "\n${BLUE}Next Steps:${NC}"
echo ""
echo -e "${YELLOW}1. Start the backend server:${NC}"
echo "   cd backend"
echo "   source ../venv/bin/activate"
echo "   uvicorn app.main:app --reload --port 8000"
echo ""
echo -e "${YELLOW}2. In a new terminal, start the frontend:${NC}"
echo "   cd frontend"
echo "   npm run dev"
echo ""
echo -e "${YELLOW}3. Open your browser:${NC}"
echo "   Frontend: http://localhost:5173"
echo "   Backend API: http://localhost:8000/docs"
echo ""
echo -e "${BLUE}Or use the quick start script:${NC}"
echo "   ./scripts/start_dev.sh"
echo ""
echo -e "${BLUE}To stop services:${NC}"
echo "   docker-compose down"
echo ""
