# Couple Face-Swap Website

AI-powered couple image collection and face-swapping service

## Project Overview

This project is a web-based platform that collects couple images from various sources (ACG, movies, TV shows), stores them with metadata, and performs high-quality face-swapping using advanced AI algorithms.

**Current Status:** ✅ **MVP COMPLETE** - Phases 0, 1, 2 Finished

See [MVP-COMPLETE.md](./docs/MVP-COMPLETE.md) for detailed completion report.

## Features (Planned)

### MVP (Phases 0-2)
- ✓ Core face-swap algorithm (InsightFace + inswapper)
- ✓ Manual image upload
- ✓ Template selection
- ✓ Background processing
- ✓ Result gallery
- ✓ Web interface

### Post-MVP (Phases 3+)
- [ ] Automated image collection (Catcher service)
- [ ] Advanced search and filtering (Browser service)
- [ ] Tag management
- [ ] User accounts and authentication
- [ ] API rate limiting
- [ ] Production deployment

## Technology Stack

### Backend
- **Language:** Python 3.10+
- **Framework:** FastAPI
- **Database:** PostgreSQL + SQLAlchemy
- **Task Queue:** Celery + Redis
- **Face-Swap:** InsightFace + inswapper_128.onnx

### Frontend
- **Framework:** React 18+ with TypeScript
- **UI Library:** Ant Design
- **State Management:** React Query
- **Build Tool:** Vite

### DevOps
- **Containerization:** Docker + Docker Compose
- **Testing:** pytest, vitest
- **CI/CD:** GitHub Actions

## Project Structure

```
couple-faceswap/
├── backend/
│   ├── app/
│   │   ├── core/           # Configuration
│   │   ├── models/         # Database models
│   │   ├── api/            # API endpoints
│   │   ├── services/       # Business logic
│   │   │   └── faceswap/  # Face-swap core
│   │   └── utils/          # Helpers
│   ├── tests/              # Unit & integration tests
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── utils/
│   ├── package.json
│   └── Dockerfile
├── docs/                    # Documentation
├── scripts/                 # Setup and utility scripts
├── tests/                   # E2E tests and fixtures
├── docker-compose.yml
├── PLAN.md                  # Detailed project plan
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Node.js 18 or higher
- PostgreSQL 14+
- Redis
- CUDA-capable GPU (optional, for faster processing)

### Phase 0: Environment Setup

#### 1. Clone the repository

```bash
git clone <repository-url>
cd couple-faceswap
```

#### 2. Set up Python environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
cd backend
pip install -r requirements.txt
```

#### 3. Download face-swap model

```bash
# Create models directory
mkdir -p backend/models

# Download inswapper model
# Option 1: Direct download
wget https://huggingface.co/ezioruan/inswapper_128.onnx -O backend/models/inswapper_128.onnx

# Option 2: Manual download
# Visit: https://huggingface.co/ezioruan/inswapper_128.onnx
# Save to: backend/models/inswapper_128.onnx
```

#### 4. Prepare test fixtures (optional)

```bash
# Add test images to tests/fixtures/
# Required for algorithm validation:
# - person_a.jpg, person_b.jpg (single faces)
# - couple.jpg, couple_template.jpg (couple images)
# - etc. (see PLAN.md Phase 0 for complete list)
```

#### 5. Run algorithm validation

```bash
python scripts/validate_algorithm.py
```

This script will:
- Validate your environment setup
- Test the face-swap algorithm with various scenarios
- Generate performance benchmarks
- Save results to `tests/validation_results/`

**Acceptance Criteria:**
- 8/10 test cases must pass
- Average processing time < 10 seconds (CPU) or < 5 seconds (GPU)
- Visual quality >= 4/5 (manual inspection)

### Phase 1: Backend Development

```bash
# Set up database
docker-compose up -d postgres redis

# Create database tables
cd backend
alembic upgrade head

# Run backend server
uvicorn app.main:app --reload --port 8000

# Run tests
pytest tests/ -v
```

### Phase 2: Frontend Development

```bash
# Install dependencies
cd frontend
npm install

# Run development server
npm run dev

# Run tests
npm test
```

### Full Stack (Docker)

```bash
# Build and run all services
docker-compose up --build

# Access services:
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

## Development Workflow

### Checkpoints

This project follows a checkpoint-based development approach:

1. **Phase 0.1** - Algorithm Validation Complete
2. **Phase 1.1** - Backend Core Complete
3. **Phase 1.2** - API Integration Tests
4. **Phase 2.1** - Frontend Core Components
5. **Phase 2.2** - MVP Complete

Each checkpoint must:
- Pass all tests
- Be committed with descriptive message
- Be tagged for easy recovery

```bash
# Example: Commit checkpoint 0.1
git add .
git commit -m "Phase 0.1: Face-swap algorithm validated with InsightFace"
git tag checkpoint-0.1
```

### Testing Strategy

- **Unit Tests:** 70% of test suite (fast, isolated)
- **Integration Tests:** 20% (API, database)
- **E2E Tests:** 10% (full workflow)

**Minimum Coverage:** 80%

```bash
# Run all tests with coverage
pytest tests/ -v --cov=app --cov-report=html

# Run specific test suite
pytest tests/test_faceswap_core.py -v

# Run with benchmarks
pytest tests/ --benchmark-only
```

## Documentation

- **[PLAN.md](./PLAN.md)** - Complete project roadmap with phases
- **[docs/phase-0/](./docs/phase-0/)** - Phase 0 documentation
  - Environment setup guide
  - Algorithm validation results
  - Database schema design
  - Technology stack rationale

## API Documentation

Once the backend is running, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## Contributing

This is currently a personal project. Contributions may be accepted in the future.

### Code Standards

- **Python:** Follow PEP 8, use type hints
- **TypeScript:** Strict mode enabled
- **Commits:** Format: `[Phase X.Y] Component: Description`
- **Testing:** Write tests before features (TDD)

## Roadmap

- [x] **Phase 0: Environment Setup & Algorithm Validation** ✅ Complete
- [x] **Phase 1: Backend MVP** ✅ Complete
- [x] **Phase 2: Frontend MVP** ✅ Complete
- [ ] **MVP Testing & Validation** (Next: Download model & run tests)
- [ ] Phase 3: Catcher Service (5-7 days) - Post-MVP
- [ ] Phase 4: Browser Service (3-4 days) - Post-MVP
- [ ] Phase 5: Production Deployment (3-4 days) - Post-MVP

## Performance Targets

### MVP Stage
- Average processing time: < 10 seconds per image pair
- API response time: < 200ms (excluding processing)
- Face detection accuracy: >= 95%
- Visual quality score: >= 4/5

### Post-MVP
- Handle 50+ concurrent users
- 99.9% uptime
- 1000+ templates in database

## License

See [LICENSE](./LICENSE) file for details.

## Acknowledgments

- **InsightFace** - Face detection and recognition
- **inswapper** - Face-swapping model
- **FastAPI** - Web framework
- **React** - Frontend framework

## Support

For issues and questions:
1. Check documentation in `docs/`
2. Review PLAN.md for detailed specifications
3. Run validation script for diagnostics

## Project Status

**Current Status:** ✅ **MVP COMPLETE** - Ready for Testing

**Completed:**
- ✅ Phase 0: Project infrastructure and face-swap core
- ✅ Phase 1: Backend MVP with full REST API
- ✅ Phase 2: Frontend MVP with React UI

**Next Steps:**
1. Download face-swap model (inswapper_128.onnx)
2. Run algorithm validation tests
3. Test complete workflow end-to-end
4. Deploy for internal testing

**Last Updated:** 2024-01-XX

---

## Quick Links

- 📖 [Complete MVP Report](./docs/MVP-COMPLETE.md)
- 🚀 [Quick Start Guide](./QUICKSTART.md)
- 📋 [Project Plan](./PLAN.md)
- 🔧 [Backend Setup](./backend/README.md)
- 🎨 [Frontend Setup](./frontend/README.md)
- 📡 [API Documentation](./docs/phase-1/api-documentation.md)
