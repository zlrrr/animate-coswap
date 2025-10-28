"""
Platform detection and acceleration provider utilities
"""

import platform
import logging
from typing import List, Tuple, Optional

# Try to import onnxruntime at module level for better testability
try:
    import onnxruntime as ort
    ONNXRUNTIME_AVAILABLE = True
except ImportError:
    ort = None
    ONNXRUNTIME_AVAILABLE = False

logger = logging.getLogger(__name__)


def detect_acceleration_provider(preferred: str = "auto") -> Tuple[List[str], str]:
    """
    Detect the best available acceleration provider for ONNX Runtime.

    Args:
        preferred: Preferred provider ("cuda", "coreml", "cpu", or "auto")

    Returns:
        Tuple of (providers_list, description)
        - providers_list: Ordered list of ONNX Runtime execution providers
        - description: Human-readable description of selected provider

    Example:
        >>> providers, desc = detect_acceleration_provider("auto")
        >>> print(desc)
        'CoreML (Apple Neural Engine) - Apple M2 Pro'
    """
    system = platform.system().lower()
    machine = platform.machine().lower()

    # If specific provider requested, try to use it
    if preferred != "auto":
        return _get_specific_provider(preferred)

    # Auto-detect based on platform
    # macOS Apple Silicon - Use CoreML
    if system == "darwin" and machine in ["arm64", "aarch64"]:
        return _get_coreml_provider()

    # Linux/Windows x86_64 - Try CUDA first, fall back to CPU
    elif machine in ["x86_64", "amd64"]:
        cuda_available = _check_cuda_available()
        if cuda_available:
            return _get_cuda_provider()
        else:
            return _get_cpu_provider()

    # ARM64 Linux (Jetson, Raspberry Pi, etc.)
    elif system == "linux" and machine in ["arm64", "aarch64"]:
        # Check if CUDA is available (Jetson devices)
        cuda_available = _check_cuda_available()
        if cuda_available:
            return _get_cuda_provider()
        else:
            return _get_cpu_provider()

    # Default to CPU
    else:
        logger.warning(f"Unknown platform: {system} {machine}, using CPU")
        return _get_cpu_provider()


def _get_specific_provider(provider: str) -> Tuple[List[str], str]:
    """Get a specific provider configuration"""
    provider = provider.lower()

    if provider == "cuda":
        return _get_cuda_provider()
    elif provider == "coreml":
        return _get_coreml_provider()
    elif provider == "cpu":
        return _get_cpu_provider()
    else:
        logger.warning(f"Unknown provider '{provider}', using CPU")
        return _get_cpu_provider()


def _get_cuda_provider() -> Tuple[List[str], str]:
    """Get CUDA provider configuration"""
    if not ONNXRUNTIME_AVAILABLE or ort is None:
        logger.warning("ONNX Runtime not available, falling back to CPU")
        return _get_cpu_provider()

    try:
        available = ort.get_available_providers()

        if "CUDAExecutionProvider" in available:
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
            desc = "CUDA (NVIDIA GPU)"
            logger.info(f"Using {desc}")
            return providers, desc
        else:
            logger.warning("CUDA requested but not available, falling back to CPU")
            return _get_cpu_provider()
    except Exception as e:
        logger.error(f"Error checking CUDA availability: {e}")
        return _get_cpu_provider()


def _get_coreml_provider() -> Tuple[List[str], str]:
    """Get CoreML provider configuration (macOS)"""
    if not ONNXRUNTIME_AVAILABLE or ort is None:
        logger.warning("ONNX Runtime not available, falling back to CPU")
        return _get_cpu_provider()

    try:
        available = ort.get_available_providers()

        if "CoreMLExecutionProvider" in available:
            providers = ["CoreMLExecutionProvider", "CPUExecutionProvider"]

            # Get Mac model info
            try:
                import subprocess
                result = subprocess.run(
                    ["sysctl", "-n", "machdep.cpu.brand_string"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                cpu_info = result.stdout.strip()
                desc = f"CoreML (Apple Neural Engine) - {cpu_info}"
            except:
                desc = "CoreML (Apple Neural Engine)"

            logger.info(f"Using {desc}")
            return providers, desc
        else:
            logger.warning("CoreML requested but not available, falling back to CPU")
            return _get_cpu_provider()
    except Exception as e:
        logger.error(f"Error checking CoreML availability: {e}")
        return _get_cpu_provider()


def _get_cpu_provider() -> Tuple[List[str], str]:
    """Get CPU-only provider configuration"""
    providers = ["CPUExecutionProvider"]
    system = platform.system()
    machine = platform.machine()
    desc = f"CPU ({system} {machine})"
    logger.info(f"Using {desc}")
    return providers, desc


def _check_cuda_available() -> bool:
    """Check if NVIDIA CUDA is available"""
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    except Exception as e:
        logger.debug(f"Error checking CUDA: {e}")
        return False


def get_platform_info() -> dict:
    """
    Get comprehensive platform information.

    Returns:
        Dictionary with platform details
    """
    system = platform.system()
    machine = platform.machine()
    python_version = platform.python_version()

    info = {
        "system": system,
        "machine": machine,
        "python_version": python_version,
        "platform": platform.platform(),
    }

    # Add macOS-specific info
    if system == "Darwin":
        info["macos_version"] = platform.mac_ver()[0]
        info["is_apple_silicon"] = machine in ["arm64", "aarch64"]

    # Add CUDA info
    info["cuda_available"] = _check_cuda_available()

    # Get ONNX Runtime providers
    if ONNXRUNTIME_AVAILABLE and ort is not None:
        try:
            info["onnx_providers"] = ort.get_available_providers()
        except Exception:
            info["onnx_providers"] = []
    else:
        info["onnx_providers"] = []

    return info


def log_platform_info():
    """Log platform information for debugging"""
    info = get_platform_info()

    logger.info("=" * 60)
    logger.info("Platform Information")
    logger.info("=" * 60)
    logger.info(f"System:          {info['system']}")
    logger.info(f"Machine:         {info['machine']}")
    logger.info(f"Python Version:  {info['python_version']}")
    logger.info(f"Platform:        {info['platform']}")

    if "macos_version" in info:
        logger.info(f"macOS Version:   {info['macos_version']}")
        logger.info(f"Apple Silicon:   {info['is_apple_silicon']}")

    logger.info(f"CUDA Available:  {info['cuda_available']}")
    logger.info(f"ONNX Providers:  {', '.join(info['onnx_providers'])}")
    logger.info("=" * 60)
