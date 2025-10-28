# Getting Started on macOS (Apple Silicon M1/M2/M3)

Complete setup guide for Couple Face-Swap on Apple Silicon Macs.

## Prerequisites

- **macOS**: 12.0 (Monterey) or later
- **Chip**: Apple M1, M2, M3, or M4
- **Python**: 3.10 or 3.11 (ARM64 native recommended)
- **Homebrew**: Latest version
- **Xcode Command Line Tools**: Installed

## Quick Check: Verify Your System

```bash
# Check macOS version
sw_vers

# Check chip architecture
uname -m  # Should show "arm64"

# Check Python architecture
python3 --version
python3 -c "import platform; print(platform.machine())"  # Should show "arm64"
```

---

## Step 1: Install System Dependencies

### Install Homebrew (if not installed)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Install Required Tools

```bash
# Install Python 3.11 (ARM64 native)
brew install python@3.11

# Install wget for model downloads
brew install wget

# Install PostgreSQL and Redis (for Phase 1+)
brew install postgresql@15 redis

# Install git (if not already installed)
brew install git
```

---

## Step 2: Clone and Setup Project

```bash
# Clone repository
git clone <your-repo-url>
cd couple-faceswap

# Create Python virtual environment (ARM64 native)
python3.11 -m venv venv
source venv/bin/activate

# Verify virtual environment is using ARM64 Python
python -c "import platform; print(f'Python: {platform.python_version()}, Arch: {platform.machine()}')"
# Should show: Python: 3.11.x, Arch: arm64
```

---

## Step 3: Install Backend Dependencies

### Install Core Dependencies

```bash
cd backend

# Install ARM64-compatible dependencies
pip install --upgrade pip wheel setuptools

# Install requirements (ARM64 optimized)
pip install -r requirements-macos-m.txt
```

**Important Notes:**

- **onnxruntime**: On Apple Silicon, use the standard version which includes CoreML acceleration
- **insightface**: Works natively on ARM64 with proper compilation
- **opencv-python**: Use the standard version which is ARM64 compatible

### Verify Installation

```bash
# Test imports
python -c "import cv2, numpy, insightface, onnxruntime; print('✓ All imports successful')"

# Check ONNX Runtime providers
python -c "import onnxruntime; print('Available providers:', onnxruntime.get_available_providers())"
# Should include: ['CoreMLExecutionProvider', 'CPUExecutionProvider']
```

---

## Step 4: Download Face-Swap Models

### Download inswapper Model

```bash
# Create models directory
mkdir -p models

# Download using wget
wget https://huggingface.co/ezioruan/inswapper_128.onnx/resolve/main/inswapper_128.onnx \
  -O models/inswapper_128.onnx

# Or use curl
curl -L https://huggingface.co/ezioruan/inswapper_128.onnx/resolve/main/inswapper_128.onnx \
  -o models/inswapper_128.onnx

# Verify file size (should be ~554MB)
ls -lh models/inswapper_128.onnx
```

### InsightFace Models (Auto-downloaded on first run)

The InsightFace `buffalo_l` model will auto-download to:
```
~/.insightface/models/buffalo_l/
```

---

## Step 5: Configure for Apple Silicon

### Create Environment Configuration

```bash
# Copy example config
cp .env.example .env

# Edit .env file
nano .env
```

**Recommended Settings for Apple Silicon:**

```bash
# .env for macOS M-series

# Database (use PostgreSQL for production)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/faceswap

# Redis
REDIS_URL=redis://localhost:6379/0

# GPU Acceleration
USE_GPU=false  # Apple Silicon doesn't use CUDA
ACCELERATION_PROVIDER=coreml  # Use CoreML for Apple Neural Engine
GPU_DEVICE_ID=0

# Processing
MAX_IMAGE_SIZE=4096

# Models
MODELS_PATH=./models
INSWAPPER_MODEL=inswapper_128.onnx
FACE_ANALYSIS_MODEL=buffalo_l
```

---

## Step 6: Prepare Test Images

```bash
# Return to project root
cd ..

# Add test images
mkdir -p tests/fixtures

# Copy your test portrait images:
# - tests/fixtures/person_a.jpg
# - tests/fixtures/person_b.jpg
# - tests/fixtures/couple.jpg (optional, with 2 faces)
```

**Test Image Requirements:**
- Format: JPEG or PNG
- Resolution: At least 512x512 pixels
- Face size: Minimum 128x128 pixels
- Lighting: Good, even lighting
- Angle: Frontal or near-frontal faces

---

## Step 7: Run Validation Tests

```bash
cd backend

# Run basic tests
pytest tests/test_basic.py -v

# Run face-swap core tests (requires models)
pytest tests/test_faceswap_core.py -v

# Run all tests
pytest tests/ -v
```

**Expected Results:**
```
tests/test_basic.py: 19/19 passed ✓
tests/test_faceswap_core.py: X/14 passed (depends on fixtures)
```

---

## Step 8: Start Services

### Option A: Local Services (Development)

```bash
# Start PostgreSQL
brew services start postgresql@15

# Start Redis
brew services start redis

# Create database
createdb faceswap

# Run backend server
cd backend
uvicorn app.main:app --reload --port 8000
```

### Option B: Docker Services (Recommended)

```bash
# Install Docker Desktop for Mac (Apple Silicon)
# Download from: https://www.docker.com/products/docker-desktop/

# Start database and redis only
docker compose up -d postgres redis

# Run backend server locally
cd backend
uvicorn app.main:app --reload --port 8000
```

**Access Points:**
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

---

## Step 9: Frontend Setup

```bash
cd frontend

# Install Node.js (if not installed)
brew install node@20

# Install dependencies
npm install

# Copy environment config
cp .env.example .env

# Edit frontend env (if needed)
echo "VITE_API_URL=http://localhost:8000" > .env

# Run development server
npm run dev
```

**Access Frontend:**
- Frontend: http://localhost:3000

---

## Performance Optimization for Apple Silicon

### Neural Engine Acceleration

Apple Silicon includes a Neural Engine (ANE) that can accelerate ML workloads:

```python
# In app/services/faceswap/core.py
# CoreML provider will automatically use ANE when available

providers = ['CoreMLExecutionProvider', 'CPUExecutionProvider']
session = onnxruntime.InferenceSession(model_path, providers=providers)
```

### Expected Performance

| Task | M1 | M2 | M3 | Intel i7 (CPU) |
|------|-----|-----|-----|----------------|
| Face Detection | ~50ms | ~40ms | ~30ms | ~100ms |
| Single Face Swap | ~2s | ~1.5s | ~1s | ~5s |
| Couple Face Swap | ~4s | ~3s | ~2s | ~10s |

**Note:** Times are approximate and depend on image resolution.

---

## Troubleshooting

### Issue: "No module named 'insightface'"

```bash
# Make sure you're in the virtual environment
source venv/bin/activate

# Reinstall insightface
pip install insightface==0.7.3
```

### Issue: "Library not loaded: @rpath/libopencv..."

```bash
# Reinstall opencv-python
pip uninstall opencv-python opencv-python-headless
pip install opencv-python==4.8.1.78
```

### Issue: "ONNX Runtime - Unsupported execution provider"

```bash
# Check available providers
python -c "import onnxruntime; print(onnxruntime.get_available_providers())"

# If CoreML is missing, reinstall onnxruntime
pip uninstall onnxruntime onnxruntime-gpu
pip install onnxruntime==1.16.3
```

### Issue: InsightFace model download fails

```bash
# Manually download buffalo_l model
mkdir -p ~/.insightface/models
cd ~/.insightface/models

# Download from alternative source
wget https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip
unzip buffalo_l.zip
```

### Issue: Slow performance

**Check Python Architecture:**
```bash
python -c "import platform; print(platform.machine())"
```
If it shows "x86_64", you're running Rosetta 2. Reinstall ARM64 Python:
```bash
deactivate
rm -rf venv
brew install python@3.11
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements-macos-m.txt
```

### Issue: PostgreSQL connection refused

```bash
# Check if PostgreSQL is running
brew services list | grep postgresql

# Start PostgreSQL
brew services start postgresql@15

# Check port
lsof -i :5432
```

### Issue: Memory warnings

```bash
# Reduce image size in .env
MAX_IMAGE_SIZE=2048  # Instead of 4096
```

---

## Apple Silicon Specific Notes

### ✅ What Works Well
- **CPU Performance**: M-series chips have excellent CPU performance
- **Neural Engine**: CoreML provider can accelerate inference
- **Memory Efficiency**: Unified memory architecture is efficient
- **Power Efficiency**: Great battery life during development

### ⚠️ Limitations
- **No CUDA**: Cannot use onnxruntime-gpu (CUDA version)
- **Limited GPU Libraries**: Some GPU-accelerated libraries don't support Metal yet
- **Model Compatibility**: Some models may need optimization for CoreML

### 🔧 Optimizations
- Use CoreML Execution Provider for ONNX models
- Keep Python and dependencies ARM64 native (no Rosetta)
- Use Metal Performance Shaders when available
- Monitor memory usage with Activity Monitor

---

## Development Workflow on macOS

### Start Development Session

```bash
# Start services
brew services start postgresql@15 redis

# Activate virtual environment
cd couple-faceswap
source venv/bin/activate

# Start backend
cd backend
uvicorn app.main:app --reload &

# Start frontend (in new terminal)
cd frontend
npm run dev &
```

### Stop Development Session

```bash
# Stop servers (Ctrl+C in terminals)

# Stop services
brew services stop postgresql@15
brew services stop redis
```

### Run Tests

```bash
# Backend tests
cd backend
pytest tests/ -v

# Frontend tests
cd frontend
npm test

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

---

## Production Deployment on macOS

For production deployment on macOS servers (rare but possible):

```bash
# Use gunicorn instead of uvicorn
pip install gunicorn

# Run with multiple workers
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Use Nginx as reverse proxy
brew install nginx
```

**Note:** For production, Linux servers are recommended due to better containerization support.

---

## Useful macOS Commands

```bash
# Check system resources
top
# or use Activity Monitor GUI

# Check disk space
df -h

# Monitor GPU/Neural Engine usage
sudo powermetrics --samplers gpu_power

# Clean Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# Update Homebrew packages
brew update && brew upgrade
```

---

## Next Steps

1. ✅ **Phase 0 Complete** - Environment validated
2. 🚀 **Phase 1** - Start backend development
3. 🎨 **Phase 2** - Build frontend interface
4. 📊 **Testing** - Run comprehensive test suite

**See Also:**
- [PLAN.md](../PLAN.md) - Complete project roadmap
- [README.md](../README.md) - Project overview
- [QUICKSTART.md](../QUICKSTART.md) - General quick start guide

---

## Additional Resources

### Apple Silicon Development
- [Apple Silicon Guide](https://developer.apple.com/documentation/apple-silicon)
- [CoreML Documentation](https://developer.apple.com/documentation/coreml)
- [Metal Performance Shaders](https://developer.apple.com/documentation/metalperformanceshaders)

### ONNX Runtime on macOS
- [ONNX Runtime Execution Providers](https://onnxruntime.ai/docs/execution-providers/)
- [CoreML Execution Provider](https://onnxruntime.ai/docs/execution-providers/CoreML-ExecutionProvider.html)

### Python on Apple Silicon
- [Python 3.11 on ARM64](https://www.python.org/downloads/macos/)
- [Homebrew Python Guide](https://docs.brew.sh/Homebrew-and-Python)

---

**Last Updated:** 2025-10-27
**Tested On:** macOS Sonoma 14.x, Apple M2 Pro
**Status:** ✅ Fully Supported
