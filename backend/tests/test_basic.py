"""
Basic smoke tests to verify setup

These tests don't require the face-swap model
"""

import pytest
from app.core.config import settings
from app.utils.storage import StorageService
import tempfile
import os


class TestConfiguration:
    """Test configuration is loaded correctly"""

    def test_settings_loaded(self):
        """Test that settings are loaded"""
        assert settings.PROJECT_NAME is not None
        assert settings.API_V1_STR == "/api/v1"
        assert settings.VERSION is not None

    def test_database_url_configured(self):
        """Test database URL is configured"""
        assert settings.DATABASE_URL is not None
        assert len(settings.DATABASE_URL) > 0

    def test_storage_configuration(self):
        """Test storage configuration"""
        assert settings.STORAGE_TYPE in ["local", "minio", "s3"]
        assert settings.STORAGE_PATH is not None


class TestStorageService:
    """Test storage service functionality"""

    @pytest.fixture
    def storage(self):
        """Create storage service with temp directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_path = settings.STORAGE_PATH
            settings.STORAGE_PATH = tmpdir

            service = StorageService()

            yield service

            settings.STORAGE_PATH = original_path

    def test_storage_initialization(self, storage):
        """Test storage service initializes correctly"""
        assert storage.storage_type == "local"
        assert storage.storage_path is not None

    def test_storage_directories_created(self, storage):
        """Test that storage directories are created"""
        for subdir in ["source", "templates", "results", "temp"]:
            dir_path = storage.storage_path / subdir
            assert dir_path.exists()
            assert dir_path.is_dir()

    def test_generate_filename(self, storage):
        """Test filename generation"""
        filename = storage._generate_filename("test.jpg", "source")

        assert filename.startswith("source_")
        assert filename.endswith(".jpg")
        assert len(filename) > len("source_.jpg")

    def test_get_file_path(self, storage):
        """Test getting absolute file path"""
        storage_path = "source/test.jpg"
        file_path = storage.get_file_path(storage_path)

        assert file_path.is_absolute()
        assert "source" in str(file_path)
        assert "test.jpg" in str(file_path)

    def test_file_exists(self, storage):
        """Test file existence check"""
        # Non-existent file
        assert not storage.file_exists("source/nonexistent.jpg")

    def test_get_file_url(self, storage):
        """Test getting file URL"""
        storage_path = "source/test.jpg"
        url = storage.get_file_url(storage_path)

        assert "/storage/" in url
        assert "test.jpg" in url


class TestImports:
    """Test that all modules can be imported"""

    def test_import_core_modules(self):
        """Test importing core modules"""
        from app.core import config
        from app.core import database

        assert config.settings is not None
        assert database.engine is not None

    def test_import_models(self):
        """Test importing database models"""
        from app.models.database import User, Image, Template, FaceSwapTask

        assert User is not None
        assert Image is not None
        assert Template is not None
        assert FaceSwapTask is not None

    def test_import_schemas(self):
        """Test importing Pydantic schemas"""
        from app.models.schemas import (
            ImageUploadResponse,
            FaceSwapRequest,
            TaskStatusResponse
        )

        assert ImageUploadResponse is not None
        assert FaceSwapRequest is not None
        assert TaskStatusResponse is not None

    def test_import_services(self):
        """Test importing services"""
        from app.services.faceswap import FaceSwapper
        from app.utils.storage import storage_service

        assert FaceSwapper is not None
        assert storage_service is not None

    def test_import_api(self):
        """Test importing API routers"""
        from app.api.v1 import api_router

        assert api_router is not None

    def test_import_main_app(self):
        """Test importing main FastAPI app"""
        from app.main import app

        assert app is not None
        assert app.title is not None


class TestDatabaseModels:
    """Test database model definitions"""

    def test_user_model_fields(self):
        """Test User model has required fields"""
        from app.models.database import User

        # Check that User has expected columns
        assert hasattr(User, 'id')
        assert hasattr(User, 'email')
        assert hasattr(User, 'username')
        assert hasattr(User, 'password_hash')
        assert hasattr(User, 'created_at')

    def test_image_model_fields(self):
        """Test Image model has required fields"""
        from app.models.database import Image

        assert hasattr(Image, 'id')
        assert hasattr(Image, 'filename')
        assert hasattr(Image, 'storage_path')
        assert hasattr(Image, 'width')
        assert hasattr(Image, 'height')
        assert hasattr(Image, 'image_type')

    def test_template_model_fields(self):
        """Test Template model has required fields"""
        from app.models.database import Template

        assert hasattr(Template, 'id')
        assert hasattr(Template, 'image_id')
        assert hasattr(Template, 'title')
        assert hasattr(Template, 'face_count')
        assert hasattr(Template, 'is_active')

    def test_faceswap_task_model_fields(self):
        """Test FaceSwapTask model has required fields"""
        from app.models.database import FaceSwapTask

        assert hasattr(FaceSwapTask, 'id')
        assert hasattr(FaceSwapTask, 'template_id')
        assert hasattr(FaceSwapTask, 'husband_image_id')
        assert hasattr(FaceSwapTask, 'wife_image_id')
        assert hasattr(FaceSwapTask, 'status')
        assert hasattr(FaceSwapTask, 'progress')
