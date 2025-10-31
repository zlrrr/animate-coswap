#!/usr/bin/env bash
#
# Quick Start Development Script
# Starts all services in separate terminal tabs/windows
#

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                                                                  ║"
echo "║              Starting Animate-CoSwap Development                ║"
echo "║                                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if Docker services are running
if ! docker ps | grep -q faceswap_postgres; then
    echo -e "${BLUE}Starting Docker services...${NC}"
    cd "$PROJECT_ROOT"
    docker-compose up -d postgres redis

    echo -e "${BLUE}Waiting for services to be ready...${NC}"
    sleep 5
fi

echo -e "${GREEN}✓ Docker services are running${NC}"

# Start backend
echo -e "\n${BLUE}Starting backend server...${NC}"
echo -e "${BLUE}Backend will be available at: http://localhost:8000${NC}"
echo -e "${BLUE}API docs: http://localhost:8000/docs${NC}"

# Start frontend
echo -e "\n${BLUE}Starting frontend...${NC}"
echo -e "${BLUE}Frontend will be available at: http://localhost:5173${NC}"

echo -e "\n${GREEN}"
echo "═══════════════════════════════════════════════════════════════════"
echo "  All services are starting!"
echo "═══════════════════════════════════════════════════════════════════"
echo -e "${NC}"

echo -e "\n${BLUE}Running services:${NC}"
echo "  • PostgreSQL: localhost:5432"
echo "  • Redis: localhost:6379"
echo "  • Backend API: http://localhost:8000"
echo "  • Frontend: http://localhost:5173"

echo -e "\n${BLUE}To stop services:${NC}"
echo "  • Press Ctrl+C to stop this script"
echo "  • Run: docker-compose down"

# Function to cleanup on exit
cleanup() {
    echo -e "\n${BLUE}Stopping services...${NC}"
    kill $(jobs -p) 2>/dev/null
    echo -e "${GREEN}Services stopped${NC}"
}

trap cleanup EXIT

# Start backend in background
cd "$PROJECT_ROOT/backend"
source ../venv/bin/activate
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

# Start frontend in background
cd "$PROJECT_ROOT/frontend"
npm run dev &
FRONTEND_PID=$!

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
