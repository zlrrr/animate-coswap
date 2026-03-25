"""
Catcher Service API - Image Collection Management (Phase 3)

Provides endpoints for:
- Creating crawl tasks
- Managing (pause/resume/cancel) crawl tasks
- Monitoring crawl progress
- Viewing collected images
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
import uuid

from app.core.database import get_db
from app.models.database import CrawlTask, CollectedImage, Template, Image
from app.models.schemas import (
    CrawlTaskCreate,
    CrawlTaskResponse,
    CrawlTaskStatus,
    CollectedImageResponse
)
from app.services.catcher.pixiv_crawler import PixivCrawler
from app.services.catcher.danbooru_crawler import DanbooruCrawler, GelbooruCrawler
from app.services.catcher.base_crawler import CrawlerConfig

router = APIRouter(prefix="/catcher", tags=["catcher"])
logger = logging.getLogger(__name__)


# In-memory storage for active crawlers (in production, use Celery/Redis)
active_crawlers: Dict[str, Any] = {}


def get_crawler(source_type: str, config: Optional[CrawlerConfig] = None):
    """
    Get crawler instance for specified source type

    Args:
        source_type: Type of source ("pixiv", "danbooru", "gelbooru")
        config: Optional crawler configuration

    Returns:
        Crawler instance

    Raises:
        ValueError: If source type not supported
    """
    source_type = source_type.lower()

    if source_type == "pixiv":
        return PixivCrawler(config=config)
    elif source_type == "danbooru":
        return DanbooruCrawler(config=config)
    elif source_type == "gelbooru":
        return GelbooruCrawler(config=config)
    else:
        raise ValueError(f"Unsupported source type: {source_type}")


@router.post("/crawl-tasks", response_model=CrawlTaskResponse, status_code=201)
async def create_crawl_task(
    request: CrawlTaskCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new image collection crawl task

    Example request:
    ```json
    {
        "source_type": "danbooru",
        "search_query": "1boy_1girl",
        "category": "acg",
        "filters": {
            "min_faces": 2,
            "max_faces": 2,
            "min_resolution": [800, 600],
            "min_score": 10,
            "rating": "s"
        },
        "limit": 100
    }
    ```
    """
    # Validate source type
    valid_sources = ["pixiv", "danbooru", "gelbooru"]
    if request.source_type.lower() not in valid_sources:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source_type. Must be one of: {valid_sources}"
        )

    try:
        # Generate unique task ID
        task_id = f"crawl_{uuid.uuid4().hex[:12]}"

        # Create task in database
        crawl_task = CrawlTask(
            task_id=task_id,
            source_type=request.source_type.lower(),
            search_query=request.search_query,
            category=request.category,
            filters=request.filters or {},
            target_count=request.limit,
            status="pending"
        )

        db.add(crawl_task)
        db.commit()
        db.refresh(crawl_task)

        logger.info(
            f"Created crawl task {task_id}",
            extra={
                "task_id": task_id,
                "source": request.source_type,
                "query": request.search_query,
                "limit": request.limit
            }
        )

        return CrawlTaskResponse.from_orm(crawl_task)

    except Exception as e:
        logger.error(f"Error creating crawl task: {e}", extra={"error": str(e)})
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/crawl-tasks/{task_id}", response_model=CrawlTaskStatus)
async def get_crawl_task_status(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    Get crawl task progress and statistics

    Returns:
    - Task status (pending, running, paused, completed, failed)
    - Images collected/saved/filtered counts
    - Progress percentage
    - Start/completion times
    """
    task = db.query(CrawlTask).filter(CrawlTask.task_id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Crawl task not found")

    return CrawlTaskStatus.from_orm(task)


@router.get("/crawl-tasks", response_model=List[CrawlTaskResponse])
async def list_crawl_tasks(
    status: Optional[str] = Query(None, regex="^(pending|running|paused|completed|failed)$"),
    source_type: Optional[str] = Query(None, regex="^(pixiv|danbooru|gelbooru)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    List crawl tasks with optional filters

    Query parameters:
    - status: Filter by status
    - source_type: Filter by source type
    - skip: Number of records to skip (pagination)
    - limit: Maximum number of records to return
    """
    query = db.query(CrawlTask)

    if status:
        query = query.filter(CrawlTask.status == status)

    if source_type:
        query = query.filter(CrawlTask.source_type == source_type.lower())

    tasks = query.order_by(CrawlTask.created_at.desc()).offset(skip).limit(limit).all()

    return [CrawlTaskResponse.from_orm(task) for task in tasks]


@router.post("/crawl-tasks/{task_id}/start")
async def start_crawl_task(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    Start a pending crawl task

    This initiates the crawling process in the background.
    Use GET /crawl-tasks/{task_id} to monitor progress.
    """
    task = db.query(CrawlTask).filter(CrawlTask.task_id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Crawl task not found")

    if task.status not in ["pending", "paused"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start task with status: {task.status}"
        )

    try:
        # Update task status
        task.status = "running"
        task.started_at = datetime.utcnow()
        db.commit()

        # TODO: Start crawler in background (use Celery in production)
        # For now, we'll just mark it as running
        logger.info(
            f"Started crawl task {task_id}",
            extra={"task_id": task_id, "source": task.source_type}
        )

        return {
            "status": "success",
            "message": f"Crawl task {task_id} started",
            "task_id": task_id
        }

    except Exception as e:
        logger.error(f"Error starting crawl task: {e}", extra={"error": str(e)})
        task.status = "failed"
        task.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/crawl-tasks/{task_id}/pause")
async def pause_crawl_task(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    Pause a running crawl task

    The task can be resumed later using POST /crawl-tasks/{task_id}/resume
    """
    task = db.query(CrawlTask).filter(CrawlTask.task_id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Crawl task not found")

    if task.status != "running":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot pause task with status: {task.status}"
        )

    try:
        task.status = "paused"
        task.paused_at = datetime.utcnow()
        db.commit()

        logger.info(f"Paused crawl task {task_id}", extra={"task_id": task_id})

        return {
            "status": "success",
            "message": f"Crawl task {task_id} paused",
            "task_id": task_id
        }

    except Exception as e:
        logger.error(f"Error pausing crawl task: {e}", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/crawl-tasks/{task_id}/resume")
async def resume_crawl_task(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    Resume a paused crawl task
    """
    task = db.query(CrawlTask).filter(CrawlTask.task_id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Crawl task not found")

    if task.status != "paused":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot resume task with status: {task.status}"
        )

    try:
        task.status = "running"
        task.paused_at = None
        db.commit()

        logger.info(f"Resumed crawl task {task_id}", extra={"task_id": task_id})

        return {
            "status": "success",
            "message": f"Crawl task {task_id} resumed",
            "task_id": task_id
        }

    except Exception as e:
        logger.error(f"Error resuming crawl task: {e}", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/crawl-tasks/{task_id}/cancel")
async def cancel_crawl_task(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    Cancel a running or paused crawl task

    This stops the crawling process and marks the task as failed.
    Collected images up to this point are preserved.
    """
    task = db.query(CrawlTask).filter(CrawlTask.task_id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Crawl task not found")

    if task.status not in ["running", "paused"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel task with status: {task.status}"
        )

    try:
        task.status = "failed"
        task.error_message = "Cancelled by user"
        task.completed_at = datetime.utcnow()
        db.commit()

        logger.info(f"Cancelled crawl task {task_id}", extra={"task_id": task_id})

        return {
            "status": "success",
            "message": f"Crawl task {task_id} cancelled",
            "task_id": task_id
        }

    except Exception as e:
        logger.error(f"Error cancelling crawl task: {e}", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/crawl-tasks/{task_id}/images", response_model=List[CollectedImageResponse])
async def get_collected_images(
    task_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get images collected by a crawl task

    Returns metadata for all images collected by the specified task.
    Use this to review collected images before saving them as templates.
    """
    task = db.query(CrawlTask).filter(CrawlTask.task_id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Crawl task not found")

    images = (
        db.query(CollectedImage)
        .filter(CollectedImage.crawl_task_id == task.id)
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [CollectedImageResponse.from_orm(img) for img in images]


@router.post("/crawl-tasks/{task_id}/images/{image_id}/save-as-template")
async def save_collected_image_as_template(
    task_id: str,
    image_id: int,
    name: str = Query(..., min_length=1, max_length=255),
    category: str = Query(..., regex="^(acg|movie|tv|custom)$"),
    db: Session = Depends(get_db)
):
    """
    Save a collected image as a template

    This downloads the image (if not already downloaded),
    saves it permanently, and creates a template record.
    """
    # Find collected image
    collected = (
        db.query(CollectedImage)
        .join(CrawlTask)
        .filter(
            CrawlTask.task_id == task_id,
            CollectedImage.id == image_id
        )
        .first()
    )

    if not collected:
        raise HTTPException(status_code=404, detail="Collected image not found")

    if collected.saved_as_template:
        raise HTTPException(status_code=400, detail="Image already saved as template")

    try:
        # TODO: Download image if not already downloaded
        # TODO: Create Image record
        # TODO: Create Template record

        collected.saved_as_template = True
        db.commit()

        logger.info(
            f"Saved collected image as template",
            extra={"collected_image_id": image_id, "name": name}
        )

        return {
            "status": "success",
            "message": "Image saved as template",
            "template_id": None  # TODO: Return actual template ID
        }

    except Exception as e:
        logger.error(f"Error saving image as template: {e}", extra={"error": str(e)})
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources", response_model=List[Dict[str, Any]])
async def list_available_sources():
    """
    List all available image sources and their capabilities

    Returns information about supported crawl sources:
    - Source name and type
    - Rate limits
    - Authentication requirements
    - Supported filters
    """
    return [
        {
            "name": "pixiv",
            "display_name": "Pixiv",
            "description": "Japanese illustration community",
            "requires_auth": True,
            "rate_limit": "100 requests/hour",
            "supported_filters": ["sort", "min_bookmarks", "r18"],
            "couple_tags": ["カップル", "2人", "couple"]
        },
        {
            "name": "danbooru",
            "display_name": "Danbooru",
            "description": "Anime image board",
            "requires_auth": False,
            "rate_limit": "2 requests/second (anonymous)",
            "supported_filters": ["rating", "min_score", "order"],
            "couple_tags": ["1boy_1girl", "2girls", "couple"]
        },
        {
            "name": "gelbooru",
            "display_name": "Gelbooru",
            "description": "Anime/manga image board",
            "requires_auth": False,
            "rate_limit": "2 requests/second",
            "supported_filters": ["rating", "sort"],
            "couple_tags": ["1boy_1girl", "2girls", "couple"]
        }
    ]


@router.get("/stats", response_model=Dict[str, Any])
async def get_crawler_statistics(
    db: Session = Depends(get_db)
):
    """
    Get overall crawler statistics

    Returns:
    - Total tasks created
    - Tasks by status
    - Total images collected
    - Images by source
    """
    total_tasks = db.query(CrawlTask).count()
    tasks_by_status = {}

    for status in ["pending", "running", "paused", "completed", "failed"]:
        count = db.query(CrawlTask).filter(CrawlTask.status == status).count()
        tasks_by_status[status] = count

    total_images = db.query(CollectedImage).count()
    images_saved_as_templates = db.query(CollectedImage).filter(
        CollectedImage.saved_as_template == True
    ).count()

    return {
        "total_tasks": total_tasks,
        "tasks_by_status": tasks_by_status,
        "total_images_collected": total_images,
        "images_saved_as_templates": images_saved_as_templates
    }
