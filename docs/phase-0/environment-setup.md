# Phase 0: Environment Setup Guide

## Prerequisites

### System Requirements

- **Operating System:** Linux (Ubuntu 20.04+), macOS, or Windows 10+
- **Python:** 3.10 or higher
- **Node.js:** 18.x or higher
- **RAM:** 8GB minimum, 16GB recommended
- **GPU:** CUDA-capable GPU (optional, but recommended for performance)
- **Disk Space:** 10GB minimum

### Required Software

1. **Python 3.10+**
   ```bash
   # Check version
   python --version

   # If needed, install via:
   # Ubuntu/Debian
   sudo apt update
   sudo apt install python3.10 python3.10-venv python3-pip

   # macOS (using Homebrew)
   brew install python@3.10

   # Windows
   # Download from https://www.python.org/downloads/
   ```

2. **Node.js 18+**
   ```bash
   # Check version
   node --version

   # Install via nvm (recommended)
   curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
   nvm install 18
   nvm use 18
   ```

3. **PostgreSQL 14+**
   ```bash
   # Ubuntu/Debian
   sudo apt install postgresql postgresql-contrib

   # macOS
   brew install postgresql@14

   # Start service
   sudo systemctl start postgresql  # Linux
   brew services start postgresql@14  # macOS
   ```

4. **Redis**
   ```bash
   # Ubuntu/Debian
   sudo apt install redis-server

   # macOS
   brew install redis

   # Start service
   sudo systemctl start redis  # Linux
   brew services start redis  # macOS
   ```

5. **Git**
   ```bash
   # Ubuntu/Debian
   sudo apt install git

   # macOS
   brew install git
   ```

## Python Environment Setup

### 1. Create Virtual Environment

```bash
# Navigate to project directory
cd couple-faceswap

# Create virtual environment
python3.10 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# OR
venv\Scripts\activate  # Windows
```

### 2. Install Python Dependencies

```bash
cd backend
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Verify Installation

```bash
# Check installed packages
pip list

# Verify key packages
python -c "import insightface; print('InsightFace OK')"
python -c "import fastapi; print('FastAPI OK')"
python -c "import cv2; print('OpenCV OK')"
```

## GPU Setup (Optional but Recommended)

### CUDA Installation

For NVIDIA GPUs:

```bash
# Check GPU availability
nvidia-smi

# Install CUDA Toolkit 11.8
# Visit: https://developer.nvidia.com/cuda-11-8-0-download-archive

# Verify CUDA
nvcc --version
```

### ONNX Runtime GPU

```bash
# Uninstall CPU version if installed
pip uninstall onnxruntime

# Install GPU version
pip install onnxruntime-gpu==1.16.3
```

### Verify GPU Support

```bash
python -c "import onnxruntime as ort; print(ort.get_available_providers())"
# Should include 'CUDAExecutionProvider'
```

## Model Download

### InsightFace Models

1. **Download inswapper model**

```bash
# Create models directory
mkdir -p backend/models

# Option 1: wget
wget https://huggingface.co/ezioruan/inswapper_128.onnx \
  -O backend/models/inswapper_128.onnx

# Option 2: curl
curl -L https://huggingface.co/ezioruan/inswapper_128.onnx \
  -o backend/models/inswapper_128.onnx

# Option 3: Manual download
# Visit: https://huggingface.co/ezioruan/inswapper_128.onnx
# Save to: backend/models/inswapper_128.onnx
```

2. **Verify model file**

```bash
ls -lh backend/models/inswapper_128.onnx
# Should show ~554MB file
```

## Database Setup

### 1. Create Database

```bash
# Connect to PostgreSQL
sudo -u postgres psql

# In psql shell:
CREATE DATABASE faceswap;
CREATE USER faceswap_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE faceswap TO faceswap_user;
\q
```

### 2. Configure Database Connection

Create `.env` file in `backend/` directory:

```bash
# backend/.env
DATABASE_URL=postgresql://faceswap_user:your_password@localhost:5432/faceswap
REDIS_URL=redis://localhost:6379/0
```

### 3. Run Migrations (Phase 1+)

```bash
cd backend
alembic upgrade head
```

## Test Fixtures Preparation

For algorithm validation, prepare test images:

```bash
# Create fixtures directory
mkdir -p tests/fixtures

# Add test images (see docs/phase-0/test-fixtures.md)
# Required images:
# - person_a.jpg, person_b.jpg (single face portraits)
# - couple.jpg, couple_template.jpg (couple images with 2 faces)
# - landscape.jpg (no faces)
# - single_face.jpg (1 face)
# - etc.
```

See [test-fixtures.md](./test-fixtures.md) for detailed requirements.

## Validation

Run the validation script to verify everything is set up correctly:

```bash
python scripts/validate_algorithm.py
```

This will check:
- ✓ Python version
- ✓ InsightFace installation
- ✓ Model availability
- ✓ Face detection
- ✓ Face swapping
- ✓ Performance benchmarks

## Troubleshooting

### Issue: InsightFace import error

```bash
# Solution: Install with specific versions
pip install insightface==0.7.3
pip install onnxruntime==1.16.3  # or onnxruntime-gpu
```

### Issue: CUDA out of memory

```python
# Solution: Use CPU mode
swapper = FaceSwapper(model_path="...", use_gpu=False)
```

### Issue: PostgreSQL connection refused

```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Start if not running
sudo systemctl start postgresql
```

### Issue: Permission denied for models directory

```bash
# Fix permissions
chmod -R 755 backend/models
```

## Docker Setup (Alternative)

For easier setup, use Docker:

```bash
# Build and run all services
docker-compose up --build

# Services will be available at:
# - Backend: http://localhost:8000
# - Frontend: http://localhost:3000
# - PostgreSQL: localhost:5432
# - Redis: localhost:6379
```

## Environment Variables

Create `.env` files:

**backend/.env:**
```env
# Database
DATABASE_URL=postgresql://faceswap_user:password@localhost:5432/faceswap

# Redis
REDIS_URL=redis://localhost:6379/0

# Storage
STORAGE_TYPE=local
STORAGE_PATH=./storage

# Models
MODELS_PATH=./models
INSWAPPER_MODEL=inswapper_128.onnx

# Processing
USE_GPU=true
GPU_DEVICE_ID=0
MAX_IMAGE_SIZE=4096

# API
API_V1_STR=/api/v1
PROJECT_NAME=Couple Face-Swap API
```

**frontend/.env:**
```env
VITE_API_URL=http://localhost:8000
VITE_APP_NAME=Couple Face-Swap
```

## Next Steps

After environment setup is complete:

1. ✓ Run validation script
2. ✓ Verify all tests pass
3. ✓ Review validation results
4. → Proceed to Phase 1: Backend Development

## Resources

- [InsightFace Documentation](https://github.com/deepinsight/insightface)
- [ONNX Runtime Documentation](https://onnxruntime.ai/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
