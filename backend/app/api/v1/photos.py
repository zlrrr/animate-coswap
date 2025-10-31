"""
Photo Upload API - Temporary Storage

Phase 1.5 Checkpoint 1.5.1
Handles temporary photo uploads with automatic expiration
"""

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
from datetime import datetime, timedelta
import uuid
import cv2

from app.core.database import get_db
from app.core.config import settings
from app.models.database import Image
from app.models.schemas import ImageResponse, PhotoListResponse, DeleteResponse
from app.utils.storage import storage_service

logger = logging.getLogger(__name__)

router = APIRouter()


def generate_session_id() -> str:
    """Generate a unique session ID"""
    return f"session_{uuid.uuid4().hex[:16]}"


@router.post("/upload", response_model=ImageResponse)
async def upload_photo(
    file: UploadFile = File(...),
    session_id: Optional[str] = Query(None, description="Session ID to group photos"),
    expiration_hours: int = Query(24, ge=1, le=168, description="Hours until expiration"),
    db: Session = Depends(get_db)
):
    """
    Upload a temporary photo

    Photos are stored temporarily with automatic expiration.
    Use session_id to group related photos together.

    Args:
        file: Image file to upload
        session_id: Optional session ID for grouping (auto-generated if not provided)
        expiration_hours: Hours until photo expires (default: 24, max: 168)
        db: Database session

    Returns:
        Image metadata with expiration info
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail={"error": "File must be an image"}
        )

    # Generate session ID if not provided
    if not session_id:
        session_id = generate_session_id()

    try:
        # Save file to temporary storage
        storage_path, file_size = storage_service.save_file(
            file.file,
            file.filename,
            category="temp"
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

        # Calculate expiration time
        expires_at = datetime.utcnow() + timedelta(hours=expiration_hours)

        # Create database record
        db_image = Image(
            filename=file.filename,
            storage_path=storage_path,
            file_size=file_size,
            width=width,
            height=height,
            image_type="photo",
            storage_type="temporary",
            expires_at=expires_at,
            session_id=session_id,
            uploaded_at=datetime.utcnow()
        )

        db.add(db_image)
        db.commit()
        db.refresh(db_image)

        logger.info(
            f"Temporary photo uploaded: id={db_image.id}, "
            f"session={session_id}, expires_at={expires_at}"
        )

        return ImageResponse(
            id=db_image.id,
            filename=db_image.filename,
            storage_path=db_image.storage_path,
            storage_type=db_image.storage_type,
            file_size=db_image.file_size,
            width=db_image.width,
            height=db_image.height,
            image_type=db_image.image_type,
            expires_at=db_image.expires_at,
            session_id=db_image.session_id,
            uploaded_at=db_image.uploaded_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading photo: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": f"Error uploading photo: {str(e)}"}
        )


@router.post("/upload/batch", response_model=PhotoListResponse)
async def upload_photos_batch(
    files: List[UploadFile] = File(...),
    session_id: Optional[str] = Query(None, description="Session ID for all photos"),
    expiration_hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db)
):
    """
    Upload multiple photos at once

    All photos will share the same session ID and expiration time.

    Args:
        files: List of image files
        session_id: Session ID for all photos (auto-generated if not provided)
        expiration_hours: Hours until expiration
        db: Database session

    Returns:
        List of uploaded photos
    """
    # Generate session ID for the batch
    if not session_id:
        session_id = generate_session_id()

    uploaded_photos = []
    errors = []

    for file in files:
        try:
            # Upload each photo with the same session ID
            photo = await upload_photo(
                file=file,
                session_id=session_id,
                expiration_hours=expiration_hours,
                db=db
            )
            uploaded_photos.append(photo)
        except HTTPException as e:
            errors.append({
                "filename": file.filename,
                "error": str(e.detail)
            })
            logger.warning(f"Failed to upload {file.filename}: {e.detail}")

    if not uploaded_photos and errors:
        raise HTTPException(
            status_code=400,
            detail={"error": "All uploads failed", "details": errors}
        )

    return PhotoListResponse(
        photos=uploaded_photos,
        total=len(uploaded_photos),
        session_id=session_id,
        errors=errors if errors else None
    )


@router.get("/session/{session_id}", response_model=PhotoListResponse)
async def get_photos_by_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all photos in a session

    Args:
        session_id: Session ID
        db: Database session

    Returns:
        List of photos in the session
    """
    photos = db.query(Image).filter(
        Image.session_id == session_id,
        Image.storage_type == "temporary"
    ).all()

    photo_responses = [
        ImageResponse(
            id=photo.id,
            filename=photo.filename,
            storage_path=photo.storage_path,
            storage_type=photo.storage_type,
            file_size=photo.file_size,
            width=photo.width,
            height=photo.height,
            image_type=photo.image_type,
            expires_at=photo.expires_at,
            session_id=photo.session_id,
            uploaded_at=photo.uploaded_at
        )
        for photo in photos
    ]

    return PhotoListResponse(
        photos=photo_responses,
        total=len(photo_responses),
        session_id=session_id
    )


@router.delete("/{photo_id}", response_model=DeleteResponse)
async def delete_photo(
    photo_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a temporary photo

    Args:
        photo_id: Photo ID to delete
        db: Database session

    Returns:
        Success message
    """
    photo = db.query(Image).filter(
        Image.id == photo_id,
        Image.storage_type == "temporary"
    ).first()

    if not photo:
        raise HTTPException(
            status_code=404,
            detail="Photo not found"
        )

    try:
        # Delete file from storage
        storage_service.delete_file(photo.storage_path)

        # Delete database record
        db.delete(photo)
        db.commit()

        logger.info(f"Photo deleted: id={photo_id}")

        return DeleteResponse(
            message="Photo deleted successfully",
            deleted_id=photo_id
        )

    except Exception as e:
        logger.error(f"Error deleting photo {photo_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting photo: {str(e)}"
        )


@router.delete("/session/{session_id}", response_model=DeleteResponse)
async def delete_session_photos(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete all photos in a session

    Args:
        session_id: Session ID
        db: Database session

    Returns:
        Count of deleted photos
    """
    photos = db.query(Image).filter(
        Image.session_id == session_id,
        Image.storage_type == "temporary"
    ).all()

    if not photos:
        return DeleteResponse(
            message="No photos found in session",
            deleted_count=0
        )

    deleted_count = 0
    errors = []

    for photo in photos:
        try:
            storage_service.delete_file(photo.storage_path)
            db.delete(photo)
            deleted_count += 1
        except Exception as e:
            errors.append({
                "photo_id": photo.id,
                "error": str(e)
            })
            logger.error(f"Error deleting photo {photo.id}: {e}")

    db.commit()

    logger.info(f"Session {session_id} photos deleted: {deleted_count}")

    return DeleteResponse(
        message=f"Deleted {deleted_count} photos from session",
        deleted_count=deleted_count,
        errors=errors if errors else None
    )


@router.get("/{photo_id}", response_model=ImageResponse)
async def get_photo(
    photo_id: int,
    db: Session = Depends(get_db)
):
    """
    Get photo details

    Args:
        photo_id: Photo ID
        db: Database session

    Returns:
        Photo metadata
    """
    photo = db.query(Image).filter(Image.id == photo_id).first()

    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    return ImageResponse(
        id=photo.id,
        filename=photo.filename,
        storage_path=photo.storage_path,
        storage_type=photo.storage_type,
        file_size=photo.file_size,
        width=photo.width,
        height=photo.height,
        image_type=photo.image_type,
        expires_at=photo.expires_at,
        session_id=photo.session_id,
        uploaded_at=photo.uploaded_at
    )
