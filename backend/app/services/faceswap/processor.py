"""
Background task processor for face-swap operations

This module provides both synchronous (FastAPI BackgroundTasks) and
asynchronous (Celery) task processing.
"""

import logging
import time
from datetime import datetime
import cv2
import os

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.database import FaceSwapTask, Image
from app.services.faceswap.core import FaceSwapper, FaceSwapError
from app.utils.storage import storage_service

logger = logging.getLogger(__name__)


def process_faceswap_task_sync(task_id: int) -> None:
    """
    Process face-swap task synchronously using FastAPI BackgroundTasks

    This is used for MVP. For production, use Celery version.

    Args:
        task_id: ID of FaceSwapTask record
    """
    db = SessionLocal()

    try:
        # Load task from database
        task = db.query(FaceSwapTask).filter(FaceSwapTask.id == task_id).first()

        if not task:
            logger.error(f"Task {task_id} not found")
            return

        # Update task status
        task.status = "processing"
        task.progress = 10
        task.started_at = datetime.utcnow()
        db.commit()

        logger.info(f"Starting face-swap task {task_id}")

        # Load images
        husband_image = db.query(Image).filter(
            Image.id == task.husband_image_id
        ).first()
        wife_image = db.query(Image).filter(
            Image.id == task.wife_image_id
        ).first()
        template = db.query(Image).filter(
            Image.id == task.template.image_id
        ).first()

        if not all([husband_image, wife_image, template]):
            raise ValueError("One or more images not found")

        # Get file paths
        husband_path = str(storage_service.get_file_path(husband_image.storage_path))
        wife_path = str(storage_service.get_file_path(wife_image.storage_path))
        template_path = str(storage_service.get_file_path(template.storage_path))

        task.progress = 30
        db.commit()

        # Initialize face swapper
        model_path = os.path.join(settings.MODELS_PATH, settings.INSWAPPER_MODEL)

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Face-swap model not found: {model_path}. "
                "Please download it from https://huggingface.co/ezioruan/inswapper_128.onnx"
            )

        swapper = FaceSwapper(
            model_path=model_path,
            use_gpu=settings.USE_GPU,
            device_id=settings.GPU_DEVICE_ID
        )

        task.progress = 50
        db.commit()

        logger.info(f"Performing face swap for task {task_id}")
        start_time = time.time()

        # Perform face swap
        result = swapper.swap_couple_faces(
            husband_img=husband_path,
            wife_img=wife_path,
            template_img=template_path
        )

        processing_time = time.time() - start_time

        task.progress = 80
        db.commit()

        # Save result
        result_filename = f"result_task_{task_id}.jpg"
        result_path = storage_service.storage_path / "results" / result_filename

        cv2.imwrite(str(result_path), result)

        # Get result image dimensions
        height, width = result.shape[:2]
        file_size = result_path.stat().st_size

        task.progress = 90
        db.commit()

        # Create result image record
        result_image = Image(
            filename=result_filename,
            storage_path=f"results/{result_filename}",
            file_size=file_size,
            width=width,
            height=height,
            image_type="result",
            uploaded_at=datetime.utcnow()
        )

        db.add(result_image)
        db.commit()
        db.refresh(result_image)

        # Update task
        task.status = "completed"
        task.progress = 100
        task.result_image_id = result_image.id
        task.processing_time = processing_time
        task.completed_at = datetime.utcnow()
        db.commit()

        logger.info(
            f"Face-swap task {task_id} completed successfully "
            f"in {processing_time:.2f}s"
        )

    except FaceSwapError as e:
        logger.error(f"Face-swap error for task {task_id}: {e}")
        task.status = "failed"
        task.error_message = str(e)
        task.completed_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        logger.error(f"Error processing task {task_id}: {e}", exc_info=True)
        task.status = "failed"
        task.error_message = str(e)
        task.completed_at = datetime.utcnow()
        db.commit()

    finally:
        db.close()


# Celery task (for production - Phase 1.2+)
# Uncomment and configure when Celery is set up

# from celery import Celery
#
# celery_app = Celery(
#     'faceswap',
#     broker=settings.CELERY_BROKER_URL,
#     backend=settings.CELERY_RESULT_BACKEND
# )
#
# @celery_app.task
# def process_faceswap_task(task_id: int):
#     """
#     Celery task for face-swap processing
#
#     Args:
#         task_id: ID of FaceSwapTask record
#     """
#     return process_faceswap_task_sync(task_id)
