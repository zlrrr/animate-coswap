# Cross-Platform Support Strategy

## Supported Platforms

The Couple Face-Swap project supports multiple hardware platforms and operating systems with optimized configurations for each.

---

## Platform Matrix

| Platform | Architecture | Acceleration | Status | Performance |
|----------|-------------|--------------|--------|-------------|
| **macOS M1/M2/M3/M4** | ARM64 | CoreML / Neural Engine | ✅ Fully Supported | Excellent (native) |
| **macOS Intel** | x86_64 | CPU | ✅ Supported | Good |
| **Linux x86_64** | x86_64 | CUDA / CPU | ✅ Fully Supported | Excellent (with GPU) |
| **Linux ARM64** | ARM64 | CUDA (Jetson) / CPU | ✅ Supported | Good |
| **Windows** | x86_64 | CUDA / CPU | ✅ Supported | Excellent (with GPU) |
| **Raspberry Pi** | ARM64 | CPU | ⚠️ Limited | Slow (CPU only) |

---

## Platform-Specific Configurations

### 1. macOS Apple Silicon (M1/M2/M3/M4) - ⭐ RECOMMENDED

**Advantages:**
- Excellent CPU performance
- Apple Neural Engine acceleration via CoreML
- Unified memory architecture
- Great power efficiency
- Native ARM64 Python packages

**Requirements:**
```bash
# Install ARM64 native Python
brew install python@3.11

# Use macOS-specific requirements
pip install -r backend/requirements-macos-m.txt
```

**Configuration (.env):**
```bash
USE_GPU=false  # macOS doesn't use CUDA
ACCELERATION_PROVIDER=coreml  # Use CoreML for Neural Engine
```

**Performance:**
- Single face swap: ~1-2s (M2/M3)
- Couple face swap: ~2-4s (M2/M3)
- Face detection: ~30-50ms

**Getting Started:**
See [docs/GETTING-STARTED-MACOS-M.md](./GETTING-STARTED-MACOS-M.md)

---

### 2. Linux x86_64 with NVIDIA GPU - ⭐ BEST FOR PRODUCTION

**Advantages:**
- Best performance with CUDA acceleration
- Proven production deployment
- Excellent Docker support
- Wide hardware compatibility

**Requirements:**
```bash
# Install CUDA (11.x or 12.x)
# See: https://developer.nvidia.com/cuda-downloads

# Use Linux x86 requirements with GPU support
pip install -r backend/requirements-linux-x86.txt
pip uninstall onnxruntime
pip install onnxruntime-gpu==1.16.3
```

**Configuration (.env):**
```bash
USE_GPU=true
ACCELERATION_PROVIDER=cuda
GPU_DEVICE_ID=0  # First GPU
```

**Performance:**
- Single face swap: ~0.5-1s (RTX 3060+)
- Couple face swap: ~1-2s (RTX 3060+)
- Face detection: ~20-30ms

**Docker Deployment:**
```yaml
# docker-compose.yml
services:
  backend:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

---

### 3. Linux x86_64 CPU Only

**Advantages:**
- No GPU required
- Lower cost
- Good for development/testing

**Requirements:**
```bash
pip install -r backend/requirements-linux-x86.txt
```

**Configuration (.env):**
```bash
USE_GPU=false
ACCELERATION_PROVIDER=cpu
```

**Performance:**
- Single face swap: ~5-10s
- Couple face swap: ~10-20s
- Face detection: ~100-200ms

---

### 4. Linux ARM64 (Jetson, Graviton, Raspberry Pi)

**Jetson Devices (NVIDIA):**
- **Advantages**: CUDA support on ARM64
- **Performance**: Similar to x86_64 with GPU
- **Setup**: Use JetPack SDK

```bash
# Jetson-specific setup
pip install -r backend/requirements-linux-arm.txt
# Install onnxruntime-gpu for ARM64-CUDA (from NVIDIA)
```

**AWS Graviton / Other ARM servers:**
- **Advantages**: Cost-effective, good CPU performance
- **Performance**: Moderate (CPU only)

```bash
pip install -r backend/requirements-linux-arm.txt
```

**Raspberry Pi 4/5:**
- **Status**: Limited support
- **Performance**: Slow (not recommended for production)
- **Use Case**: Development/testing only

---

### 5. Windows x86_64

**With NVIDIA GPU:**
```bash
# Install CUDA Toolkit
# Download from: https://developer.nvidia.com/cuda-downloads

pip install -r backend/requirements-windows.txt
pip uninstall onnxruntime
pip install onnxruntime-gpu==1.16.3
```

**Configuration (.env):**
```bash
USE_GPU=true
ACCELERATION_PROVIDER=cuda
GPU_DEVICE_ID=0
```

**CPU Only:**
```bash
pip install -r backend/requirements-windows.txt
```

**Configuration (.env):**
```bash
USE_GPU=false
ACCELERATION_PROVIDER=cpu
```

---

## Acceleration Backends

### ONNX Runtime Execution Providers

The project uses ONNX Runtime with different execution providers:

| Provider | Platform | Hardware | Performance |
|----------|----------|----------|-------------|
| **CUDAExecutionProvider** | Linux/Windows | NVIDIA GPU | ⭐⭐⭐⭐⭐ Excellent |
| **CoreMLExecutionProvider** | macOS | Apple Neural Engine | ⭐⭐⭐⭐ Very Good |
| **CPUExecutionProvider** | All | CPU | ⭐⭐ Moderate |

### Auto-Detection

The system automatically detects the best available provider:

```python
# Automatic detection
ACCELERATION_PROVIDER=auto  # Recommended

# Manual override
ACCELERATION_PROVIDER=cuda   # Force CUDA
ACCELERATION_PROVIDER=coreml # Force CoreML
ACCELERATION_PROVIDER=cpu    # Force CPU
```

---

## Installation Quick Reference

### Automatic Platform Detection

```bash
# Run platform detection script
python scripts/detect_platform.py

# Output example:
# Platform: macOS Apple Silicon (M2 Pro)
# Recommended: requirements-macos-m.txt
# Acceleration: CoreML (Apple Neural Engine)
```

### Install Dependencies

```bash
# Automatic installation based on platform
python scripts/detect_platform.py --install

# Or manually:
# macOS M-series
pip install -r backend/requirements-macos-m.txt

# Linux x86_64
pip install -r backend/requirements-linux-x86.txt

# Linux ARM64
pip install -r backend/requirements-linux-arm.txt

# Windows
pip install -r backend/requirements-windows.txt
```

---

## Performance Benchmarks

### Face Detection (640x640 image)

| Platform | Time | Notes |
|----------|------|-------|
| M2 Pro (CoreML) | 40ms | Apple Neural Engine |
| RTX 3060 (CUDA) | 25ms | NVIDIA GPU |
| i7-12700K (CPU) | 120ms | Intel 12th gen |
| Graviton 3 (ARM) | 80ms | AWS ARM CPU |

### Single Face Swap (1024x1024 template)

| Platform | Time | Notes |
|----------|------|-------|
| M2 Pro (CoreML) | 1.5s | Apple Neural Engine |
| RTX 3060 (CUDA) | 0.7s | NVIDIA GPU |
| i7-12700K (CPU) | 6s | Intel 12th gen |
| Graviton 3 (ARM) | 9s | AWS ARM CPU |

### Couple Face Swap (2048x2048 template)

| Platform | Time | Notes |
|----------|------|-------|
| M3 Pro (CoreML) | 2.5s | Latest Apple Silicon |
| RTX 4070 (CUDA) | 1.2s | NVIDIA GPU |
| i7-12700K (CPU) | 12s | Intel 12th gen |
| Raspberry Pi 5 | 45s | Not recommended |

*Benchmarks are approximate and depend on model complexity*

---

## Development Recommendations

### For Local Development

**macOS Developers:**
- ✅ Use native Apple Silicon Mac
- ✅ Leverage CoreML acceleration
- ✅ Great battery life for mobile development

**Linux Developers:**
- ✅ Use Linux workstation with NVIDIA GPU
- ✅ Best performance for testing
- ✅ Matches production environment

**Windows Developers:**
- ✅ Use WSL2 for Linux compatibility
- ✅ Or use Windows natively with NVIDIA GPU
- ⚠️ Docker Desktop recommended for services

### For Production Deployment

**Recommended Stack:**
1. **Primary**: Linux x86_64 + NVIDIA GPU (best performance)
2. **Alternative**: Linux ARM64 (Graviton) for cost efficiency
3. **Not Recommended**: Raspberry Pi, old hardware

---

## Troubleshooting by Platform

### macOS M-series

**Issue: "Running under Rosetta 2"**
```bash
# Check architecture
python -c "import platform; print(platform.machine())"
# Should show "arm64", not "x86_64"

# Fix: Reinstall ARM64 Python
deactivate
rm -rf venv
brew install python@3.11
python3.11 -m venv venv
source venv/bin/activate
```

**Issue: "CoreML provider not available"**
```bash
# Check ONNX Runtime providers
python -c "import onnxruntime; print(onnxruntime.get_available_providers())"

# Should include: ['CoreMLExecutionProvider', 'CPUExecutionProvider']

# Fix: Reinstall onnxruntime
pip uninstall onnxruntime onnxruntime-gpu
pip install onnxruntime==1.16.3
```

### Linux with NVIDIA GPU

**Issue: "CUDA not available"**
```bash
# Check NVIDIA driver
nvidia-smi

# Check CUDA version
nvcc --version

# Install onnxruntime-gpu
pip uninstall onnxruntime
pip install onnxruntime-gpu==1.16.3
```

**Issue: "CUDA out of memory"**
```bash
# Reduce image size in .env
MAX_IMAGE_SIZE=2048  # Instead of 4096

# Or use smaller batch sizes
```

### Windows

**Issue: "Redis not found"**
```bash
# Option 1: Use Docker Desktop
docker run -d -p 6379:6379 redis:alpine

# Option 2: Use WSL2
wsl -d Ubuntu
sudo apt install redis-server
redis-server
```

---

## Migration Guide

### From Linux to macOS M-series

1. **Update requirements:**
   ```bash
   pip uninstall -r requirements-linux-x86.txt
   pip install -r requirements-macos-m.txt
   ```

2. **Update .env:**
   ```bash
   # Remove CUDA settings
   # USE_GPU=true
   # Add CoreML settings
   ACCELERATION_PROVIDER=coreml
   ```

3. **Test:**
   ```bash
   python scripts/detect_platform.py
   pytest tests/test_faceswap_core.py -v
   ```

### From macOS to Linux Production

1. **Prepare Docker:**
   ```bash
   # Build for Linux on macOS
   docker buildx build --platform linux/amd64 -t faceswap-backend .
   ```

2. **Configure GPU:**
   ```yaml
   # docker-compose.yml
   deploy:
     resources:
       reservations:
         devices:
           - driver: nvidia
             capabilities: [gpu]
   ```

---

## Best Practices

### ✅ Do's

- Use platform-specific requirements files
- Run platform detection script before setup
- Match development and production platforms when possible
- Use GPU acceleration for production
- Monitor resource usage

### ❌ Don'ts

- Don't use Rosetta 2 on macOS (performance penalty)
- Don't mix onnxruntime and onnxruntime-gpu
- Don't deploy to Raspberry Pi for production
- Don't ignore platform warnings from detection script

---

## Future Platform Support

### Planned

- **AMD ROCm** (AMD GPUs on Linux)
- **Intel OpenVINO** (Intel GPUs/NPUs)
- **DirectML** (Windows with AMD/Intel GPUs)
- **TensorRT** (NVIDIA optimization)

### Under Consideration

- **Android** (mobile deployment)
- **iOS** (mobile deployment)
- **WebAssembly** (browser deployment)

---

**Last Updated:** 2025-10-27
**Maintained By:** Project Team
**Status:** ✅ Production Ready
