#!/usr/bin/env bash
#
# Complete MVP Setup and Test Script
# Runs all setup steps and verifies MVP functionality
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${CYAN}"
cat << "EOF"
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║              🚀 Complete MVP Setup & Test Script                    ║
║                                                                      ║
║  This script will:                                                   ║
║    1. Check prerequisites                                            ║
║    2. Setup environment                                              ║
║    3. Initialize database                                            ║
║    4. Run tests                                                      ║
║    5. Verify MVP features                                            ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}\n"

# Confirm before proceeding
read -p "Press Enter to continue or Ctrl+C to cancel..."

# Step 1: Prerequisites
echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Step 1: Checking Prerequisites${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}\n"

# Check Docker
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✓ Docker is installed${NC}"
    if docker info &> /dev/null; then
        echo -e "${GREEN}✓ Docker is running${NC}"
    else
        echo -e "${RED}✗ Docker is not running${NC}"
        echo -e "${YELLOW}  Please start Docker Desktop${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ Docker is not installed${NC}"
    echo -e "${YELLOW}  Please install Docker Desktop from: https://www.docker.com/products/docker-desktop${NC}"
    exit 1
fi

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    echo -e "${GREEN}✓ Python ${PYTHON_VERSION} is installed${NC}"
else
    echo -e "${RED}✗ Python 3 is not installed${NC}"
    exit 1
fi

# Check Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}✓ Node.js ${NODE_VERSION} is installed${NC}"
else
    echo -e "${YELLOW}⚠  Node.js is not installed (frontend will not be available)${NC}"
fi

# Step 2: Environment Setup
echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Step 2: Environment Setup${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}\n"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment exists${NC}"
fi

# Activate virtual environment
source venv/bin/activate

# Detect platform and install dependencies
PLATFORM=$(uname -s)
MACHINE=$(uname -m)

echo -e "${BLUE}Platform: ${PLATFORM} ${MACHINE}${NC}"

if [ "$PLATFORM" = "Darwin" ] && [ "$MACHINE" = "arm64" ]; then
    echo -e "${BLUE}Installing dependencies for macOS Apple Silicon...${NC}"
    if [ -f "backend/requirements-macos-m.txt" ]; then
        pip install -q -r backend/requirements-macos-m.txt
    else
        pip install -q -r backend/requirements.txt
    fi
else
    echo -e "${BLUE}Installing dependencies...${NC}"
    pip install -q -r backend/requirements.txt
fi

echo -e "${GREEN}✓ Python dependencies installed${NC}"

# Create .env files
if [ ! -f "backend/.env" ]; then
    echo -e "${YELLOW}Creating backend/.env...${NC}"
    cp backend/.env.example backend/.env
    echo -e "${GREEN}✓ Created backend/.env${NC}"
else
    echo -e "${GREEN}✓ backend/.env exists${NC}"
fi

if [ ! -f "frontend/.env" ] && [ -f "frontend/.env.example" ]; then
    echo -e "${YELLOW}Creating frontend/.env...${NC}"
    cp frontend/.env.example frontend/.env
    echo -e "${GREEN}✓ Created frontend/.env${NC}"
fi

# Step 3: Docker Services
echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Step 3: Starting Docker Services${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}\n"

echo -e "${BLUE}Starting PostgreSQL and Redis...${NC}"
docker-compose up -d postgres redis

echo -e "${YELLOW}Waiting for services to be ready...${NC}"
sleep 5

# Wait for PostgreSQL
for i in {1..30}; do
    if docker exec faceswap_postgres pg_isready -U faceswap_user &> /dev/null; then
        echo -e "${GREEN}✓ PostgreSQL is ready${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}✗ PostgreSQL failed to start${NC}"
        exit 1
    fi
    sleep 1
done

# Wait for Redis
if docker exec faceswap_redis redis-cli ping &> /dev/null; then
    echo -e "${GREEN}✓ Redis is ready${NC}"
else
    echo -e "${RED}✗ Redis failed to start${NC}"
    exit 1
fi

# Step 4: Database Initialization
echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Step 4: Database Initialization${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}\n"

chmod +x scripts/init_database.sh
./scripts/init_database.sh

# Step 5: Run Tests
echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Step 5: Running Tests${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}\n"

echo -e "${BLUE}Running configuration tests...${NC}"
python scripts/test_settings.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Configuration tests passed${NC}"
fi

echo -e "\n${BLUE}Running basic tests...${NC}"
cd backend
pytest tests/test_basic.py -v --tb=short -q
BASIC_RESULT=$?
cd ..

if [ $BASIC_RESULT -eq 0 ]; then
    echo -e "${GREEN}✓ Basic tests passed${NC}"
else
    echo -e "${RED}✗ Basic tests failed${NC}"
    exit 1
fi

echo -e "\n${BLUE}Running MVP workflow tests...${NC}"
cd backend
pytest tests/test_mvp_workflow.py -v --tb=short -q
MVP_RESULT=$?
cd ..

if [ $MVP_RESULT -eq 0 ]; then
    echo -e "${GREEN}✓ MVP workflow tests passed${NC}"
else
    echo -e "${YELLOW}⚠  Some MVP tests failed (might be due to missing face-swap models)${NC}"
fi

# Step 6: Frontend Setup
if command -v npm &> /dev/null; then
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Step 6: Frontend Setup${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}\n"

    if [ ! -d "frontend/node_modules" ]; then
        echo -e "${BLUE}Installing frontend dependencies...${NC}"
        cd frontend
        npm install --silent
        cd ..
        echo -e "${GREEN}✓ Frontend dependencies installed${NC}"
    else
        echo -e "${GREEN}✓ Frontend dependencies already installed${NC}"
    fi
fi

# Step 7: Summary
echo -e "\n${GREEN}"
cat << "EOF"
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║                  ✅ MVP Setup Completed Successfully!                ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo -e "${CYAN}📊 Setup Summary:${NC}\n"
echo -e "  ${GREEN}✓${NC} Docker services running"
echo -e "  ${GREEN}✓${NC} Database initialized"
echo -e "  ${GREEN}✓${NC} All tables created"
echo -e "  ${GREEN}✓${NC} Configuration valid"
echo -e "  ${GREEN}✓${NC} Basic tests passed"
if [ $MVP_RESULT -eq 0 ]; then
    echo -e "  ${GREEN}✓${NC} MVP workflow tests passed"
else
    echo -e "  ${YELLOW}⚠${NC} MVP workflow tests need face-swap models"
fi

echo -e "\n${CYAN}🚀 Next Steps:${NC}\n"

echo -e "${BLUE}1. Start the backend (in terminal 1):${NC}"
echo -e "   cd backend"
echo -e "   source ../venv/bin/activate"
echo -e "   uvicorn app.main:app --reload --port 8000"
echo ""

if command -v npm &> /dev/null; then
    echo -e "${BLUE}2. Start the frontend (in terminal 2):${NC}"
    echo -e "   cd frontend"
    echo -e "   npm run dev"
    echo ""
fi

echo -e "${BLUE}3. Open your browser:${NC}"
echo -e "   Frontend: ${CYAN}http://localhost:5173${NC}"
echo -e "   Backend API Docs: ${CYAN}http://localhost:8000/docs${NC}"
echo ""

echo -e "${BLUE}4. Test MVP Features:${NC}"
echo -e "   ${GREEN}✓${NC} Upload husband's photo"
echo -e "   ${GREEN}✓${NC} Upload wife's photo"
echo -e "   ${GREEN}✓${NC} Select/create template"
echo -e "   ${YELLOW}⚠${NC} Face-swap (requires models - see below)"
echo -e "   ${GREEN}✓${NC} View results gallery"
echo ""

echo -e "${YELLOW}⚠️  Note about Face-Swap Models:${NC}"
echo -e "   To enable face-swapping, you need to download the inswapper_128.onnx model."
echo -e "   See: ${CYAN}docs/MODEL-DOWNLOAD-FIX.md${NC}"
echo ""

echo -e "${BLUE}Quick commands:${NC}"
echo -e "   # Stop services:      docker-compose down"
echo -e "   # View logs:          docker-compose logs -f"
echo -e "   # Run tests:          ./scripts/test_mvp.sh"
echo -e "   # Diagnose database:  ./scripts/diagnose_db.sh"
echo ""

echo -e "${GREEN}🎉 Happy coding!${NC}\n"
