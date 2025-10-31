"""
Images API - Generic image operations

Provides generic image retrieval and management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.core.database import get_db
from app.models.database import Image
from app.models.schemas import ImageResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{image_id}", response_model=ImageResponse)
async def get_image(
    image_id: int,
    db: Session = Depends(get_db)
):
    """
    Get image details by ID

    Works for both temporary photos and permanent templates.

    Args:
        image_id: Image ID
        db: Database session

    Returns:
        Image metadata
    """
    image = db.query(Image).filter(Image.id == image_id).first()

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    return ImageResponse(
        id=image.id,
        filename=image.filename,
        storage_path=image.storage_path,
        storage_type=image.storage_type,
        file_size=image.file_size,
        width=image.width,
        height=image.height,
        image_type=image.image_type,
        expires_at=image.expires_at,
        session_id=image.session_id,
        uploaded_at=image.uploaded_at
    )
