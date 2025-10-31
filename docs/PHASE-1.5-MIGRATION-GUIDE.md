# Phase 1.5 Database Migration Guide

## Overview

This guide explains how to apply the Phase 1.5 database migration that creates the complete schema with all enhanced MVP features.

## What's Included in Phase 1.5 Migration

### New Tables
- **template_preprocessing**: Stores face detection, gender classification, and masking data
- **batch_tasks**: Manages batch processing of multiple templates

### Enhanced Tables

#### Images Table (Phase 1.5 Additions)
- `storage_type`: 'permanent' or 'temporary'
- `expires_at`: Auto-cleanup timestamp
- `session_id`: Group temporary photos

#### Templates Table (Phase 1.5 Additions)
- `name`: Renamed from 'title'
- `original_image_id`: Renamed from 'image_id'
- `is_preprocessed`: Preprocessing completion status
- `male_face_count`: Number of male faces detected
- `female_face_count`: Number of female faces detected
- `updated_at`: Track template modifications

#### FaceSwap Tasks Table (Phase 1.5 Additions)
- `task_id`: Unique task identifier
- `batch_id`: Link to batch processing
- `husband_photo_id`: Renamed from 'husband_image_id'
- `wife_photo_id`: Renamed from 'wife_image_id'
- `face_mappings`: Custom face mapping configuration
- `use_preprocessed`: Whether to use preprocessed templates

## Prerequisites

Before applying the migration, ensure:

1. ✅ Docker Desktop is running
2. ✅ PostgreSQL container is up
3. ✅ Redis container is up
4. ✅ `.env` file exists in `backend/` directory
5. ✅ Python virtual environment is activated

## Quick Start (Automated)

### Option 1: One-Command Setup

```bash
cd ~/develop/project/animate-coswap

# Pull latest changes
git pull origin claude/implement-plan-steps-011CUWofAJKPWXPtKKeXEhGH

# Run automated migration script
./scripts/apply_phase_1_5_migration.sh
```

This script will:
- ✅ Check all prerequisites
- ✅ Start Docker services if needed
- ✅ Create `.env` file if missing
- ✅ Apply Phase 1.5 migration
- ✅ Verify all tables and columns
- ✅ Show success confirmation

### Option 2: Verify Existing Schema

If you want to verify your current database schema matches Phase 1.5:

```bash
cd backend
python ../scripts/verify_phase_1_5_schema.py
```

This will check:
- All required tables exist
- All Phase 1.5 columns are present
- Indexes are created correctly
- Foreign keys are set up
- Alembic revision is correct

## Manual Migration Steps

If you prefer to run migration steps manually:

### Step 1: Start Docker Services

```bash
cd ~/develop/project/animate-coswap

# Start PostgreSQL and Redis
docker compose up -d postgres redis

# Wait for services to be ready
sleep 5

# Verify PostgreSQL is ready
docker exec faceswap_postgres pg_isready -U faceswap_user
# Should output: ready

# Verify Redis is ready
docker exec faceswap_redis redis-cli ping
# Should output: PONG
```

### Step 2: Set Up Environment

```bash
# Create .env file if it doesn't exist
if [ ! -f backend/.env ]; then
    cp backend/.env.example backend/.env
fi

# Activate virtual environment
source venv/bin/activate

# Install/update requirements
cd backend
pip install -r requirements.txt
```

### Step 3: Check Current Migration Status

```bash
# Check if database has existing migrations
docker exec faceswap_postgres psql -U faceswap_user -d faceswap -c "\dt"

# Check Alembic current revision
alembic current
```

### Step 4: Apply Migration

```bash
# Apply the Phase 1.5 migration
alembic upgrade head
```

You should see output like:
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 00f2e8fecd91, Initial schema with Phase 1.5 features
Creating users table...
Creating images table...
Creating templates table...
Creating template_preprocessing table...
Creating batch_tasks table...
Creating faceswap_tasks table...
Creating crawl_tasks table...
✅ All tables created successfully with Phase 1.5 features!
INFO  [alembic.runtime.migration] Upgrade complete.
```

### Step 5: Verify Migration

```bash
# Check tables were created
docker exec faceswap_postgres psql -U faceswap_user -d faceswap -c "\dt"

# Run verification script
cd ..
python scripts/verify_phase_1_5_schema.py
```

Expected output:
```
============================================================
  Phase 1.5 Database Schema Verification
============================================================

✅ Connected to database

============================================================
  1. Checking Tables
============================================================
✅ Table exists: users
✅ Table exists: images
✅ Table exists: templates
✅ Table exists: template_preprocessing
✅ Table exists: batch_tasks
✅ Table exists: faceswap_tasks
✅ Table exists: crawl_tasks
✅ Table exists: alembic_version

[... more checks ...]

============================================================
  Verification Summary
============================================================
✅ All Phase 1.5 schema checks passed!

📋 Database is ready for Phase 1.5 development
```

## Troubleshooting

### Issue 1: "Database already has migration history"

If you see this error, it means your database has existing migrations that don't match the Phase 1.5 schema.

**Solution A: Fresh Start (Recommended for Development)**

⚠️ **WARNING: This will delete all data!**

```bash
# Reset database
docker exec faceswap_postgres psql -U faceswap_user -d faceswap -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'

# Rerun migration script
./scripts/apply_phase_1_5_migration.sh
```

**Solution B: Keep Existing Data (Advanced)**

If you have existing data you want to preserve:

1. Backup your database:
   ```bash
   docker exec faceswap_postgres pg_dump -U faceswap_user faceswap > backup.sql
   ```

2. Check your current schema:
   ```bash
   docker exec faceswap_postgres psql -U faceswap_user -d faceswap -c "\d images"
   docker exec faceswap_postgres psql -U faceswap_user -d faceswap -c "\d templates"
   ```

3. Contact the development team to create a custom migration

### Issue 2: "relation 'images' already exists"

This means tables exist but Alembic doesn't know about them.

**Solution:**

```bash
cd backend

# Stamp database with current revision
alembic stamp 00f2e8fecd91

# Verify
alembic current
```

### Issue 3: Migration fails with "NOT NULL constraint"

If the migration fails with NOT NULL constraint errors, check if you have existing data that doesn't match the new schema.

**Solution:**

```bash
# Check for existing data
docker exec faceswap_postgres psql -U faceswap_user -d faceswap -c "SELECT COUNT(*) FROM faceswap_tasks;"

# If you have data, back it up first
docker exec faceswap_postgres pg_dump -U faceswap_user faceswap > backup.sql

# Then reset and reapply
docker exec faceswap_postgres psql -U faceswap_user -d faceswap -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'
./scripts/apply_phase_1_5_migration.sh
```

### Issue 4: "Module 'alembic' not found"

**Solution:**

```bash
# Activate virtual environment
source venv/bin/activate

# Install requirements
cd backend
pip install -r requirements.txt

# Verify
python -c "import alembic; print(alembic.__version__)"
```

### Issue 5: Docker services not running

**Solution:**

```bash
# Check Docker is installed
docker --version

# Start Docker Desktop (macOS)
open -a Docker

# Wait for Docker to start
sleep 10

# Start services
docker compose up -d postgres redis

# Verify
docker compose ps
```

## Verification Checklist

After migration, verify the following:

### Database Tables
- [ ] `users` table exists
- [ ] `images` table exists with Phase 1.5 columns
- [ ] `templates` table exists with Phase 1.5 columns
- [ ] `template_preprocessing` table exists (NEW)
- [ ] `batch_tasks` table exists (NEW)
- [ ] `faceswap_tasks` table exists with Phase 1.5 columns
- [ ] `crawl_tasks` table exists
- [ ] `alembic_version` table shows revision `00f2e8fecd91`

### Phase 1.5 Features
- [ ] Images table has `storage_type`, `expires_at`, `session_id`
- [ ] Templates table has `is_preprocessed`, `male_face_count`, `female_face_count`
- [ ] Templates table uses `name` instead of `title`
- [ ] Templates table uses `original_image_id` instead of `image_id`
- [ ] FaceSwap tasks has `task_id`, `batch_id`, `face_mappings`, `use_preprocessed`
- [ ] FaceSwap tasks uses `husband_photo_id` and `wife_photo_id`

### Indexes
- [ ] `ix_images_storage_type` exists
- [ ] `ix_images_session` exists
- [ ] `ix_preprocessing_status` exists
- [ ] `ix_batch_status` exists
- [ ] `ix_tasks_batch` exists

### Foreign Keys
- [ ] template_preprocessing → templates
- [ ] template_preprocessing → images
- [ ] batch_tasks → users, images
- [ ] faceswap_tasks → batch_tasks, templates, images, users

## Next Steps After Migration

Once migration is complete, you can start implementing Phase 1.5 features:

### Checkpoint 1.5.1: Separated Upload APIs (2-3 hours)
```bash
# Start implementing
cd backend/app/api/v1/endpoints
# Create/update upload endpoints
```

See: `docs/PHASE-1.5-QUICK-REFERENCE.md` for implementation details

### Checkpoint 1.5.2: Template Preprocessing (4-5 hours)
```bash
# Implement preprocessing service
cd backend/app/services
# Add face detection, gender classification, masking
```

See: `docs/PHASE-1.5-IMPLEMENTATION-GUIDE.md` for code examples

### Run Tests
```bash
# Create tests for new features
cd backend
pytest tests/test_phase_1_5/ -v

# Run all tests
pytest tests/ -v --cov=app
```

## Migration Files Reference

### Main Migration File
- **Location**: `backend/alembic/versions/00f2e8fecd91_initial_schema_with_phase_1_5.py`
- **Revision ID**: `00f2e8fecd91`
- **Down Revision**: `None` (initial migration)
- **Purpose**: Creates complete schema with Phase 1.5 features

### Helper Scripts
- **apply_phase_1_5_migration.sh**: Automated migration application
- **verify_phase_1_5_schema.py**: Schema verification script

### Documentation
- **PHASE-1.5-QUICK-REFERENCE.md**: Quick start guide
- **PHASE-1.5-IMPLEMENTATION-GUIDE.md**: Detailed implementation guide
- **PLAN-PHASE-1.5.md**: Complete phase plan with checkpoints

## Database Schema Diagram

```
┌─────────────┐
│   Users     │
└──────┬──────┘
       │
       ├─────────────────────────┐
       │                         │
       ▼                         ▼
┌─────────────┐         ┌─────────────────┐
│   Images    │◄────────│  Batch Tasks    │
│             │         │                 │
│ Phase 1.5:  │         │ Phase 1.5: NEW  │
│ - storage_  │         │ - batch_id      │
│   type      │         │ - template_ids  │
│ - expires_  │         │ - total_tasks   │
│   at        │         │ - completed     │
│ - session_  │         └─────────────────┘
│   id        │                   │
└──────┬──────┘                   │
       │                          │
       ▼                          ▼
┌─────────────┐         ┌─────────────────┐
│  Templates  │◄────────│  FaceSwap       │
│             │         │  Tasks          │
│ Phase 1.5:  │         │                 │
│ - name      │         │ Phase 1.5:      │
│ - is_       │         │ - task_id       │
│   prepro-   │         │ - batch_id      │
│   cessed    │         │ - face_         │
│ - male_     │         │   mappings      │
│   face_     │         │ - use_          │
│   count     │         │   preprocessed  │
│ - female_   │         └─────────────────┘
│   face_     │
│   count     │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│ Template            │
│ Preprocessing       │
│                     │
│ Phase 1.5: NEW      │
│ - faces_detected    │
│ - face_data (JSON)  │
│ - masked_image_id   │
│ - preprocessing_    │
│   status            │
└─────────────────────┘
```

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Run the verification script: `python scripts/verify_phase_1_5_schema.py`
3. Check logs: `docker compose logs postgres`
4. Review Alembic history: `cd backend && alembic history`

## Summary

✅ **Migration Applied**: Database now has Phase 1.5 schema
✅ **Features Ready**: Template preprocessing, batch processing, flexible mapping
✅ **Next Step**: Begin implementing Phase 1.5 checkpoints

The database is now ready for Phase 1.5 development!
