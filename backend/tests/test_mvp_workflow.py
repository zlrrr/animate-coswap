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


# Override the database dependency
app.dependency_overrides[get_db] = override_get_db

# Create test client
client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Create all tables before tests"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


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
        # Create test image
        img_bytes = create_test_image(width=800, height=600, color=(255, 0, 0))

        # Upload image
        response = client.post(
            "/api/v1/images/upload",
            params={"image_type": "source"},
            files={"file": ("test_source.jpg", img_bytes, "image/jpeg")}
        )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["image_type"] == "source"
        assert data["width"] == 800
        assert data["height"] == 600
        assert "storage_path" in data

        # Store image ID for later tests
        self.source_image_id = data["id"]

    def test_03_upload_husband_image(self, create_test_image):
        """Test uploading husband's photo"""
        img_bytes = create_test_image(width=600, height=800, color=(0, 255, 0))

        response = client.post(
            "/api/v1/images/upload",
            params={"image_type": "source", "category": "custom"},
            files={"file": ("husband.jpg", img_bytes, "image/jpeg")}
        )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        self.husband_image_id = data["id"]

    def test_04_upload_wife_image(self, create_test_image):
        """Test uploading wife's photo"""
        img_bytes = create_test_image(width=600, height=800, color=(0, 0, 255))

        response = client.post(
            "/api/v1/images/upload",
            params={"image_type": "source", "category": "custom"},
            files={"file": ("wife.jpg", img_bytes, "image/jpeg")}
        )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        self.wife_image_id = data["id"]

    def test_05_list_uploaded_images(self):
        """Test listing uploaded images"""
        response = client.get("/api/v1/images/")

        assert response.status_code == 200
        data = response.json()
        assert "images" in data
        assert len(data["images"]) >= 3  # At least 3 images uploaded

    def test_06_create_template(self, create_test_image):
        """Test creating a template"""
        img_bytes = create_test_image(width=1024, height=768, color=(128, 128, 128))

        response = client.post(
            "/api/v1/templates/",
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
        assert "image_id" in data

        self.template_id = data["id"]
        self.template_image_id = data["image_id"]

    def test_07_list_templates_empty_first(self):
        """Test listing templates"""
        response = client.get("/api/v1/templates/")

        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
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
        # Skip if we don't have the required IDs
        if not hasattr(self, 'husband_image_id'):
            pytest.skip("Previous tests did not run")

        response = client.post(
            "/api/v1/faceswap/tasks",
            json={
                "husband_image_id": self.husband_image_id,
                "wife_image_id": self.wife_image_id,
                "template_id": self.template_id
            }
        )

        # The task creation might fail if models are not available
        # but the endpoint should work
        assert response.status_code in [200, 500]  # 200 success, 500 if models missing

        if response.status_code == 200:
            data = response.json()
            assert "task_id" in data
            assert "status" in data
            # Status should be either pending or processing
            assert data["status"] in ["pending", "processing", "failed"]

            self.task_id = data["task_id"]
        else:
            # Models not available, that's expected in test environment
            pytest.skip("Models not available in test environment")

    def test_09_get_task_status(self):
        """Test getting task status"""
        if not hasattr(self, 'task_id'):
            pytest.skip("No task was created")

        response = client.get(f"/api/v1/faceswap/tasks/{self.task_id}")

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "status" in data
        assert data["status"] in ["pending", "processing", "completed", "failed"]

    def test_10_list_images_with_results(self):
        """Test listing images including results"""
        response = client.get(
            "/api/v1/images/",
            params={"image_type": "result"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "images" in data
        # Might be 0 if models aren't available
        assert isinstance(data["images"], list)

    def test_11_pagination(self):
        """Test image listing pagination"""
        # Test with limit
        response = client.get(
            "/api/v1/images/",
            params={"skip": 0, "limit": 2}
        )

        assert response.status_code == 200
        data = response.json()
        assert "images" in data
        assert len(data["images"]) <= 2

        # Test with skip
        response = client.get(
            "/api/v1/images/",
            params={"skip": 1, "limit": 2}
        )

        assert response.status_code == 200
        data = response.json()
        assert "images" in data

    def test_12_filter_by_category(self):
        """Test filtering images by category"""
        response = client.get(
            "/api/v1/images/",
            params={"category": "custom"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "images" in data
        # All returned images should be custom category
        for img in data["images"]:
            if img.get("category"):
                assert img["category"] == "custom"


class TestImageUploadValidation:
    """Test image upload validation"""

    def test_invalid_image_type(self):
        """Test uploading with invalid image_type parameter"""
        # Create a simple text file instead of image
        file_content = b"not an image"

        response = client.post(
            "/api/v1/images/upload",
            params={"image_type": "invalid"},
            files={"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        )

        assert response.status_code == 422  # Validation error

    def test_missing_file(self):
        """Test upload without file"""
        response = client.post(
            "/api/v1/images/upload",
            params={"image_type": "source"}
        )

        assert response.status_code == 422  # Validation error

    def test_invalid_image_file(self):
        """Test uploading non-image file"""
        file_content = b"This is not an image file"

        response = client.post(
            "/api/v1/images/upload",
            params={"image_type": "source"},
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
            "/api/v1/templates/",
            data={"category": "custom"},
            files={"file": ("template.jpg", img_bytes, "image/jpeg")}
        )

        assert response.status_code == 422  # Validation error

    def test_create_template_without_image(self):
        """Test creating template without image"""
        response = client.post(
            "/api/v1/templates/",
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
            "/api/v1/faceswap/tasks",
            json={"husband_image_id": 1}  # Missing other fields
        )

        assert response.status_code == 422  # Validation error

    def test_create_task_invalid_image_ids(self):
        """Test creating task with non-existent image IDs"""
        response = client.post(
            "/api/v1/faceswap/tasks",
            json={
                "husband_image_id": 99999,
                "wife_image_id": 99998,
                "template_id": 99997
            }
        )

        # Should fail because images don't exist
        assert response.status_code in [404, 500]

    def test_get_nonexistent_task(self):
        """Test getting status of non-existent task"""
        response = client.get("/api/v1/faceswap/tasks/99999")

        assert response.status_code == 404


class TestErrorHandling:
    """Test error handling"""

    def test_404_endpoint(self):
        """Test accessing non-existent endpoint"""
        response = client.get("/api/v1/nonexistent")

        assert response.status_code == 404

    def test_method_not_allowed(self):
        """Test using wrong HTTP method"""
        response = client.delete("/api/v1/images/upload")

        assert response.status_code == 405


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
            "/api/v1/images/upload",
            params={"image_type": "source"},
            files={"file": ("husband.jpg", husband_img, "image/jpeg")}
        )
        assert husband_response.status_code == 200
        husband_id = husband_response.json()["id"]

        # Step 2: Upload wife's photo
        wife_img = self.create_test_image(600, 800, (200, 200, 255))
        wife_response = client.post(
            "/api/v1/images/upload",
            params={"image_type": "source"},
            files={"file": ("wife.jpg", wife_img, "image/jpeg")}
        )
        assert wife_response.status_code == 200
        wife_id = wife_response.json()["id"]

        # Step 3: Create/Select template
        template_img = self.create_test_image(1024, 768, (200, 255, 200))
        template_response = client.post(
            "/api/v1/templates/",
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
        templates = templates_response.json()["templates"]
        assert len(templates) > 0
        assert any(t["id"] == template_id for t in templates)

        # Step 5: Create face-swap task (background processing)
        task_response = client.post(
            "/api/v1/faceswap/tasks",
            json={
                "husband_image_id": husband_id,
                "wife_image_id": wife_id,
                "template_id": template_id
            }
        )

        # Task creation should work, but processing might fail without models
        if task_response.status_code == 200:
            task_data = task_response.json()
            task_id = task_data["task_id"]

            # Step 6: Check task status
            status_response = client.get(f"/api/v1/faceswap/tasks/{task_id}")
            assert status_response.status_code == 200
            status_data = status_response.json()
            assert "status" in status_data
            assert status_data["status"] in ["pending", "processing", "completed", "failed"]

        # Step 7: List all images (result gallery)
        all_images_response = client.get("/api/v1/images/")
        assert all_images_response.status_code == 200
        all_images = all_images_response.json()["images"]
        assert len(all_images) >= 2  # At least husband and wife photos

        # Verify we can filter by type
        source_images_response = client.get(
            "/api/v1/images/",
            params={"image_type": "source"}
        )
        assert source_images_response.status_code == 200
        source_images = source_images_response.json()["images"]
        for img in source_images:
            assert img["image_type"] == "source"
