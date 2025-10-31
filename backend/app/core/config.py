"""
Application configuration settings
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""

    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Couple Face-Swap API"
    VERSION: str = "0.1.0"

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/faceswap"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Storage
    STORAGE_TYPE: str = "local"  # "local", "minio", or "s3"
    STORAGE_PATH: str = "./storage"
    MINIO_ENDPOINT: Optional[str] = None
    MINIO_ACCESS_KEY: Optional[str] = None
    MINIO_SECRET_KEY: Optional[str] = None
    MINIO_BUCKET: str = "faceswap"

    # Face-Swap Models
    MODELS_PATH: str = "./models"
    INSWAPPER_MODEL: str = "inswapper_128.onnx"
    FACE_ANALYSIS_MODEL: str = "buffalo_l"

    # Processing
    MAX_IMAGE_SIZE: int = 4096  # Max width/height in pixels
    USE_GPU: bool = True
    GPU_DEVICE_ID: int = 0

    # Acceleration Backend
    # Options: "cuda", "coreml", "cpu", "auto"
    # - "cuda": NVIDIA GPU (Linux/Windows with CUDA)
    # - "coreml": Apple Neural Engine (macOS M-series)
    # - "cpu": CPU only (all platforms)
    # - "auto": Auto-detect best available
    ACCELERATION_PROVIDER: str = "auto"

    # Task Queue
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Security (for future authentication features)
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()
