"""API v1 routes"""

from fastapi import APIRouter
from app.api.v1 import faceswap

api_router = APIRouter()

# Include sub-routers
api_router.include_router(
    faceswap.router,
    prefix="/faceswap",
    tags=["faceswap"]
)
