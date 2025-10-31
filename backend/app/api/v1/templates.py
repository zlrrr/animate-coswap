"""
Template Upload API - Permanent Storage

Phase 1.5 Checkpoint 1.5.1 & 1.5.2
Handles permanent template uploads and preprocessing
"""

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from typing import Optional
import logging
from datetime import datetime
import cv2

from app.core.database import get_db
from app.models.database import Image, Template
from app.models.schemas import TemplateResponse, TemplateListResponse, DeleteResponse
from app.utils.storage import storage_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/upload", response_model=TemplateResponse)
async def upload_template(
    file: UploadFile = File(...),
    name: str = Form(..., description="Template name"),
    category: str = Form(default="custom", description="Template category"),
    description: Optional[str] = Form(None, description="Template description"),
    db: Session = Depends(get_db)
):
    """
    Upload a permanent template

    Templates are stored permanently without expiration.
    They can be preprocessed for faster face-swapping.

    Args:
        file: Template image file
        name: Template name
        category: Category (wedding, outdoor, studio, custom, etc.)
        description: Optional description
        db: Database session

    Returns:
        Template metadata
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail={"error": "File must be an image"}
        )

    try:
        # Save file to permanent storage
        storage_path, file_size = storage_service.save_file(
            file.file,
            file.filename,
            category="templates"
        )

        # Read image to get dimensions
        full_path = storage_service.get_file_path(storage_path)
        img = cv2.imread(str(full_path))

        if img is None:
            # Clean up invalid file
            storage_service.delete_file(storage_path)
            raise HTTPException(
                status_code=400,
                detail={"error": "Invalid image file"}
            )

        height, width = img.shape[:2]

        # Create image record (permanent storage)
        db_image = Image(
            filename=file.filename,
            storage_path=storage_path,
            file_size=file_size,
            width=width,
            height=height,
            image_type="template",
            storage_type="permanent",  # No expiration
            category=category,
            expires_at=None,  # Permanent storage
            uploaded_at=datetime.utcnow()
        )

        db.add(db_image)
        db.flush()  # Get image ID without committing

        # Create template record
        db_template = Template(
            name=name,
            description=description,
            category=category,
            original_image_id=db_image.id,
            is_preprocessed=False,  # Will be preprocessed in Checkpoint 1.5.2
            face_count=0,  # Will be detected during preprocessing
            male_face_count=0,
            female_face_count=0,
            popularity_score=0,
            is_active=True,
            created_at=datetime.utcnow()
        )

        db.add(db_template)
        db.commit()
        db.refresh(db_template)
        db.refresh(db_image)

        logger.info(
            f"Template uploaded: id={db_template.id}, "
            f"name={name}, category={category}"
        )

        return TemplateResponse(
            id=db_template.id,
            name=db_template.name,
            description=db_template.description,
            category=db_template.category,
            original_image_id=db_template.original_image_id,
            is_preprocessed=db_template.is_preprocessed,
            face_count=db_template.face_count,
            male_face_count=db_template.male_face_count,
            female_face_count=db_template.female_face_count,
            popularity_score=db_template.popularity_score,
            is_active=db_template.is_active,
            created_at=db_template.created_at,
            updated_at=db_template.updated_at,
            image_url=storage_service.get_file_url(db_image.storage_path)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading template: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={"error": f"Error uploading template: {str(e)}"}
        )


@router.get("/", response_model=TemplateListResponse)
async def list_templates(
    category: Optional[str] = None,
    is_preprocessed: Optional[bool] = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    List available templates

    Args:
        category: Filter by category
        is_preprocessed: Filter by preprocessing status
        limit: Number of results (max 100)
        offset: Pagination offset
        db: Database session

    Returns:
        List of templates
    """
    query = db.query(Template).filter(Template.is_active == True)

    # Apply filters
    if category:
        query = query.filter(Template.category == category)

    if is_preprocessed is not None:
        query = query.filter(Template.is_preprocessed == is_preprocessed)

    # Order by popularity
    query = query.order_by(Template.popularity_score.desc())

    # Get total count
    total = query.count()

    # Apply pagination
    templates = query.offset(offset).limit(min(limit, 100)).all()

    # Convert to response models
    template_responses = []
    for template in templates:
        image = db.query(Image).filter(Image.id == template.original_image_id).first()

        template_responses.append(
            TemplateResponse(
                id=template.id,
                name=template.name,
                description=template.description,
                category=template.category,
                original_image_id=template.original_image_id,
                is_preprocessed=template.is_preprocessed,
                face_count=template.face_count,
                male_face_count=template.male_face_count,
                female_face_count=template.female_face_count,
                popularity_score=template.popularity_score,
                is_active=template.is_active,
                created_at=template.created_at,
                updated_at=template.updated_at,
                image_url=storage_service.get_file_url(image.storage_path) if image else None
            )
        )

    return TemplateListResponse(
        templates=template_responses,
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: int,
    db: Session = Depends(get_db)
):
    """
    Get template details

    Args:
        template_id: Template ID
        db: Database session

    Returns:
        Template metadata
    """
    template = db.query(Template).filter(Template.id == template_id).first()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    image = db.query(Image).filter(Image.id == template.original_image_id).first()

    return TemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        category=template.category,
        original_image_id=template.original_image_id,
        is_preprocessed=template.is_preprocessed,
        face_count=template.face_count,
        male_face_count=template.male_face_count,
        female_face_count=template.female_face_count,
        popularity_score=template.popularity_score,
        is_active=template.is_active,
        created_at=template.created_at,
        updated_at=template.updated_at,
        image_url=storage_service.get_file_url(image.storage_path) if image else None
    )


@router.delete("/{template_id}", response_model=DeleteResponse)
async def delete_template(
    template_id: int,
    cascade: bool = True,
    db: Session = Depends(get_db)
):
    """
    Delete a template

    Args:
        template_id: Template ID
        cascade: Also delete associated images (default: True)
        db: Database session

    Returns:
        Success message
    """
    template = db.query(Template).filter(Template.id == template_id).first()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    try:
        # Get associated image
        image = db.query(Image).filter(Image.id == template.original_image_id).first()

        # Delete template
        db.delete(template)

        # Delete image if cascade is True
        if cascade and image:
            storage_service.delete_file(image.storage_path)
            db.delete(image)

        db.commit()

        logger.info(f"Template deleted: id={template_id}, cascade={cascade}")

        return DeleteResponse(
            message="Template deleted successfully",
            deleted_id=template_id
        )

    except Exception as e:
        logger.error(f"Error deleting template {template_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting template: {str(e)}"
        )


@router.patch("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: int,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    is_active: Optional[bool] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Update template metadata

    Args:
        template_id: Template ID
        name: New name
        description: New description
        category: New category
        is_active: Active status
        db: Database session

    Returns:
        Updated template
    """
    template = db.query(Template).filter(Template.id == template_id).first()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Update fields if provided
    if name is not None:
        template.name = name
    if description is not None:
        template.description = description
    if category is not None:
        template.category = category
    if is_active is not None:
        template.is_active = is_active

    template.updated_at = datetime.utcnow()

    try:
        db.commit()
        db.refresh(template)

        image = db.query(Image).filter(Image.id == template.original_image_id).first()

        logger.info(f"Template updated: id={template_id}")

        return TemplateResponse(
            id=template.id,
            name=template.name,
            description=template.description,
            category=template.category,
            original_image_id=template.original_image_id,
            is_preprocessed=template.is_preprocessed,
            face_count=template.face_count,
            male_face_count=template.male_face_count,
            female_face_count=template.female_face_count,
            popularity_score=template.popularity_score,
            is_active=template.is_active,
            created_at=template.created_at,
            updated_at=template.updated_at,
            image_url=storage_service.get_file_url(image.storage_path) if image else None
        )

    except Exception as e:
        logger.error(f"Error updating template {template_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error updating template: {str(e)}"
        )
