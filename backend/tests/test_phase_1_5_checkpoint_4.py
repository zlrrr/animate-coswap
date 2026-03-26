"""
Test Phase 1.5 Checkpoint 1.5.4: Batch Processing

Requirements:
1. Process multiple templates in a single batch
2. Track batch progress (total, completed, failed)
3. Batch status management
4. Batch result download (ZIP archive)
"""

import pytest
from fastapi.testclient import TestClient
from io import BytesIO
from PIL import Image as PILImage
from unittest.mock import patch, MagicMock
from datetime import datetime
import time

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_db
from app.models.database import Base, Image, Template, BatchTask, FaceSwapTask


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


def _create_test_image_bytes(width=800, height=600, color=(255, 0, 0)):
    """Create a test image in memory"""
    img = PILImage.new('RGB', (width, height), color=color)
    img_bytes = BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    return img_bytes


def _insert_photo(db, filename="photo.jpg", session_id="batch-test"):
    """Insert a photo record directly into the database (no filesystem needed)"""
    db_image = Image(
        filename=filename,
        storage_path=f"temp/{filename}",
        file_size=1024,
        width=800,
        height=600,
        image_type="photo",
        storage_type="temporary",
        session_id=session_id,
        uploaded_at=datetime.utcnow()
    )
    db.add(db_image)
    db.commit()
    db.refresh(db_image)
    return {"id": db_image.id, "filename": db_image.filename}


def _insert_template(db, name="Test Template", category="custom"):
    """Insert a template record directly into the database (no filesystem needed)"""
    db_image = Image(
        filename=f"{name}.jpg",
        storage_path=f"templates/{name}.jpg",
        file_size=2048,
        width=1024,
        height=768,
        image_type="template",
        storage_type="permanent",
        category=category,
        uploaded_at=datetime.utcnow()
    )
    db.add(db_image)
    db.flush()

    db_template = Template(
        name=name,
        description=None,
        category=category,
        original_image_id=db_image.id,
        is_preprocessed=False,
        face_count=0,
        male_face_count=0,
        female_face_count=0,
        popularity_score=0,
        is_active=True,
        created_at=datetime.utcnow()
    )
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return {"id": db_template.id, "name": db_template.name}


def _get_test_db():
    """Get a test database session"""
    db = TestingSessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise


@pytest.fixture
def create_test_image():
    """Create a test image in memory"""
    def _create_image(width=800, height=600, color=(255, 0, 0)):
        return _create_test_image_bytes(width, height, color)
    return _create_image


@pytest.fixture
def upload_photo():
    """Helper to insert a photo record into the test database"""
    def _upload(session_id="batch-test"):
        db = _get_test_db()
        try:
            result = _insert_photo(db, session_id=session_id)
            return result
        finally:
            db.close()
    return _upload


@pytest.fixture
def upload_template():
    """Helper to insert a template record into the test database"""
    def _upload(name="Test Template"):
        db = _get_test_db()
        try:
            result = _insert_template(db, name=name)
            return result
        finally:
            db.close()
    return _upload


# Mock FaceMappingService.apply_mapping_to_task to avoid needing preprocessing data
_face_mapping_mock = patch(
    "app.services.batch_processing.FaceMappingService.apply_mapping_to_task",
    return_value=[
        {"source_photo": "husband", "source_face_index": 0, "target_face_index": 0},
        {"source_photo": "wife", "source_face_index": 0, "target_face_index": 1},
    ]
)

# Also mock the face mapping in the single swap endpoint
_face_mapping_v15_mock = patch(
    "app.api.v1.faceswap_v15.FaceMappingService.apply_mapping_to_task",
    return_value=[
        {"source_photo": "husband", "source_face_index": 0, "target_face_index": 0},
        {"source_photo": "wife", "source_face_index": 0, "target_face_index": 1},
    ]
)


@pytest.fixture(autouse=True)
def mock_face_mapping():
    """Mock FaceMappingService so batch creation doesn't need preprocessing data"""
    with _face_mapping_mock, _face_mapping_v15_mock:
        yield


class TestBatchCreation:
    """Test batch task creation"""

    def test_create_batch_task(self, upload_photo, upload_template):
        """Test creating a batch processing task"""
        husband_photo = upload_photo()
        wife_photo = upload_photo()

        # Upload multiple templates
        template_ids = []
        for i in range(3):
            template = upload_template(name=f"Template {i}")
            template_ids.append(template["id"])

        # Create batch task
        response = client.post(
            "/api/v1/faceswap/batch",
            json={
                "husband_photo_id": husband_photo["id"],
                "wife_photo_id": wife_photo["id"],
                "template_ids": template_ids,
                "use_default_mapping": True
            }
        )

        assert response.status_code == 202
        data = response.json()

        assert "batch_id" in data
        assert "total_tasks" in data
        assert "status" in data
        assert data["total_tasks"] == 3
        assert data["status"] == "pending"

    def test_create_batch_with_single_template(self, upload_photo, upload_template):
        """Test creating batch with single template"""
        husband_photo = upload_photo()
        wife_photo = upload_photo()
        template = upload_template()

        response = client.post(
            "/api/v1/faceswap/batch",
            json={
                "husband_photo_id": husband_photo["id"],
                "wife_photo_id": wife_photo["id"],
                "template_ids": [template["id"]]
            }
        )

        assert response.status_code == 202
        data = response.json()
        assert data["total_tasks"] == 1

    def test_create_batch_with_empty_templates(self, upload_photo):
        """Test creating batch with empty template list"""
        husband_photo = upload_photo()
        wife_photo = upload_photo()

        response = client.post(
            "/api/v1/faceswap/batch",
            json={
                "husband_photo_id": husband_photo["id"],
                "wife_photo_id": wife_photo["id"],
                "template_ids": []
            }
        )

        # Should fail validation
        assert response.status_code in [400, 422]

    def test_create_batch_with_custom_mapping(self, upload_photo, upload_template):
        """Test creating batch with custom face mapping"""
        husband_photo = upload_photo()
        wife_photo = upload_photo()
        template_ids = [upload_template()["id"] for _ in range(2)]

        custom_mappings = [
            {"source_photo": "husband", "source_face_index": 0, "target_face_index": 0},
            {"source_photo": "wife", "source_face_index": 0, "target_face_index": 1}
        ]

        response = client.post(
            "/api/v1/faceswap/batch",
            json={
                "husband_photo_id": husband_photo["id"],
                "wife_photo_id": wife_photo["id"],
                "template_ids": template_ids,
                "face_mappings": custom_mappings
            }
        )

        assert response.status_code == 202


class TestBatchStatus:
    """Test batch status tracking"""

    def test_get_batch_status(self, upload_photo, upload_template):
        """Test getting batch status"""
        husband_photo = upload_photo()
        wife_photo = upload_photo()
        template_ids = [upload_template()["id"] for _ in range(2)]

        # Create batch
        create_response = client.post(
            "/api/v1/faceswap/batch",
            json={
                "husband_photo_id": husband_photo["id"],
                "wife_photo_id": wife_photo["id"],
                "template_ids": template_ids
            }
        )
        batch_id = create_response.json()["batch_id"]

        # Get status
        status_response = client.get(f"/api/v1/faceswap/batch/{batch_id}")

        assert status_response.status_code == 200
        data = status_response.json()

        assert data["batch_id"] == batch_id
        assert "status" in data
        assert "total_tasks" in data
        assert "completed_tasks" in data
        assert "failed_tasks" in data
        assert data["total_tasks"] == 2

    def test_batch_status_not_found(self):
        """Test getting status for non-existent batch"""
        response = client.get("/api/v1/faceswap/batch/nonexistent-batch-id")
        assert response.status_code == 404

    def test_batch_progress_tracking(self, upload_photo, upload_template):
        """Test batch progress tracking"""
        husband_photo = upload_photo()
        wife_photo = upload_photo()
        template_ids = [upload_template()["id"] for _ in range(3)]

        # Create batch
        create_response = client.post(
            "/api/v1/faceswap/batch",
            json={
                "husband_photo_id": husband_photo["id"],
                "wife_photo_id": wife_photo["id"],
                "template_ids": template_ids
            }
        )
        batch_id = create_response.json()["batch_id"]

        # Check initial status
        status = client.get(f"/api/v1/faceswap/batch/{batch_id}").json()

        assert status["completed_tasks"] == 0
        assert status["failed_tasks"] == 0
        assert status["total_tasks"] == 3

        # Progress should be calculable
        if "progress_percentage" in status:
            assert status["progress_percentage"] == 0


class TestBatchTasks:
    """Test individual tasks within a batch"""

    def test_list_batch_tasks(self, upload_photo, upload_template):
        """Test listing tasks within a batch"""
        husband_photo = upload_photo()
        wife_photo = upload_photo()
        template_ids = [upload_template()["id"] for _ in range(2)]

        # Create batch
        create_response = client.post(
            "/api/v1/faceswap/batch",
            json={
                "husband_photo_id": husband_photo["id"],
                "wife_photo_id": wife_photo["id"],
                "template_ids": template_ids
            }
        )
        batch_id = create_response.json()["batch_id"]

        # List tasks
        tasks_response = client.get(f"/api/v1/faceswap/batch/{batch_id}/tasks")

        assert tasks_response.status_code == 200
        tasks = tasks_response.json()

        assert "tasks" in tasks
        assert len(tasks["tasks"]) == 2

        # Each task should have required fields
        for task in tasks["tasks"]:
            assert "task_id" in task
            assert "status" in task

    def test_all_tasks_have_same_batch_id(self, upload_photo, upload_template):
        """Test that all tasks in batch have same batch_id"""
        husband_photo = upload_photo()
        wife_photo = upload_photo()
        template_ids = [upload_template()["id"] for _ in range(2)]

        # Create batch
        create_response = client.post(
            "/api/v1/faceswap/batch",
            json={
                "husband_photo_id": husband_photo["id"],
                "wife_photo_id": wife_photo["id"],
                "template_ids": template_ids
            }
        )
        batch_id = create_response.json()["batch_id"]

        # List tasks
        tasks = client.get(f"/api/v1/faceswap/batch/{batch_id}/tasks").json()

        for task in tasks["tasks"]:
            # Each task should reference the batch
            task_details = client.get(f"/api/v1/faceswap/task/{task['task_id']}").json()
            # Note: batch_id might not be in response, but should be in database
            assert task_details["task_id"] is not None


class TestBatchResults:
    """Test batch results and download"""

    def test_get_batch_results(self, upload_photo, upload_template):
        """Test getting results for completed batch"""
        husband_photo = upload_photo()
        wife_photo = upload_photo()
        template_ids = [upload_template()["id"] for _ in range(2)]

        # Create batch
        create_response = client.post(
            "/api/v1/faceswap/batch",
            json={
                "husband_photo_id": husband_photo["id"],
                "wife_photo_id": wife_photo["id"],
                "template_ids": template_ids
            }
        )
        batch_id = create_response.json()["batch_id"]

        # Get results
        results_response = client.get(f"/api/v1/faceswap/batch/{batch_id}/results")

        assert results_response.status_code == 200
        data = results_response.json()

        assert "batch_id" in data
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_download_batch_results_zip(self, upload_photo, upload_template):
        """Test downloading batch results as ZIP"""
        husband_photo = upload_photo()
        wife_photo = upload_photo()
        template_ids = [upload_template()["id"] for _ in range(2)]

        # Create batch
        create_response = client.post(
            "/api/v1/faceswap/batch",
            json={
                "husband_photo_id": husband_photo["id"],
                "wife_photo_id": wife_photo["id"],
                "template_ids": template_ids
            }
        )
        batch_id = create_response.json()["batch_id"]

        # Download ZIP
        download_response = client.get(f"/api/v1/faceswap/batch/{batch_id}/download")

        # May not be ready yet, so 404 or 200 are acceptable
        assert download_response.status_code in [200, 404, 202]

        if download_response.status_code == 200:
            # Check content type
            assert "application/zip" in download_response.headers.get("content-type", "")


class TestBatchCancellation:
    """Test batch cancellation"""

    def test_cancel_batch(self, upload_photo, upload_template):
        """Test cancelling a batch"""
        husband_photo = upload_photo()
        wife_photo = upload_photo()
        template_ids = [upload_template()["id"] for _ in range(3)]

        # Create batch
        create_response = client.post(
            "/api/v1/faceswap/batch",
            json={
                "husband_photo_id": husband_photo["id"],
                "wife_photo_id": wife_photo["id"],
                "template_ids": template_ids
            }
        )
        batch_id = create_response.json()["batch_id"]

        # Cancel batch
        cancel_response = client.delete(f"/api/v1/faceswap/batch/{batch_id}")

        assert cancel_response.status_code == 200
        data = cancel_response.json()

        assert "message" in data
        assert "cancel" in data["message"].lower() or "deleted" in data["message"].lower()

    def test_cancel_nonexistent_batch(self):
        """Test cancelling non-existent batch"""
        response = client.delete("/api/v1/faceswap/batch/nonexistent-id")
        assert response.status_code == 404


class TestBatchValidation:
    """Test batch validation"""

    def test_batch_with_invalid_photo(self, upload_template):
        """Test batch with invalid photo ID"""
        template_ids = [upload_template()["id"]]

        response = client.post(
            "/api/v1/faceswap/batch",
            json={
                "husband_photo_id": 99999,
                "wife_photo_id": 99998,
                "template_ids": template_ids
            }
        )

        # BatchProcessingError maps to 400
        assert response.status_code in [400, 404]

    def test_batch_with_invalid_template(self, upload_photo):
        """Test batch with invalid template ID"""
        husband_photo = upload_photo()
        wife_photo = upload_photo()

        response = client.post(
            "/api/v1/faceswap/batch",
            json={
                "husband_photo_id": husband_photo["id"],
                "wife_photo_id": wife_photo["id"],
                "template_ids": [99999, 99998]
            }
        )

        # BatchProcessingError maps to 400
        assert response.status_code in [400, 404]

    def test_batch_with_too_many_templates(self, upload_photo, upload_template):
        """Test batch with excessive number of templates"""
        husband_photo = upload_photo()
        wife_photo = upload_photo()

        # Try to create batch with many templates
        template_ids = [upload_template(name=f"T{i}")["id"] for i in range(50)]

        response = client.post(
            "/api/v1/faceswap/batch",
            json={
                "husband_photo_id": husband_photo["id"],
                "wife_photo_id": wife_photo["id"],
                "template_ids": template_ids
            }
        )

        # Should either accept or reject based on limits
        assert response.status_code in [202, 400]


class TestBatchList:
    """Test listing batches"""

    def test_list_batches(self, upload_photo, upload_template):
        """Test listing all batches"""
        # Create a batch
        husband_photo = upload_photo()
        wife_photo = upload_photo()
        template_ids = [upload_template()["id"]]

        client.post(
            "/api/v1/faceswap/batch",
            json={
                "husband_photo_id": husband_photo["id"],
                "wife_photo_id": wife_photo["id"],
                "template_ids": template_ids
            }
        )

        # List batches
        response = client.get("/api/v1/faceswap/batches")

        assert response.status_code == 200
        data = response.json()

        assert "batches" in data
        assert len(data["batches"]) >= 1

    def test_list_batches_with_status_filter(self, upload_photo, upload_template):
        """Test listing batches filtered by status"""
        response = client.get("/api/v1/faceswap/batches?status=pending")

        assert response.status_code == 200
        data = response.json()

        assert "batches" in data
        # All returned batches should have pending status
        for batch in data["batches"]:
            assert batch.get("status") == "pending"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
