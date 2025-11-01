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


class FaceMappingItem(BaseModel):
    """Single face mapping rule"""
    source_photo: str  # "husband" or "wife"
    source_face_index: int = 0
    target_face_index: int


class FaceSwapRequest(BaseModel):
    """Request to create a face-swap task (Phase 1.5)"""
    husband_photo_id: int  # Renamed from husband_image_id
    wife_photo_id: int  # Renamed from wife_image_id
    template_id: int
    use_default_mapping: bool = True  # Phase 1.5: Auto-map by gender
    use_preprocessed: bool = True  # Phase 1.5: Use preprocessed template
    face_mappings: Optional[List[FaceMappingItem]] = None  # Phase 1.5: Custom mapping


class FaceSwapResponse(BaseModel):
    """Response for face-swap task creation (Phase 1.5)"""
    task_id: str  # Phase 1.5: Changed to string (UUID-like)
    status: str
    created_at: datetime
    face_mappings: Optional[List[dict]] = None  # Phase 1.5: Show computed mappings
    use_preprocessed: bool = True


class TaskStatusResponse(BaseModel):
    """Response for task status query (Phase 1.5)"""
    task_id: str  # Phase 1.5: String task_id
    status: str
    progress: int
    result_image_url: Optional[str] = None
    processing_time: Optional[float] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    face_mappings: Optional[List[dict]] = None  # Phase 1.5: Show mappings used


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


# ============================================================
# Phase 1.5 Schemas
# ============================================================

class ImageResponse(BaseModel):
    """Image response with Phase 1.5 fields"""
    id: int
    filename: str
    storage_path: str
    storage_type: Optional[str] = None
    file_size: int
    width: int
    height: int
    image_type: Optional[str] = None
    expires_at: Optional[datetime] = None
    session_id: Optional[str] = None
    uploaded_at: datetime

    class Config:
        from_attributes = True


class PhotoListResponse(BaseModel):
    """Response for photo list"""
    photos: List[ImageResponse]
    total: int
    session_id: Optional[str] = None
    errors: Optional[List[dict]] = None


class TemplateResponse(BaseModel):
    """Template response with Phase 1.5 fields"""
    id: int
    name: str
    description: Optional[str] = None
    category: str
    original_image_id: int
    is_preprocessed: bool
    face_count: int
    male_face_count: int
    female_face_count: int
    popularity_score: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    image_url: Optional[str] = None

    class Config:
        from_attributes = True


class TemplateListResponse(BaseModel):
    """Response for template list"""
    templates: List[TemplateResponse]
    total: int
    limit: int
    offset: int


class DeleteResponse(BaseModel):
    """Response for delete operations"""
    message: str
    deleted_id: Optional[int] = None
    deleted_count: Optional[int] = None
    errors: Optional[List[dict]] = None


class PreprocessingResponse(BaseModel):
    """Response for preprocessing trigger"""
    template_id: int
    status: str
    message: str

    class Config:
        from_attributes = True


class PreprocessingStatusResponse(BaseModel):
    """Response for preprocessing status"""
    template_id: int
    preprocessing_status: str
    faces_detected: int
    face_data: List[dict]
    masked_image_id: Optional[int] = None
    masked_image_url: Optional[str] = None
    original_image_id: int
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class BatchPreprocessingResponse(BaseModel):
    """Response for batch preprocessing"""
    total: int
    queued: int
    already_processed: int
    message: str
