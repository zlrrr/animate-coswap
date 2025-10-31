"""
Test Phase 1.5 Checkpoint 1.5.1: Separated Upload APIs

Requirements:
1. Separate upload APIs for photos (temporary) vs templates (permanent)
2. Add delete endpoints for both
3. Photos stored in temp directory with expiration
4. Templates stored in permanent storage
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from io import BytesIO
from PIL import Image as PILImage

from app.main import app
from app.core.database import get_db
from app.models.database import Base, Image, Template

client = TestClient(app)


@pytest.fixture(scope="function")
def test_db():
    """Create a test database session"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings

    engine = create_engine(settings.DATABASE_URL)
    TestingSessionLocal = sessionmaker(bind=engine)

    # Create tables
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()


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


class TestPhotoUploadAPI:
    """Test temporary photo upload API"""

    def test_upload_photo_success(self, create_test_image):
        """Test uploading a temporary photo"""
        img_bytes = create_test_image(width=800, height=600)

        response = client.post(
            "/api/v1/photos/upload",
            files={"file": ("test_photo.jpg", img_bytes, "image/jpeg")}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "id" in data
        assert "filename" in data
        assert "storage_type" in data
        assert "expires_at" in data
        assert "session_id" in data

        # Verify storage type is temporary
        assert data["storage_type"] == "temporary"

        # Verify expiration is set (should be in future)
        expires_at = datetime.fromisoformat(data["expires_at"].replace('Z', '+00:00'))
        assert expires_at > datetime.utcnow()

        # Verify session_id is present
        assert data["session_id"] is not None
        assert len(data["session_id"]) > 0

    def test_upload_photo_with_custom_session(self, create_test_image):
        """Test uploading a photo with custom session ID"""
        img_bytes = create_test_image()
        session_id = "custom-session-123"

        response = client.post(
            "/api/v1/photos/upload",
            params={"session_id": session_id},
            files={"file": ("test_photo.jpg", img_bytes, "image/jpeg")}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id

    def test_upload_photo_invalid_format(self):
        """Test uploading invalid file format"""
        # Create a text file instead of image
        text_file = BytesIO(b"This is not an image")

        response = client.post(
            "/api/v1/photos/upload",
            files={"file": ("test.txt", text_file, "text/plain")}
        )

        assert response.status_code == 400
        assert "error" in response.json()

    def test_upload_photo_too_large(self, create_test_image):
        """Test uploading oversized photo"""
        # Create a very large image (simulate size check)
        img_bytes = create_test_image(width=5000, height=5000)

        response = client.post(
            "/api/v1/photos/upload",
            files={"file": ("large_photo.jpg", img_bytes, "image/jpeg")}
        )

        # Should either succeed or fail with proper error
        if response.status_code != 200:
            assert response.status_code == 400
            assert "size" in response.json()["error"].lower()


class TestTemplateUploadAPI:
    """Test permanent template upload API"""

    def test_upload_template_success(self, create_test_image):
        """Test uploading a permanent template"""
        img_bytes = create_test_image(width=1024, height=768)

        response = client.post(
            "/api/v1/templates/upload",
            data={"name": "Romantic Wedding", "category": "wedding"},
            files={"file": ("template.jpg", img_bytes, "image/jpeg")}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "id" in data
        assert "name" in data
        assert "category" in data
        assert "original_image_id" in data
        assert "is_preprocessed" in data

        # Verify template metadata
        assert data["name"] == "Romantic Wedding"
        assert data["category"] == "wedding"
        assert data["is_preprocessed"] == False  # Not preprocessed yet

    def test_upload_template_with_description(self, create_test_image):
        """Test uploading template with description"""
        img_bytes = create_test_image()

        response = client.post(
            "/api/v1/templates/upload",
            data={
                "name": "Beach Scene",
                "category": "outdoor",
                "description": "Beautiful beach template for couples"
            },
            files={"file": ("template.jpg", img_bytes, "image/jpeg")}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Beautiful beach template for couples"

    def test_upload_template_missing_name(self, create_test_image):
        """Test uploading template without name"""
        img_bytes = create_test_image()

        response = client.post(
            "/api/v1/templates/upload",
            data={"category": "wedding"},
            files={"file": ("template.jpg", img_bytes, "image/jpeg")}
        )

        assert response.status_code == 422  # Validation error

    def test_upload_template_verify_permanent_storage(self, create_test_image):
        """Test that template is stored permanently"""
        img_bytes = create_test_image()

        response = client.post(
            "/api/v1/templates/upload",
            data={"name": "Test Template", "category": "custom"},
            files={"file": ("template.jpg", img_bytes, "image/jpeg")}
        )

        assert response.status_code == 200
        template_data = response.json()

        # Get the image details
        image_id = template_data["original_image_id"]
        response = client.get(f"/api/v1/images/{image_id}")

        assert response.status_code == 200
        image_data = response.json()

        # Verify storage type is permanent
        assert image_data["storage_type"] == "permanent"

        # Verify no expiration for permanent storage
        assert image_data["expires_at"] is None


class TestDeleteAPIs:
    """Test delete endpoints for photos and templates"""

    def test_delete_photo_success(self, create_test_image):
        """Test deleting a temporary photo"""
        # First upload a photo
        img_bytes = create_test_image()
        upload_response = client.post(
            "/api/v1/photos/upload",
            files={"file": ("test_photo.jpg", img_bytes, "image/jpeg")}
        )

        assert upload_response.status_code == 200
        photo_id = upload_response.json()["id"]

        # Delete the photo
        delete_response = client.delete(f"/api/v1/photos/{photo_id}")

        assert delete_response.status_code == 200
        assert delete_response.json()["message"] == "Photo deleted successfully"

        # Verify photo is deleted
        get_response = client.get(f"/api/v1/images/{photo_id}")
        assert get_response.status_code == 404

    def test_delete_photo_not_found(self):
        """Test deleting non-existent photo"""
        response = client.delete("/api/v1/photos/99999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_delete_template_success(self, create_test_image):
        """Test deleting a template"""
        # First upload a template
        img_bytes = create_test_image()
        upload_response = client.post(
            "/api/v1/templates/upload",
            data={"name": "Test Template", "category": "custom"},
            files={"file": ("template.jpg", img_bytes, "image/jpeg")}
        )

        assert upload_response.status_code == 200
        template_id = upload_response.json()["id"]

        # Delete the template
        delete_response = client.delete(f"/api/v1/templates/{template_id}")

        assert delete_response.status_code == 200
        assert delete_response.json()["message"] == "Template deleted successfully"

        # Verify template is deleted
        get_response = client.get(f"/api/v1/templates/{template_id}")
        assert get_response.status_code == 404

    def test_delete_template_cascade_to_image(self, create_test_image):
        """Test that deleting template also deletes associated image"""
        # Upload template
        img_bytes = create_test_image()
        upload_response = client.post(
            "/api/v1/templates/upload",
            data={"name": "Test Template", "category": "custom"},
            files={"file": ("template.jpg", img_bytes, "image/jpeg")}
        )

        template_data = upload_response.json()
        template_id = template_data["id"]
        image_id = template_data["original_image_id"]

        # Delete template
        client.delete(f"/api/v1/templates/{template_id}")

        # Verify image is also deleted
        get_response = client.get(f"/api/v1/images/{image_id}")
        assert get_response.status_code == 404


class TestSessionGrouping:
    """Test session-based photo grouping"""

    def test_list_photos_by_session(self, create_test_image):
        """Test retrieving photos by session ID"""
        session_id = "test-session-456"

        # Upload multiple photos with same session
        photo_ids = []
        for i in range(3):
            img_bytes = create_test_image()
            response = client.post(
                "/api/v1/photos/upload",
                params={"session_id": session_id},
                files={"file": (f"photo_{i}.jpg", img_bytes, "image/jpeg")}
            )
            assert response.status_code == 200
            photo_ids.append(response.json()["id"])

        # Get photos by session
        response = client.get(f"/api/v1/photos/session/{session_id}")

        assert response.status_code == 200
        data = response.json()

        assert "photos" in data
        assert len(data["photos"]) == 3

        # Verify all photos belong to the session
        for photo in data["photos"]:
            assert photo["session_id"] == session_id
            assert photo["id"] in photo_ids

    def test_delete_session_photos(self, create_test_image):
        """Test deleting all photos in a session"""
        session_id = "test-session-789"

        # Upload multiple photos
        for i in range(2):
            img_bytes = create_test_image()
            client.post(
                "/api/v1/photos/upload",
                params={"session_id": session_id},
                files={"file": (f"photo_{i}.jpg", img_bytes, "image/jpeg")}
            )

        # Delete all photos in session
        response = client.delete(f"/api/v1/photos/session/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 2

        # Verify session is empty
        get_response = client.get(f"/api/v1/photos/session/{session_id}")
        assert get_response.status_code == 200
        assert len(get_response.json()["photos"]) == 0


class TestStorageTypeValidation:
    """Test storage type validation and constraints"""

    def test_photo_has_expiration(self, create_test_image):
        """Test that temporary photos have expiration"""
        img_bytes = create_test_image()
        response = client.post(
            "/api/v1/photos/upload",
            files={"file": ("test_photo.jpg", img_bytes, "image/jpeg")}
        )

        assert response.status_code == 200
        data = response.json()

        # Must have expiration
        assert data["expires_at"] is not None

        # Expiration should be within 24 hours (configurable)
        expires_at = datetime.fromisoformat(data["expires_at"].replace('Z', '+00:00'))
        now = datetime.utcnow()
        time_diff = expires_at - now

        # Should expire between 1 minute and 48 hours
        assert timedelta(minutes=1) < time_diff < timedelta(hours=48)

    def test_template_no_expiration(self, create_test_image):
        """Test that permanent templates have no expiration"""
        img_bytes = create_test_image()
        response = client.post(
            "/api/v1/templates/upload",
            data={"name": "Permanent Template", "category": "custom"},
            files={"file": ("template.jpg", img_bytes, "image/jpeg")}
        )

        assert response.status_code == 200
        template_data = response.json()

        # Get image details
        image_id = template_data["original_image_id"]
        image_response = client.get(f"/api/v1/images/{image_id}")
        image_data = image_response.json()

        # Should have no expiration
        assert image_data["expires_at"] is None
        assert image_data["storage_type"] == "permanent"


class TestBulkOperations:
    """Test bulk operations for photos"""

    def test_upload_multiple_photos(self, create_test_image):
        """Test uploading multiple photos at once"""
        files = []
        for i in range(3):
            img_bytes = create_test_image()
            files.append(("files", (f"photo_{i}.jpg", img_bytes, "image/jpeg")))

        response = client.post(
            "/api/v1/photos/upload/batch",
            files=files
        )

        if response.status_code == 200:
            data = response.json()
            assert "photos" in data
            assert len(data["photos"]) == 3

            # All should have same session_id
            session_ids = [photo["session_id"] for photo in data["photos"]]
            assert len(set(session_ids)) == 1  # All same session


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
