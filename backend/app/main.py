"""
Couple Face-Swap API - Main Application

FastAPI application for face-swapping service
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging
import json
import time
import uuid
import os

from app.core.config import settings
from app.core.database import init_db, check_db_connection
from app.api.v1 import api_router


# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------

class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter for production use."""

    def format(self, record):
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        # Include extra fields if present
        for key in ("request_id", "method", "path", "status_code", "duration_ms"):
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging():
    """Configure application logging based on settings."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    handler = logging.StreamHandler()
    handler.setLevel(log_level)

    if settings.LOG_FORMAT.lower() == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))

    root_logger.addHandler(handler)

    # Quiet noisy third-party loggers
    for name in ("uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(name).setLevel(logging.WARNING)


setup_logging()
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AI-powered couple image face-swapping service",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log every request with timing and a correlation request_id."""
    request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex[:12])
    start = time.time()

    response = await call_next(request)

    duration_ms = round((time.time() - start) * 1000, 1)
    logger.info(
        "%s %s -> %s (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    response.headers["X-Request-ID"] = request_id
    return response

# Mount static files (for serving uploaded images)
storage_path = os.path.join(os.getcwd(), settings.STORAGE_PATH)
if os.path.exists(storage_path):
    app.mount("/storage", StaticFiles(directory=storage_path), name="storage")


@app.on_event("startup")
async def startup_event():
    """
    Run on application startup

    - Check database connection
    - Initialize database tables
    - Verify models directory exists
    """
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")

    # Check database connection
    if check_db_connection():
        logger.info("Database connection verified")

        # Initialize database tables
        try:
            init_db()
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
    else:
        logger.warning("Database connection failed - some features may not work")

    # Check models directory
    models_path = os.path.join(os.getcwd(), settings.MODELS_PATH)
    if not os.path.exists(models_path):
        logger.warning(f"Models directory not found: {models_path}")
        os.makedirs(models_path, exist_ok=True)

    # Check for face-swap model
    model_file = os.path.join(models_path, settings.INSWAPPER_MODEL)
    if os.path.exists(model_file):
        logger.info(f"Face-swap model found: {settings.INSWAPPER_MODEL}")
    else:
        logger.warning(
            f"Face-swap model not found: {model_file}\n"
            "Download from: https://huggingface.co/ezioruan/inswapper_128.onnx"
        )

    # Check storage directories
    storage_path = os.path.join(os.getcwd(), settings.STORAGE_PATH)
    for subdir in ["source", "templates", "results", "temp"]:
        dir_path = os.path.join(storage_path, subdir)
        os.makedirs(dir_path, exist_ok=True)

    logger.info("Application startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    logger.info("Shutting down application")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "running",
        "docs": "/docs",
        "api": settings.API_V1_STR
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    # Check database
    db_status = "healthy" if check_db_connection() else "unhealthy"

    # Check models
    model_path = os.path.join(os.getcwd(), settings.MODELS_PATH, settings.INSWAPPER_MODEL)
    model_status = "available" if os.path.exists(model_path) else "missing"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "model": model_status,
        "storage": settings.STORAGE_TYPE
    }


# Include API routers
app.include_router(api_router, prefix=settings.API_V1_STR)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
