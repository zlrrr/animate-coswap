# API Documentation - Phase 1

## Overview

The Couple Face-Swap API provides endpoints for:
- Uploading images (source photos and templates)
- Managing templates
- Creating and monitoring face-swap tasks
- Retrieving results

Base URL: `http://localhost:8000`

API Version: `v1`

## Authentication

Phase 1 (MVP): No authentication required

Phase 3+: JWT-based authentication will be implemented

## Endpoints

### Health and Status

#### GET /

Root endpoint - returns API information

**Response:**
```json
{
  "name": "Couple Face-Swap API",
  "version": "0.1.0",
  "status": "running",
  "docs": "/docs",
  "api": "/api/v1"
}
```

#### GET /health

Health check endpoint

**Response:**
```json
{
  "status": "healthy",
  "database": "healthy",
  "model": "available",
  "storage": "local"
}
```

### Image Management

#### POST /api/v1/faceswap/upload-image

Upload an image file

**Request:**
- Content-Type: `multipart/form-data`
- Parameters:
  - `file` (required): Image file
  - `image_type` (required): One of `source`, `template`, `result`

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/faceswap/upload-image?image_type=source" \
  -F "file=@photo.jpg"
```

**Response:** `200 OK`
```json
{
  "image_id": 1,
  "filename": "photo.jpg",
  "storage_path": "source/source_20240101_123456_abc123.jpg",
  "file_size": 524288,
  "width": 1920,
  "height": 1080
}
```

**Errors:**
- `400 Bad Request`: Invalid file or file type
- `422 Unprocessable Entity`: Invalid parameters

### Template Management

#### POST /api/v1/faceswap/templates

Create a new template from an uploaded image

**Request:**
```json
{
  "image_id": 1,
  "title": "Romantic Movie Scene",
  "description": "A couple embracing",
  "artist": "Artist Name",
  "source_url": "https://example.com/original"
}
```

**Response:** `201 Created`
```json
{
  "template_id": 1,
  "title": "Romantic Movie Scene",
  "face_count": 2,
  "image_url": "/storage/templates/template_001.jpg"
}
```

#### GET /api/v1/faceswap/templates

List available templates

**Query Parameters:**
- `category` (optional): Filter by category (`acg`, `movie`, `tv`, `custom`, `all`)
- `limit` (optional): Number of results (1-100, default: 20)
- `offset` (optional): Pagination offset (default: 0)

**Example:**
```bash
curl "http://localhost:8000/api/v1/faceswap/templates?category=acg&limit=10"
```

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "title": "Anime Couple 1",
    "image_url": "/storage/templates/template_001.jpg",
    "category": "acg",
    "face_count": 2,
    "popularity_score": 150
  },
  {
    "id": 2,
    "title": "Movie Scene",
    "image_url": "/storage/templates/template_002.jpg",
    "category": "movie",
    "face_count": 2,
    "popularity_score": 89
  }
]
```

### Face-Swap Operations

#### POST /api/v1/faceswap/swap-faces

Create a face-swap task

**Request:**
```json
{
  "husband_image_id": 1,
  "wife_image_id": 2,
  "template_id": 3
}
```

**Response:** `202 Accepted`
```json
{
  "task_id": 123,
  "status": "pending",
  "created_at": "2024-01-01T12:34:56.789Z"
}
```

**Errors:**
- `404 Not Found`: One or more images/template not found
- `422 Unprocessable Entity`: Invalid request format

#### GET /api/v1/faceswap/task/{task_id}

Get face-swap task status

**Response:** `200 OK`
```json
{
  "task_id": 123,
  "status": "completed",
  "progress": 100,
  "result_image_url": "/storage/results/result_task_123.jpg",
  "processing_time": 4.52,
  "error_message": null,
  "created_at": "2024-01-01T12:34:56.789Z",
  "completed_at": "2024-01-01T12:35:01.309Z"
}
```

**Task Statuses:**
- `pending`: Task queued, not yet started
- `processing`: Face-swap in progress
- `completed`: Successfully completed
- `failed`: Processing failed (see `error_message`)

**Errors:**
- `404 Not Found`: Task ID not found

## Data Models

### ImageUploadResponse

```typescript
{
  image_id: number
  filename: string
  storage_path: string
  file_size: number
  width: number
  height: number
}
```

### TemplateListItem

```typescript
{
  id: number
  title: string
  image_url: string
  category: string
  face_count: number
  popularity_score: number
}
```

### FaceSwapRequest

```typescript
{
  husband_image_id: number
  wife_image_id: number
  template_id: number
}
```

### TaskStatusResponse

```typescript
{
  task_id: number
  status: "pending" | "processing" | "completed" | "failed"
  progress: number  // 0-100
  result_image_url?: string
  processing_time?: number
  error_message?: string
  created_at: string  // ISO 8601
  completed_at?: string  // ISO 8601
}
```

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

Common HTTP status codes:
- `400 Bad Request`: Invalid input
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

## Rate Limiting

Phase 1 (MVP): No rate limiting

Phase 3+: Rate limiting will be implemented

## File Storage

### Supported Formats

- **Image formats**: JPEG, PNG
- **Max file size**: 10MB (configurable)
- **Max dimensions**: 4096x4096 pixels

### Storage Structure

```
storage/
├── source/         # User-uploaded photos
├── templates/      # Template images
├── results/        # Face-swap results
└── temp/           # Temporary files
```

## Examples

### Complete Workflow Example

```bash
# 1. Upload husband's photo
HUSBAND_RESPONSE=$(curl -X POST \
  "http://localhost:8000/api/v1/faceswap/upload-image?image_type=source" \
  -F "file=@husband.jpg")
HUSBAND_ID=$(echo $HUSBAND_RESPONSE | jq -r '.image_id')

# 2. Upload wife's photo
WIFE_RESPONSE=$(curl -X POST \
  "http://localhost:8000/api/v1/faceswap/upload-image?image_type=source" \
  -F "file=@wife.jpg")
WIFE_ID=$(echo $WIFE_RESPONSE | jq -r '.image_id')

# 3. Get a template
TEMPLATE_RESPONSE=$(curl "http://localhost:8000/api/v1/faceswap/templates?limit=1")
TEMPLATE_ID=$(echo $TEMPLATE_RESPONSE | jq -r '.[0].id')

# 4. Create face-swap task
TASK_RESPONSE=$(curl -X POST \
  "http://localhost:8000/api/v1/faceswap/swap-faces" \
  -H "Content-Type: application/json" \
  -d "{
    \"husband_image_id\": $HUSBAND_ID,
    \"wife_image_id\": $WIFE_ID,
    \"template_id\": $TEMPLATE_ID
  }")
TASK_ID=$(echo $TASK_RESPONSE | jq -r '.task_id')

# 5. Poll for completion
while true; do
  STATUS_RESPONSE=$(curl "http://localhost:8000/api/v1/faceswap/task/$TASK_ID")
  STATUS=$(echo $STATUS_RESPONSE | jq -r '.status')

  if [ "$STATUS" == "completed" ]; then
    RESULT_URL=$(echo $STATUS_RESPONSE | jq -r '.result_image_url')
    echo "Completed! Result: http://localhost:8000$RESULT_URL"
    break
  elif [ "$STATUS" == "failed" ]; then
    ERROR=$(echo $STATUS_RESPONSE | jq -r '.error_message')
    echo "Failed: $ERROR"
    break
  fi

  echo "Status: $STATUS"
  sleep 2
done
```

### Python Example

```python
import requests
import time

BASE_URL = "http://localhost:8000"

# Upload images
with open("husband.jpg", "rb") as f:
    response = requests.post(
        f"{BASE_URL}/api/v1/faceswap/upload-image",
        files={"file": f},
        params={"image_type": "source"}
    )
    husband_id = response.json()["image_id"]

with open("wife.jpg", "rb") as f:
    response = requests.post(
        f"{BASE_URL}/api/v1/faceswap/upload-image",
        files={"file": f},
        params={"image_type": "source"}
    )
    wife_id = response.json()["image_id"]

# Get template
response = requests.get(f"{BASE_URL}/api/v1/faceswap/templates", params={"limit": 1})
template_id = response.json()[0]["id"]

# Create task
response = requests.post(
    f"{BASE_URL}/api/v1/faceswap/swap-faces",
    json={
        "husband_image_id": husband_id,
        "wife_image_id": wife_id,
        "template_id": template_id
    }
)
task_id = response.json()["task_id"]

# Poll for completion
while True:
    response = requests.get(f"{BASE_URL}/api/v1/faceswap/task/{task_id}")
    task = response.json()

    print(f"Status: {task['status']} - Progress: {task['progress']}%")

    if task["status"] == "completed":
        print(f"Result: {BASE_URL}{task['result_image_url']}")
        break
    elif task["status"] == "failed":
        print(f"Error: {task['error_message']}")
        break

    time.sleep(2)
```

## OpenAPI/Swagger

Interactive API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/api/v1/openapi.json

## Changelog

### v0.1.0 (Phase 1.1 - MVP Backend Core)
- Image upload endpoint
- Template management endpoints
- Face-swap task creation and status
- Background task processing
- SQLite/PostgreSQL database support
- Local file storage
