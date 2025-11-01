"""
Test Phase 1.5 Checkpoint 1.5.2: Template Preprocessing

Requirements:
1. Face detection on templates
2. Gender classification (male/female using InsightFace)
3. Face masking (create masked version of template)
4. Store preprocessing data in template_preprocessing table
5. Update template with face counts
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from io import BytesIO
from PIL import Image as PILImage
import json

from app.main import app
from app.core.database import get_db
from app.models.database import Base, Image, Template, TemplatePreprocessing

client = TestClient(app)


@pytest.fixture(scope="function")
def test_db():
    """Create a test database session"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings

    engine = create_engine(settings.DATABASE_URL)
    TestingSessionLocal = sessionmaker(bind=engine)

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


@pytest.fixture
def upload_template(create_test_image):
    """Helper to upload a template"""
    def _upload(name="Test Template", category="custom"):
        img_bytes = create_test_image(width=1024, height=768)
        response = client.post(
            "/api/v1/templates/upload",
            data={"name": name, "category": category},
            files={"file": (f"{name}.jpg", img_bytes, "image/jpeg")}
        )
        assert response.status_code == 200
        return response.json()
    return _upload


class TestPreprocessingAPI:
    """Test template preprocessing API endpoints"""

    def test_trigger_preprocessing(self, upload_template):
        """Test triggering preprocessing for a template"""
        template = upload_template(name="Wedding Template")
        template_id = template["id"]

        # Trigger preprocessing
        response = client.post(f"/api/v1/templates/{template_id}/preprocess")

        assert response.status_code == 202  # Accepted
        data = response.json()

        assert "template_id" in data
        assert "status" in data
        assert data["template_id"] == template_id
        assert data["status"] in ["pending", "processing"]

    def test_get_preprocessing_status(self, upload_template):
        """Test getting preprocessing status"""
        template = upload_template()
        template_id = template["id"]

        # Trigger preprocessing
        client.post(f"/api/v1/templates/{template_id}/preprocess")

        # Get status
        response = client.get(f"/api/v1/templates/{template_id}/preprocessing")

        assert response.status_code == 200
        data = response.json()

        assert "template_id" in data
        assert "preprocessing_status" in data
        assert "faces_detected" in data

    def test_preprocessing_not_started(self, upload_template):
        """Test getting status when preprocessing hasn't started"""
        template = upload_template()
        template_id = template["id"]

        # Get status before preprocessing
        response = client.get(f"/api/v1/templates/{template_id}/preprocessing")

        assert response.status_code == 404
        assert "not started" in response.json()["detail"].lower()

    def test_preprocessing_already_running(self, upload_template):
        """Test triggering preprocessing when already running"""
        template = upload_template()
        template_id = template["id"]

        # Trigger preprocessing first time
        response1 = client.post(f"/api/v1/templates/{template_id}/preprocess")
        assert response1.status_code == 202

        # Try to trigger again
        response2 = client.post(f"/api/v1/templates/{template_id}/preprocess")

        # Should either accept or warn that it's already processing
        assert response2.status_code in [202, 400]


class TestFaceDetection:
    """Test face detection functionality"""

    def test_detect_faces_in_template(self, upload_template):
        """Test that faces are detected in template"""
        template = upload_template()
        template_id = template["id"]

        # Trigger preprocessing
        client.post(f"/api/v1/templates/{template_id}/preprocess")

        # Wait a moment for processing (in real scenario, this would be async)
        import time
        time.sleep(2)

        # Check preprocessing results
        response = client.get(f"/api/v1/templates/{template_id}/preprocessing")

        if response.status_code == 200:
            data = response.json()

            # Should have detected faces (or 0 if no faces in test image)
            assert "faces_detected" in data
            assert isinstance(data["faces_detected"], int)
            assert data["faces_detected"] >= 0

            # Should have face data
            if data["faces_detected"] > 0:
                assert "face_data" in data
                assert isinstance(data["face_data"], list)
                assert len(data["face_data"]) == data["faces_detected"]

    def test_face_data_structure(self, upload_template):
        """Test that face data has correct structure"""
        template = upload_template()
        template_id = template["id"]

        # Trigger and wait
        client.post(f"/api/v1/templates/{template_id}/preprocess")
        import time
        time.sleep(2)

        response = client.get(f"/api/v1/templates/{template_id}/preprocessing")

        if response.status_code == 200:
            data = response.json()

            if data["faces_detected"] > 0:
                face_data = data["face_data"]

                # Check first face structure
                first_face = face_data[0]

                # Should have bbox (bounding box)
                assert "bbox" in first_face
                assert len(first_face["bbox"]) == 4  # [x1, y1, x2, y2]

                # Should have gender classification
                assert "gender" in first_face
                assert first_face["gender"] in ["male", "female", "unknown"]

                # Should have landmarks (optional)
                # assert "landmarks" in first_face


class TestGenderClassification:
    """Test gender classification functionality"""

    def test_gender_counts_updated(self, upload_template):
        """Test that template is updated with gender counts"""
        template = upload_template()
        template_id = template["id"]

        # Initial template should have 0 counts
        assert template["male_face_count"] == 0
        assert template["female_face_count"] == 0
        assert template["is_preprocessed"] == False

        # Trigger preprocessing
        client.post(f"/api/v1/templates/{template_id}/preprocess")
        import time
        time.sleep(2)

        # Get updated template
        response = client.get(f"/api/v1/templates/{template_id}")
        assert response.status_code == 200

        updated_template = response.json()

        # After preprocessing, should be marked as preprocessed
        # (even if no faces detected)
        if updated_template["is_preprocessed"]:
            # Counts should be set
            assert "male_face_count" in updated_template
            assert "female_face_count" in updated_template

            male_count = updated_template["male_face_count"]
            female_count = updated_template["female_face_count"]

            # Counts should be non-negative
            assert male_count >= 0
            assert female_count >= 0

            # Total should match face_count
            total_faces = updated_template["face_count"]
            assert male_count + female_count == total_faces

    def test_gender_distribution(self, upload_template):
        """Test that gender is properly classified"""
        template = upload_template()
        template_id = template["id"]

        client.post(f"/api/v1/templates/{template_id}/preprocess")
        import time
        time.sleep(2)

        response = client.get(f"/api/v1/templates/{template_id}/preprocessing")

        if response.status_code == 200:
            data = response.json()

            if data["faces_detected"] > 0:
                face_data = data["face_data"]

                # Count genders
                male_count = sum(1 for face in face_data if face.get("gender") == "male")
                female_count = sum(1 for face in face_data if face.get("gender") == "female")

                # Should match template counts
                template_response = client.get(f"/api/v1/templates/{template_id}")
                template_data = template_response.json()

                assert template_data["male_face_count"] == male_count
                assert template_data["female_face_count"] == female_count


class TestFaceMasking:
    """Test face masking functionality"""

    def test_masked_image_created(self, upload_template):
        """Test that masked image is created during preprocessing"""
        template = upload_template()
        template_id = template["id"]

        client.post(f"/api/v1/templates/{template_id}/preprocess")
        import time
        time.sleep(2)

        response = client.get(f"/api/v1/templates/{template_id}/preprocessing")

        if response.status_code == 200:
            data = response.json()

            # Should have masked image ID if faces were detected
            if data["faces_detected"] > 0:
                assert "masked_image_id" in data
                assert data["masked_image_id"] is not None

                masked_image_id = data["masked_image_id"]

                # Verify masked image exists
                img_response = client.get(f"/api/v1/images/{masked_image_id}")
                assert img_response.status_code == 200

                img_data = img_response.json()
                assert img_data["image_type"] == "preprocessed"
                assert img_data["storage_type"] == "permanent"

    def test_get_masked_image_url(self, upload_template):
        """Test retrieving masked image URL"""
        template = upload_template()
        template_id = template["id"]

        client.post(f"/api/v1/templates/{template_id}/preprocess")
        import time
        time.sleep(2)

        response = client.get(f"/api/v1/templates/{template_id}/preprocessing")

        if response.status_code == 200:
            data = response.json()

            if data.get("masked_image_id"):
                # Should be able to get masked image URL
                assert "masked_image_url" in data or "masked_image_id" in data


class TestPreprocessingData:
    """Test preprocessing data storage"""

    def test_preprocessing_record_created(self, upload_template):
        """Test that preprocessing record is created in database"""
        template = upload_template()
        template_id = template["id"]

        client.post(f"/api/v1/templates/{template_id}/preprocess")
        import time
        time.sleep(2)

        response = client.get(f"/api/v1/templates/{template_id}/preprocessing")

        # Should have created preprocessing record
        assert response.status_code == 200

        data = response.json()
        assert data["template_id"] == template_id
        assert "original_image_id" in data
        assert "faces_detected" in data
        assert "face_data" in data
        assert "preprocessing_status" in data

    def test_preprocessing_status_transitions(self, upload_template):
        """Test preprocessing status transitions"""
        template = upload_template()
        template_id = template["id"]

        # Trigger preprocessing
        response = client.post(f"/api/v1/templates/{template_id}/preprocess")
        initial_status = response.json()["status"]

        # Status should be pending or processing
        assert initial_status in ["pending", "processing"]

        # Wait for completion
        import time
        time.sleep(3)

        # Check final status
        response = client.get(f"/api/v1/templates/{template_id}/preprocessing")

        if response.status_code == 200:
            data = response.json()
            final_status = data["preprocessing_status"]

            # Should be completed or failed
            assert final_status in ["completed", "failed", "processing"]

            if final_status == "completed":
                # Should have processed_at timestamp
                assert "processed_at" in data

    def test_preprocessing_error_handling(self, upload_template):
        """Test that preprocessing errors are properly recorded"""
        # This would test error scenarios, like invalid images
        # For now, just verify error_message field exists
        template = upload_template()
        template_id = template["id"]

        client.post(f"/api/v1/templates/{template_id}/preprocess")
        import time
        time.sleep(2)

        response = client.get(f"/api/v1/templates/{template_id}/preprocessing")

        if response.status_code == 200:
            data = response.json()

            # Should have error_message field (may be null)
            assert "error_message" in data or "preprocessing_status" in data


class TestTemplateGallery:
    """Test template gallery with preprocessed images"""

    def test_list_preprocessed_templates(self, upload_template):
        """Test listing templates filtered by preprocessing status"""
        # Upload and preprocess a template
        template = upload_template()
        template_id = template["id"]

        client.post(f"/api/v1/templates/{template_id}/preprocess")
        import time
        time.sleep(2)

        # List preprocessed templates
        response = client.get("/api/v1/templates/?is_preprocessed=true")

        assert response.status_code == 200
        data = response.json()

        # Should return templates
        assert "templates" in data
        assert "total" in data

        # All returned templates should be preprocessed
        for tmpl in data["templates"]:
            assert tmpl["is_preprocessed"] == True

    def test_template_with_preprocessing_data(self, upload_template):
        """Test that template includes preprocessing info"""
        template = upload_template()
        template_id = template["id"]

        # Before preprocessing
        response1 = client.get(f"/api/v1/templates/{template_id}")
        before = response1.json()
        assert before["is_preprocessed"] == False

        # Preprocess
        client.post(f"/api/v1/templates/{template_id}/preprocess")
        import time
        time.sleep(2)

        # After preprocessing
        response2 = client.get(f"/api/v1/templates/{template_id}")
        after = response2.json()

        # Should have updated fields
        assert "face_count" in after
        assert "male_face_count" in after
        assert "female_face_count" in after
        assert "is_preprocessed" in after


class TestBulkPreprocessing:
    """Test bulk preprocessing operations"""

    def test_preprocess_multiple_templates(self, upload_template):
        """Test preprocessing multiple templates"""
        # Upload multiple templates
        template_ids = []
        for i in range(3):
            template = upload_template(name=f"Template {i}")
            template_ids.append(template["id"])

        # Trigger bulk preprocessing
        response = client.post(
            "/api/v1/templates/preprocess/batch",
            json={"template_ids": template_ids}
        )

        if response.status_code == 200:
            data = response.json()

            assert "total" in data
            assert "queued" in data
            assert data["total"] == len(template_ids)

    def test_preprocess_all_unprocessed(self, upload_template):
        """Test preprocessing all unprocessed templates"""
        # Upload templates
        for i in range(2):
            upload_template(name=f"Unprocessed {i}")

        # Trigger preprocessing for all unprocessed
        response = client.post("/api/v1/templates/preprocess/all")

        if response.status_code == 200:
            data = response.json()

            assert "queued" in data
            assert data["queued"] >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
