"""
Face-swap API endpoints
"""

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
from datetime import datetime
import cv2
import numpy as np

from app.core.database import get_db
from app.models.database import Image, Template, FaceSwapTask
from app.models.schemas import (
    ImageUploadResponse,
    FaceSwapRequest,
    FaceSwapResponse,
    TaskStatusResponse,
    TemplateListItem
)
from app.utils.storage import storage_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/upload-image", response_model=ImageUploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    image_type: str = Query("source", regex="^(source|template|result)$"),
    db: Session = Depends(get_db)
):
    """
    Upload an image (source photo or template)

    Args:
        file: Image file to upload
        image_type: Type of image ('source', 'template', or 'result')
        db: Database session

    Returns:
        Image metadata with ID and storage path
    """
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="File must be an image"
        )

    try:
        # Save file to storage
        storage_path, file_size = storage_service.save_file(
            file.file,
            file.filename,
            category=image_type
        )

        # Read image to get dimensions
        full_path = storage_service.get_file_path(storage_path)
        img = cv2.imread(str(full_path))

        if img is None:
            # Clean up invalid file
            storage_service.delete_file(storage_path)
            raise HTTPException(
                status_code=400,
                detail="Invalid image file"
            )

        height, width = img.shape[:2]

        # Create database record
        db_image = Image(
            filename=file.filename,
            storage_path=storage_path,
            file_size=file_size,
            width=width,
            height=height,
            image_type=image_type,
            uploaded_at=datetime.utcnow()
        )

        db.add(db_image)
        db.commit()
        db.refresh(db_image)

        logger.info(
            f"Image uploaded: id={db_image.id}, "
            f"filename={file.filename}, "
            f"size={file_size}, "
            f"dimensions={width}x{height}"
        )

        return ImageUploadResponse(
            image_id=db_image.id,
            filename=db_image.filename,
            storage_path=db_image.storage_path,
            file_size=db_image.file_size,
            width=db_image.width,
            height=db_image.height
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error uploading image: {str(e)}"
        )


@router.post("/swap-faces", response_model=FaceSwapResponse, status_code=202)
async def swap_faces(
    request: FaceSwapRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Create a face-swap task

    Args:
        request: Face-swap request with image IDs
        background_tasks: FastAPI background tasks
        db: Database session

    Returns:
        Task ID and status
    """
    # Validate that images exist
    husband_image = db.query(Image).filter(Image.id == request.husband_image_id).first()
    wife_image = db.query(Image).filter(Image.id == request.wife_image_id).first()
    template = db.query(Template).filter(Template.id == request.template_id).first()

    if not husband_image:
        raise HTTPException(status_code=404, detail="Husband image not found")
    if not wife_image:
        raise HTTPException(status_code=404, detail="Wife image not found")
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Create task record
    task = FaceSwapTask(
        template_id=request.template_id,
        husband_image_id=request.husband_image_id,
        wife_image_id=request.wife_image_id,
        status="pending",
        progress=0,
        created_at=datetime.utcnow()
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    logger.info(f"Face-swap task created: task_id={task.id}")

    # Queue background processing
    # For now, we'll use FastAPI BackgroundTasks
    # In production, this should use Celery
    from app.services.faceswap.processor import process_faceswap_task_sync
    background_tasks.add_task(process_faceswap_task_sync, task.id)

    return FaceSwapResponse(
        task_id=task.id,
        status=task.status,
        created_at=task.created_at
    )


@router.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: int,
    db: Session = Depends(get_db)
):
    """
    Get face-swap task status and result

    Args:
        task_id: Task ID
        db: Database session

    Returns:
        Task status and result information
    """
    task = db.query(FaceSwapTask).filter(FaceSwapTask.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Get result image URL if available
    result_image_url = None
    if task.result_image_id:
        result_image = db.query(Image).filter(Image.id == task.result_image_id).first()
        if result_image:
            result_image_url = storage_service.get_file_url(result_image.storage_path)

    return TaskStatusResponse(
        task_id=task.id,
        status=task.status,
        progress=task.progress,
        result_image_url=result_image_url,
        processing_time=task.processing_time,
        error_message=task.error_message,
        created_at=task.created_at,
        completed_at=task.completed_at
    )


@router.get("/templates", response_model=List[TemplateListItem])
async def list_templates(
    category: Optional[str] = Query(None, regex="^(acg|movie|tv|custom|all)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    List available templates

    Args:
        category: Filter by category ('acg', 'movie', 'tv', 'custom', 'all')
        limit: Number of results to return
        offset: Pagination offset
        db: Database session

    Returns:
        List of templates
    """
    query = db.query(Template).filter(Template.is_active == True)

    # Filter by category if specified
    if category and category != "all":
        query = query.join(Image).filter(Image.category == category)

    # Order by popularity
    query = query.order_by(Template.popularity_score.desc())

    # Apply pagination
    templates = query.offset(offset).limit(limit).all()

    # Convert to response model
    result = []
    for template in templates:
        image = db.query(Image).filter(Image.id == template.image_id).first()
        if image:
            result.append(TemplateListItem(
                id=template.id,
                title=template.title,
                image_url=storage_service.get_file_url(image.storage_path),
                category=image.category or "custom",
                face_count=template.face_count,
                popularity_score=template.popularity_score
            ))

    return result


@router.post("/templates", status_code=201)
async def create_template(
    image_id: int,
    title: str,
    description: Optional[str] = None,
    artist: Optional[str] = None,
    source_url: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Create a new template from an uploaded image

    Args:
        image_id: ID of uploaded template image
        title: Template title
        description: Optional description
        artist: Optional artist name
        source_url: Optional source URL
        db: Database session

    Returns:
        Created template
    """
    # Verify image exists
    image = db.query(Image).filter(Image.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    # Detect faces in the image
    try:
        from app.services.faceswap.core import FaceSwapper
        from app.core.config import settings
        import os

        model_path = os.path.join(settings.MODELS_PATH, settings.INSWAPPER_MODEL)

        # Only create FaceSwapper if model exists
        if os.path.exists(model_path):
            swapper = FaceSwapper(model_path=model_path, use_gpu=settings.USE_GPU)
            image_path = storage_service.get_file_path(image.storage_path)
            face_info = swapper.get_face_info(str(image_path))

            face_count = face_info["face_count"]
            face_positions = face_info["faces"]
        else:
            logger.warning("Face-swap model not found, creating template without face detection")
            face_count = 2  # Default assumption
            face_positions = []

    except Exception as e:
        logger.warning(f"Face detection failed, using defaults: {e}")
        face_count = 2
        face_positions = []

    # Create template
    template = Template(
        image_id=image_id,
        title=title,
        description=description,
        artist=artist,
        source_url=source_url,
        face_count=face_count,
        face_positions=face_positions,
        popularity_score=0,
        is_active=True,
        created_at=datetime.utcnow()
    )

    db.add(template)
    db.commit()
    db.refresh(template)

    logger.info(f"Template created: id={template.id}, title={title}, faces={face_count}")

    return {
        "template_id": template.id,
        "title": template.title,
        "face_count": template.face_count,
        "image_url": storage_service.get_file_url(image.storage_path)
    }
