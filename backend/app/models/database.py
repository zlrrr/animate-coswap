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
    image_type = Column(String(20), index=True)  # 'source', 'template', 'result'
    category = Column(String(50))  # 'acg', 'movie', 'tv', 'custom'
    tags = Column(JSON, default=lambda: [])  # Use JSON for SQLite compatibility
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    image_metadata = Column(JSON)  # Renamed from 'metadata' to avoid SQLAlchemy reserved name

    # Relationships
    user = relationship("User", back_populates="images")
    template = relationship("Template", back_populates="image", uselist=False)


class Template(Base):
    """Template model for couple images"""
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    image_id = Column(Integer, ForeignKey("images.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(String)
    artist = Column(String(255))
    source_url = Column(String(500))
    face_count = Column(Integer, default=2)
    face_positions = Column(JSON)  # Detected face bounding boxes
    popularity_score = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    image = relationship("Image", back_populates="template")
    faceswap_tasks = relationship("FaceSwapTask", back_populates="template")


class FaceSwapTask(Base):
    """Face-swap task model"""
    __tablename__ = "faceswap_tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=False)
    husband_image_id = Column(Integer, ForeignKey("images.id"), nullable=False)
    wife_image_id = Column(Integer, ForeignKey("images.id"), nullable=False)
    result_image_id = Column(Integer, ForeignKey("images.id"), nullable=True)
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
    husband_image = relationship("Image", foreign_keys=[husband_image_id])
    wife_image = relationship("Image", foreign_keys=[wife_image_id])
    result_image = relationship("Image", foreign_keys=[result_image_id])


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
