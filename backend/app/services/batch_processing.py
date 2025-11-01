"""
Batch Processing Service

Phase 1.5 Checkpoint 1.5.4
Handles batch face-swap processing for multiple templates
"""

import logging
import uuid
import zipfile
import io
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session

from app.models.database import BatchTask, FaceSwapTask, Template, Image
from app.services.face_mapping import FaceMappingService, FaceMappingError
from app.utils.storage import storage_service

logger = logging.getLogger(__name__)


class BatchProcessingError(Exception):
    """Base exception for batch processing errors"""
    pass


class BatchProcessingService:
    """
    Service for managing batch face-swap processing

    Provides:
    - Batch creation with multiple templates
    - Progress tracking across tasks
    - ZIP archive generation for completed batches
    - Batch cancellation
    """

    @staticmethod
    def generate_batch_id() -> str:
        """Generate unique batch ID"""
        return f"batch_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def generate_task_id() -> str:
        """Generate unique task ID"""
        return f"task_{uuid.uuid4().hex[:16]}"

    @staticmethod
    def create_batch(
        husband_photo_id: int,
        wife_photo_id: int,
        template_ids: List[int],
        use_default_mapping: bool,
        use_preprocessed: bool,
        custom_mappings: Optional[List[Dict]],
        db: Session,
        user_id: Optional[int] = None
    ) -> Tuple[str, int]:
        """
        Create a batch face-swap task

        Args:
            husband_photo_id: Husband photo ID
            wife_photo_id: Wife photo ID
            template_ids: List of template IDs to process
            use_default_mapping: Use default gender-based mapping
            use_preprocessed: Use preprocessed templates
            custom_mappings: Custom face mappings (optional)
            db: Database session
            user_id: User ID (optional)

        Returns:
            Tuple of (batch_id, total_tasks_created)

        Raises:
            BatchProcessingError: If batch creation fails
        """
        # Validate inputs
        if not template_ids or len(template_ids) == 0:
            raise BatchProcessingError("template_ids cannot be empty")

        # Remove duplicates while preserving order
        unique_template_ids = []
        seen = set()
        for tid in template_ids:
            if tid not in seen:
                unique_template_ids.append(tid)
                seen.add(tid)

        logger.info(
            f"Creating batch for {len(unique_template_ids)} templates "
            f"(removed {len(template_ids) - len(unique_template_ids)} duplicates)"
        )

        # Validate that photos exist
        husband_photo = db.query(Image).filter(
            Image.id == husband_photo_id
        ).first()
        wife_photo = db.query(Image).filter(
            Image.id == wife_photo_id
        ).first()

        if not husband_photo:
            raise BatchProcessingError(f"Husband photo {husband_photo_id} not found")
        if not wife_photo:
            raise BatchProcessingError(f"Wife photo {wife_photo_id} not found")

        # Validate templates exist
        templates = db.query(Template).filter(
            Template.id.in_(unique_template_ids)
        ).all()

        if len(templates) != len(unique_template_ids):
            found_ids = {t.id for t in templates}
            missing_ids = [tid for tid in unique_template_ids if tid not in found_ids]
            raise BatchProcessingError(
                f"Templates not found: {missing_ids}"
            )

        # Generate batch ID
        batch_id = BatchProcessingService.generate_batch_id()

        # Create batch record
        batch = BatchTask(
            batch_id=batch_id,
            user_id=user_id,
            husband_photo_id=husband_photo_id,
            wife_photo_id=wife_photo_id,
            template_ids=unique_template_ids,
            status="pending",
            total_tasks=len(unique_template_ids),
            completed_tasks=0,
            failed_tasks=0,
            created_at=datetime.utcnow()
        )

        db.add(batch)
        db.flush()  # Get batch.id

        # Create individual face-swap tasks
        tasks_created = 0

        for template_id in unique_template_ids:
            try:
                # Determine face mappings for this template
                face_mappings = FaceMappingService.apply_mapping_to_task(
                    husband_photo_id=husband_photo_id,
                    wife_photo_id=wife_photo_id,
                    template_id=template_id,
                    use_default_mapping=use_default_mapping,
                    custom_mappings=custom_mappings,
                    db=db
                )

                # Check if preprocessed is available
                template = next((t for t in templates if t.id == template_id), None)
                use_preprocessed_final = use_preprocessed and template.is_preprocessed

                if use_preprocessed and not use_preprocessed_final:
                    logger.warning(
                        f"Template {template_id} not preprocessed, "
                        "using original"
                    )

                # Create task
                task_id = BatchProcessingService.generate_task_id()
                task = FaceSwapTask(
                    task_id=task_id,
                    batch_id=batch_id,
                    user_id=user_id,
                    template_id=template_id,
                    husband_photo_id=husband_photo_id,
                    wife_photo_id=wife_photo_id,
                    face_mappings=face_mappings,
                    use_preprocessed=use_preprocessed_final,
                    status="pending",
                    progress=0,
                    created_at=datetime.utcnow()
                )

                db.add(task)
                tasks_created += 1

            except FaceMappingError as e:
                logger.error(
                    f"Failed to create task for template {template_id}: {str(e)}"
                )
                # Continue creating other tasks
                continue

        if tasks_created == 0:
            db.rollback()
            raise BatchProcessingError("Failed to create any tasks")

        # Update batch total_tasks with actual created tasks
        batch.total_tasks = tasks_created

        db.commit()

        logger.info(
            f"Batch created: batch_id={batch_id}, "
            f"tasks={tasks_created}/{len(unique_template_ids)}"
        )

        return batch_id, tasks_created

    @staticmethod
    def get_batch_status(
        batch_id: str,
        db: Session
    ) -> Optional[Dict]:
        """
        Get batch status

        Args:
            batch_id: Batch ID
            db: Database session

        Returns:
            Batch status dictionary or None if not found
        """
        batch = db.query(BatchTask).filter(
            BatchTask.batch_id == batch_id
        ).first()

        if not batch:
            return None

        # Calculate progress
        progress_percentage = 0.0
        if batch.total_tasks > 0:
            progress_percentage = round(
                (batch.completed_tasks + batch.failed_tasks) / batch.total_tasks * 100,
                2
            )

        return {
            "batch_id": batch.batch_id,
            "status": batch.status,
            "total_tasks": batch.total_tasks,
            "completed_tasks": batch.completed_tasks,
            "failed_tasks": batch.failed_tasks,
            "progress_percentage": progress_percentage,
            "created_at": batch.created_at,
            "completed_at": batch.completed_at
        }

    @staticmethod
    def get_batch_tasks(
        batch_id: str,
        db: Session
    ) -> List[FaceSwapTask]:
        """
        Get all tasks in a batch

        Args:
            batch_id: Batch ID
            db: Database session

        Returns:
            List of FaceSwapTask objects
        """
        tasks = db.query(FaceSwapTask).filter(
            FaceSwapTask.batch_id == batch_id
        ).order_by(FaceSwapTask.created_at).all()

        return tasks

    @staticmethod
    def get_batch_results(
        batch_id: str,
        db: Session
    ) -> Dict:
        """
        Get batch results

        Args:
            batch_id: Batch ID
            db: Database session

        Returns:
            Dictionary with batch results
        """
        tasks = BatchProcessingService.get_batch_tasks(batch_id, db)

        results = []
        completed_count = 0
        failed_count = 0

        for task in tasks:
            result_image_url = None

            if task.result_image_id:
                result_image = db.query(Image).filter(
                    Image.id == task.result_image_id
                ).first()

                if result_image:
                    result_image_url = storage_service.get_file_url(
                        result_image.storage_path
                    )

            results.append({
                "task_id": task.task_id,
                "template_id": task.template_id,
                "status": task.status,
                "result_image_url": result_image_url,
                "error_message": task.error_message
            })

            if task.status == "completed":
                completed_count += 1
            elif task.status == "failed":
                failed_count += 1

        return {
            "batch_id": batch_id,
            "results": results,
            "completed_count": completed_count,
            "failed_count": failed_count
        }

    @staticmethod
    def create_results_zip(
        batch_id: str,
        db: Session
    ) -> Optional[bytes]:
        """
        Create ZIP archive of batch results

        Args:
            batch_id: Batch ID
            db: Database session

        Returns:
            ZIP file content as bytes, or None if no results
        """
        tasks = db.query(FaceSwapTask).filter(
            FaceSwapTask.batch_id == batch_id,
            FaceSwapTask.status == "completed",
            FaceSwapTask.result_image_id.isnot(None)
        ).all()

        if not tasks:
            logger.warning(f"No completed results for batch {batch_id}")
            return None

        # Create ZIP in memory
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for task in tasks:
                # Get result image
                result_image = db.query(Image).filter(
                    Image.id == task.result_image_id
                ).first()

                if not result_image:
                    logger.warning(
                        f"Result image {task.result_image_id} not found for task {task.task_id}"
                    )
                    continue

                # Get template name for filename
                template = db.query(Template).filter(
                    Template.id == task.template_id
                ).first()

                template_name = template.name if template else f"template_{task.template_id}"

                # Clean filename
                safe_template_name = "".join(
                    c for c in template_name if c.isalnum() or c in (' ', '-', '_')
                ).strip()

                # Read image file
                image_path = storage_service.get_full_path(result_image.storage_path)

                if not Path(image_path).exists():
                    logger.warning(f"Image file not found: {image_path}")
                    continue

                with open(image_path, 'rb') as f:
                    image_data = f.read()

                # Add to ZIP with descriptive filename
                # Format: template_name_task_id.ext
                extension = Path(result_image.filename).suffix
                zip_filename = f"{safe_template_name}_{task.task_id}{extension}"

                zip_file.writestr(zip_filename, image_data)

                logger.debug(f"Added {zip_filename} to ZIP")

        zip_buffer.seek(0)
        zip_content = zip_buffer.getvalue()

        logger.info(
            f"Created ZIP for batch {batch_id}: "
            f"{len(tasks)} files, {len(zip_content)} bytes"
        )

        return zip_content

    @staticmethod
    def cancel_batch(
        batch_id: str,
        db: Session
    ) -> bool:
        """
        Cancel a batch and all pending tasks

        Args:
            batch_id: Batch ID
            db: Database session

        Returns:
            True if canceled successfully
        """
        batch = db.query(BatchTask).filter(
            BatchTask.batch_id == batch_id
        ).first()

        if not batch:
            return False

        # Can only cancel if not completed
        if batch.status in ["completed", "failed"]:
            logger.warning(f"Cannot cancel batch {batch_id} with status {batch.status}")
            return False

        # Cancel all pending/processing tasks
        tasks = db.query(FaceSwapTask).filter(
            FaceSwapTask.batch_id == batch_id,
            FaceSwapTask.status.in_(["pending", "processing"])
        ).all()

        canceled_count = 0
        for task in tasks:
            task.status = "failed"
            task.error_message = "Canceled by user"
            task.completed_at = datetime.utcnow()
            canceled_count += 1

        # Update batch status
        batch.status = "failed"
        batch.completed_at = datetime.utcnow()

        db.commit()

        logger.info(f"Canceled batch {batch_id}: {canceled_count} tasks")

        return True

    @staticmethod
    def update_batch_progress(
        batch_id: str,
        db: Session
    ) -> None:
        """
        Update batch progress based on task statuses

        This should be called after task status changes

        Args:
            batch_id: Batch ID
            db: Database session
        """
        batch = db.query(BatchTask).filter(
            BatchTask.batch_id == batch_id
        ).first()

        if not batch:
            return

        # Count task statuses
        tasks = db.query(FaceSwapTask).filter(
            FaceSwapTask.batch_id == batch_id
        ).all()

        completed = sum(1 for t in tasks if t.status == "completed")
        failed = sum(1 for t in tasks if t.status == "failed")

        # Update batch
        batch.completed_tasks = completed
        batch.failed_tasks = failed

        # Update batch status
        total_finished = completed + failed

        if total_finished >= batch.total_tasks:
            # All tasks finished
            if failed == batch.total_tasks:
                batch.status = "failed"
            else:
                batch.status = "completed"

            batch.completed_at = datetime.utcnow()
        elif total_finished > 0:
            batch.status = "processing"

        db.commit()

        logger.debug(
            f"Updated batch {batch_id}: "
            f"completed={completed}, failed={failed}, status={batch.status}"
        )

    @staticmethod
    def list_batches(
        status: Optional[str],
        limit: int,
        offset: int,
        db: Session
    ) -> Tuple[List[Dict], int]:
        """
        List batches with pagination

        Args:
            status: Filter by status (optional)
            limit: Max results
            offset: Pagination offset
            db: Database session

        Returns:
            Tuple of (batches, total_count)
        """
        query = db.query(BatchTask)

        if status:
            query = query.filter(BatchTask.status == status)

        # Get total count
        total = query.count()

        # Order by most recent first
        query = query.order_by(BatchTask.created_at.desc())

        # Paginate
        batches = query.offset(offset).limit(limit).all()

        # Convert to dicts
        results = []
        for batch in batches:
            progress_percentage = 0.0
            if batch.total_tasks > 0:
                progress_percentage = round(
                    (batch.completed_tasks + batch.failed_tasks) / batch.total_tasks * 100,
                    2
                )

            results.append({
                "batch_id": batch.batch_id,
                "status": batch.status,
                "total_tasks": batch.total_tasks,
                "completed_tasks": batch.completed_tasks,
                "failed_tasks": batch.failed_tasks,
                "progress_percentage": progress_percentage,
                "created_at": batch.created_at,
                "completed_at": batch.completed_at
            })

        return results, total
