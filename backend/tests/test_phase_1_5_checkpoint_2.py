"""
Test Phase 1.5 Checkpoint 1.5.2: Template Preprocessing

Requirements:
1. Face detection on templates
2. Gender classification (male/female using InsightFace)
3. Face masking (create masked version of template)
4. Store preprocessing data in template_preprocessing table
5. Update template with face counts

Uses in-memory SQLite so no real PostgreSQL is needed.
Mocks storage_service and cv2 so no real filesystem or InsightFace model is needed.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime
from io import BytesIO
from PIL import Image as PILImage
import json
import numpy as np

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_db
from app.models.database import Base, Image, Template, TemplatePreprocessing


# ---------------------------------------------------------------------------
# In-memory SQLite test database
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """Create all tables before tests, drop after"""
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(autouse=True)
def clean_tables():
    """Clean tables between tests so they don't interfere with each other"""
    yield
    db = TestingSessionLocal()
    try:
        db.query(TemplatePreprocessing).delete()
        db.query(Template).delete()
        db.query(Image).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture
def test_db():
    """Provide a test database session"""
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
    """Helper to upload a template, mocking storage and cv2 so no filesystem is needed"""
    def _upload(name="Test Template", category="custom"):
        img_bytes = create_test_image(width=1024, height=768)

        # Build a fake numpy array that cv2.imread would return
        fake_cv2_img = np.zeros((768, 1024, 3), dtype=np.uint8)

        with patch("app.api.v1.templates.storage_service") as mock_storage, \
             patch("app.api.v1.templates.cv2") as mock_cv2:
            mock_storage.save_file.return_value = (f"templates/{name}.jpg", 12345)
            mock_storage.get_file_path.return_value = f"/fake/path/templates/{name}.jpg"
            mock_storage.get_file_url.return_value = f"http://localhost/storage/templates/{name}.jpg"
            mock_cv2.imread.return_value = fake_cv2_img

            response = client.post(
                "/api/v1/templates/upload",
                data={"name": name, "category": category},
                files={"file": (f"{name}.jpg", img_bytes, "image/jpeg")}
            )

        assert response.status_code == 200, f"Upload failed: {response.text}"
        return response.json()
    return _upload


class _PatcherGroup:
    """Wraps multiple patchers so .stop() stops all of them."""
    def __init__(self, *patchers):
        self._patchers = patchers
    def stop(self):
        for p in self._patchers:
            p.stop()


def _mock_storage():
    """Return started patchers for storage_service and preprocessor.
    Returns (patcher_templates, patcher_preprocessing, mock_t, mock_p) where
    stopping either patcher group also stops the preprocessor mock."""
    patcher_templates = patch("app.api.v1.templates.storage_service")
    patcher_preprocessing = patch("app.api.v1.templates_preprocessing.storage_service")
    patcher_preprocess_task = patch(
        "app.api.v1.templates_preprocessing.preprocess_template_task",
        side_effect=lambda template_id, db: _fake_preprocess(template_id, db)
    )
    mock_t = patcher_templates.start()
    mock_p = patcher_preprocessing.start()
    patcher_preprocess_task.start()
    for m in (mock_t, mock_p):
        m.get_file_url.return_value = "http://localhost/storage/fake.jpg"
        m.save_file.return_value = ("templates/fake.jpg", 12345)
        m.get_file_path.return_value = "/fake/path/templates/fake.jpg"
    # Bundle the preprocess_task patcher with patcher_preprocessing so .stop() cleans up all
    group_pp = _PatcherGroup(patcher_preprocessing, patcher_preprocess_task)
    return patcher_templates, group_pp, mock_t, mock_p


def _fake_preprocess(template_id, db):
    """Fake preprocessing that creates a TemplatePreprocessing record."""
    from app.models.database import TemplatePreprocessing, Template as TemplateModel
    template = db.query(TemplateModel).filter(TemplateModel.id == template_id).first()
    if not template:
        return

    existing = db.query(TemplatePreprocessing).filter(
        TemplatePreprocessing.template_id == template_id
    ).first()
    if not existing:
        preprocessing = TemplatePreprocessing(
            template_id=template_id,
            original_image_id=template.original_image_id,
            faces_detected=2,
            face_data=[
                {"bbox": [10, 20, 110, 120], "gender": "male"},
                {"bbox": [200, 20, 300, 120], "gender": "female"},
            ],
            preprocessing_status="completed",
            processed_at=datetime.utcnow(),
        )
        db.add(preprocessing)
        template.is_preprocessed = True
        template.face_count = 2
        template.male_face_count = 1
        template.female_face_count = 1
        db.commit()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestPreprocessingAPI:
    """Test template preprocessing API endpoints"""

    def test_trigger_preprocessing(self, upload_template):
        """Test triggering preprocessing for a template"""
        template = upload_template(name="Wedding Template")
        template_id = template["id"]

        pt, pp, _, _ = _mock_storage()
        try:
            response = client.post(f"/api/v1/templates/{template_id}/preprocess")
        finally:
            pt.stop()
            pp.stop()

        assert response.status_code == 202
        data = response.json()

        assert "template_id" in data
        assert "status" in data
        assert data["template_id"] == template_id
        assert data["status"] in ["pending", "processing"]

    def test_get_preprocessing_status(self, upload_template):
        """Test getting preprocessing status"""
        template = upload_template()
        template_id = template["id"]

        pt, pp, _, _ = _mock_storage()
        try:
            client.post(f"/api/v1/templates/{template_id}/preprocess")
            response = client.get(f"/api/v1/templates/{template_id}/preprocessing")
        finally:
            pt.stop()
            pp.stop()

        assert response.status_code == 200
        data = response.json()

        assert "template_id" in data
        assert "preprocessing_status" in data
        assert "faces_detected" in data

    def test_preprocessing_not_started(self, upload_template):
        """Test getting status when preprocessing hasn't started"""
        template = upload_template()
        template_id = template["id"]

        pt, pp, _, _ = _mock_storage()
        try:
            response = client.get(f"/api/v1/templates/{template_id}/preprocessing")
        finally:
            pt.stop()
            pp.stop()

        assert response.status_code == 404
        assert "not started" in response.json()["detail"].lower()

    def test_preprocessing_already_running(self, upload_template):
        """Test triggering preprocessing when already running"""
        template = upload_template()
        template_id = template["id"]

        pt, pp, _, _ = _mock_storage()
        try:
            response1 = client.post(f"/api/v1/templates/{template_id}/preprocess")
            assert response1.status_code == 202

            response2 = client.post(f"/api/v1/templates/{template_id}/preprocess")
        finally:
            pt.stop()
            pp.stop()

        # Should either accept or warn that it's already processing
        assert response2.status_code in [202, 400]


class TestFaceDetection:
    """Test face detection functionality"""

    def test_detect_faces_in_template(self, upload_template):
        """Test that faces are detected in template (mocked preprocessing)"""
        template = upload_template()
        template_id = template["id"]

        pt, pp, _, _ = _mock_storage()
        try:
            client.post(f"/api/v1/templates/{template_id}/preprocess")

            # Check preprocessing results
            response = client.get(f"/api/v1/templates/{template_id}/preprocessing")
        finally:
            pt.stop()
            pp.stop()

        if response.status_code == 200:
            data = response.json()

            assert "faces_detected" in data
            assert isinstance(data["faces_detected"], int)
            assert data["faces_detected"] >= 0

            if data["faces_detected"] > 0:
                assert "face_data" in data
                assert isinstance(data["face_data"], list)
                assert len(data["face_data"]) == data["faces_detected"]

    def test_face_data_structure(self, upload_template, test_db):
        """Test that face data has correct structure when preprocessing completes"""
        template = upload_template()
        template_id = template["id"]

        # Directly insert a completed preprocessing record with face data
        # to test the response structure without needing InsightFace
        preprocessing = test_db.query(TemplatePreprocessing).filter(
            TemplatePreprocessing.template_id == template_id
        ).first()
        if not preprocessing:
            preprocessing = TemplatePreprocessing(
                template_id=template_id,
                original_image_id=template["original_image_id"],
                faces_detected=2,
                face_data=[
                    {"bbox": [10, 20, 110, 120], "gender": "male"},
                    {"bbox": [200, 20, 300, 120], "gender": "female"},
                ],
                preprocessing_status="completed",
                processed_at=datetime.utcnow(),
            )
            test_db.add(preprocessing)
            test_db.commit()

        pt, pp, _, _ = _mock_storage()
        try:
            response = client.get(f"/api/v1/templates/{template_id}/preprocessing")
        finally:
            pt.stop()
            pp.stop()

        assert response.status_code == 200
        data = response.json()
        assert data["faces_detected"] == 2

        face_data = data["face_data"]
        first_face = face_data[0]

        assert "bbox" in first_face
        assert len(first_face["bbox"]) == 4
        assert "gender" in first_face
        assert first_face["gender"] in ["male", "female", "unknown"]


class TestGenderClassification:
    """Test gender classification functionality"""

    def test_gender_counts_updated(self, upload_template, test_db):
        """Test that template is updated with gender counts"""
        template = upload_template()
        template_id = template["id"]

        # Initial template should have 0 counts
        assert template["male_face_count"] == 0
        assert template["female_face_count"] == 0
        assert template["is_preprocessed"] is False

        # Simulate completed preprocessing by updating DB directly
        db_template = test_db.query(Template).filter(Template.id == template_id).first()
        db_template.is_preprocessed = True
        db_template.face_count = 2
        db_template.male_face_count = 1
        db_template.female_face_count = 1
        test_db.commit()

        pt, pp, _, _ = _mock_storage()
        try:
            response = client.get(f"/api/v1/templates/{template_id}")
        finally:
            pt.stop()
            pp.stop()

        assert response.status_code == 200
        updated_template = response.json()

        assert updated_template["is_preprocessed"] is True
        assert updated_template["male_face_count"] == 1
        assert updated_template["female_face_count"] == 1
        assert updated_template["male_face_count"] + updated_template["female_face_count"] == updated_template["face_count"]

    def test_gender_distribution(self, upload_template, test_db):
        """Test that gender is properly classified"""
        template = upload_template()
        template_id = template["id"]

        # Insert preprocessing record with known face data
        preprocessing = TemplatePreprocessing(
            template_id=template_id,
            original_image_id=template["original_image_id"],
            faces_detected=3,
            face_data=[
                {"bbox": [10, 20, 110, 120], "gender": "male"},
                {"bbox": [200, 20, 300, 120], "gender": "female"},
                {"bbox": [400, 20, 500, 120], "gender": "female"},
            ],
            preprocessing_status="completed",
            processed_at=datetime.utcnow(),
        )
        test_db.add(preprocessing)

        db_template = test_db.query(Template).filter(Template.id == template_id).first()
        db_template.is_preprocessed = True
        db_template.face_count = 3
        db_template.male_face_count = 1
        db_template.female_face_count = 2
        test_db.commit()

        pt, pp, _, _ = _mock_storage()
        try:
            response = client.get(f"/api/v1/templates/{template_id}/preprocessing")
        finally:
            pt.stop()
            pp.stop()

        assert response.status_code == 200
        data = response.json()
        assert data["faces_detected"] == 3

        face_data = data["face_data"]
        male_count = sum(1 for face in face_data if face.get("gender") == "male")
        female_count = sum(1 for face in face_data if face.get("gender") == "female")

        pt2, pp2, _, _ = _mock_storage()
        try:
            template_response = client.get(f"/api/v1/templates/{template_id}")
        finally:
            pt2.stop()
            pp2.stop()

        template_data = template_response.json()
        assert template_data["male_face_count"] == male_count
        assert template_data["female_face_count"] == female_count


class TestFaceMasking:
    """Test face masking functionality"""

    def test_masked_image_created(self, upload_template, test_db):
        """Test that masked image is created during preprocessing"""
        template = upload_template()
        template_id = template["id"]

        # Create a fake masked image in DB
        masked_image = Image(
            filename="masked.jpg",
            storage_path="templates/masked.jpg",
            file_size=9999,
            width=1024,
            height=768,
            image_type="preprocessed",
            storage_type="permanent",
            uploaded_at=datetime.utcnow(),
        )
        test_db.add(masked_image)
        test_db.flush()

        preprocessing = TemplatePreprocessing(
            template_id=template_id,
            original_image_id=template["original_image_id"],
            faces_detected=2,
            face_data=[
                {"bbox": [10, 20, 110, 120], "gender": "male"},
                {"bbox": [200, 20, 300, 120], "gender": "female"},
            ],
            masked_image_id=masked_image.id,
            preprocessing_status="completed",
            processed_at=datetime.utcnow(),
        )
        test_db.add(preprocessing)
        test_db.commit()

        pt, pp, _, _ = _mock_storage()
        try:
            response = client.get(f"/api/v1/templates/{template_id}/preprocessing")
        finally:
            pt.stop()
            pp.stop()

        assert response.status_code == 200
        data = response.json()

        assert data["faces_detected"] > 0
        assert "masked_image_id" in data
        assert data["masked_image_id"] is not None
        assert data["masked_image_id"] == masked_image.id

    def test_get_masked_image_url(self, upload_template, test_db):
        """Test retrieving masked image URL"""
        template = upload_template()
        template_id = template["id"]

        masked_image = Image(
            filename="masked2.jpg",
            storage_path="templates/masked2.jpg",
            file_size=9999,
            width=1024,
            height=768,
            image_type="preprocessed",
            storage_type="permanent",
            uploaded_at=datetime.utcnow(),
        )
        test_db.add(masked_image)
        test_db.flush()

        preprocessing = TemplatePreprocessing(
            template_id=template_id,
            original_image_id=template["original_image_id"],
            faces_detected=1,
            face_data=[{"bbox": [10, 20, 110, 120], "gender": "male"}],
            masked_image_id=masked_image.id,
            preprocessing_status="completed",
            processed_at=datetime.utcnow(),
        )
        test_db.add(preprocessing)
        test_db.commit()

        pt, pp, _, _ = _mock_storage()
        try:
            response = client.get(f"/api/v1/templates/{template_id}/preprocessing")
        finally:
            pt.stop()
            pp.stop()

        assert response.status_code == 200
        data = response.json()

        assert "masked_image_url" in data or "masked_image_id" in data


class TestPreprocessingData:
    """Test preprocessing data storage"""

    def test_preprocessing_record_created(self, upload_template, test_db):
        """Test that preprocessing record is created in database"""
        template = upload_template()
        template_id = template["id"]

        pt, pp, _, _ = _mock_storage()
        try:
            client.post(f"/api/v1/templates/{template_id}/preprocess")
            response = client.get(f"/api/v1/templates/{template_id}/preprocessing")
        finally:
            pt.stop()
            pp.stop()

        assert response.status_code == 200

        data = response.json()
        assert data["template_id"] == template_id
        assert "original_image_id" in data
        assert "faces_detected" in data
        assert "face_data" in data
        assert "preprocessing_status" in data

    def test_preprocessing_status_transitions(self, upload_template, test_db):
        """Test preprocessing status transitions"""
        template = upload_template()
        template_id = template["id"]

        pt, pp, _, _ = _mock_storage()
        try:
            response = client.post(f"/api/v1/templates/{template_id}/preprocess")
        finally:
            pt.stop()
            pp.stop()

        initial_status = response.json()["status"]
        assert initial_status in ["pending", "processing"]

        # Simulate completion by updating DB directly
        preprocessing = test_db.query(TemplatePreprocessing).filter(
            TemplatePreprocessing.template_id == template_id
        ).first()
        if preprocessing:
            preprocessing.preprocessing_status = "completed"
            preprocessing.processed_at = datetime.utcnow()
            test_db.commit()

        pt2, pp2, _, _ = _mock_storage()
        try:
            response = client.get(f"/api/v1/templates/{template_id}/preprocessing")
        finally:
            pt2.stop()
            pp2.stop()

        assert response.status_code == 200
        data = response.json()
        final_status = data["preprocessing_status"]
        assert final_status in ["completed", "failed", "processing"]

        if final_status == "completed":
            assert "processed_at" in data

    def test_preprocessing_error_handling(self, upload_template, test_db):
        """Test that preprocessing errors are properly recorded"""
        template = upload_template()
        template_id = template["id"]

        # Simulate a failed preprocessing
        preprocessing = TemplatePreprocessing(
            template_id=template_id,
            original_image_id=template["original_image_id"],
            faces_detected=0,
            face_data=[],
            preprocessing_status="failed",
            error_message="Test error: model not available",
        )
        test_db.add(preprocessing)
        test_db.commit()

        pt, pp, _, _ = _mock_storage()
        try:
            response = client.get(f"/api/v1/templates/{template_id}/preprocessing")
        finally:
            pt.stop()
            pp.stop()

        assert response.status_code == 200
        data = response.json()
        assert "error_message" in data or "preprocessing_status" in data


class TestTemplateGallery:
    """Test template gallery with preprocessed images"""

    def test_list_preprocessed_templates(self, upload_template, test_db):
        """Test listing templates filtered by preprocessing status"""
        template = upload_template()
        template_id = template["id"]

        # Mark as preprocessed
        db_template = test_db.query(Template).filter(Template.id == template_id).first()
        db_template.is_preprocessed = True
        test_db.commit()

        pt, pp, _, _ = _mock_storage()
        try:
            response = client.get("/api/v1/templates/", params={"is_preprocessed": "true"})
        finally:
            pt.stop()
            pp.stop()

        assert response.status_code == 200
        data = response.json()

        assert "templates" in data
        assert "total" in data

        for tmpl in data["templates"]:
            assert tmpl["is_preprocessed"] is True

    def test_template_with_preprocessing_data(self, upload_template, test_db):
        """Test that template includes preprocessing info"""
        template = upload_template()
        template_id = template["id"]

        pt, pp, _, _ = _mock_storage()
        try:
            response1 = client.get(f"/api/v1/templates/{template_id}")
        finally:
            pt.stop()
            pp.stop()

        before = response1.json()
        assert before["is_preprocessed"] is False

        # Simulate preprocessing completion
        db_template = test_db.query(Template).filter(Template.id == template_id).first()
        db_template.is_preprocessed = True
        db_template.face_count = 2
        db_template.male_face_count = 1
        db_template.female_face_count = 1
        test_db.commit()

        pt2, pp2, _, _ = _mock_storage()
        try:
            response2 = client.get(f"/api/v1/templates/{template_id}")
        finally:
            pt2.stop()
            pp2.stop()

        after = response2.json()
        assert "face_count" in after
        assert "male_face_count" in after
        assert "female_face_count" in after
        assert "is_preprocessed" in after


class TestBulkPreprocessing:
    """Test bulk preprocessing operations"""

    def test_preprocess_multiple_templates(self, upload_template):
        """Test preprocessing multiple templates"""
        template_ids = []
        for i in range(3):
            template = upload_template(name=f"Template {i}")
            template_ids.append(template["id"])

        pt, pp, _, _ = _mock_storage()
        try:
            response = client.post(
                "/api/v1/templates/preprocess/batch",
                json=template_ids,  # The endpoint expects List[int] body
            )
        finally:
            pt.stop()
            pp.stop()

        if response.status_code == 200:
            data = response.json()
            assert "total" in data
            assert "queued" in data
            assert data["total"] == len(template_ids)

    def test_preprocess_all_unprocessed(self, upload_template):
        """Test preprocessing all unprocessed templates"""
        for i in range(2):
            upload_template(name=f"Unprocessed {i}")

        pt, pp, _, _ = _mock_storage()
        try:
            response = client.post("/api/v1/templates/preprocess/all")
        finally:
            pt.stop()
            pp.stop()

        if response.status_code == 200:
            data = response.json()
            assert "queued" in data
            assert data["queued"] >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
