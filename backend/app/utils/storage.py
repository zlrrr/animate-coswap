"""
Storage service for managing image files

Supports local filesystem and S3-compatible storage (MinIO/AWS S3)
"""

import os
import shutil
from pathlib import Path
from typing import Optional, BinaryIO
import logging
from datetime import datetime
import hashlib

from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """
    Service for storing and retrieving image files

    Supports:
    - Local filesystem storage
    - MinIO/S3 storage (Phase 3+)
    """

    def __init__(self):
        self.storage_type = settings.STORAGE_TYPE
        self.storage_path = Path(settings.STORAGE_PATH)

        if self.storage_type == "local":
            self._init_local_storage()

    def _init_local_storage(self):
        """Initialize local filesystem storage"""
        # Create storage directories
        for subdir in ["source", "templates", "results", "temp"]:
            dir_path = self.storage_path / subdir
            dir_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Local storage initialized at {self.storage_path}")

    def _generate_filename(self, original_filename: str, category: str) -> str:
        """
        Generate unique filename with timestamp and hash

        Args:
            original_filename: Original file name
            category: Category (source, templates, results, temp)

        Returns:
            Generated filename
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = Path(original_filename).suffix
        name_hash = hashlib.md5(original_filename.encode()).hexdigest()[:8]

        return f"{category}_{timestamp}_{name_hash}{ext}"

    def save_file(
        self,
        file: BinaryIO,
        filename: str,
        category: str = "source"
    ) -> tuple[str, int]:
        """
        Save uploaded file to storage

        Args:
            file: File object to save
            filename: Original filename
            category: Storage category (source, templates, results, temp)

        Returns:
            Tuple of (storage_path, file_size)
        """
        # Generate unique filename
        new_filename = self._generate_filename(filename, category)

        # Build full path
        category_dir = self.storage_path / category
        file_path = category_dir / new_filename

        # Save file
        file_size = 0
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file, f)
            file_size = file_path.stat().st_size

        # Return relative path for database storage
        relative_path = f"{category}/{new_filename}"

        logger.info(f"File saved: {relative_path} ({file_size} bytes)")

        return relative_path, file_size

    def get_file_path(self, storage_path: str) -> Path:
        """
        Get absolute file path from storage path

        Args:
            storage_path: Relative storage path (e.g., "source/image_123.jpg")

        Returns:
            Absolute file path
        """
        return self.storage_path / storage_path

    def file_exists(self, storage_path: str) -> bool:
        """
        Check if file exists in storage

        Args:
            storage_path: Relative storage path

        Returns:
            True if file exists
        """
        file_path = self.get_file_path(storage_path)
        return file_path.exists()

    def delete_file(self, storage_path: str) -> bool:
        """
        Delete file from storage

        Args:
            storage_path: Relative storage path

        Returns:
            True if deleted successfully
        """
        try:
            file_path = self.get_file_path(storage_path)
            if file_path.exists():
                file_path.unlink()
                logger.info(f"File deleted: {storage_path}")
                return True
            else:
                logger.warning(f"File not found for deletion: {storage_path}")
                return False
        except Exception as e:
            logger.error(f"Error deleting file {storage_path}: {e}")
            return False

    def get_file_url(self, storage_path: str) -> str:
        """
        Get URL for accessing file

        For local storage, returns relative path
        For S3, would return presigned URL

        Args:
            storage_path: Relative storage path

        Returns:
            File URL or path
        """
        if self.storage_type == "local":
            # In production, this should be served by a web server
            return f"/storage/{storage_path}"
        else:
            # For S3/MinIO, generate presigned URL
            # TODO: Implement in Phase 3+
            return storage_path


# Global storage service instance
storage_service = StorageService()
