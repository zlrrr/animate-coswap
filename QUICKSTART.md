# Quick Start Guide

Get the Couple Face-Swap project running in 5 minutes!

## Prerequisites

- Python 3.10+
- Git

## Step 1: Clone and Setup

```bash
# Clone repository
git clone <your-repo-url>
cd couple-faceswap

# Create Python virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install backend dependencies
cd backend
pip install -r requirements.txt
cd ..
```

## Step 2: Download Face-Swap Model

```bash
# Create models directory
mkdir -p backend/models

# Download the inswapper model (~554MB)
wget https://huggingface.co/ezioruan/inswapper_128.onnx \
  -O backend/models/inswapper_128.onnx

# Or use curl:
curl -L https://huggingface.co/ezioruan/inswapper_128.onnx \
  -o backend/models/inswapper_128.onnx
```

**Manual download:**
If wget/curl don't work, visit https://huggingface.co/ezioruan/inswapper_128.onnx
and save the file to `backend/models/inswapper_128.onnx`

## Step 3: Prepare Test Images (Optional)

For algorithm validation, add test images to `tests/fixtures/`:

```bash
# At minimum, add these two images:
# - tests/fixtures/person_a.jpg (a portrait photo)
# - tests/fixtures/person_b.jpg (another portrait photo)
```

See `tests/fixtures/README.md` for complete list of test images.

## Step 4: Validate Algorithm

```bash
# Run validation script
python scripts/validate_algorithm.py
```

Expected output:
```
Environment Tests: 3/3 passed
Algorithm Validation: X/10 tests passed
```

## Step 5: View Results

Check the generated face-swap results:

```bash
# Results are saved to:
ls tests/validation_results/
```

## What's Next?

### Phase 0 Complete ✓

If validation passed, you're ready for Phase 1!

### Phase 1: Backend Development

```bash
# Start database and redis (using Docker)
docker-compose up -d postgres redis

# Run backend server
cd backend
uvicorn app.main:app --reload --port 8000
```

### Phase 2: Frontend Development

```bash
# Install frontend dependencies
cd frontend
npm install

# Run frontend dev server
npm run dev
```

Visit http://localhost:3000

## Troubleshooting

### "InsightFace not found"

```bash
pip install insightface==0.7.3 onnxruntime==1.16.3
```

### "Model file not found"

Make sure the model is downloaded to:
```
backend/models/inswapper_128.onnx
```

Check file size should be ~554MB

### "No face detected"

- Make sure test images contain clear, frontal faces
- Faces should be at least 128x128 pixels
- Image should be well-lit

### GPU Support

For GPU acceleration:

```bash
# Uninstall CPU version
pip uninstall onnxruntime

# Install GPU version
pip install onnxruntime-gpu==1.16.3

# Requires CUDA 11.x
```

## Docker Quick Start (Alternative)

```bash
# Start just database and redis
docker-compose up -d postgres redis

# Or start everything (Phase 1+)
docker-compose --profile full up --build
```

## Useful Commands

```bash
# Run tests
pytest backend/tests/ -v

# Run with coverage
pytest backend/tests/ --cov=app --cov-report=html

# Run specific test
pytest backend/tests/test_faceswap_core.py -v

# Format code
black backend/app/
isort backend/app/
```

## Getting Help

1. Check documentation in `docs/`
2. Review `PLAN.md` for detailed specifications
3. Run validation script for diagnostics

## Full Documentation

For complete setup instructions, see:
- [README.md](./README.md) - Project overview
- [docs/phase-0/environment-setup.md](./docs/phase-0/environment-setup.md) - Detailed setup
- [PLAN.md](./PLAN.md) - Complete project plan

## Progress Checklist

Phase 0:
- [ ] Python environment set up
- [ ] InsightFace installed
- [ ] Model downloaded
- [ ] Validation script runs
- [ ] Test images added
- [ ] Results look good (visual quality >= 4/5)
- [ ] Phase 0.1 committed and tagged

Ready for Phase 1? Let's build the backend!
