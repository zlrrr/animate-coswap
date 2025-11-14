"""API v1 routes"""

from fastapi import APIRouter
from app.api.v1 import faceswap, faceswap_v15, photos, templates, templates_preprocessing, images, cleanup, catcher, browser

api_router = APIRouter()

# Include sub-routers
api_router.include_router(
    faceswap.router,
    prefix="/faceswap",
    tags=["faceswap"]
)

# Phase 1.5: Enhanced FaceSwap with flexible mapping
api_router.include_router(
    faceswap_v15.router,
    prefix="/faceswap",
    tags=["faceswap-v1.5"]
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

# Phase 1.5: Auto cleanup
api_router.include_router(
    cleanup.router,
    prefix="/admin",
    tags=["cleanup"]
)

# Phase 3: Catcher Service (Image Collection)
api_router.include_router(
    catcher.router,
    tags=["catcher"]
)

# Phase 4: Browser Service (Image Management)
api_router.include_router(
    browser.router,
    tags=["browser"]
)
