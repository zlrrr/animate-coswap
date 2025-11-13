"""
SQLAlchemy database models
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    """User model"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    images = relationship("Image", back_populates="user")
    faceswap_tasks = relationship("FaceSwapTask", back_populates="user")


class Image(Base):
    """Image model"""
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    filename = Column(String(255), nullable=False)
    storage_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    width = Column(Integer)
    height = Column(Integer)
    image_type = Column(String(20), index=True)  # 'photo', 'template', 'preprocessed', 'result'
    storage_type = Column(String(20), default='permanent')  # 'permanent', 'temporary'
    category = Column(String(50))  # 'acg', 'movie', 'tv', 'custom'
    tags = Column(JSON, default=lambda: [])  # Use JSON for SQLite compatibility
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # For temporary images
    session_id = Column(String(100), nullable=True, index=True)  # For grouping temp photos
    image_metadata = Column(JSON)  # Renamed from 'metadata' to avoid SQLAlchemy reserved name

    # Relationships
    user = relationship("User", back_populates="images")
    template = relationship("Template", back_populates="image", uselist=False)


class Template(Base):
    """Template model for couple images"""
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)  # Renamed from title for consistency
    description = Column(String)
    category = Column(String(50))  # 'acg', 'movie', 'tv', 'custom'
    original_image_id = Column(Integer, ForeignKey("images.id"), nullable=False)
    is_preprocessed = Column(Boolean, default=False)
    face_count = Column(Integer, default=0)
    male_face_count = Column(Integer, default=0)
    female_face_count = Column(Integer, default=0)
    popularity_score = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    image = relationship("Image", back_populates="template", foreign_keys=[original_image_id])
    preprocessing = relationship("TemplatePreprocessing", back_populates="template", uselist=False)
    faceswap_tasks = relationship("FaceSwapTask", back_populates="template")


class FaceSwapTask(Base):
    """Face-swap task model"""
    __tablename__ = "faceswap_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(100), unique=True, nullable=False)  # Unique task identifier
    batch_id = Column(String(100), ForeignKey("batch_tasks.batch_id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=False)
    husband_photo_id = Column(Integer, ForeignKey("images.id"), nullable=False)
    wife_photo_id = Column(Integer, ForeignKey("images.id"), nullable=False)
    result_image_id = Column(Integer, ForeignKey("images.id"), nullable=True)
    face_mappings = Column(JSON, nullable=True)  # Custom face mapping configuration
    use_preprocessed = Column(Boolean, default=True)  # Use preprocessed template
    status = Column(String(20), default="pending", index=True)  # 'pending', 'processing', 'completed', 'failed'
    progress = Column(Integer, default=0)
    error_message = Column(String)
    processing_time = Column(Float)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="faceswap_tasks")
    template = relationship("Template", back_populates="faceswap_tasks")
    husband_photo = relationship("Image", foreign_keys=[husband_photo_id])
    wife_photo = relationship("Image", foreign_keys=[wife_photo_id])
    result_image = relationship("Image", foreign_keys=[result_image_id])
    batch = relationship("BatchTask", back_populates="tasks")


class TemplatePreprocessing(Base):
    """Template preprocessing data model"""
    __tablename__ = "template_preprocessing"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("templates.id"), unique=True, nullable=False)
    original_image_id = Column(Integer, ForeignKey("images.id"), nullable=False)
    faces_detected = Column(Integer, nullable=False, default=0)
    face_data = Column(JSON, nullable=False)  # Array of face info (bbox, gender, landmarks, etc.)
    masked_image_id = Column(Integer, ForeignKey("images.id"), nullable=True)
    preprocessing_status = Column(String(20), default="pending", index=True)  # 'pending', 'completed', 'failed'
    error_message = Column(String)
    processed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    template = relationship("Template", back_populates="preprocessing")
    original_image = relationship("Image", foreign_keys=[original_image_id])
    masked_image = relationship("Image", foreign_keys=[masked_image_id])


class BatchTask(Base):
    """Batch processing task model"""
    __tablename__ = "batch_tasks"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(String(100), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    husband_photo_id = Column(Integer, ForeignKey("images.id"), nullable=False)
    wife_photo_id = Column(Integer, ForeignKey("images.id"), nullable=False)
    template_ids = Column(JSON, nullable=False)  # Array of template IDs
    status = Column(String(20), default="pending", index=True)  # 'pending', 'processing', 'completed', 'failed'
    total_tasks = Column(Integer, nullable=False)
    completed_tasks = Column(Integer, default=0)
    failed_tasks = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

    # Relationships
    user = relationship("User")
    husband_photo = relationship("Image", foreign_keys=[husband_photo_id])
    wife_photo = relationship("Image", foreign_keys=[wife_photo_id])
    tasks = relationship("FaceSwapTask", back_populates="batch")


class CrawlTask(Base):
    """Crawl task model for image collection (Phase 3)"""
    __tablename__ = "crawl_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(100), unique=True, nullable=False)  # Unique task identifier
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    source_type = Column(String(50), nullable=False, index=True)  # 'pixiv', 'danbooru', 'gelbooru'
    search_query = Column(String, nullable=False)
    category = Column(String(50))  # Target category for collected images
    filters = Column(JSON)  # Search filters (rating, min_score, etc.)
    status = Column(String(20), default="pending", index=True)  # 'pending', 'running', 'paused', 'completed', 'failed'
    images_collected = Column(Integer, default=0)
    images_saved = Column(Integer, default=0)
    images_filtered = Column(Integer, default=0)  # Images filtered out
    target_count = Column(Integer, nullable=False)  # Target number of images
    progress = Column(Integer, default=0)  # Progress percentage
    error_message = Column(String)
    started_at = Column(DateTime)
    paused_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")
    collected_images = relationship("CollectedImage", back_populates="crawl_task")


class CollectedImage(Base):
    """Collected image metadata from crawlers (Phase 3)"""
    __tablename__ = "collected_images"

    id = Column(Integer, primary_key=True, index=True)
    crawl_task_id = Column(Integer, ForeignKey("crawl_tasks.id"), nullable=False, index=True)
    image_id = Column(Integer, ForeignKey("images.id"), nullable=True)  # Reference to saved image
    source_url = Column(String(500), nullable=False)
    source = Column(String(50), nullable=False)  # 'pixiv', 'danbooru', etc.
    title = Column(String(255))
    artist = Column(String(255))
    tags = Column(JSON, default=lambda: [])
    width = Column(Integer)
    height = Column(Integer)
    file_size = Column(Integer)
    face_count = Column(Integer)
    source_id = Column(String(100))  # ID from source (pixiv_id, danbooru_id, etc.)
    score = Column(Integer)  # Popularity score from source
    rating = Column(String(10))  # Content rating
    download_status = Column(String(20), default="pending")  # 'pending', 'downloaded', 'failed'
    saved_as_template = Column(Boolean, default=False)
    collected_at = Column(DateTime, default=datetime.utcnow)
    downloaded_at = Column(DateTime)

    # Relationships
    crawl_task = relationship("CrawlTask", back_populates="collected_images")
    image = relationship("Image")
