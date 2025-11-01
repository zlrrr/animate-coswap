"""API v1 routes"""

from fastapi import APIRouter
from app.api.v1 import faceswap, photos, templates, templates_preprocessing, images

api_router = APIRouter()

# Include sub-routers
api_router.include_router(
    faceswap.router,
    prefix="/faceswap",
    tags=["faceswap"]
)

# Phase 1.5: Separated upload APIs
api_router.include_router(
    photos.router,
    prefix="/photos",
    tags=["photos"]
)

api_router.include_router(
    templates.router,
    prefix="/templates",
    tags=["templates"]
)

# Phase 1.5: Template preprocessing
api_router.include_router(
    templates_preprocessing.router,
    prefix="/templates",
    tags=["preprocessing"]
)

api_router.include_router(
    images.router,
    prefix="/images",
    tags=["images"]
)
