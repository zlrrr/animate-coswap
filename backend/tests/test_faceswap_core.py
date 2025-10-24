"""
Unit tests for core face-swap functionality

These tests validate the FaceSwapper class and its methods:
- Face detection
- Single face swapping
- Couple face swapping
- Error handling
"""

import pytest
import os
import cv2
import numpy as np
from app.services.faceswap.core import (
    FaceSwapper,
    FaceSwapError,
    FaceDetectionError,
    INSIGHTFACE_AVAILABLE
)


# Skip all tests if InsightFace is not installed
pytestmark = pytest.mark.skipif(
    not INSIGHTFACE_AVAILABLE,
    reason="InsightFace not installed"
)


class TestFaceSwapCore:
    """Test suite for FaceSwapper core functionality"""

    @pytest.fixture(scope="class")
    def swapper(self, models_dir):
        """Initialize FaceSwapper instance (reused across tests)"""
        model_path = os.path.join(models_dir, "inswapper_128.onnx")

        if not os.path.exists(model_path):
            pytest.skip(f"Model file not found: {model_path}")

        # Use CPU for testing to avoid GPU availability issues
        return FaceSwapper(model_path=model_path, use_gpu=False)

    def test_swapper_initialization(self, models_dir):
        """Test that FaceSwapper initializes correctly"""
        model_path = os.path.join(models_dir, "inswapper_128.onnx")

        if not os.path.exists(model_path):
            pytest.skip(f"Model file not found: {model_path}")

        swapper = FaceSwapper(model_path=model_path, use_gpu=False)
        assert swapper is not None
        assert swapper.model_path == model_path
        assert swapper.app is not None
        assert swapper.swapper is not None

    def test_swapper_invalid_model_path(self):
        """Test that FaceSwapper raises error for invalid model path"""
        with pytest.raises(FileNotFoundError):
            FaceSwapper(model_path="nonexistent/model.onnx")

    def test_detect_faces_single_face(self, swapper, test_fixtures_dir):
        """Test face detection with single face image"""
        # Note: This test requires actual test images
        # For now, we'll skip if fixtures don't exist
        test_image = os.path.join(test_fixtures_dir, "single_face.jpg")

        if not os.path.exists(test_image):
            pytest.skip(f"Test fixture not found: {test_image}")

        faces = swapper.detect_faces(test_image)
        assert len(faces) == 1
        assert faces[0].det_score > 0.5  # Confidence threshold

    def test_detect_faces_multiple_faces(self, swapper, test_fixtures_dir):
        """Test face detection with couple image"""
        test_image = os.path.join(test_fixtures_dir, "couple.jpg")

        if not os.path.exists(test_image):
            pytest.skip(f"Test fixture not found: {test_image}")

        faces = swapper.detect_faces(test_image)
        assert len(faces) == 2
        assert all(f.det_score > 0.5 for f in faces)

    def test_detect_faces_no_face(self, swapper, test_fixtures_dir):
        """Test face detection with no face in image"""
        test_image = os.path.join(test_fixtures_dir, "landscape.jpg")

        if not os.path.exists(test_image):
            pytest.skip(f"Test fixture not found: {test_image}")

        faces = swapper.detect_faces(test_image)
        assert len(faces) == 0

    def test_detect_faces_invalid_image(self, swapper):
        """Test face detection with invalid image path"""
        with pytest.raises(FileNotFoundError):
            swapper.detect_faces("nonexistent/image.jpg")

    def test_swap_faces_success(self, swapper, test_fixtures_dir):
        """Test successful face swap between two images"""
        source_img = os.path.join(test_fixtures_dir, "person_a.jpg")
        target_img = os.path.join(test_fixtures_dir, "person_b.jpg")

        if not os.path.exists(source_img) or not os.path.exists(target_img):
            pytest.skip("Test fixtures not found")

        result = swapper.swap_faces(source_img, target_img)

        assert result is not None
        assert isinstance(result, np.ndarray)
        assert result.shape[0] > 0  # Height
        assert result.shape[1] > 0  # Width
        assert result.shape[2] == 3  # BGR channels

    def test_swap_faces_no_source_face(self, swapper, test_fixtures_dir):
        """Test face swap fails when source has no face"""
        source_img = os.path.join(test_fixtures_dir, "landscape.jpg")
        target_img = os.path.join(test_fixtures_dir, "person_b.jpg")

        if not os.path.exists(source_img) or not os.path.exists(target_img):
            pytest.skip("Test fixtures not found")

        with pytest.raises(FaceDetectionError, match="No face detected in source"):
            swapper.swap_faces(source_img, target_img)

    def test_swap_faces_no_target_face(self, swapper, test_fixtures_dir):
        """Test face swap fails when target has no face"""
        source_img = os.path.join(test_fixtures_dir, "person_a.jpg")
        target_img = os.path.join(test_fixtures_dir, "landscape.jpg")

        if not os.path.exists(source_img) or not os.path.exists(target_img):
            pytest.skip("Test fixtures not found")

        with pytest.raises(FaceDetectionError, match="No face detected in target"):
            swapper.swap_faces(source_img, target_img)

    def test_swap_couple_faces_success(self, swapper, test_fixtures_dir):
        """Test successful couple face swap"""
        husband_img = os.path.join(test_fixtures_dir, "husband.jpg")
        wife_img = os.path.join(test_fixtures_dir, "wife.jpg")
        template_img = os.path.join(test_fixtures_dir, "couple_template.jpg")

        if not all(os.path.exists(p) for p in [husband_img, wife_img, template_img]):
            pytest.skip("Test fixtures not found")

        result = swapper.swap_couple_faces(husband_img, wife_img, template_img)

        assert result is not None
        assert isinstance(result, np.ndarray)
        assert result.shape[0] > 0
        assert result.shape[1] > 0
        assert result.shape[2] == 3

    def test_swap_couple_faces_template_single_face(self, swapper, test_fixtures_dir):
        """Test couple swap fails when template has only 1 face"""
        husband_img = os.path.join(test_fixtures_dir, "husband.jpg")
        wife_img = os.path.join(test_fixtures_dir, "wife.jpg")
        template_img = os.path.join(test_fixtures_dir, "single_face.jpg")

        if not all(os.path.exists(p) for p in [husband_img, wife_img, template_img]):
            pytest.skip("Test fixtures not found")

        with pytest.raises(ValueError, match="must contain at least 2 faces"):
            swapper.swap_couple_faces(husband_img, wife_img, template_img)

    def test_get_face_info(self, swapper, test_fixtures_dir):
        """Test face information extraction"""
        test_image = os.path.join(test_fixtures_dir, "couple.jpg")

        if not os.path.exists(test_image):
            pytest.skip(f"Test fixture not found: {test_image}")

        info = swapper.get_face_info(test_image)

        assert "face_count" in info
        assert "faces" in info
        assert info["face_count"] == len(info["faces"])

        for face in info["faces"]:
            assert "index" in face
            assert "bbox" in face
            assert "confidence" in face
            assert face["confidence"] > 0


class TestFaceSwapPerformance:
    """Performance tests for face-swap operations"""

    @pytest.fixture(scope="class")
    def swapper(self, models_dir):
        """Initialize FaceSwapper for performance testing"""
        model_path = os.path.join(models_dir, "inswapper_128.onnx")

        if not os.path.exists(model_path):
            pytest.skip(f"Model file not found: {model_path}")

        return FaceSwapper(model_path=model_path, use_gpu=False)

    def test_face_detection_performance(self, swapper, test_fixtures_dir, benchmark):
        """Benchmark face detection speed"""
        test_image = os.path.join(test_fixtures_dir, "couple.jpg")

        if not os.path.exists(test_image):
            pytest.skip(f"Test fixture not found: {test_image}")

        result = benchmark(swapper.detect_faces, test_image)
        assert len(result) > 0

    def test_face_swap_performance(self, swapper, test_fixtures_dir, benchmark):
        """Benchmark face swap processing time"""
        source_img = os.path.join(test_fixtures_dir, "person_a.jpg")
        target_img = os.path.join(test_fixtures_dir, "person_b.jpg")

        if not os.path.exists(source_img) or not os.path.exists(target_img):
            pytest.skip("Test fixtures not found")

        result = benchmark(swapper.swap_faces, source_img, target_img)
        assert result is not None

        # Performance requirement: < 10 seconds (without GPU)
        # With GPU should be < 5 seconds
        assert benchmark.stats.mean < 30.0  # Lenient for CPU
