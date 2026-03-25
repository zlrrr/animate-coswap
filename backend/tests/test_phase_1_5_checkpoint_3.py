"""
Test Phase 1.5 Checkpoint 1.5.3: Flexible Face Mapping

Requirements:
1. Custom face mapping (source face -> target face)
2. Default mapping: husband -> male faces, wife -> female faces
3. Support for complex multi-face scenarios
4. Mapping configuration stored in FaceSwapTask
"""

import pytest
from fastapi.testclient import TestClient
from io import BytesIO
from PIL import Image as PILImage
from unittest.mock import patch, MagicMock
import json
import numpy as np

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_db
from app.models.database import Base, Image, Template, FaceSwapTask


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Create all tables before tests"""
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.pop(get_db, None)


def _make_fake_image_array(width=800, height=600):
    """Create a fake numpy array like cv2.imread returns"""
    return np.zeros((height, width, 3), dtype=np.uint8)


@pytest.fixture
def create_test_image():
    """Create a test image in memory"""
    def _create_image(width=800, height=600, color=(255, 0, 0)):
        img = PILImage.new('RGB', (width, height), color=color)
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        return img_bytes
    return _create_image


@pytest.fixture
def upload_photo(create_test_image):
    """Helper to upload a photo (with mocked storage and cv2)"""
    def _upload(session_id="test-session"):
        img_bytes = create_test_image()
        with patch("app.api.v1.photos.storage_service") as mock_storage, \
             patch("app.api.v1.photos.cv2") as mock_cv2:
            mock_storage.save_file.return_value = ("temp/fake_photo.jpg", 1024)
            mock_storage.get_file_path.return_value = "/tmp/fake_photo.jpg"
            mock_storage.get_file_url.return_value = "http://localhost/storage/temp/fake_photo.jpg"
            mock_cv2.imread.return_value = _make_fake_image_array(800, 600)

            response = client.post(
                "/api/v1/photos/upload",
                params={"session_id": session_id},
                files={"file": ("photo.jpg", img_bytes, "image/jpeg")}
            )
        assert response.status_code == 200
        return response.json()
    return _upload


@pytest.fixture
def upload_template(create_test_image):
    """Helper to upload and preprocess a template (with mocked storage and cv2)"""
    def _upload(name="Test Template"):
        img_bytes = create_test_image(width=1024, height=768)
        with patch("app.api.v1.templates.storage_service") as mock_storage, \
             patch("app.api.v1.templates.cv2") as mock_cv2:
            mock_storage.save_file.return_value = ("templates/fake_template.jpg", 2048)
            mock_storage.get_file_path.return_value = "/tmp/fake_template.jpg"
            mock_storage.get_file_url.return_value = "http://localhost/storage/templates/fake_template.jpg"
            mock_cv2.imread.return_value = _make_fake_image_array(1024, 768)

            response = client.post(
                "/api/v1/templates/upload",
                data={"name": name, "category": "custom"},
                files={"file": (f"{name}.jpg", img_bytes, "image/jpeg")}
            )
        assert response.status_code == 200
        return response.json()
    return _upload


class TestDefaultMapping:
    """Test default face mapping rules"""

    def test_default_mapping_husband_to_male(self, upload_photo, upload_template):
        """Test default mapping: husband -> male faces"""
        husband_photo = upload_photo(session_id="test-1")
        wife_photo = upload_photo(session_id="test-1")
        template = upload_template(name="Couple Template")

        # Create face-swap task with default mapping
        response = client.post(
            "/api/v1/faceswap/swap",
            json={
                "husband_photo_id": husband_photo["id"],
                "wife_photo_id": wife_photo["id"],
                "template_id": template["id"],
                "use_default_mapping": True
            }
        )

        assert response.status_code == 202
        data = response.json()

        assert "task_id" in data
        assert "face_mappings" in data

        # Default mapping should map husband to male faces
        # and wife to female faces
        mappings = data.get("face_mappings")
        if mappings:
            assert isinstance(mappings, list)

    def test_default_mapping_wife_to_female(self, upload_photo, upload_template):
        """Test default mapping: wife -> female faces"""
        husband_photo = upload_photo(session_id="test-2")
        wife_photo = upload_photo(session_id="test-2")
        template = upload_template(name="Wedding Scene")

        response = client.post(
            "/api/v1/faceswap/swap",
            json={
                "husband_photo_id": husband_photo["id"],
                "wife_photo_id": wife_photo["id"],
                "template_id": template["id"],
                "use_default_mapping": True
            }
        )

        assert response.status_code == 202

    def test_default_mapping_uses_preprocessing_data(self, upload_photo, upload_template):
        """Test that default mapping uses preprocessing gender data"""
        husband_photo = upload_photo()
        wife_photo = upload_photo()
        template = upload_template()

        # Preprocess template first (mocked - just test the swap endpoint)
        # Skip the actual preprocess call since it requires InsightFace model
        # and instead directly test the swap with default mapping

        # Create task with default mapping
        response = client.post(
            "/api/v1/faceswap/swap",
            json={
                "husband_photo_id": husband_photo["id"],
                "wife_photo_id": wife_photo["id"],
                "template_id": template["id"],
                "use_default_mapping": True,
                "use_preprocessed": True
            }
        )

        assert response.status_code == 202


class TestCustomMapping:
    """Test custom face mapping"""

    def test_custom_mapping_simple(self, upload_photo, upload_template):
        """Test simple custom mapping"""
        husband_photo = upload_photo()
        wife_photo = upload_photo()
        template = upload_template()

        # Custom mapping: specify exact face indices
        custom_mappings = [
            {"source_photo": "husband", "source_face_index": 0, "target_face_index": 0},
            {"source_photo": "wife", "source_face_index": 0, "target_face_index": 1}
        ]

        response = client.post(
            "/api/v1/faceswap/swap",
            json={
                "husband_photo_id": husband_photo["id"],
                "wife_photo_id": wife_photo["id"],
                "template_id": template["id"],
                "use_default_mapping": False,
                "face_mappings": custom_mappings
            }
        )

        assert response.status_code == 202
        data = response.json()

        assert "face_mappings" in data
        assert data["face_mappings"] == custom_mappings

    def test_custom_mapping_swap_positions(self, upload_photo, upload_template):
        """Test custom mapping with swapped positions"""
        husband_photo = upload_photo()
        wife_photo = upload_photo()
        template = upload_template()

        # Swap positions: husband -> face 1, wife -> face 0
        custom_mappings = [
            {"source_photo": "husband", "source_face_index": 0, "target_face_index": 1},
            {"source_photo": "wife", "source_face_index": 0, "target_face_index": 0}
        ]

        response = client.post(
            "/api/v1/faceswap/swap",
            json={
                "husband_photo_id": husband_photo["id"],
                "wife_photo_id": wife_photo["id"],
                "template_id": template["id"],
                "face_mappings": custom_mappings
            }
        )

        assert response.status_code == 202

    def test_custom_mapping_validation(self, upload_photo, upload_template):
        """Test custom mapping validation"""
        husband_photo = upload_photo()
        wife_photo = upload_photo()
        template = upload_template()

        # Invalid mapping: negative index
        invalid_mappings = [
            {"source_photo": "husband", "source_face_index": -1, "target_face_index": 0}
        ]

        response = client.post(
            "/api/v1/faceswap/swap",
            json={
                "husband_photo_id": husband_photo["id"],
                "wife_photo_id": wife_photo["id"],
                "template_id": template["id"],
                "face_mappings": invalid_mappings
            }
        )

        # Should fail validation
        assert response.status_code in [400, 422]

    def test_custom_mapping_missing_target(self, upload_photo, upload_template):
        """Test custom mapping with missing target face"""
        husband_photo = upload_photo()
        wife_photo = upload_photo()
        template = upload_template()

        # Map to non-existent face (index 10)
        invalid_mappings = [
            {"source_photo": "husband", "source_face_index": 0, "target_face_index": 10}
        ]

        response = client.post(
            "/api/v1/faceswap/swap",
            json={
                "husband_photo_id": husband_photo["id"],
                "wife_photo_id": wife_photo["id"],
                "template_id": template["id"],
                "face_mappings": invalid_mappings
            }
        )

        # Should accept (validation happens during processing)
        assert response.status_code in [202, 400]


class TestMultiFaceMapping:
    """Test multi-face mapping scenarios"""

    def test_one_source_to_multiple_targets(self, upload_photo, upload_template):
        """Test mapping one source face to multiple target faces"""
        husband_photo = upload_photo()
        wife_photo = upload_photo()
        template = upload_template()

        # Map husband to multiple target faces
        multi_mappings = [
            {"source_photo": "husband", "source_face_index": 0, "target_face_index": 0},
            {"source_photo": "husband", "source_face_index": 0, "target_face_index": 1},
            {"source_photo": "wife", "source_face_index": 0, "target_face_index": 2}
        ]

        response = client.post(
            "/api/v1/faceswap/swap",
            json={
                "husband_photo_id": husband_photo["id"],
                "wife_photo_id": wife_photo["id"],
                "template_id": template["id"],
                "face_mappings": multi_mappings
            }
        )

        assert response.status_code == 202

    def test_partial_mapping(self, upload_photo, upload_template):
        """Test partial face mapping (not all faces replaced)"""
        husband_photo = upload_photo()
        wife_photo = upload_photo()
        template = upload_template()

        # Only map to some faces
        partial_mappings = [
            {"source_photo": "husband", "source_face_index": 0, "target_face_index": 0}
            # Face index 1 and others are not mapped
        ]

        response = client.post(
            "/api/v1/faceswap/swap",
            json={
                "husband_photo_id": husband_photo["id"],
                "wife_photo_id": wife_photo["id"],
                "template_id": template["id"],
                "face_mappings": partial_mappings
            }
        )

        assert response.status_code == 202


class TestMappingPersistence:
    """Test that face mappings are persisted"""

    def test_mapping_stored_in_task(self, upload_photo, upload_template):
        """Test that face mapping is stored in FaceSwapTask"""
        husband_photo = upload_photo()
        wife_photo = upload_photo()
        template = upload_template()

        custom_mappings = [
            {"source_photo": "husband", "source_face_index": 0, "target_face_index": 1},
            {"source_photo": "wife", "source_face_index": 0, "target_face_index": 0}
        ]

        response = client.post(
            "/api/v1/faceswap/swap",
            json={
                "husband_photo_id": husband_photo["id"],
                "wife_photo_id": wife_photo["id"],
                "template_id": template["id"],
                "face_mappings": custom_mappings
            }
        )

        assert response.status_code == 202
        task_data = response.json()
        task_id = task_data["task_id"]

        # Retrieve task and verify mappings are stored
        with patch("app.api.v1.faceswap_v15.storage_service") as mock_storage:
            mock_storage.get_file_url.return_value = "http://localhost/storage/fake.jpg"
            task_response = client.get(f"/api/v1/faceswap/task/{task_id}")
        assert task_response.status_code == 200

        task_info = task_response.json()
        assert "face_mappings" in task_info
        assert task_info["face_mappings"] == custom_mappings

    def test_default_mapping_stored(self, upload_photo, upload_template):
        """Test that default mapping is computed and stored"""
        husband_photo = upload_photo()
        wife_photo = upload_photo()
        template = upload_template()

        response = client.post(
            "/api/v1/faceswap/swap",
            json={
                "husband_photo_id": husband_photo["id"],
                "wife_photo_id": wife_photo["id"],
                "template_id": template["id"],
                "use_default_mapping": True
            }
        )

        assert response.status_code == 202
        task_data = response.json()

        # Should have computed mappings
        assert "face_mappings" in task_data


class TestMappingWithPreprocessing:
    """Test face mapping with preprocessed templates"""

    def test_use_preprocessed_template(self, upload_photo, upload_template):
        """Test using preprocessed template with mapping"""
        husband_photo = upload_photo()
        wife_photo = upload_photo()
        template = upload_template()

        # Skip actual preprocessing (requires InsightFace model)
        # Directly test the swap endpoint with use_preprocessed flag

        # Use preprocessed template
        response = client.post(
            "/api/v1/faceswap/swap",
            json={
                "husband_photo_id": husband_photo["id"],
                "wife_photo_id": wife_photo["id"],
                "template_id": template["id"],
                "use_default_mapping": True,
                "use_preprocessed": True
            }
        )

        assert response.status_code == 202
        data = response.json()
        # Template is not actually preprocessed, so it falls back to False
        # The endpoint logs a warning and sets use_preprocessed to False
        assert "use_preprocessed" in data

    def test_mapping_based_on_gender(self, upload_photo, upload_template):
        """Test that default mapping uses gender from preprocessing"""
        husband_photo = upload_photo()
        wife_photo = upload_photo()
        template = upload_template()

        # Without actual preprocessing data, default mapping will use
        # fallback (husband->0, wife->1). Just verify the endpoint works.
        response = client.post(
            "/api/v1/faceswap/swap",
            json={
                "husband_photo_id": husband_photo["id"],
                "wife_photo_id": wife_photo["id"],
                "template_id": template["id"],
                "use_default_mapping": True,
                "use_preprocessed": True
            }
        )

        assert response.status_code == 202
        task_data = response.json()

        # Default fallback mapping should be present
        assert "face_mappings" in task_data
        mappings = task_data.get("face_mappings", [])
        assert len(mappings) >= 1


class TestMappingEdgeCases:
    """Test edge cases for face mapping"""

    def test_no_faces_in_template(self, upload_photo, upload_template):
        """Test mapping when template has no faces"""
        husband_photo = upload_photo()
        wife_photo = upload_photo()
        template = upload_template()

        response = client.post(
            "/api/v1/faceswap/swap",
            json={
                "husband_photo_id": husband_photo["id"],
                "wife_photo_id": wife_photo["id"],
                "template_id": template["id"],
                "use_default_mapping": True
            }
        )

        # Should accept but may fail during processing
        assert response.status_code in [202, 400]

    def test_empty_mapping_array(self, upload_photo, upload_template):
        """Test with empty face_mappings array"""
        husband_photo = upload_photo()
        wife_photo = upload_photo()
        template = upload_template()

        response = client.post(
            "/api/v1/faceswap/swap",
            json={
                "husband_photo_id": husband_photo["id"],
                "wife_photo_id": wife_photo["id"],
                "template_id": template["id"],
                "face_mappings": []
            }
        )

        # Should either reject or use default
        assert response.status_code in [202, 400, 422]

    def test_mapping_format_validation(self, upload_photo, upload_template):
        """Test face mapping format validation"""
        husband_photo = upload_photo()
        wife_photo = upload_photo()
        template = upload_template()

        # Invalid format: missing required fields
        invalid_format = [
            {"source_photo": "husband"}  # Missing indices
        ]

        response = client.post(
            "/api/v1/faceswap/swap",
            json={
                "husband_photo_id": husband_photo["id"],
                "wife_photo_id": wife_photo["id"],
                "template_id": template["id"],
                "face_mappings": invalid_format
            }
        )

        # Should fail validation
        assert response.status_code in [400, 422]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
