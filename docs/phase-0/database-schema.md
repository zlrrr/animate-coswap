# Database Schema Design

## Overview
This document describes the database schema for the Couple Face-Swap application.

## Core Tables (MVP)

### users
Stores user account information.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique user ID |
| email | VARCHAR(255) | UNIQUE, NOT NULL | User email address |
| username | VARCHAR(100) | UNIQUE, NOT NULL | Display username |
| password_hash | VARCHAR(255) | NOT NULL | Hashed password |
| created_at | TIMESTAMP | DEFAULT NOW() | Account creation time |

### images
Stores metadata for all images (source photos, templates, results).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique image ID |
| user_id | INTEGER | REFERENCES users(id) | Image owner (nullable for templates) |
| filename | VARCHAR(255) | NOT NULL | Original filename |
| storage_path | VARCHAR(500) | NOT NULL | Path in storage system |
| file_size | INTEGER | | File size in bytes |
| width | INTEGER | | Image width in pixels |
| height | INTEGER | | Image height in pixels |
| image_type | VARCHAR(20) | | 'source', 'template', or 'result' |
| category | VARCHAR(50) | | 'acg', 'movie', 'tv', 'custom' |
| tags | TEXT[] | | Array of tags |
| uploaded_at | TIMESTAMP | DEFAULT NOW() | Upload timestamp |
| metadata | JSONB | | Flexible metadata storage |

### templates
Couple image templates for face swapping.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique template ID |
| image_id | INTEGER | REFERENCES images(id) | Associated image |
| title | VARCHAR(255) | NOT NULL | Template title |
| description | TEXT | | Template description |
| artist | VARCHAR(255) | | Artist name |
| source_url | VARCHAR(500) | | Original source URL |
| face_count | INTEGER | DEFAULT 2 | Number of faces detected |
| face_positions | JSONB | | Face bounding boxes |
| popularity_score | INTEGER | DEFAULT 0 | Usage popularity |
| is_active | BOOLEAN | DEFAULT TRUE | Active/archived status |
| created_at | TIMESTAMP | DEFAULT NOW() | Creation timestamp |

### faceswap_tasks
Face-swap processing tasks and their status.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique task ID |
| user_id | INTEGER | REFERENCES users(id) | Task owner |
| template_id | INTEGER | REFERENCES templates(id) | Selected template |
| husband_image_id | INTEGER | REFERENCES images(id) | Husband's photo |
| wife_image_id | INTEGER | REFERENCES images(id) | Wife's photo |
| result_image_id | INTEGER | REFERENCES images(id) | Result image (after completion) |
| status | VARCHAR(20) | DEFAULT 'pending' | 'pending', 'processing', 'completed', 'failed' |
| progress | INTEGER | DEFAULT 0 | Progress percentage (0-100) |
| error_message | TEXT | | Error details (if failed) |
| processing_time | FLOAT | | Time taken in seconds |
| started_at | TIMESTAMP | | Processing start time |
| completed_at | TIMESTAMP | | Processing completion time |
| created_at | TIMESTAMP | DEFAULT NOW() | Task creation time |

## Post-MVP Tables (Phase 3+)

### crawl_tasks
Image collection/crawling tasks.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique task ID |
| source_type | VARCHAR(50) | | 'pixiv', 'danbooru', 'custom' |
| search_query | TEXT | | Search keywords |
| filters | JSONB | | Filter criteria |
| status | VARCHAR(20) | DEFAULT 'pending' | Task status |
| images_collected | INTEGER | DEFAULT 0 | Number of images collected |
| created_at | TIMESTAMP | DEFAULT NOW() | Task creation time |

## Indexes

```sql
-- Performance indexes
CREATE INDEX idx_images_user ON images(user_id);
CREATE INDEX idx_images_type ON images(image_type);
CREATE INDEX idx_templates_category ON templates(category);
CREATE INDEX idx_tasks_status ON faceswap_tasks(status);
CREATE INDEX idx_tasks_user ON faceswap_tasks(user_id);
```

## Schema Creation SQL

```sql
-- Create database
CREATE DATABASE faceswap;

-- Connect to database
\c faceswap

-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Images table
CREATE TABLE images (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    filename VARCHAR(255) NOT NULL,
    storage_path VARCHAR(500) NOT NULL,
    file_size INTEGER,
    width INTEGER,
    height INTEGER,
    image_type VARCHAR(20),
    category VARCHAR(50),
    tags TEXT[],
    uploaded_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB
);

-- Templates table
CREATE TABLE templates (
    id SERIAL PRIMARY KEY,
    image_id INTEGER REFERENCES images(id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    artist VARCHAR(255),
    source_url VARCHAR(500),
    face_count INTEGER DEFAULT 2,
    face_positions JSONB,
    popularity_score INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Face-swap tasks table
CREATE TABLE faceswap_tasks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    template_id INTEGER REFERENCES templates(id),
    husband_image_id INTEGER REFERENCES images(id),
    wife_image_id INTEGER REFERENCES images(id),
    result_image_id INTEGER REFERENCES images(id),
    status VARCHAR(20) DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    error_message TEXT,
    processing_time FLOAT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Crawl tasks table (Phase 3+)
CREATE TABLE crawl_tasks (
    id SERIAL PRIMARY KEY,
    source_type VARCHAR(50),
    search_query TEXT,
    filters JSONB,
    status VARCHAR(20) DEFAULT 'pending',
    images_collected INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_images_user ON images(user_id);
CREATE INDEX idx_images_type ON images(image_type);
CREATE INDEX idx_templates_category ON templates(category);
CREATE INDEX idx_tasks_status ON faceswap_tasks(status);
CREATE INDEX idx_tasks_user ON faceswap_tasks(user_id);
```

## Relationships

```
users (1) ----< (*) images
users (1) ----< (*) faceswap_tasks
images (1) ----< (1) templates
templates (1) ----< (*) faceswap_tasks
images (1) ----< (*) faceswap_tasks [husband_image_id]
images (1) ----< (*) faceswap_tasks [wife_image_id]
images (1) ----< (*) faceswap_tasks [result_image_id]
```

## Data Flow

1. **User uploads photos**: Creates `images` records with type='source'
2. **Admin/system adds templates**: Creates `images` + `templates` records
3. **User selects template and submits**: Creates `faceswap_tasks` record with status='pending'
4. **Background worker processes**: Updates task status to 'processing', then 'completed'
5. **Result saved**: Creates new `images` record with type='result', updates task.result_image_id

## Storage Strategy

- **Database**: Metadata and relationships only
- **File Storage**: Actual image files stored in filesystem or S3
- **Path Format**: `{storage_type}/{category}/{year}/{month}/{filename}`
  - Example: `local/source/2024/01/user123_photo1.jpg`
  - Example: `s3/templates/acg/template_001.png`

## Migration Strategy

Using Alembic for database migrations:

```bash
# Initialize Alembic
alembic init alembic

# Create initial migration
alembic revision --autogenerate -m "Initial schema"

# Apply migration
alembic upgrade head
```
