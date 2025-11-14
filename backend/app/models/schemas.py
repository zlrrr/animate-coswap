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


# ============================================================
# Phase 1.5 Checkpoint 1.5.4: Batch Processing Schemas
# ============================================================

class BatchFaceSwapRequest(BaseModel):
    """Request for batch face-swap"""
    husband_photo_id: int
    wife_photo_id: int
    template_ids: List[int]
    use_default_mapping: bool = True
    use_preprocessed: bool = True
    face_mappings: Optional[List[FaceMappingItem]] = None


class BatchFaceSwapResponse(BaseModel):
    """Response for batch face-swap creation"""
    batch_id: str
    total_tasks: int
    status: str
    created_at: datetime
    message: str


class BatchStatusResponse(BaseModel):
    """Response for batch status"""
    batch_id: str
    status: str
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    progress_percentage: float
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BatchTaskListResponse(BaseModel):
    """Response for batch task list"""
    batch_id: str
    tasks: List[TaskStatusResponse]
    total: int


class BatchResultItem(BaseModel):
    """Single result in batch"""
    task_id: str
    template_id: int
    status: str
    result_image_url: Optional[str] = None
    error_message: Optional[str] = None


class BatchResultsResponse(BaseModel):
    """Response for batch results"""
    batch_id: str
    results: List[BatchResultItem]
    completed_count: int
    failed_count: int


class BatchListResponse(BaseModel):
    """Response for batch list"""
    batches: List[BatchStatusResponse]
    total: int


# ======================================
# Phase 3: Catcher Service Schemas
# ======================================

class CrawlTaskCreate(BaseModel):
    """Request to create a new crawl task"""
    source_type: str = Field(..., description="Source type: pixiv, danbooru, gelbooru")
    search_query: str = Field(..., min_length=1, description="Search query/tags")
    category: str = Field("acg", description="Target category for collected images")
    filters: Optional[dict] = Field(default=None, description="Additional filters")
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of images to collect")


class CrawlTaskResponse(BaseModel):
    """Response for crawl task"""
    task_id: str
    source_type: str
    search_query: str
    category: str
    filters: Optional[dict] = None
    target_count: int
    status: str
    images_collected: int
    images_saved: int
    images_filtered: int
    progress: int
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CrawlTaskStatus(BaseModel):
    """Detailed status for crawl task"""
    task_id: str
    status: str
    source_type: str
    search_query: str
    target_count: int
    images_collected: int
    images_saved: int
    images_filtered: int
    progress: int
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CollectedImageResponse(BaseModel):
    """Response for collected image metadata"""
    id: int
    source_url: str
    source: str
    title: Optional[str] = None
    artist: Optional[str] = None
    tags: List[str] = []
    width: Optional[int] = None
    height: Optional[int] = None
    file_size: Optional[int] = None
    face_count: Optional[int] = None
    score: Optional[int] = None
    rating: Optional[str] = None
    download_status: str
    saved_as_template: bool
    collected_at: datetime
    downloaded_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# ======================================
# Phase 4: Browser Service Schemas
# ======================================

class TagCreate(BaseModel):
    """Request to create a new tag"""
    name: str = Field(..., min_length=1, max_length=100)
    category: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None


class TagResponse(BaseModel):
    """Response for tag"""
    id: int
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    usage_count: int
    is_system: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ImageTagCreate(BaseModel):
    """Request to add tag to image"""
    image_id: int
    tag_id: int
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class ImageTagResponse(BaseModel):
    """Response for image tag"""
    id: int
    image_id: int
    tag_id: int
    tag_name: str
    confidence: Optional[float] = None
    created_by: str
    created_at: datetime

    class Config:
        from_attributes = True


class CollectionCreate(BaseModel):
    """Request to create a new collection"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    is_public: bool = False


class CollectionUpdate(BaseModel):
    """Request to update collection"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_public: Optional[bool] = None
    cover_image_id: Optional[int] = None


class CollectionResponse(BaseModel):
    """Response for collection"""
    id: int
    name: str
    description: Optional[str] = None
    is_public: bool
    image_count: int
    cover_image_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CollectionItemCreate(BaseModel):
    """Request to add item to collection"""
    collection_id: int
    image_id: Optional[int] = None
    template_id: Optional[int] = None
    notes: Optional[str] = None


class CollectionItemResponse(BaseModel):
    """Response for collection item"""
    id: int
    collection_id: int
    image_id: Optional[int] = None
    template_id: Optional[int] = None
    order: int
    notes: Optional[str] = None
    added_at: datetime

    class Config:
        from_attributes = True


class FavoriteCreate(BaseModel):
    """Request to add favorite"""
    image_id: Optional[int] = None
    template_id: Optional[int] = None


class FavoriteResponse(BaseModel):
    """Response for favorite"""
    id: int
    image_id: Optional[int] = None
    template_id: Optional[int] = None
    favorited_at: datetime

    class Config:
        from_attributes = True


class AdvancedSearchRequest(BaseModel):
    """Request for advanced search"""
    query: Optional[str] = Field(None, description="Text search query")
    tags: Optional[List[str]] = Field(None, description="Tag filters")
    category: Optional[str] = Field(None, description="Category filter")
    min_width: Optional[int] = Field(None, ge=1, description="Minimum width")
    min_height: Optional[int] = Field(None, ge=1, description="Minimum height")
    min_faces: Optional[int] = Field(None, ge=0, description="Minimum face count")
    max_faces: Optional[int] = Field(None, ge=0, description="Maximum face count")
    has_preprocessing: Optional[bool] = Field(None, description="Filter by preprocessing status")
    sort_by: str = Field("created_at", description="Sort field")
    sort_order: str = Field("desc", description="Sort order: asc or desc")
    skip: int = Field(0, ge=0, description="Pagination offset")
    limit: int = Field(20, ge=1, le=100, description="Results per page")


class AdvancedSearchResponse(BaseModel):
    """Response for advanced search"""
    results: List[dict]  # Can be templates or images
    total: int
    query: Optional[str] = None
    filters_applied: dict


class ImageMetadataUpdate(BaseModel):
    """Request to update image metadata"""
    filename: Optional[str] = Field(None, max_length=255)
    category: Optional[str] = Field(None, max_length=50)
    tags: Optional[List[str]] = None


class BatchTagOperation(BaseModel):
    """Request for batch tag operation"""
    image_ids: List[int] = Field(..., min_items=1)
    tag_ids: List[int] = Field(..., min_items=1)
    operation: str = Field(..., pattern="^(add|remove)$")


class SearchSuggestionResponse(BaseModel):
    """Response for search suggestions"""
    suggestions: List[str]
    popular_tags: List[TagResponse]
    recent_searches: List[str]
