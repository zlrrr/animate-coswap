"""
Template Preprocessing API

Phase 1.5 Checkpoint 1.5.2
Handles template preprocessing: face detection, gender classification, face masking
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import logging

from app.core.database import get_db
from app.models.database import Template, TemplatePreprocessing, Image
from app.models.schemas import (
    PreprocessingResponse,
    PreprocessingStatusResponse,
    BatchPreprocessingResponse
)
from app.utils.storage import storage_service

logger = logging.getLogger(__name__)

router = APIRouter()


def preprocess_template_task(template_id: int, db: Session):
    """Background task to preprocess template"""
    from app.services.preprocessing import get_preprocessor

    try:
        preprocessor = get_preprocessor()
        result = preprocessor.preprocess_template(template_id, db)
        logger.info(f"Background preprocessing completed for template {template_id}")
        return result
    except Exception as e:
        logger.error(f"Background preprocessing failed for template {template_id}: {e}")
        raise


@router.post("/{template_id}/preprocess", response_model=PreprocessingResponse, status_code=202)
async def trigger_preprocessing(
    template_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Trigger preprocessing for a template

    This will:
    1. Detect faces in the template
    2. Classify gender for each face
    3. Create a masked version of the template
    4. Store preprocessing data

    Args:
        template_id: Template ID
        background_tasks: FastAPI background tasks
        db: Database session

    Returns:
        Preprocessing status
    """
    # Check if template exists
    template = db.query(Template).filter(Template.id == template_id).first()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Check if already preprocessing or preprocessed
    existing = db.query(TemplatePreprocessing).filter(
        TemplatePreprocessing.template_id == template_id
    ).first()

    if existing:
        if existing.preprocessing_status == "processing":
            return PreprocessingResponse(
                template_id=template_id,
                status="processing",
                message="Preprocessing already in progress"
            )
        elif existing.preprocessing_status == "completed":
            return PreprocessingResponse(
                template_id=template_id,
                status="completed",
                message="Template already preprocessed. Reprocessing..."
            )

    # Create preprocessing record with pending status
    if not existing:
        preprocessing = TemplatePreprocessing(
            template_id=template_id,
            original_image_id=template.original_image_id,
            faces_detected=0,
            face_data=[],
            preprocessing_status="pending"
        )
        db.add(preprocessing)
        db.commit()
    else:
        existing.preprocessing_status = "processing"
        db.commit()

    # Queue background task
    background_tasks.add_task(preprocess_template_task, template_id, db)

    logger.info(f"Preprocessing queued for template {template_id}")

    return PreprocessingResponse(
        template_id=template_id,
        status="pending",
        message="Preprocessing started"
    )


@router.get("/{template_id}/preprocessing", response_model=PreprocessingStatusResponse)
async def get_preprocessing_status(
    template_id: int,
    db: Session = Depends(get_db)
):
    """
    Get preprocessing status for a template

    Args:
        template_id: Template ID
        db: Database session

    Returns:
        Preprocessing status and results
    """
    preprocessing = db.query(TemplatePreprocessing).filter(
        TemplatePreprocessing.template_id == template_id
    ).first()

    if not preprocessing:
        raise HTTPException(
            status_code=404,
            detail="Preprocessing not started for this template"
        )

    # Get masked image URL if available
    masked_image_url = None
    if preprocessing.masked_image_id:
        masked_image = db.query(Image).filter(
            Image.id == preprocessing.masked_image_id
        ).first()
        if masked_image:
            masked_image_url = storage_service.get_file_url(masked_image.storage_path)

    return PreprocessingStatusResponse(
        template_id=preprocessing.template_id,
        preprocessing_status=preprocessing.preprocessing_status,
        faces_detected=preprocessing.faces_detected,
        face_data=preprocessing.face_data or [],
        masked_image_id=preprocessing.masked_image_id,
        masked_image_url=masked_image_url,
        original_image_id=preprocessing.original_image_id,
        processed_at=preprocessing.processed_at,
        error_message=preprocessing.error_message
    )


@router.post("/preprocess/batch", response_model=BatchPreprocessingResponse)
async def preprocess_batch(
    template_ids: List[int],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Trigger preprocessing for multiple templates

    Args:
        template_ids: List of template IDs
        background_tasks: FastAPI background tasks
        db: Database session

    Returns:
        Batch preprocessing status
    """
    queued = 0
    already_processed = 0

    for template_id in template_ids:
        template = db.query(Template).filter(Template.id == template_id).first()

        if not template:
            logger.warning(f"Template {template_id} not found, skipping")
            continue

        # Check if already preprocessed
        preprocessing = db.query(TemplatePreprocessing).filter(
            TemplatePreprocessing.template_id == template_id
        ).first()

        if preprocessing and preprocessing.preprocessing_status == "completed":
            already_processed += 1
            continue

        # Queue preprocessing
        if not preprocessing:
            preprocessing = TemplatePreprocessing(
                template_id=template_id,
                original_image_id=template.original_image_id,
                faces_detected=0,
                face_data=[],
                preprocessing_status="pending"
            )
            db.add(preprocessing)

        background_tasks.add_task(preprocess_template_task, template_id, db)
        queued += 1

    db.commit()

    logger.info(f"Batch preprocessing: queued={queued}, already_processed={already_processed}")

    return BatchPreprocessingResponse(
        total=len(template_ids),
        queued=queued,
        already_processed=already_processed,
        message=f"Queued {queued} templates for preprocessing"
    )


@router.post("/preprocess/all", response_model=BatchPreprocessingResponse)
async def preprocess_all_unprocessed(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Trigger preprocessing for all unprocessed templates

    Args:
        background_tasks: FastAPI background tasks
        db: Database session

    Returns:
        Batch preprocessing status
    """
    # Get all unprocessed templates
    unprocessed_templates = db.query(Template).filter(
        Template.is_active == True,
        Template.is_preprocessed == False
    ).all()

    template_ids = [t.id for t in unprocessed_templates]

    if not template_ids:
        return BatchPreprocessingResponse(
            total=0,
            queued=0,
            already_processed=0,
            message="No unprocessed templates found"
        )

    # Use batch preprocessing
    return await preprocess_batch(template_ids, background_tasks, db)
