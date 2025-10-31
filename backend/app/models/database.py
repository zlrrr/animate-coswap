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
    """Crawl task model (Phase 3+)"""
    __tablename__ = "crawl_tasks"

    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(String(50))  # 'pixiv', 'danbooru', 'custom'
    search_query = Column(String)
    filters = Column(JSON)
    status = Column(String(20), default="pending")
    images_collected = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
