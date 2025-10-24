"""
Couple Face-Swap API - Main Application

FastAPI application for face-swapping service
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging
import os

from app.core.config import settings
from app.core.database import init_db, check_db_connection
from app.api.v1 import api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

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
