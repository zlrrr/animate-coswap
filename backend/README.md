## Backend API - Couple Face-Swap

FastAPI backend for the couple face-swap service.

## Project Structure

```
backend/
├── app/
│   ├── core/           # Core configuration and database
│   ├── models/         # SQLAlchemy models and Pydantic schemas
│   ├── api/            # API endpoints
│   │   └── v1/         # API version 1
│   ├── services/       # Business logic
│   │   └── faceswap/  # Face-swap service
│   └── utils/          # Utility functions
├── tests/              # Test suite
├── models/             # ML model files (gitignored)
├── storage/            # File storage (gitignored)
└── requirements.txt    # Python dependencies
```

## Setup

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# For development (includes testing tools)
pip install -r requirements-dev.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
# Edit .env with your settings
```

### 3. Download Face-Swap Model

```bash
mkdir -p models
wget https://huggingface.co/ezioruan/inswapper_128.onnx -O models/inswapper_128.onnx
```

### 4. Initialize Database

```bash
# Using Docker
docker-compose up -d postgres redis

# Or install PostgreSQL locally
# Then create database:
# createdb faceswap

# The app will automatically create tables on startup
```

## Running the Application

### Development Mode

```bash
# Run with auto-reload
uvicorn app.main:app --reload --port 8000

# Or using the main module
python -m app.main
```

The API will be available at:
- API: http://localhost:8000
- Swagger Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Production Mode

```bash
# Using gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

## Testing

### Run All Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run specific test file
pytest tests/test_basic.py -v

# Run specific test
pytest tests/test_basic.py::TestConfiguration::test_settings_loaded -v
```

### Test Categories

- `test_basic.py` - Basic smoke tests (no model required)
- `test_faceswap_core.py` - Face-swap algorithm tests (requires model)
- `test_api_faceswap.py` - API integration tests

## API Endpoints

### Health Check

```bash
GET /health
```

### Image Upload

```bash
POST /api/v1/faceswap/upload-image
Content-Type: multipart/form-data

file: <image_file>
image_type: source|template|result
```

### Create Face-Swap Task

```bash
POST /api/v1/faceswap/swap-faces
Content-Type: application/json

{
  "husband_image_id": 1,
  "wife_image_id": 2,
  "template_id": 3
}
```

### Get Task Status

```bash
GET /api/v1/faceswap/task/{task_id}
```

### List Templates

```bash
GET /api/v1/faceswap/templates?category=acg&limit=20&offset=0
```

### Create Template

```bash
POST /api/v1/faceswap/templates
Content-Type: application/json

{
  "image_id": 1,
  "title": "Template Title",
  "description": "Optional description"
}
```

## Development Workflow

### Code Formatting

```bash
# Format code
black app/ tests/

# Sort imports
isort app/ tests/

# Check linting
flake8 app/ tests/

# Type checking
mypy app/
```

### Database Migrations

When database schema changes:

```bash
# Generate migration
alembic revision --autogenerate -m "Description of changes"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Troubleshooting

### "Model not found" error

Download the inswapper model:
```bash
wget https://huggingface.co/ezioruan/inswapper_128.onnx -O models/inswapper_128.onnx
```

### "Database connection failed"

Make sure PostgreSQL is running:
```bash
docker-compose up -d postgres
# Or check local PostgreSQL: sudo systemctl status postgresql
```

### "Import error: InsightFace"

Install InsightFace and dependencies:
```bash
pip install insightface==0.7.3 onnxruntime==1.16.3
```

For GPU support:
```bash
pip install onnxruntime-gpu==1.16.3
```

## Performance

- Average face-swap time: < 10s (CPU), < 5s (GPU)
- Recommended: Use GPU for production
- Background processing: Uses FastAPI BackgroundTasks (MVP) or Celery (production)

## License

See main project LICENSE file.
