"""
Pydantic schemas for request/response validation
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ImageUploadResponse(BaseModel):
    """Response for image upload"""
    image_id: int
    filename: str
    storage_path: str
    file_size: int
    width: int
    height: int


class FaceSwapRequest(BaseModel):
    """Request to create a face-swap task"""
    husband_image_id: int
    wife_image_id: int
    template_id: int


class FaceSwapResponse(BaseModel):
    """Response for face-swap task creation"""
    task_id: int
    status: str
    created_at: datetime


class TaskStatusResponse(BaseModel):
    """Response for task status query"""
    task_id: int
    status: str
    progress: int
    result_image_url: Optional[str] = None
    processing_time: Optional[float] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class TemplateListItem(BaseModel):
    """Template list item"""
    id: int
    title: str
    image_url: str
    category: str
    face_count: int
    popularity_score: int

    class Config:
        from_attributes = True


class FaceDetectionResult(BaseModel):
    """Face detection result"""
    face_count: int
    faces: List[dict]
    confidence_scores: List[float]


class FaceSwapResult(BaseModel):
    """Face-swap operation result"""
    success: bool
    result_image_path: Optional[str] = None
    processing_time: float
    error_message: Optional[str] = None
