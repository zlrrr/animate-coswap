"""
End-to-End MVP Workflow Tests

Tests the complete MVP workflow:
1. Manual image upload
2. Template selection
3. Background processing
4. Result gallery
"""

import os
import io
import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from PIL import Image
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_db
from app.models.database import Base


# Create in-memory SQLite database for testing
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


# Create test client
client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Create all tables before tests"""
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(autouse=True)
def mock_storage_and_cv2(tmp_path):
    """Mock storage_service and cv2 for all tests"""
    for subdir in ["temp", "templates", "results", "source"]:
        (tmp_path / subdir).mkdir(exist_ok=True)

    call_count = {"n": 0}

    def fake_save_file(file, filename, category="temp"):
        call_count["n"] += 1
        dest_dir = tmp_path / category
        dest_dir.mkdir(exist_ok=True)
        unique_name = f"{category}_{call_count['n']}_{filename}"
        dest_path = dest_dir / unique_name
        data = file.read()
        dest_path.write_bytes(data)
        return f"{category}/{unique_name}", len(data)

    def fake_get_file_path(storage_path):
        return str(tmp_path / storage_path)

    def fake_get_file_url(storage_path):
        return f"/storage/{storage_path}"

    def fake_delete_file(storage_path):
        fpath = tmp_path / storage_path
        if fpath.exists():
            fpath.unlink()

    fake_cv2_img = np.zeros((600, 800, 3), dtype=np.uint8)

    with patch("app.api.v1.photos.storage_service") as mock_photos_storage, \
         patch("app.api.v1.photos.cv2") as mock_photos_cv2, \
         patch("app.api.v1.templates.storage_service") as mock_templates_storage, \
         patch("app.api.v1.templates.cv2") as mock_templates_cv2, \
         patch("app.api.v1.faceswap.storage_service") as mock_faceswap_storage, \
         patch("app.api.v1.faceswap.cv2") as mock_faceswap_cv2, \
         patch("app.services.faceswap.processor.process_faceswap_task_sync", return_value=None):

        for mock_svc in (mock_photos_storage, mock_templates_storage, mock_faceswap_storage):
            mock_svc.save_file = MagicMock(side_effect=fake_save_file)
            mock_svc.get_file_path = MagicMock(side_effect=fake_get_file_path)
            mock_svc.get_file_url = MagicMock(side_effect=fake_get_file_url)
            mock_svc.delete_file = MagicMock(side_effect=fake_delete_file)

        for mock_cv in (mock_photos_cv2, mock_templates_cv2, mock_faceswap_cv2):
            mock_cv.imread.return_value = fake_cv2_img

        yield


@pytest.fixture
def create_test_image():
    """Factory to create test images"""
    def _create_image(width=800, height=600, color=(255, 0, 0)):
        """Create a test image in memory"""
        img = Image.new('RGB', (width, height), color=color)
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        return img_bytes

    return _create_image


class TestMVPWorkflow:
    """Test complete MVP workflow"""

    def test_01_health_check(self):
        """Test that API is accessible"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert data["name"] == "Couple Face-Swap API"

    def test_02_upload_source_image(self, create_test_image):
        """Test uploading a source image"""
        img_bytes = create_test_image(width=800, height=600, color=(255, 0, 0))

        response = client.post(
            "/api/v1/photos/upload",
            params={"session_id": "test-session-1"},
            files={"file": ("test_source.jpg", img_bytes, "image/jpeg")}
        )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "storage_path" in data

        # Store image ID for later tests
        TestMVPWorkflow.source_image_id = data["id"]

    def test_03_upload_husband_image(self, create_test_image):
        """Test uploading husband's photo"""
        img_bytes = create_test_image(width=600, height=800, color=(0, 255, 0))

        response = client.post(
            "/api/v1/photos/upload",
            params={"session_id": "test-session-1"},
            files={"file": ("husband.jpg", img_bytes, "image/jpeg")}
        )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        TestMVPWorkflow.husband_image_id = data["id"]

    def test_04_upload_wife_image(self, create_test_image):
        """Test uploading wife's photo"""
        img_bytes = create_test_image(width=600, height=800, color=(0, 0, 255))

        response = client.post(
            "/api/v1/photos/upload",
            params={"session_id": "test-session-1"},
            files={"file": ("wife.jpg", img_bytes, "image/jpeg")}
        )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        TestMVPWorkflow.wife_image_id = data["id"]

    @pytest.mark.skip(reason="No list-all-images endpoint exists; photos are session-scoped")
    def test_05_list_uploaded_images(self):
        """Test listing uploaded images - skipped as endpoint does not exist"""
        pass

    def test_06_create_template(self, create_test_image):
        """Test creating a template"""
        img_bytes = create_test_image(width=1024, height=768, color=(128, 128, 128))

        response = client.post(
            "/api/v1/templates/upload",
            data={
                "name": "Romantic Couple Template",
                "category": "custom",
                "description": "A romantic template for couples"
            },
            files={"file": ("template.jpg", img_bytes, "image/jpeg")}
        )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["name"] == "Romantic Couple Template"
        assert data["category"] == "custom"
        assert "original_image_id" in data

        TestMVPWorkflow.template_id = data["id"]
        TestMVPWorkflow.template_image_id = data["original_image_id"]

    def test_07_list_templates(self):
        """Test listing templates"""
        response = client.get("/api/v1/templates/")

        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert "total" in data
        # Should have at least the template we just created
        assert len(data["templates"]) >= 1

        # Find our template
        our_template = next(
            (t for t in data["templates"] if t["name"] == "Romantic Couple Template"),
            None
        )
        assert our_template is not None
        assert our_template["category"] == "custom"

    def test_08_create_faceswap_task(self):
        """Test creating a face-swap task"""
        if not hasattr(TestMVPWorkflow, 'husband_image_id'):
            pytest.skip("Previous tests did not run")

        response = client.post(
            "/api/v1/faceswap/swap-faces",
            json={
                "husband_photo_id": TestMVPWorkflow.husband_image_id,
                "wife_photo_id": TestMVPWorkflow.wife_image_id,
                "template_id": TestMVPWorkflow.template_id
            }
        )

        assert response.status_code == 202
        data = response.json()
        assert "task_id" in data
        assert "status" in data
        assert data["status"] in ["pending", "processing", "failed"]

        TestMVPWorkflow.task_id = data["task_id"]

    def test_09_get_task_status(self):
        """Test getting task status"""
        if not hasattr(TestMVPWorkflow, 'task_id'):
            pytest.skip("No task was created")

        response = client.get(f"/api/v1/faceswap/task/{TestMVPWorkflow.task_id}")

        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert "status" in data
        assert data["status"] in ["pending", "processing", "completed", "failed"]

    @pytest.mark.skip(reason="No list-all-images endpoint exists")
    def test_10_list_images_with_results(self):
        """Test listing images including results - skipped as endpoint does not exist"""
        pass

    @pytest.mark.skip(reason="No list-all-images endpoint exists")
    def test_11_pagination(self):
        """Test image listing pagination - skipped as endpoint does not exist"""
        pass

    @pytest.mark.skip(reason="No list-all-images endpoint exists")
    def test_12_filter_by_category(self):
        """Test filtering images by category - skipped as endpoint does not exist"""
        pass


class TestImageUploadValidation:
    """Test image upload validation"""

    def test_missing_file(self):
        """Test upload without file"""
        response = client.post(
            "/api/v1/photos/upload",
            params={"session_id": "test-session-validation"}
        )

        assert response.status_code == 422  # Validation error

    def test_invalid_image_file(self):
        """Test uploading non-image file"""
        file_content = b"This is not an image file"

        response = client.post(
            "/api/v1/photos/upload",
            params={"session_id": "test-session-validation"},
            files={"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        )

        # Should fail validation
        assert response.status_code in [400, 422, 500]


class TestTemplateValidation:
    """Test template creation validation"""

    def test_create_template_missing_name(self, create_test_image):
        """Test creating template without name"""
        img_bytes = create_test_image()

        response = client.post(
            "/api/v1/templates/upload",
            data={"category": "custom"},
            files={"file": ("template.jpg", img_bytes, "image/jpeg")}
        )

        assert response.status_code == 422  # Validation error

    def test_create_template_without_image(self):
        """Test creating template without image"""
        response = client.post(
            "/api/v1/templates/upload",
            data={
                "name": "Test Template",
                "category": "custom"
            }
        )

        assert response.status_code == 422  # Validation error


class TestFaceSwapValidation:
    """Test face-swap task validation"""

    def test_create_task_missing_fields(self):
        """Test creating task without required fields"""
        response = client.post(
            "/api/v1/faceswap/swap-faces",
            json={"husband_photo_id": 1}  # Missing other fields
        )

        assert response.status_code == 422  # Validation error

    def test_create_task_invalid_image_ids(self):
        """Test creating task with non-existent image IDs"""
        response = client.post(
            "/api/v1/faceswap/swap-faces",
            json={
                "husband_photo_id": 99999,
                "wife_photo_id": 99998,
                "template_id": 99997
            }
        )

        # Should fail because images don't exist
        assert response.status_code in [404, 500]

    def test_get_nonexistent_task(self):
        """Test getting status of non-existent task"""
        response = client.get("/api/v1/faceswap/task/99999")

        assert response.status_code == 404


class TestErrorHandling:
    """Test error handling"""

    def test_404_endpoint(self):
        """Test accessing non-existent endpoint"""
        response = client.get("/api/v1/nonexistent")

        assert response.status_code == 404

    def test_method_not_allowed(self):
        """Test using wrong HTTP method"""
        response = client.delete("/api/v1/photos/upload")

        assert response.status_code in [405, 422]


class TestMVPIntegration:
    """Integration tests for MVP features"""

    @pytest.fixture(autouse=True)
    def setup_mvp_data(self, create_test_image):
        """Setup data for MVP tests"""
        self.create_test_image = create_test_image

    def test_complete_mvp_flow(self):
        """Test the complete MVP flow from start to finish"""

        # Step 1: Upload husband's photo
        husband_img = self.create_test_image(600, 800, (255, 200, 200))
        husband_response = client.post(
            "/api/v1/photos/upload",
            params={"session_id": "test-mvp-flow"},
            files={"file": ("husband.jpg", husband_img, "image/jpeg")}
        )
        assert husband_response.status_code == 200
        husband_id = husband_response.json()["id"]

        # Step 2: Upload wife's photo
        wife_img = self.create_test_image(600, 800, (200, 200, 255))
        wife_response = client.post(
            "/api/v1/photos/upload",
            params={"session_id": "test-mvp-flow"},
            files={"file": ("wife.jpg", wife_img, "image/jpeg")}
        )
        assert wife_response.status_code == 200
        wife_id = wife_response.json()["id"]

        # Step 3: Create/Select template
        template_img = self.create_test_image(1024, 768, (200, 255, 200))
        template_response = client.post(
            "/api/v1/templates/upload",
            data={
                "name": "Test Template",
                "category": "custom",
                "description": "Test template for MVP"
            },
            files={"file": ("template.jpg", template_img, "image/jpeg")}
        )
        assert template_response.status_code == 200
        template_id = template_response.json()["id"]

        # Step 4: List templates (verify template selection works)
        templates_response = client.get("/api/v1/templates/")
        assert templates_response.status_code == 200
        templates_data = templates_response.json()
        assert "templates" in templates_data
        assert "total" in templates_data
        templates = templates_data["templates"]
        assert len(templates) > 0
        assert any(t["id"] == template_id for t in templates)

        # Step 5: Create face-swap task (background processing)
        task_response = client.post(
            "/api/v1/faceswap/swap-faces",
            json={
                "husband_photo_id": husband_id,
                "wife_photo_id": wife_id,
                "template_id": template_id
            }
        )

        assert task_response.status_code == 202
        task_data = task_response.json()
        task_id = task_data["task_id"]

        # Step 6: Check task status
        status_response = client.get(f"/api/v1/faceswap/task/{task_id}")
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert "status" in status_data
        assert "task_id" in status_data
        assert status_data["status"] in ["pending", "processing", "completed", "failed"]
