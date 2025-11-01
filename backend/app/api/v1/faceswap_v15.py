"""
FaceSwap API - Phase 1.5 Enhanced

Checkpoint 1.5.3: Flexible Face Mapping
Supports custom and default face mappings
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import logging
from datetime import datetime
import uuid

from app.core.database import get_db
from app.models.database import Image, Template, FaceSwapTask
from app.models.schemas import FaceSwapRequest, FaceSwapResponse, TaskStatusResponse
from app.services.face_mapping import FaceMappingService, FaceMappingError
from app.utils.storage import storage_service

logger = logging.getLogger(__name__)

router = APIRouter()


def generate_task_id() -> str:
    """Generate unique task ID"""
    return f"task_{uuid.uuid4().hex[:16]}"


@router.post("/swap", response_model=FaceSwapResponse, status_code=202)
async def create_faceswap_task(
    request: FaceSwapRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Create a face-swap task with flexible face mapping (Phase 1.5)

    Supports:
    - Default mapping: husband -> male faces, wife -> female faces
    - Custom mapping: specify exact source-to-target mappings
    - Preprocessed templates for faster processing

    Args:
        request: FaceSwap request with mapping configuration
        background_tasks: FastAPI background tasks
        db: Database session

    Returns:
        Task information with computed face mappings
    """
    # Validate that resources exist
    husband_photo = db.query(Image).filter(
        Image.id == request.husband_photo_id
    ).first()
    wife_photo = db.query(Image).filter(
        Image.id == request.wife_photo_id
    ).first()
    template = db.query(Template).filter(
        Template.id == request.template_id
    ).first()

    if not husband_photo:
        raise HTTPException(status_code=404, detail="Husband photo not found")
    if not wife_photo:
        raise HTTPException(status_code=404, detail="Wife photo not found")
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Check if preprocessed template is requested but not available
    if request.use_preprocessed and not template.is_preprocessed:
        logger.warning(
            f"Template {template.id} not preprocessed yet, "
            "will use original"
        )
        request.use_preprocessed = False

    # Determine face mappings
    try:
        # Convert Pydantic models to dicts if needed
        custom_mappings = None
        if request.face_mappings:
            custom_mappings = FaceMappingService.convert_to_dict(
                request.face_mappings
            )

        face_mappings = FaceMappingService.apply_mapping_to_task(
            husband_photo_id=request.husband_photo_id,
            wife_photo_id=request.wife_photo_id,
            template_id=request.template_id,
            use_default_mapping=request.use_default_mapping,
            custom_mappings=custom_mappings,
            db=db
        )

        logger.info(
            f"Computed {len(face_mappings)} face mappings for task"
        )

    except FaceMappingError as e:
        logger.error(f"Face mapping error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid face mapping: {str(e)}"
        )

    # Generate unique task ID
    task_id = generate_task_id()

    # Create task record
    task = FaceSwapTask(
        task_id=task_id,
        template_id=request.template_id,
        husband_photo_id=request.husband_photo_id,
        wife_photo_id=request.wife_photo_id,
        face_mappings=face_mappings,  # Phase 1.5: Store mappings
        use_preprocessed=request.use_preprocessed,  # Phase 1.5
        status="pending",
        progress=0,
        created_at=datetime.utcnow()
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    logger.info(
        f"Face-swap task created: task_id={task_id}, "
        f"template={request.template_id}, "
        f"use_preprocessed={request.use_preprocessed}, "
        f"mappings={len(face_mappings)}"
    )

    # Queue background processing
    # TODO: In production, use Celery
    # from app.services.faceswap.processor import process_faceswap_task_sync
    # background_tasks.add_task(process_faceswap_task_sync, task.id)

    return FaceSwapResponse(
        task_id=task_id,
        status=task.status,
        created_at=task.created_at,
        face_mappings=face_mappings,
        use_preprocessed=request.use_preprocessed
    )


@router.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    Get face-swap task status and result (Phase 1.5)

    Args:
        task_id: Task ID (string format)
        db: Database session

    Returns:
        Task status and result information
    """
    task = db.query(FaceSwapTask).filter(
        FaceSwapTask.task_id == task_id
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Get result image URL if available
    result_image_url = None
    if task.result_image_id:
        result_image = db.query(Image).filter(
            Image.id == task.result_image_id
        ).first()
        if result_image:
            result_image_url = storage_service.get_file_url(
                result_image.storage_path
            )

    return TaskStatusResponse(
        task_id=task.task_id,
        status=task.status,
        progress=task.progress or 0,
        result_image_url=result_image_url,
        processing_time=task.processing_time,
        error_message=task.error_message,
        created_at=task.created_at,
        completed_at=task.completed_at,
        face_mappings=task.face_mappings  # Phase 1.5: Return mappings
    )


@router.get("/tasks", response_model=list[TaskStatusResponse])
async def list_tasks(
    status: str = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    List face-swap tasks

    Args:
        status: Filter by status (pending, processing, completed, failed)
        limit: Number of results
        offset: Pagination offset
        db: Database session

    Returns:
        List of tasks
    """
    query = db.query(FaceSwapTask)

    if status:
        query = query.filter(FaceSwapTask.status == status)

    # Order by most recent first
    query = query.order_by(FaceSwapTask.created_at.desc())

    # Paginate
    tasks = query.offset(offset).limit(limit).all()

    # Convert to response models
    results = []
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

        results.append(
            TaskStatusResponse(
                task_id=task.task_id,
                status=task.status,
                progress=task.progress or 0,
                result_image_url=result_image_url,
                processing_time=task.processing_time,
                error_message=task.error_message,
                created_at=task.created_at,
                completed_at=task.completed_at,
                face_mappings=task.face_mappings
            )
        )

    return results
