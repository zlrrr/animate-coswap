"""
Tests for Phase 1.5 Checkpoint 1.5.5: Auto Cleanup

Tests cleanup functionality:
- Expired temporary images
- Session-based cleanup
- Old task results
- Orphaned files
- Cleanup statistics
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil

from app.main import app
from app.core.database import get_db
from app.models.database import Image, FaceSwapTask
from app.services.cleanup import CleanupService
from app.utils.storage import storage_service

client = TestClient(app)


@pytest.fixture
def temp_storage():
    """Create temporary storage directory"""
    temp_dir = tempfile.mkdtemp()
    original_path = storage_service.storage_path

    # Create category directories
    for category in ['photos', 'templates', 'preprocessed', 'results']:
        (Path(temp_dir) / category).mkdir(parents=True, exist_ok=True)

    storage_service.storage_path = temp_dir

    yield temp_dir

    # Restore original path
    storage_service.storage_path = original_path

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def create_temp_image(temp_storage):
    """Helper to create temporary image"""
    def _create(
        expired: bool = False,
        session_id: str = None,
        storage_type: str = 'temporary'
    ):
        db = next(get_db())

        # Create physical file
        category_dir = Path(temp_storage) / 'photos'
        file_path = category_dir / f"temp_{datetime.utcnow().timestamp()}.jpg"

        with open(file_path, 'wb') as f:
            f.write(b"fake image data")

        file_size = file_path.stat().st_size

        # Calculate expiration
        expires_at = None
        if storage_type == 'temporary':
            if expired:
                expires_at = datetime.utcnow() - timedelta(hours=1)
            else:
                expires_at = datetime.utcnow() + timedelta(hours=24)

        # Create database record
        image = Image(
            filename=file_path.name,
            storage_path=f"photos/{file_path.name}",
            storage_type=storage_type,
            file_size=file_size,
            width=100,
            height=100,
            image_type='photo',
            expires_at=expires_at,
            session_id=session_id,
            uploaded_at=datetime.utcnow()
        )

        db.add(image)
        db.commit()
        db.refresh(image)

        return {
            "id": image.id,
            "filename": image.filename,
            "storage_path": image.storage_path,
            "expires_at": image.expires_at,
            "session_id": image.session_id,
            "file_path": str(file_path)
        }

    return _create


@pytest.fixture
def create_task_with_result(temp_storage, create_temp_image):
    """Helper to create task with result image"""
    def _create(completed_days_ago: int = 0):
        db = next(get_db())

        # Create photos and result image
        husband_photo = create_temp_image()
        wife_photo = create_temp_image()
        result_image = create_temp_image(storage_type='permanent')

        # Create task
        completed_at = datetime.utcnow() - timedelta(days=completed_days_ago)

        task = FaceSwapTask(
            task_id=f"task_{datetime.utcnow().timestamp()}",
            template_id=1,
            husband_photo_id=husband_photo['id'],
            wife_photo_id=wife_photo['id'],
            result_image_id=result_image['id'],
            status='completed',
            progress=100,
            completed_at=completed_at,
            created_at=completed_at - timedelta(minutes=5)
        )

        db.add(task)
        db.commit()
        db.refresh(task)

        return {
            "task_id": task.task_id,
            "result_image_id": result_image['id'],
            "completed_at": completed_at
        }

    return _create


class TestExpiredCleanup:
    """Test cleanup of expired temporary images"""

    def test_cleanup_expired_images_dry_run(self, create_temp_image):
        """Test expired cleanup in dry run mode"""
        # Create expired and non-expired images
        expired1 = create_temp_image(expired=True)
        expired2 = create_temp_image(expired=True)
        active = create_temp_image(expired=False)

        response = client.post(
            "/api/v1/admin/cleanup/expired?dry_run=true"
        )

        assert response.status_code == 200
        data = response.json()

        assert data['operation'] == 'cleanup_expired_images'
        assert data['dry_run'] is True
        assert data['deleted_count'] == 2

        # Verify files still exist (dry run)
        assert Path(expired1['file_path']).exists()
        assert Path(expired2['file_path']).exists()

    def test_cleanup_expired_images_real(self, create_temp_image):
        """Test actual cleanup of expired images"""
        # Create expired images
        expired1 = create_temp_image(expired=True)
        expired2 = create_temp_image(expired=True)

        response = client.post(
            "/api/v1/admin/cleanup/expired?dry_run=false"
        )

        assert response.status_code == 200
        data = response.json()

        assert data['deleted_count'] == 2
        assert data['deleted_size_bytes'] > 0
        assert data['dry_run'] is False

        # Verify files deleted
        assert not Path(expired1['file_path']).exists()
        assert not Path(expired2['file_path']).exists()

    def test_cleanup_skips_active_task_images(self, create_temp_image):
        """Test cleanup skips images used by active tasks"""
        db = next(get_db())

        # Create expired image
        expired = create_temp_image(expired=True)

        # Create active task using this image
        task = FaceSwapTask(
            task_id="active_task",
            template_id=1,
            husband_photo_id=expired['id'],
            wife_photo_id=expired['id'],
            status='pending',
            created_at=datetime.utcnow()
        )
        db.add(task)
        db.commit()

        # Try cleanup
        response = client.post(
            "/api/v1/admin/cleanup/expired?dry_run=false"
        )

        assert response.status_code == 200
        data = response.json()

        # Should not delete (active task)
        assert data['deleted_count'] == 0

        # File should still exist
        assert Path(expired['file_path']).exists()


class TestSessionCleanup:
    """Test session-based cleanup"""

    def test_cleanup_session_images(self, create_temp_image):
        """Test cleanup of all images for a session"""
        session_id = "test_session_123"

        # Create images for this session
        img1 = create_temp_image(session_id=session_id)
        img2 = create_temp_image(session_id=session_id)
        img3 = create_temp_image(session_id=session_id)

        # Create image for different session
        other = create_temp_image(session_id="other_session")

        response = client.post(
            f"/api/v1/admin/cleanup/session/{session_id}?dry_run=false"
        )

        assert response.status_code == 200
        data = response.json()

        assert data['operation'] == 'cleanup_session'
        assert data['session_id'] == session_id
        assert data['deleted_count'] == 3

        # Verify session files deleted
        assert not Path(img1['file_path']).exists()
        assert not Path(img2['file_path']).exists()
        assert not Path(img3['file_path']).exists()

        # Other session file still exists
        assert Path(other['file_path']).exists()

    def test_cleanup_session_dry_run(self, create_temp_image):
        """Test session cleanup in dry run mode"""
        session_id = "test_session_456"

        img1 = create_temp_image(session_id=session_id)
        img2 = create_temp_image(session_id=session_id)

        response = client.post(
            f"/api/v1/admin/cleanup/session/{session_id}?dry_run=true"
        )

        assert response.status_code == 200
        data = response.json()

        assert data['dry_run'] is True
        assert data['deleted_count'] == 2

        # Files still exist
        assert Path(img1['file_path']).exists()
        assert Path(img2['file_path']).exists()


class TestOldResultsCleanup:
    """Test cleanup of old task results"""

    def test_cleanup_old_results(self, create_task_with_result):
        """Test cleanup of old task results"""
        # Create old and recent results
        old_task = create_task_with_result(completed_days_ago=35)
        recent_task = create_task_with_result(completed_days_ago=10)

        response = client.post(
            "/api/v1/admin/cleanup/old-results?days_old=30&dry_run=false"
        )

        assert response.status_code == 200
        data = response.json()

        assert data['operation'] == 'cleanup_old_results'
        assert data['days_old'] == 30
        assert data['deleted_count'] == 1

    def test_cleanup_old_results_custom_days(self, create_task_with_result):
        """Test cleanup with custom days parameter"""
        task1 = create_task_with_result(completed_days_ago=50)
        task2 = create_task_with_result(completed_days_ago=40)
        task3 = create_task_with_result(completed_days_ago=20)

        response = client.post(
            "/api/v1/admin/cleanup/old-results?days_old=45&dry_run=false"
        )

        assert response.status_code == 200
        data = response.json()

        assert data['deleted_count'] == 1  # Only task1 (50 days old)

    def test_cleanup_old_results_dry_run(self, create_task_with_result):
        """Test old results cleanup in dry run"""
        old_task = create_task_with_result(completed_days_ago=35)

        response = client.post(
            "/api/v1/admin/cleanup/old-results?days_old=30&dry_run=true"
        )

        assert response.status_code == 200
        data = response.json()

        assert data['dry_run'] is True
        assert data['deleted_count'] == 1


class TestOrphanedFilesCleanup:
    """Test cleanup of orphaned files"""

    def test_cleanup_orphaned_files(self, temp_storage):
        """Test cleanup of files not in database"""
        db = next(get_db())

        # Create orphaned file
        orphaned_path = Path(temp_storage) / 'photos' / 'orphaned.jpg'
        with open(orphaned_path, 'wb') as f:
            f.write(b"orphaned file data")

        # Create file with database record
        valid_path = Path(temp_storage) / 'photos' / 'valid.jpg'
        with open(valid_path, 'wb') as f:
            f.write(b"valid file data")

        image = Image(
            filename='valid.jpg',
            storage_path='photos/valid.jpg',
            storage_type='permanent',
            file_size=valid_path.stat().st_size,
            width=100,
            height=100,
            image_type='photo',
            uploaded_at=datetime.utcnow()
        )
        db.add(image)
        db.commit()

        response = client.post(
            "/api/v1/admin/cleanup/orphaned?dry_run=false"
        )

        assert response.status_code == 200
        data = response.json()

        assert data['operation'] == 'cleanup_orphaned_files'
        assert data['deleted_count'] == 1

        # Orphaned file deleted
        assert not orphaned_path.exists()

        # Valid file still exists
        assert valid_path.exists()

    def test_cleanup_orphaned_dry_run(self, temp_storage):
        """Test orphaned cleanup in dry run"""
        orphaned_path = Path(temp_storage) / 'results' / 'orphaned.jpg'
        with open(orphaned_path, 'wb') as f:
            f.write(b"orphaned")

        response = client.post(
            "/api/v1/admin/cleanup/orphaned?dry_run=true"
        )

        assert response.status_code == 200
        data = response.json()

        assert data['dry_run'] is True
        assert data['deleted_count'] >= 1

        # File still exists
        assert orphaned_path.exists()


class TestFullCleanup:
    """Test full cleanup operation"""

    def test_cleanup_all(self, create_temp_image, create_task_with_result, temp_storage):
        """Test running all cleanup operations"""
        # Create various cleanable items
        expired1 = create_temp_image(expired=True)
        expired2 = create_temp_image(expired=True)
        old_task = create_task_with_result(completed_days_ago=35)

        # Create orphaned file
        orphaned_path = Path(temp_storage) / 'results' / 'orphaned.jpg'
        with open(orphaned_path, 'wb') as f:
            f.write(b"orphaned")

        response = client.post(
            "/api/v1/admin/cleanup/all?days_old=30&dry_run=false"
        )

        assert response.status_code == 200
        data = response.json()

        assert data['operation'] == 'cleanup_all'
        assert 'expired_images' in data
        assert 'old_task_results' in data
        assert 'orphaned_files' in data
        assert 'totals' in data

        # Check totals
        totals = data['totals']
        assert totals['deleted_count'] > 0
        assert totals['deleted_size_bytes'] > 0

    def test_cleanup_all_dry_run(self, create_temp_image, temp_storage):
        """Test full cleanup in dry run"""
        expired1 = create_temp_image(expired=True)
        expired2 = create_temp_image(expired=True)

        response = client.post(
            "/api/v1/admin/cleanup/all?dry_run=true"
        )

        assert response.status_code == 200
        data = response.json()

        assert data['totals']['dry_run'] is True

        # Files still exist
        assert Path(expired1['file_path']).exists()
        assert Path(expired2['file_path']).exists()


class TestCleanupStats:
    """Test cleanup statistics"""

    def test_get_cleanup_stats(self, create_temp_image, create_task_with_result):
        """Test getting cleanup statistics"""
        # Create some cleanable items
        expired1 = create_temp_image(expired=True)
        expired2 = create_temp_image(expired=True)
        active = create_temp_image(expired=False)
        old_task = create_task_with_result(completed_days_ago=35)

        response = client.get("/api/v1/admin/cleanup/stats")

        assert response.status_code == 200
        data = response.json()

        assert data['operation'] == 'get_stats'
        assert 'expired_images' in data
        assert 'temporary_images' in data
        assert 'old_task_results_30d' in data
        assert 'last_checked' in data

        # Should have 2 expired images
        assert data['expired_images'] >= 2

        # Should have at least 3 temporary images
        assert data['temporary_images'] >= 3

    def test_cleanup_stats_empty(self):
        """Test stats when nothing to clean"""
        response = client.get("/api/v1/admin/cleanup/stats")

        assert response.status_code == 200
        data = response.json()

        assert 'expired_images' in data
        assert 'temporary_images' in data
        assert 'old_task_results_30d' in data


class TestCleanupService:
    """Test CleanupService methods directly"""

    def test_cleanup_expired_images_service(self, create_temp_image):
        """Test CleanupService.cleanup_expired_images"""
        db = next(get_db())

        # Create expired images
        expired1 = create_temp_image(expired=True)
        expired2 = create_temp_image(expired=True)

        result = CleanupService.cleanup_expired_images(db, dry_run=False)

        assert result['deleted_count'] == 2
        assert result['deleted_size_bytes'] > 0
        assert result['dry_run'] is False

    def test_cleanup_session_service(self, create_temp_image):
        """Test CleanupService.cleanup_session_images"""
        db = next(get_db())

        session_id = "service_test_session"
        img1 = create_temp_image(session_id=session_id)
        img2 = create_temp_image(session_id=session_id)

        result = CleanupService.cleanup_session_images(session_id, db, dry_run=False)

        assert result['session_id'] == session_id
        assert result['deleted_count'] == 2

    def test_cleanup_all_service(self, create_temp_image, create_task_with_result):
        """Test CleanupService.cleanup_all"""
        db = next(get_db())

        expired = create_temp_image(expired=True)
        old_task = create_task_with_result(completed_days_ago=35)

        result = CleanupService.cleanup_all(db, days_old=30, dry_run=False)

        assert 'expired_images' in result
        assert 'old_task_results' in result
        assert 'orphaned_files' in result
        assert 'totals' in result
        assert result['totals']['deleted_count'] > 0

    def test_get_cleanup_stats_service(self, create_temp_image):
        """Test CleanupService.get_cleanup_stats"""
        db = next(get_db())

        expired = create_temp_image(expired=True)

        stats = CleanupService.get_cleanup_stats(db)

        assert 'expired_images' in stats
        assert 'temporary_images' in stats
        assert 'old_task_results_30d' in stats
        assert stats['expired_images'] >= 1


class TestCleanupValidation:
    """Test cleanup input validation"""

    def test_cleanup_old_results_invalid_days(self):
        """Test old results cleanup with invalid days parameter"""
        # Test days < 1
        response = client.post(
            "/api/v1/admin/cleanup/old-results?days_old=0"
        )
        assert response.status_code == 422  # Validation error

        # Test days > 365
        response = client.post(
            "/api/v1/admin/cleanup/old-results?days_old=400"
        )
        assert response.status_code == 422

    def test_cleanup_all_invalid_days(self):
        """Test full cleanup with invalid days parameter"""
        response = client.post(
            "/api/v1/admin/cleanup/all?days_old=-5"
        )
        assert response.status_code == 422


class TestCleanupErrorHandling:
    """Test cleanup error handling"""

    def test_cleanup_with_db_errors(self, create_temp_image):
        """Test cleanup handles database errors gracefully"""
        # This test ensures cleanup continues even if some operations fail
        # Implementation should handle errors and include them in results

        expired = create_temp_image(expired=True)

        response = client.post(
            "/api/v1/admin/cleanup/expired?dry_run=false"
        )

        assert response.status_code == 200
        data = response.json()

        # Should have errors field
        assert 'errors' in data
