# Checkpoint 1.5.5: Auto Cleanup - COMPLETE ✅

## Overview

Checkpoint 1.5.5 implements **automatic cleanup** functionality for temporary files and expired data, ensuring efficient storage management and preventing disk space bloat.

**Status**: ✅ **COMPLETE**

## Features Implemented

### 1. Expired Image Cleanup
- Automatically delete temporary images past their expiration date
- Respects `expires_at` field on temporary images
- Skips images currently used by active tasks
- Dry-run mode for preview before deletion

### 2. Session-Based Cleanup
- Clean up all images associated with a specific session
- Useful when user sessions end
- Prevents orphaned data accumulation

### 3. Old Task Results Cleanup
- Delete result images from old completed/failed tasks
- Configurable retention period (default: 30 days)
- Preserves task records, only deletes result images

### 4. Orphaned Files Cleanup
- Detect and remove files on disk not referenced in database
- Scans all storage categories (photos, templates, preprocessed, results)
- Helps recover from database-file sync issues

### 5. Full Cleanup
- Run all cleanup operations in one call
- Provides combined statistics
- Efficient batch processing

### 6. Cleanup Statistics
- Get real-time stats on cleanable data
- Monitor cleanup opportunities
- No actual deletion

## Architecture

### Services

**CleanupService** (`app/services/cleanup.py`):

Key methods:
- `cleanup_expired_images()`: Delete expired temporary images
- `cleanup_session_images()`: Delete all images for a session
- `cleanup_old_task_results()`: Delete old task results
- `cleanup_orphaned_files()`: Remove files not in database
- `cleanup_all()`: Run all cleanup operations
- `get_cleanup_stats()`: Get cleanup statistics

All methods support `dry_run` mode for preview.

### API Endpoints

All endpoints under `/api/v1/admin/cleanup`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/cleanup/expired` | POST | Clean expired temporary images |
| `/cleanup/session/{session_id}` | POST | Clean session images |
| `/cleanup/old-results` | POST | Clean old task results |
| `/cleanup/orphaned` | POST | Clean orphaned files |
| `/cleanup/all` | POST | Run all cleanups |
| `/cleanup/stats` | GET | Get cleanup statistics |

## Usage Examples

### 1. Clean Expired Images

```bash
# Dry run (preview)
curl -X POST "http://localhost:8000/api/v1/admin/cleanup/expired?dry_run=true"

# Actual cleanup
curl -X POST "http://localhost:8000/api/v1/admin/cleanup/expired?dry_run=false"
```

Response:
```json
{
  "operation": "cleanup_expired_images",
  "deleted_count": 15,
  "deleted_size_bytes": 5242880,
  "deleted_size_mb": 5.0,
  "errors": [],
  "dry_run": false
}
```

### 2. Clean Session Images

```bash
# Clean all images for a session
curl -X POST "http://localhost:8000/api/v1/admin/cleanup/session/session_abc123?dry_run=false"
```

Response:
```json
{
  "operation": "cleanup_session",
  "session_id": "session_abc123",
  "deleted_count": 8,
  "deleted_size_bytes": 3145728,
  "deleted_size_mb": 3.0,
  "errors": [],
  "dry_run": false
}
```

### 3. Clean Old Task Results

```bash
# Delete results older than 30 days
curl -X POST "http://localhost:8000/api/v1/admin/cleanup/old-results?days_old=30&dry_run=false"

# Custom retention (60 days)
curl -X POST "http://localhost:8000/api/v1/admin/cleanup/old-results?days_old=60&dry_run=false"
```

Response:
```json
{
  "operation": "cleanup_old_results",
  "cutoff_date": "2025-10-01T00:00:00",
  "days_old": 30,
  "deleted_count": 42,
  "deleted_size_bytes": 52428800,
  "deleted_size_mb": 50.0,
  "errors": [],
  "dry_run": false
}
```

### 4. Clean Orphaned Files

```bash
curl -X POST "http://localhost:8000/api/v1/admin/cleanup/orphaned?dry_run=false"
```

Response:
```json
{
  "operation": "cleanup_orphaned_files",
  "deleted_count": 3,
  "deleted_size_bytes": 1048576,
  "deleted_size_mb": 1.0,
  "errors": [],
  "dry_run": false
}
```

### 5. Run Full Cleanup

```bash
# Run all cleanup operations
curl -X POST "http://localhost:8000/api/v1/admin/cleanup/all?days_old=30&dry_run=false"

# Dry run preview
curl -X POST "http://localhost:8000/api/v1/admin/cleanup/all?days_old=30&dry_run=true"
```

Response:
```json
{
  "operation": "cleanup_all",
  "expired_images": {
    "deleted_count": 15,
    "deleted_size_bytes": 5242880,
    "deleted_size_mb": 5.0,
    "errors": [],
    "dry_run": false
  },
  "old_task_results": {
    "cutoff_date": "2025-10-01T00:00:00",
    "days_old": 30,
    "deleted_count": 42,
    "deleted_size_bytes": 52428800,
    "deleted_size_mb": 50.0,
    "errors": [],
    "dry_run": false
  },
  "orphaned_files": {
    "deleted_count": 3,
    "deleted_size_bytes": 1048576,
    "deleted_size_mb": 1.0,
    "errors": [],
    "dry_run": false
  },
  "totals": {
    "deleted_count": 60,
    "deleted_size_bytes": 58720256,
    "deleted_size_mb": 56.0,
    "dry_run": false
  }
}
```

### 6. Get Cleanup Statistics

```bash
curl "http://localhost:8000/api/v1/admin/cleanup/stats"
```

Response:
```json
{
  "operation": "get_stats",
  "expired_images": 15,
  "temporary_images": 45,
  "old_task_results_30d": 42,
  "last_checked": "2025-11-01T10:00:00"
}
```

## Cleanup Logic

### Expired Images Cleanup

```python
# Criteria for deletion:
- storage_type = 'temporary'
- expires_at < now()
- NOT used by active tasks (pending/processing)

# If image is used by active task -> skip
active_tasks = db.query(FaceSwapTask).filter(
    status.in_(['pending', 'processing']),
    (husband_photo_id == image.id OR wife_photo_id == image.id)
).count()

if active_tasks > 0:
    skip deletion
```

### Session Cleanup

```python
# Criteria:
- session_id = specified_session
- NOT used by active tasks

# Cleans ALL images for a session regardless of expiration
```

### Old Results Cleanup

```python
# Criteria:
- status in ['completed', 'failed']
- completed_at < (now - days_old)
- result_image_id is not None

# Process:
1. Delete result image file
2. Delete result image record
3. Set task.result_image_id = None
4. Keep task record for history
```

### Orphaned Files Cleanup

```python
# Process:
1. Get all storage_path values from database
2. Scan all files in storage directories
3. If file not in database paths -> delete

# Categories scanned:
- photos/
- templates/
- preprocessed/
- results/
```

## Dry Run Mode

All cleanup operations support dry-run mode:

```bash
# Preview without deleting
?dry_run=true

# Actual cleanup
?dry_run=false  (default)
```

Dry run mode:
- Reports what would be deleted
- Does NOT delete files or database records
- Useful for verification before cleanup
- Returns same statistics structure

## Safety Features

### 1. Active Task Protection

Images used by pending or processing tasks are never deleted:

```python
# Check before deletion
if task.status in ['pending', 'processing']:
    skip deletion
```

### 2. Error Isolation

Cleanup continues even if individual operations fail:

```python
for image in images:
    try:
        delete_image(image)
    except Exception as e:
        log_error(e)
        errors.append({"image_id": image.id, "error": str(e)})
        continue  # Continue with next image
```

### 3. Transaction Safety

Database operations use transactions:

```python
try:
    db.delete(image)
    db.commit()
except:
    db.rollback()
    raise
```

### 4. Physical File Verification

Check file exists before deletion:

```python
if Path(file_path).exists():
    Path(file_path).unlink()
```

## Scheduled Cleanup (Production)

For production deployment, set up scheduled cleanup:

### Using Cron

```bash
# /etc/cron.d/faceswap-cleanup

# Daily cleanup at 2 AM
0 2 * * * curl -X POST "http://localhost:8000/api/v1/admin/cleanup/all?days_old=30&dry_run=false"

# Weekly orphaned files cleanup (Sundays at 3 AM)
0 3 * * 0 curl -X POST "http://localhost:8000/api/v1/admin/cleanup/orphaned?dry_run=false"
```

### Using Celery Beat

```python
# celeryconfig.py

from celery.schedules import crontab

beat_schedule = {
    'cleanup-expired-images': {
        'task': 'app.tasks.cleanup.cleanup_expired',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    'cleanup-old-results': {
        'task': 'app.tasks.cleanup.cleanup_old_results',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),  # Sundays at 3 AM
    },
}
```

### Using APScheduler

```python
from apscheduler.schedulers.background import BackgroundScheduler
from app.services.cleanup import CleanupService

scheduler = BackgroundScheduler()

def scheduled_cleanup():
    db = SessionLocal()
    try:
        result = CleanupService.cleanup_all(db, days_old=30, dry_run=False)
        logger.info(f"Scheduled cleanup: {result['totals']}")
    finally:
        db.close()

# Schedule daily at 2 AM
scheduler.add_job(
    scheduled_cleanup,
    'cron',
    hour=2,
    minute=0
)

scheduler.start()
```

## Testing

Run the test suite:

```bash
# From project root
./scripts/test_checkpoint_1_5_5.sh
```

Test coverage:
- ✅ Expired images cleanup (dry run and real)
- ✅ Session-based cleanup
- ✅ Old task results cleanup
- ✅ Orphaned files cleanup
- ✅ Full cleanup operation
- ✅ Cleanup statistics
- ✅ Active task protection
- ✅ Error handling
- ✅ Input validation

Test file: `backend/tests/test_phase_1_5_checkpoint_5.py`

## Performance Considerations

### MVP Implementation

Current implementation:
- Synchronous cleanup operations
- Sequential file processing
- In-memory file scanning

### Production Optimizations

1. **Batch Processing**
   ```python
   # Process in batches to avoid memory issues
   batch_size = 1000
   for i in range(0, total_count, batch_size):
       batch = query.offset(i).limit(batch_size).all()
       process_batch(batch)
   ```

2. **Async Processing**
   ```python
   # Use background tasks for large cleanups
   from app.tasks import cleanup_expired_async
   cleanup_expired_async.delay()
   ```

3. **Parallel File Scanning**
   ```python
   from concurrent.futures import ThreadPoolExecutor

   with ThreadPoolExecutor(max_workers=4) as executor:
       futures = [executor.submit(scan_category, cat) for cat in categories]
       results = [f.result() for f in futures]
   ```

4. **Progress Tracking**
   ```python
   # For large cleanup operations
   total = count_cleanable_items()
   processed = 0

   for item in items:
       cleanup_item(item)
       processed += 1

       if processed % 100 == 0:
           logger.info(f"Progress: {processed}/{total}")
   ```

## Monitoring

### Cleanup Metrics to Track

1. **Deletion Counts**
   - Expired images per cleanup
   - Old results per cleanup
   - Orphaned files found

2. **Storage Saved**
   - Bytes deleted per operation
   - Total storage freed
   - Storage growth rate

3. **Error Rates**
   - Failed deletions
   - File access errors
   - Database errors

4. **Performance**
   - Cleanup duration
   - Files processed per second
   - Database query time

### Example Logging

```python
logger.info(
    "Cleanup completed",
    extra={
        "operation": "cleanup_all",
        "deleted_count": 60,
        "deleted_mb": 56.0,
        "duration_seconds": 12.5,
        "errors": 0
    }
)
```

## Error Handling

### Common Errors

1. **File Not Found**
   ```
   Error: [Errno 2] No such file or directory
   Solution: File already deleted or moved
   Action: Log and continue (cleanup successful)
   ```

2. **Permission Denied**
   ```
   Error: [Errno 13] Permission denied
   Solution: Insufficient file system permissions
   Action: Check storage directory permissions
   ```

3. **Database Locked**
   ```
   Error: database is locked
   Solution: Another operation in progress
   Action: Retry or schedule cleanup for later
   ```

4. **Foreign Key Constraint**
   ```
   Error: foreign key constraint fails
   Solution: Image still referenced by active task
   Action: Skip deletion (protected by active task check)
   ```

### Error Response Format

```json
{
  "operation": "cleanup_expired_images",
  "deleted_count": 10,
  "deleted_size_mb": 5.0,
  "errors": [
    {
      "image_id": 123,
      "filename": "photo.jpg",
      "error": "Permission denied"
    }
  ],
  "dry_run": false
}
```

## Integration with Phase 1.5

### Checkpoint 1.5.1: Separated Upload APIs
- Cleans temporary photos uploaded via `/photos/upload`
- Respects `storage_type` and `expires_at` fields
- Session-based cleanup for grouped uploads

### Checkpoint 1.5.2: Template Preprocessing
- Cleans preprocessed template images if needed
- Handles masked images in cleanup

### Checkpoint 1.5.3: Flexible Face Mapping
- Preserves images used by active face-swap tasks
- Safe cleanup even during processing

### Checkpoint 1.5.4: Batch Processing
- Can clean results from old batch operations
- Respects batch task statuses

## Best Practices

### 1. Always Use Dry Run First

```bash
# Preview before cleanup
curl -X POST ".../cleanup/all?dry_run=true"

# Review results, then run actual cleanup
curl -X POST ".../cleanup/all?dry_run=false"
```

### 2. Schedule During Low Traffic

- Run major cleanups during off-peak hours
- Avoid cleanup during high-load periods
- Monitor impact on system performance

### 3. Retain Results Appropriately

```bash
# Development: shorter retention (7 days)
?days_old=7

# Production: longer retention (60-90 days)
?days_old=60
```

### 4. Monitor Cleanup Operations

- Log all cleanup operations
- Track deletion metrics
- Alert on high error rates
- Review cleanup stats regularly

### 5. Backup Before Major Cleanup

```bash
# Backup database before cleanup
pg_dump faceswap > backup_before_cleanup.sql

# Run cleanup
curl -X POST ".../cleanup/all"

# Verify results
curl ".../cleanup/stats"
```

## Security Considerations

### 1. Access Control

Cleanup endpoints should be admin-only:

```python
from app.core.security import require_admin

@router.post("/cleanup/all")
@require_admin
async def cleanup_all(...):
    # Only accessible by admins
```

### 2. Rate Limiting

Prevent abuse of cleanup endpoints:

```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@router.post("/cleanup/all")
@limiter.limit("5/hour")  # Max 5 cleanups per hour
async def cleanup_all(...):
    ...
```

### 3. Audit Logging

Log all cleanup operations:

```python
logger.info(
    f"Cleanup initiated by user {user_id}",
    extra={
        "user_id": user_id,
        "operation": "cleanup_all",
        "dry_run": dry_run
    }
)
```

## Files Modified/Created

### New Files
- `backend/app/services/cleanup.py` - Cleanup service
- `backend/app/api/v1/cleanup.py` - Cleanup API endpoints
- `backend/tests/test_phase_1_5_checkpoint_5.py` - Test suite
- `scripts/test_checkpoint_1_5_5.sh` - Test script
- `docs/CHECKPOINT-1.5.5-COMPLETE.md` - This file

### Modified Files
- `backend/app/api/v1/__init__.py` - Added cleanup router

## Verification

To verify Checkpoint 1.5.5 is complete:

1. ✅ CleanupService implemented
2. ✅ All 6 cleanup endpoints working
3. ✅ Dry-run mode functional
4. ✅ Active task protection working
5. ✅ Error handling robust
6. ✅ All tests passing

Check with:
```bash
./scripts/test_checkpoint_1_5_5.sh
```

Expected output:
```
✅ All Checkpoint 1.5.5 tests passed!

🎉 PHASE 1.5 COMPLETE! 🎉

All Phase 1.5 checkpoints are now complete:
  ✅ Checkpoint 1.5.1: Separated Upload APIs
  ✅ Checkpoint 1.5.2: Template Preprocessing
  ✅ Checkpoint 1.5.3: Flexible Face Mapping
  ✅ Checkpoint 1.5.4: Batch Processing
  ✅ Checkpoint 1.5.5: Auto Cleanup
```

## Summary

Checkpoint 1.5.5 provides comprehensive automatic cleanup:
- ✅ Expired temporary images
- ✅ Session-based cleanup
- ✅ Old task results
- ✅ Orphaned files
- ✅ Full cleanup operation
- ✅ Cleanup statistics
- ✅ Dry-run mode
- ✅ Active task protection

**Phase 1.5 MVP Enhanced Features are now complete and ready for production!**
