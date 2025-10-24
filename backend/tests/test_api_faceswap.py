"""
Integration tests for Face-swap API endpoints

These tests validate the API endpoints using TestClient
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import io
from PIL import Image as PILImage
import numpy as np

from app.main import app
from app.core.database import get_db
from app.models.database import Base, Image, Template, FaceSwapTask


# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Override database dependency
def override_get_db():
    """Override database session for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module")
def setup_database():
    """Create test database tables"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(setup_database):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def test_image_bytes():
    """Generate a test image as bytes"""
    # Create a simple 512x512 red image
    img_array = np.zeros((512, 512, 3), dtype=np.uint8)
    img_array[:, :] = [255, 0, 0]  # Red

    pil_image = PILImage.fromarray(img_array)
    img_bytes = io.BytesIO()
    pil_image.save(img_bytes, format='JPEG')
    img_bytes.seek(0)

    return img_bytes


class TestHealthEndpoints:
    """Test health and status endpoints"""

    def test_root_endpoint(self, client):
        """Test root endpoint returns app info"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "status" in data

    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "model" in data


class TestImageUpload:
    """Test image upload endpoint"""

    def test_upload_image_success(self, client, test_image_bytes):
        """Test successful image upload"""
        response = client.post(
            "/api/v1/faceswap/upload-image",
            files={"file": ("test.jpg", test_image_bytes, "image/jpeg")},
            params={"image_type": "source"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "image_id" in data
        assert "filename" in data
        assert "storage_path" in data
        assert data["filename"] == "test.jpg"
        assert data["width"] == 512
        assert data["height"] == 512

    def test_upload_image_invalid_type(self, client):
        """Test upload with non-image file"""
        text_file = io.BytesIO(b"This is not an image")

        response = client.post(
            "/api/v1/faceswap/upload-image",
            files={"file": ("test.txt", text_file, "text/plain")},
            params={"image_type": "source"}
        )

        assert response.status_code == 400
        assert "must be an image" in response.json()["detail"]

    def test_upload_image_invalid_image_type_param(self, client, test_image_bytes):
        """Test upload with invalid image_type parameter"""
        response = client.post(
            "/api/v1/faceswap/upload-image",
            files={"file": ("test.jpg", test_image_bytes, "image/jpeg")},
            params={"image_type": "invalid"}
        )

        assert response.status_code == 422  # Validation error


class TestTemplateEndpoints:
    """Test template management endpoints"""

    @pytest.fixture
    def uploaded_image_id(self, client, test_image_bytes):
        """Upload a test image and return its ID"""
        response = client.post(
            "/api/v1/faceswap/upload-image",
            files={"file": ("template.jpg", test_image_bytes, "image/jpeg")},
            params={"image_type": "template"}
        )
        return response.json()["image_id"]

    def test_create_template(self, client, uploaded_image_id):
        """Test template creation"""
        response = client.post(
            "/api/v1/faceswap/templates",
            params={
                "image_id": uploaded_image_id,
                "title": "Test Template",
                "description": "A test template"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert "template_id" in data
        assert data["title"] == "Test Template"

    def test_create_template_invalid_image(self, client):
        """Test template creation with non-existent image"""
        response = client.post(
            "/api/v1/faceswap/templates",
            params={
                "image_id": 99999,
                "title": "Test Template"
            }
        )

        assert response.status_code == 404

    def test_list_templates_empty(self, client):
        """Test listing templates when none exist"""
        response = client.get("/api/v1/faceswap/templates")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_templates_with_data(self, client, uploaded_image_id):
        """Test listing templates after creating one"""
        # Create a template first
        client.post(
            "/api/v1/faceswap/templates",
            params={
                "image_id": uploaded_image_id,
                "title": "Test Template 1"
            }
        )

        # List templates
        response = client.get("/api/v1/faceswap/templates")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["title"] == "Test Template 1"

    def test_list_templates_pagination(self, client):
        """Test template pagination"""
        response = client.get(
            "/api/v1/faceswap/templates",
            params={"limit": 5, "offset": 0}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 5


class TestFaceSwapWorkflow:
    """Test complete face-swap workflow"""

    @pytest.fixture
    def setup_images_and_template(self, client, test_image_bytes):
        """Set up images and template for face-swap"""
        # Upload husband image
        response1 = client.post(
            "/api/v1/faceswap/upload-image",
            files={"file": ("husband.jpg", test_image_bytes, "image/jpeg")},
            params={"image_type": "source"}
        )
        husband_id = response1.json()["image_id"]

        # Upload wife image
        img_bytes2 = io.BytesIO()
        img_array = np.zeros((512, 512, 3), dtype=np.uint8)
        img_array[:, :] = [0, 255, 0]  # Green
        PILImage.fromarray(img_array).save(img_bytes2, format='JPEG')
        img_bytes2.seek(0)

        response2 = client.post(
            "/api/v1/faceswap/upload-image",
            files={"file": ("wife.jpg", img_bytes2, "image/jpeg")},
            params={"image_type": "source"}
        )
        wife_id = response2.json()["image_id"]

        # Upload template
        img_bytes3 = io.BytesIO()
        img_array = np.zeros((512, 512, 3), dtype=np.uint8)
        img_array[:, :] = [0, 0, 255]  # Blue
        PILImage.fromarray(img_array).save(img_bytes3, format='JPEG')
        img_bytes3.seek(0)

        response3 = client.post(
            "/api/v1/faceswap/upload-image",
            files={"file": ("template.jpg", img_bytes3, "image/jpeg")},
            params={"image_type": "template"}
        )
        template_image_id = response3.json()["image_id"]

        # Create template
        response4 = client.post(
            "/api/v1/faceswap/templates",
            params={
                "image_id": template_image_id,
                "title": "Test Couple Template"
            }
        )
        template_id = response4.json()["template_id"]

        return husband_id, wife_id, template_id

    def test_create_faceswap_task(self, client, setup_images_and_template):
        """Test creating a face-swap task"""
        husband_id, wife_id, template_id = setup_images_and_template

        response = client.post(
            "/api/v1/faceswap/swap-faces",
            json={
                "husband_image_id": husband_id,
                "wife_image_id": wife_id,
                "template_id": template_id
            }
        )

        assert response.status_code == 202  # Accepted
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "pending"

    def test_get_task_status(self, client, setup_images_and_template):
        """Test getting task status"""
        husband_id, wife_id, template_id = setup_images_and_template

        # Create task
        create_response = client.post(
            "/api/v1/faceswap/swap-faces",
            json={
                "husband_image_id": husband_id,
                "wife_image_id": wife_id,
                "template_id": template_id
            }
        )
        task_id = create_response.json()["task_id"]

        # Get task status
        status_response = client.get(f"/api/v1/faceswap/task/{task_id}")

        assert status_response.status_code == 200
        data = status_response.json()
        assert data["task_id"] == task_id
        assert data["status"] in ["pending", "processing", "completed", "failed"]
        assert "progress" in data

    def test_get_task_status_not_found(self, client):
        """Test getting status of non-existent task"""
        response = client.get("/api/v1/faceswap/task/99999")

        assert response.status_code == 404

    def test_create_task_invalid_images(self, client):
        """Test creating task with invalid image IDs"""
        response = client.post(
            "/api/v1/faceswap/swap-faces",
            json={
                "husband_image_id": 99999,
                "wife_image_id": 99998,
                "template_id": 99997
            }
        )

        assert response.status_code == 404


class TestAPIValidation:
    """Test API input validation"""

    def test_missing_required_fields(self, client):
        """Test API with missing required fields"""
        response = client.post(
            "/api/v1/faceswap/swap-faces",
            json={"husband_image_id": 1}  # Missing other fields
        )

        assert response.status_code == 422  # Validation error

    def test_invalid_field_types(self, client):
        """Test API with invalid field types"""
        response = client.post(
            "/api/v1/faceswap/swap-faces",
            json={
                "husband_image_id": "not_a_number",
                "wife_image_id": 2,
                "template_id": 3
            }
        )

        assert response.status_code == 422

    def test_pagination_limits(self, client):
        """Test pagination parameter validation"""
        # Test exceeding max limit
        response = client.get(
            "/api/v1/faceswap/templates",
            params={"limit": 200}  # Max is 100
        )

        assert response.status_code == 422

        # Test negative offset
        response = client.get(
            "/api/v1/faceswap/templates",
            params={"offset": -1}
        )

        assert response.status_code == 422
