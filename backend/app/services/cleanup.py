"""
Auto Cleanup Service

Phase 1.5 Checkpoint 1.5.5
Handles automatic cleanup of temporary files and expired data
"""

import logging
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.database import Image, FaceSwapTask
from app.utils.storage import storage_service

logger = logging.getLogger(__name__)


class CleanupService:
    """
    Service for automatic cleanup of temporary files

    Provides:
    - Cleanup of expired temporary images
    - Session-based cleanup
    - Orphaned file cleanup
    - Old task result cleanup
    """

    @staticmethod
    def cleanup_expired_images(
        db: Session,
        dry_run: bool = False
    ) -> Dict:
        """
        Clean up expired temporary images

        Deletes images where:
        - storage_type = 'temporary'
        - expires_at < now()

        Args:
            db: Database session
            dry_run: If True, only report what would be deleted

        Returns:
            Dictionary with cleanup statistics
        """
        now = datetime.utcnow()

        # Find expired temporary images
        expired_images = db.query(Image).filter(
            and_(
                Image.storage_type == 'temporary',
                Image.expires_at.isnot(None),
                Image.expires_at < now
            )
        ).all()

        deleted_count = 0
        deleted_size = 0
        errors = []

        logger.info(
            f"Found {len(expired_images)} expired temporary images "
            f"(dry_run={dry_run})"
        )

        for image in expired_images:
            try:
                # Check if image is referenced by any active tasks
                # Don't delete if used in pending/processing tasks
                active_tasks = db.query(FaceSwapTask).filter(
                    and_(
                        FaceSwapTask.status.in_(['pending', 'processing']),
                        (
                            (FaceSwapTask.husband_photo_id == image.id) |
                            (FaceSwapTask.wife_photo_id == image.id)
                        )
                    )
                ).count()

                if active_tasks > 0:
                    logger.info(
                        f"Skipping image {image.id}: "
                        f"used by {active_tasks} active tasks"
                    )
                    continue

                file_size = image.file_size or 0

                if not dry_run:
                    # Delete physical file
                    file_path = storage_service.get_full_path(image.storage_path)

                    if Path(file_path).exists():
                        Path(file_path).unlink()
                        logger.debug(f"Deleted file: {file_path}")

                    # Delete database record
                    db.delete(image)
                    db.commit()

                deleted_count += 1
                deleted_size += file_size

                logger.info(
                    f"{'Would delete' if dry_run else 'Deleted'} "
                    f"image {image.id}: {image.filename}"
                )

            except Exception as e:
                logger.error(f"Error deleting image {image.id}: {str(e)}")
                errors.append({
                    "image_id": image.id,
                    "filename": image.filename,
                    "error": str(e)
                })
                db.rollback()

        return {
            "deleted_count": deleted_count,
            "deleted_size_bytes": deleted_size,
            "deleted_size_mb": round(deleted_size / 1024 / 1024, 2),
            "errors": errors,
            "dry_run": dry_run
        }

    @staticmethod
    def cleanup_session_images(
        session_id: str,
        db: Session,
        dry_run: bool = False
    ) -> Dict:
        """
        Clean up all images for a specific session

        Useful when user's session ends or they explicitly clear their data

        Args:
            session_id: Session ID
            db: Database session
            dry_run: If True, only report what would be deleted

        Returns:
            Dictionary with cleanup statistics
        """
        # Find images for this session
        session_images = db.query(Image).filter(
            Image.session_id == session_id
        ).all()

        deleted_count = 0
        deleted_size = 0
        errors = []

        logger.info(
            f"Found {len(session_images)} images for session {session_id} "
            f"(dry_run={dry_run})"
        )

        for image in session_images:
            try:
                # Check if image is referenced by active tasks
                active_tasks = db.query(FaceSwapTask).filter(
                    and_(
                        FaceSwapTask.status.in_(['pending', 'processing']),
                        (
                            (FaceSwapTask.husband_photo_id == image.id) |
                            (FaceSwapTask.wife_photo_id == image.id)
                        )
                    )
                ).count()

                if active_tasks > 0:
                    logger.info(
                        f"Skipping image {image.id}: "
                        f"used by {active_tasks} active tasks"
                    )
                    continue

                file_size = image.file_size or 0

                if not dry_run:
                    # Delete physical file
                    file_path = storage_service.get_full_path(image.storage_path)

                    if Path(file_path).exists():
                        Path(file_path).unlink()
                        logger.debug(f"Deleted file: {file_path}")

                    # Delete database record
                    db.delete(image)
                    db.commit()

                deleted_count += 1
                deleted_size += file_size

            except Exception as e:
                logger.error(f"Error deleting image {image.id}: {str(e)}")
                errors.append({
                    "image_id": image.id,
                    "filename": image.filename,
                    "error": str(e)
                })
                db.rollback()

        return {
            "session_id": session_id,
            "deleted_count": deleted_count,
            "deleted_size_bytes": deleted_size,
            "deleted_size_mb": round(deleted_size / 1024 / 1024, 2),
            "errors": errors,
            "dry_run": dry_run
        }

    @staticmethod
    def cleanup_old_task_results(
        days_old: int,
        db: Session,
        dry_run: bool = False
    ) -> Dict:
        """
        Clean up old completed/failed task results

        Deletes result images from tasks older than specified days

        Args:
            days_old: Delete results older than this many days
            db: Database session
            dry_run: If True, only report what would be deleted

        Returns:
            Dictionary with cleanup statistics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        # Find old completed/failed tasks with result images
        old_tasks = db.query(FaceSwapTask).filter(
            and_(
                FaceSwapTask.status.in_(['completed', 'failed']),
                FaceSwapTask.completed_at.isnot(None),
                FaceSwapTask.completed_at < cutoff_date,
                FaceSwapTask.result_image_id.isnot(None)
            )
        ).all()

        deleted_count = 0
        deleted_size = 0
        errors = []

        logger.info(
            f"Found {len(old_tasks)} old task results (>{days_old} days) "
            f"(dry_run={dry_run})"
        )

        for task in old_tasks:
            try:
                # Get result image
                result_image = db.query(Image).filter(
                    Image.id == task.result_image_id
                ).first()

                if not result_image:
                    logger.warning(
                        f"Result image {task.result_image_id} not found for task {task.task_id}"
                    )
                    continue

                file_size = result_image.file_size or 0

                if not dry_run:
                    # Delete physical file
                    file_path = storage_service.get_full_path(result_image.storage_path)

                    if Path(file_path).exists():
                        Path(file_path).unlink()
                        logger.debug(f"Deleted result file: {file_path}")

                    # Delete image record
                    db.delete(result_image)

                    # Clear task reference
                    task.result_image_id = None

                    db.commit()

                deleted_count += 1
                deleted_size += file_size

                logger.info(
                    f"{'Would delete' if dry_run else 'Deleted'} "
                    f"result for task {task.task_id}"
                )

            except Exception as e:
                logger.error(f"Error deleting result for task {task.task_id}: {str(e)}")
                errors.append({
                    "task_id": task.task_id,
                    "error": str(e)
                })
                db.rollback()

        return {
            "cutoff_date": cutoff_date.isoformat(),
            "days_old": days_old,
            "deleted_count": deleted_count,
            "deleted_size_bytes": deleted_size,
            "deleted_size_mb": round(deleted_size / 1024 / 1024, 2),
            "errors": errors,
            "dry_run": dry_run
        }

    @staticmethod
    def cleanup_orphaned_files(
        db: Session,
        dry_run: bool = False
    ) -> Dict:
        """
        Clean up orphaned files (files on disk not in database)

        Scans storage directories and removes files not referenced in database

        Args:
            db: Database session
            dry_run: If True, only report what would be deleted

        Returns:
            Dictionary with cleanup statistics
        """
        deleted_count = 0
        deleted_size = 0
        errors = []

        # Get all storage paths from database
        db_images = db.query(Image).all()
        db_paths = {storage_service.get_full_path(img.storage_path) for img in db_images}

        # Scan storage directories
        storage_root = Path(storage_service.storage_path)
        categories = ['photos', 'templates', 'preprocessed', 'results']

        for category in categories:
            category_dir = storage_root / category

            if not category_dir.exists():
                continue

            # Scan all files in category
            for file_path in category_dir.rglob('*'):
                if not file_path.is_file():
                    continue

                # Check if file is in database
                if str(file_path) not in db_paths:
                    try:
                        file_size = file_path.stat().st_size

                        if not dry_run:
                            file_path.unlink()
                            logger.debug(f"Deleted orphaned file: {file_path}")

                        deleted_count += 1
                        deleted_size += file_size

                        logger.info(
                            f"{'Would delete' if dry_run else 'Deleted'} "
                            f"orphaned file: {file_path.name}"
                        )

                    except Exception as e:
                        logger.error(f"Error deleting orphaned file {file_path}: {str(e)}")
                        errors.append({
                            "file_path": str(file_path),
                            "error": str(e)
                        })

        return {
            "deleted_count": deleted_count,
            "deleted_size_bytes": deleted_size,
            "deleted_size_mb": round(deleted_size / 1024 / 1024, 2),
            "errors": errors,
            "dry_run": dry_run
        }

    @staticmethod
    def cleanup_all(
        db: Session,
        days_old: int = 30,
        dry_run: bool = False
    ) -> Dict:
        """
        Run all cleanup operations

        Args:
            db: Database session
            days_old: Delete task results older than this many days
            dry_run: If True, only report what would be deleted

        Returns:
            Dictionary with all cleanup statistics
        """
        logger.info(
            f"Starting full cleanup (days_old={days_old}, dry_run={dry_run})"
        )

        results = {
            "expired_images": CleanupService.cleanup_expired_images(db, dry_run),
            "old_task_results": CleanupService.cleanup_old_task_results(days_old, db, dry_run),
            "orphaned_files": CleanupService.cleanup_orphaned_files(db, dry_run),
        }

        # Calculate totals
        total_deleted = sum(r["deleted_count"] for r in results.values())
        total_size = sum(r["deleted_size_bytes"] for r in results.values())

        results["totals"] = {
            "deleted_count": total_deleted,
            "deleted_size_bytes": total_size,
            "deleted_size_mb": round(total_size / 1024 / 1024, 2),
            "dry_run": dry_run
        }

        logger.info(
            f"Cleanup complete: {total_deleted} files, "
            f"{results['totals']['deleted_size_mb']} MB"
        )

        return results

    @staticmethod
    def get_cleanup_stats(db: Session) -> Dict:
        """
        Get statistics about cleanable data

        Args:
            db: Database session

        Returns:
            Dictionary with cleanup statistics
        """
        now = datetime.utcnow()

        # Count expired temporary images
        expired_count = db.query(Image).filter(
            and_(
                Image.storage_type == 'temporary',
                Image.expires_at.isnot(None),
                Image.expires_at < now
            )
        ).count()

        # Count temporary images
        temp_count = db.query(Image).filter(
            Image.storage_type == 'temporary'
        ).count()

        # Count old task results (>30 days)
        cutoff_date = now - timedelta(days=30)
        old_results_count = db.query(FaceSwapTask).filter(
            and_(
                FaceSwapTask.status.in_(['completed', 'failed']),
                FaceSwapTask.completed_at.isnot(None),
                FaceSwapTask.completed_at < cutoff_date,
                FaceSwapTask.result_image_id.isnot(None)
            )
        ).count()

        return {
            "expired_images": expired_count,
            "temporary_images": temp_count,
            "old_task_results_30d": old_results_count,
            "last_checked": now.isoformat()
        }
