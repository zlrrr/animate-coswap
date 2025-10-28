"""
Unit tests for platform utilities module
"""

import pytest
import platform
from unittest.mock import patch, MagicMock
from app.utils.platform_utils import (
    detect_acceleration_provider,
    get_platform_info,
    _get_cuda_provider,
    _get_coreml_provider,
    _get_cpu_provider,
    _check_cuda_available
)


class TestDetectAccelerationProvider:
    """Test acceleration provider detection"""

    def test_detect_auto_macos_arm64(self):
        """Test auto-detection on macOS ARM64"""
        with patch('platform.system', return_value='Darwin'), \
             patch('platform.machine', return_value='arm64'), \
             patch('app.utils.platform_utils._check_cuda_available', return_value=False):

            providers, desc = detect_acceleration_provider("auto")

            # Should contain CoreML provider (if available) or CPU
            assert isinstance(providers, list)
            assert len(providers) > 0
            assert isinstance(desc, str)
            # CoreML or CPU should be mentioned
            assert "CoreML" in desc or "CPU" in desc

    def test_detect_auto_linux_x86_with_cuda(self):
        """Test auto-detection on Linux x86_64 with CUDA"""
        with patch('platform.system', return_value='Linux'), \
             patch('platform.machine', return_value='x86_64'), \
             patch('app.utils.platform_utils._check_cuda_available', return_value=True):

            # Mock onnxruntime to include CUDA provider
            mock_ort = MagicMock()
            mock_ort.get_available_providers.return_value = ['CUDAExecutionProvider', 'CPUExecutionProvider']

            with patch('app.utils.platform_utils.ort', mock_ort), \
                 patch('app.utils.platform_utils.ONNXRUNTIME_AVAILABLE', True):
                providers, desc = detect_acceleration_provider("auto")

                assert 'CUDAExecutionProvider' in providers or 'CPUExecutionProvider' in providers
                assert isinstance(desc, str)

    def test_detect_auto_linux_x86_without_cuda(self):
        """Test auto-detection on Linux x86_64 without CUDA"""
        with patch('platform.system', return_value='Linux'), \
             patch('platform.machine', return_value='x86_64'), \
             patch('app.utils.platform_utils._check_cuda_available', return_value=False):

            providers, desc = detect_acceleration_provider("auto")

            assert 'CPUExecutionProvider' in providers
            assert 'CPU' in desc

    def test_detect_specific_cuda(self):
        """Test requesting specific CUDA provider"""
        providers, desc = detect_acceleration_provider("cuda")

        assert isinstance(providers, list)
        assert isinstance(desc, str)
        # Should attempt to use CUDA or fallback to CPU
        assert 'CUDA' in desc or 'CPU' in desc

    def test_detect_specific_coreml(self):
        """Test requesting specific CoreML provider"""
        providers, desc = detect_acceleration_provider("coreml")

        assert isinstance(providers, list)
        assert isinstance(desc, str)
        # Should attempt to use CoreML or fallback to CPU
        assert 'CoreML' in desc or 'CPU' in desc

    def test_detect_specific_cpu(self):
        """Test requesting specific CPU provider"""
        providers, desc = detect_acceleration_provider("cpu")

        assert providers == ['CPUExecutionProvider']
        assert 'CPU' in desc

    def test_detect_unknown_provider_fallback(self):
        """Test that unknown provider falls back to CPU"""
        providers, desc = detect_acceleration_provider("unknown_provider")

        assert providers == ['CPUExecutionProvider']
        assert 'CPU' in desc


class TestCudaProvider:
    """Test CUDA provider configuration"""

    def test_cuda_provider_available(self):
        """Test CUDA provider when available"""
        mock_ort = MagicMock()
        mock_ort.get_available_providers.return_value = ['CUDAExecutionProvider', 'CPUExecutionProvider']

        with patch('app.utils.platform_utils.ort', mock_ort), \
             patch('app.utils.platform_utils.ONNXRUNTIME_AVAILABLE', True):
            providers, desc = _get_cuda_provider()

            assert 'CUDAExecutionProvider' in providers
            assert 'CPUExecutionProvider' in providers
            assert 'CUDA' in desc

    def test_cuda_provider_not_available(self):
        """Test CUDA provider when not available"""
        mock_ort = MagicMock()
        mock_ort.get_available_providers.return_value = ['CPUExecutionProvider']

        with patch('app.utils.platform_utils.ort', mock_ort), \
             patch('app.utils.platform_utils.ONNXRUNTIME_AVAILABLE', True):
            providers, desc = _get_cuda_provider()

            # Should fallback to CPU
            assert providers == ['CPUExecutionProvider']
            assert 'CPU' in desc

    def test_cuda_provider_import_error(self):
        """Test CUDA provider when onnxruntime not available"""
        with patch('app.utils.platform_utils.ort', None), \
             patch('app.utils.platform_utils.ONNXRUNTIME_AVAILABLE', False):
            providers, desc = _get_cuda_provider()

            # Should fallback to CPU
            assert providers == ['CPUExecutionProvider']
            assert 'CPU' in desc


class TestCoreMLProvider:
    """Test CoreML provider configuration"""

    def test_coreml_provider_available(self):
        """Test CoreML provider when available"""
        mock_ort = MagicMock()
        mock_ort.get_available_providers.return_value = ['CoreMLExecutionProvider', 'CPUExecutionProvider']

        with patch('app.utils.platform_utils.ort', mock_ort), \
             patch('app.utils.platform_utils.ONNXRUNTIME_AVAILABLE', True):
            providers, desc = _get_coreml_provider()

            assert 'CoreMLExecutionProvider' in providers
            assert 'CPUExecutionProvider' in providers
            assert 'CoreML' in desc

    def test_coreml_provider_not_available(self):
        """Test CoreML provider when not available"""
        mock_ort = MagicMock()
        mock_ort.get_available_providers.return_value = ['CPUExecutionProvider']

        with patch('app.utils.platform_utils.ort', mock_ort), \
             patch('app.utils.platform_utils.ONNXRUNTIME_AVAILABLE', True):
            providers, desc = _get_coreml_provider()

            # Should fallback to CPU
            assert providers == ['CPUExecutionProvider']
            assert 'CPU' in desc


class TestCPUProvider:
    """Test CPU provider configuration"""

    def test_cpu_provider(self):
        """Test CPU provider returns correct configuration"""
        providers, desc = _get_cpu_provider()

        assert providers == ['CPUExecutionProvider']
        assert 'CPU' in desc
        assert platform.system() in desc
        assert platform.machine() in desc


class TestCheckCudaAvailable:
    """Test CUDA availability check"""

    def test_cuda_available(self):
        """Test when nvidia-smi succeeds"""
        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch('subprocess.run', return_value=mock_result):
            assert _check_cuda_available() is True

    def test_cuda_not_available_command_not_found(self):
        """Test when nvidia-smi command not found"""
        with patch('subprocess.run', side_effect=FileNotFoundError):
            assert _check_cuda_available() is False

    def test_cuda_not_available_timeout(self):
        """Test when nvidia-smi times out"""
        import subprocess
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('nvidia-smi', 5)):
            assert _check_cuda_available() is False

    def test_cuda_not_available_error(self):
        """Test when nvidia-smi returns error"""
        mock_result = MagicMock()
        mock_result.returncode = 1

        with patch('subprocess.run', return_value=mock_result):
            assert _check_cuda_available() is False


class TestGetPlatformInfo:
    """Test platform information gathering"""

    def test_get_platform_info_structure(self):
        """Test that platform info returns correct structure"""
        info = get_platform_info()

        # Check required keys
        assert 'system' in info
        assert 'machine' in info
        assert 'python_version' in info
        assert 'platform' in info
        assert 'cuda_available' in info
        assert 'onnx_providers' in info

    def test_get_platform_info_macos_specific(self):
        """Test macOS-specific information"""
        with patch('platform.system', return_value='Darwin'), \
             patch('platform.mac_ver', return_value=('14.0', '', '')), \
             patch('platform.machine', return_value='arm64'):

            info = get_platform_info()

            if info['system'] == 'Darwin':
                assert 'macos_version' in info
                assert 'is_apple_silicon' in info

    def test_get_platform_info_cuda_check(self):
        """Test CUDA availability is checked"""
        info = get_platform_info()

        assert isinstance(info['cuda_available'], bool)

    def test_get_platform_info_onnx_providers(self):
        """Test ONNX providers are retrieved"""
        info = get_platform_info()

        assert isinstance(info['onnx_providers'], list)

    def test_get_platform_info_without_onnxruntime(self):
        """Test platform info when onnxruntime not installed"""
        with patch('app.utils.platform_utils.ONNXRUNTIME_AVAILABLE', False), \
             patch('app.utils.platform_utils.ort', None):
            info = get_platform_info()

            assert 'onnx_providers' in info
            assert isinstance(info['onnx_providers'], list)
            assert info['onnx_providers'] == []


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_provider_string(self):
        """Test with empty provider string"""
        providers, desc = detect_acceleration_provider("")

        # Should fallback to CPU
        assert providers == ['CPUExecutionProvider']
        assert 'CPU' in desc

    def test_none_provider(self):
        """Test with None provider (should handle gracefully)"""
        # This might raise an error, which is acceptable
        # or it should fallback to auto
        try:
            providers, desc = detect_acceleration_provider(None)
            # If it doesn't raise, should return valid result
            assert isinstance(providers, list)
            assert isinstance(desc, str)
        except (TypeError, AttributeError):
            # Acceptable to raise error for None
            pass

    def test_case_insensitive_provider(self):
        """Test that provider detection is case-insensitive"""
        providers_lower, _ = detect_acceleration_provider("cuda")
        providers_upper, _ = detect_acceleration_provider("CUDA")
        providers_mixed, _ = detect_acceleration_provider("CuDa")

        # All should return same result
        assert providers_lower == providers_upper == providers_mixed


class TestIntegration:
    """Integration tests for platform utilities"""

    def test_full_detection_flow(self):
        """Test complete detection flow"""
        # Get platform info
        info = get_platform_info()

        # Detect provider
        providers, desc = detect_acceleration_provider("auto")

        # Verify consistency
        assert isinstance(info, dict)
        assert isinstance(providers, list)
        assert len(providers) > 0
        assert isinstance(desc, str)
        assert len(desc) > 0

    def test_all_provider_types_work(self):
        """Test that all provider types can be requested"""
        provider_types = ["auto", "cuda", "coreml", "cpu"]

        for provider_type in provider_types:
            providers, desc = detect_acceleration_provider(provider_type)

            assert isinstance(providers, list)
            assert len(providers) > 0
            assert isinstance(desc, str)
            assert len(desc) > 0
            # All should include at least CPU provider
            assert 'CPUExecutionProvider' in providers or 'CoreMLExecutionProvider' in providers or 'CUDAExecutionProvider' in providers


class TestLogging:
    """Test logging functionality"""

    def test_log_platform_info_no_errors(self):
        """Test that log_platform_info doesn't raise errors"""
        from app.utils.platform_utils import log_platform_info

        # Should not raise any errors
        try:
            log_platform_info()
        except Exception as e:
            pytest.fail(f"log_platform_info raised {type(e).__name__}: {e}")
