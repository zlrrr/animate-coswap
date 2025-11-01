"""
Cleanup API - Phase 1.5

Checkpoint 1.5.5: Auto Cleanup
Provides endpoints for manual and automatic cleanup operations
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
import logging

from app.core.database import get_db
from app.services.cleanup import CleanupService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/cleanup/expired")
async def cleanup_expired_images(
    dry_run: bool = Query(False, description="Preview without deleting"),
    db: Session = Depends(get_db)
):
    """
    Clean up expired temporary images (Phase 1.5.5)

    Deletes images where:
    - storage_type = 'temporary'
    - expires_at < now()

    Args:
        dry_run: If true, preview without deleting
        db: Database session

    Returns:
        Cleanup statistics
    """
    logger.info(f"Cleaning up expired images (dry_run={dry_run})")

    result = CleanupService.cleanup_expired_images(db, dry_run=dry_run)

    return {
        "operation": "cleanup_expired_images",
        **result
    }


@router.post("/cleanup/session/{session_id}")
async def cleanup_session(
    session_id: str,
    dry_run: bool = Query(False, description="Preview without deleting"),
    db: Session = Depends(get_db)
):
    """
    Clean up all images for a specific session (Phase 1.5.5)

    Useful when user's session ends

    Args:
        session_id: Session ID to clean up
        dry_run: If true, preview without deleting
        db: Database session

    Returns:
        Cleanup statistics
    """
    logger.info(f"Cleaning up session {session_id} (dry_run={dry_run})")

    result = CleanupService.cleanup_session_images(session_id, db, dry_run=dry_run)

    return {
        "operation": "cleanup_session",
        **result
    }


@router.post("/cleanup/old-results")
async def cleanup_old_results(
    days_old: int = Query(30, ge=1, le=365, description="Delete results older than N days"),
    dry_run: bool = Query(False, description="Preview without deleting"),
    db: Session = Depends(get_db)
):
    """
    Clean up old task results (Phase 1.5.5)

    Deletes result images from completed/failed tasks older than specified days

    Args:
        days_old: Delete results older than this many days (default: 30)
        dry_run: If true, preview without deleting
        db: Database session

    Returns:
        Cleanup statistics
    """
    logger.info(f"Cleaning up old results (>{days_old} days, dry_run={dry_run})")

    result = CleanupService.cleanup_old_task_results(days_old, db, dry_run=dry_run)

    return {
        "operation": "cleanup_old_results",
        **result
    }


@router.post("/cleanup/orphaned")
async def cleanup_orphaned_files(
    dry_run: bool = Query(False, description="Preview without deleting"),
    db: Session = Depends(get_db)
):
    """
    Clean up orphaned files (Phase 1.5.5)

    Removes files on disk that are not referenced in database

    Args:
        dry_run: If true, preview without deleting
        db: Database session

    Returns:
        Cleanup statistics
    """
    logger.info(f"Cleaning up orphaned files (dry_run={dry_run})")

    result = CleanupService.cleanup_orphaned_files(db, dry_run=dry_run)

    return {
        "operation": "cleanup_orphaned_files",
        **result
    }


@router.post("/cleanup/all")
async def cleanup_all(
    days_old: int = Query(30, ge=1, le=365, description="Delete results older than N days"),
    dry_run: bool = Query(False, description="Preview without deleting"),
    db: Session = Depends(get_db)
):
    """
    Run all cleanup operations (Phase 1.5.5)

    Performs:
    - Expired images cleanup
    - Old task results cleanup
    - Orphaned files cleanup

    Args:
        days_old: Delete results older than this many days (default: 30)
        dry_run: If true, preview without deleting
        db: Database session

    Returns:
        Combined cleanup statistics
    """
    logger.info(f"Running full cleanup (days_old={days_old}, dry_run={dry_run})")

    result = CleanupService.cleanup_all(db, days_old=days_old, dry_run=dry_run)

    return {
        "operation": "cleanup_all",
        **result
    }


@router.get("/cleanup/stats")
async def get_cleanup_stats(
    db: Session = Depends(get_db)
):
    """
    Get cleanup statistics (Phase 1.5.5)

    Shows how many items are eligible for cleanup

    Args:
        db: Database session

    Returns:
        Cleanup statistics
    """
    stats = CleanupService.get_cleanup_stats(db)

    return {
        "operation": "get_stats",
        **stats
    }
