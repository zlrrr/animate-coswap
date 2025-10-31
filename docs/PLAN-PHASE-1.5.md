# MVP Enhanced Requirements - Phase 1.5

## New Features for MVP

### 1. Separated Upload APIs
**Requirement:** Husband & Wife photos and templates use different upload endpoints

**Rationale:**
- Templates are permanent assets (stored in database)
- User photos are temporary (stored in temp directory, auto-deleted after processing)
- Different validation rules for each type
- Better separation of concerns

**Implementation:**
- `POST /api/v1/photos/upload` - Upload user photos (husband/wife)
- `POST /api/v1/templates/upload` - Upload templates
- `DELETE /api/v1/photos/{photo_id}` - Delete user photo
- `DELETE /api/v1/templates/{template_id}` - Delete template

**Storage Strategy:**
```
storage/
├── templates/           # Persistent storage
│   ├── originals/       # Original uploaded templates
│   └── preprocessed/    # Preprocessed templates (face-masked)
└── temp/                # Temporary storage (auto-cleanup)
    └── photos/          # User-uploaded husband/wife photos
        └── {session_id}/
            ├── husband.jpg
            └── wife.jpg
```

### 2. Template Preprocessing System ⭐ CRITICAL
**Requirement:** Templates must be preprocessed before use

**Preprocessing Pipeline:**
1. **Face Detection** - Detect all faces in template
2. **Gender Classification** - Identify male/female faces
3. **Face Masking** - Generate face-masked version
4. **Metadata Storage** - Store face positions, genders, mask paths

**Preprocessed Data Structure:**
```json
{
  "template_id": 123,
  "original_image_id": 456,
  "faces": [
    {
      "face_index": 0,
      "bbox": [x1, y1, x2, y2],
      "gender": "male",
      "confidence": 0.98,
      "landmarks": [[x1,y1], [x2,y2], ...],
      "position": "left"
    },
    {
      "face_index": 1,
      "bbox": [x3, y3, x4, y4],
      "gender": "female",
      "confidence": 0.96,
      "landmarks": [[x3,y3], [x4,y4], ...],
      "position": "right"
    }
  ],
  "preprocessed_images": [
    {
      "type": "face_masked",
      "image_id": 789,
      "path": "templates/preprocessed/template_123_masked.jpg",
      "description": "All faces masked"
    }
  ]
}
```

**Gallery Display:**
- Show original template image
- Show preprocessed (face-masked) images
- Display detected faces with gender labels
- Visual indicators for male/female faces

### 3. Flexible Face Mapping
**Requirement:** Support custom face mapping

**Default Mapping:**
- Husband photo → Male face in template
- Wife photo → Female face in template

**Custom Mapping:**
- Allow user to specify which source face maps to which template face
- Example: Husband photo face 0 → Template face 1 (female)

**API Design:**
```json
{
  "husband_photo_id": 1,
  "wife_photo_id": 2,
  "template_id": 3,
  "face_mappings": [
    {
      "source_photo": "husband",
      "source_face_index": 0,
      "target_face_index": 0
    },
    {
      "source_photo": "wife",
      "source_face_index": 0,
      "target_face_index": 1
    }
  ]
}
```

### 4. Batch Processing
**Requirement:** Select multiple templates for batch processing

**Features:**
- Select multiple templates at once
- Process same husband/wife photos with all selected templates
- Generate multiple results simultaneously
- Batch download results as ZIP file

**API Design:**
```json
POST /api/v1/faceswap/batch
{
  "husband_photo_id": 1,
  "wife_photo_id": 2,
  "template_ids": [3, 5, 7, 9],
  "use_default_mapping": true
}

Response:
{
  "batch_id": "batch_123",
  "tasks": [
    {"task_id": "task_1", "template_id": 3, "status": "pending"},
    {"task_id": "task_2", "template_id": 5, "status": "pending"},
    {"task_id": "task_3", "template_id": 7, "status": "pending"},
    {"task_id": "task_4", "template_id": 9, "status": "pending"}
  ]
}

GET /api/v1/faceswap/batch/{batch_id}/download
Returns: ZIP file with all results
```

### 5. Automatic Cleanup
**Requirement:** Auto-delete temporary photos after processing

**Cleanup Strategy:**
- Delete photos after successful batch processing
- Retain photos for 24 hours if processing fails
- Periodic cleanup job (Celery task)
- Manual cleanup option

---

## Updated Database Schema

### New/Modified Tables

```sql
-- Enhanced images table
CREATE TABLE images (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    filename VARCHAR(255) NOT NULL,
    storage_path VARCHAR(500) NOT NULL,
    file_size INTEGER,
    width INTEGER,
    height INTEGER,
    image_type VARCHAR(20), -- 'photo', 'template', 'preprocessed', 'result'
    storage_type VARCHAR(20), -- 'permanent', 'temporary'
    category VARCHAR(50),
    tags JSONB,
    uploaded_at TIMESTAMP DEFAULT NOW(),
    image_metadata JSONB,
    expires_at TIMESTAMP, -- For temporary images
    session_id VARCHAR(100) -- For grouping temp photos
);

-- Template preprocessing data
CREATE TABLE template_preprocessing (
    id SERIAL PRIMARY KEY,
    template_id INTEGER REFERENCES templates(id) UNIQUE,
    original_image_id INTEGER REFERENCES images(id),
    faces_detected INTEGER NOT NULL,
    face_data JSONB NOT NULL, -- Array of face info (bbox, gender, landmarks)
    masked_image_id INTEGER REFERENCES images(id),
    preprocessing_status VARCHAR(20), -- 'pending', 'completed', 'failed'
    error_message TEXT,
    processed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Enhanced templates table
CREATE TABLE templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(50),
    original_image_id INTEGER REFERENCES images(id),
    is_preprocessed BOOLEAN DEFAULT FALSE,
    face_count INTEGER DEFAULT 0,
    male_face_count INTEGER DEFAULT 0,
    female_face_count INTEGER DEFAULT 0,
    popularity_score INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Batch processing
CREATE TABLE batch_tasks (
    id SERIAL PRIMARY KEY,
    batch_id VARCHAR(100) UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users(id),
    husband_photo_id INTEGER REFERENCES images(id),
    wife_photo_id INTEGER REFERENCES images(id),
    template_ids INTEGER[], -- Array of template IDs
    status VARCHAR(20), -- 'pending', 'processing', 'completed', 'failed'
    total_tasks INTEGER,
    completed_tasks INTEGER DEFAULT 0,
    failed_tasks INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Enhanced faceswap_tasks
CREATE TABLE faceswap_tasks (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(100) UNIQUE NOT NULL,
    batch_id VARCHAR(100) REFERENCES batch_tasks(batch_id),
    user_id INTEGER REFERENCES users(id),
    template_id INTEGER REFERENCES templates(id),
    husband_photo_id INTEGER REFERENCES images(id),
    wife_photo_id INTEGER REFERENCES images(id),
    result_image_id INTEGER REFERENCES images(id),
    face_mappings JSONB, -- Custom face mapping config
    use_preprocessed BOOLEAN DEFAULT TRUE,
    status VARCHAR(20),
    progress INTEGER DEFAULT 0,
    error_message TEXT,
    processing_time FLOAT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_images_storage_type ON images(storage_type);
CREATE INDEX idx_images_expires_at ON images(expires_at);
CREATE INDEX idx_images_session ON images(session_id);
CREATE INDEX idx_preprocessing_status ON template_preprocessing(preprocessing_status);
CREATE INDEX idx_batch_status ON batch_tasks(status);
CREATE INDEX idx_tasks_batch ON faceswap_tasks(batch_id);
```

---

## Updated Phase Plan

### Phase 1.5 - Enhanced MVP Features
**Duration:** 5-7 days
**Prerequisites:** Phase 0 and Phase 1 completed

#### Checkpoint 1.5.1 - Separated Upload APIs
**Duration:** 1 day

**Tasks:**
1. Create photo upload endpoint (`POST /api/v1/photos/upload`)
2. Create template upload endpoint (`POST /api/v1/templates/upload`)
3. Implement storage separation (permanent vs temporary)
4. Add delete endpoints for both types
5. Update storage service to handle temp directory

**Test Cases:**
```python
def test_upload_user_photo():
    """Test uploading husband/wife photo to temp storage"""
    response = client.post("/api/v1/photos/upload", ...)
    assert response.json()["storage_type"] == "temporary"
    assert "session_id" in response.json()

def test_upload_template():
    """Test uploading template to permanent storage"""
    response = client.post("/api/v1/templates/upload", ...)
    assert response.json()["storage_type"] == "permanent"
    assert response.json()["is_preprocessed"] == False

def test_delete_photo():
    """Test deleting user photo"""
    response = client.delete(f"/api/v1/photos/{photo_id}")
    assert response.status_code == 200
```

**Acceptance Criteria:**
- [ ] Photos saved to temp directory with session_id
- [ ] Templates saved to permanent directory
- [ ] Delete endpoints work correctly
- [ ] All tests pass

#### Checkpoint 1.5.2 - Template Preprocessing
**Duration:** 2-3 days

**Tasks:**
1. Implement gender classification model integration
2. Create face masking algorithm
3. Build preprocessing pipeline
4. Store preprocessing results in database
5. Create preprocessing status endpoint

**Test Cases:**
```python
def test_template_preprocessing():
    """Test template preprocessing pipeline"""
    template = upload_template(...)
    result = preprocess_template(template.id)

    assert result["faces_detected"] == 2
    assert result["face_data"][0]["gender"] in ["male", "female"]
    assert result["masked_image_id"] is not None

def test_gender_classification():
    """Test gender classification accuracy"""
    male_face = detect_face("tests/fixtures/male_face.jpg")
    female_face = detect_face("tests/fixtures/female_face.jpg")

    assert classify_gender(male_face) == "male"
    assert classify_gender(female_face) == "female"

def test_face_masking():
    """Test face masking generation"""
    template = load_image("tests/fixtures/couple_template.jpg")
    masked = generate_face_mask(template, faces)

    assert masked is not None
    assert masked.shape == template.shape
```

**Acceptance Criteria:**
- [ ] Gender classification accuracy >= 90%
- [ ] Face masking produces clean results
- [ ] Preprocessing metadata stored correctly
- [ ] Gallery shows original + preprocessed images
- [ ] All tests pass

#### Checkpoint 1.5.3 - Flexible Face Mapping
**Duration:** 1 day

**Tasks:**
1. Update faceswap service to support custom mappings
2. Create face mapping validation
3. Update API to accept mapping configuration
4. Add default mapping logic

**Test Cases:**
```python
def test_default_face_mapping():
    """Test default mapping (husband->male, wife->female)"""
    result = swap_faces(
        husband_photo, wife_photo, template,
        use_default_mapping=True
    )
    assert result is not None

def test_custom_face_mapping():
    """Test custom face mapping"""
    mappings = [
        {"source_photo": "husband", "target_face": 1},
        {"source_photo": "wife", "target_face": 0}
    ]
    result = swap_faces(..., face_mappings=mappings)
    assert result is not None
```

**Acceptance Criteria:**
- [ ] Default mapping works correctly
- [ ] Custom mapping validated and applied
- [ ] Invalid mappings rejected with clear errors
- [ ] All tests pass

#### Checkpoint 1.5.4 - Batch Processing
**Duration:** 2 days

**Tasks:**
1. Create batch task management system
2. Implement batch processing endpoint
3. Create batch status tracking
4. Implement ZIP download for results
5. Add progress tracking

**Test Cases:**
```python
def test_batch_processing():
    """Test batch processing multiple templates"""
    response = client.post("/api/v1/faceswap/batch", json={
        "husband_photo_id": 1,
        "wife_photo_id": 2,
        "template_ids": [3, 4, 5]
    })

    batch_id = response.json()["batch_id"]
    assert len(response.json()["tasks"]) == 3

def test_batch_download():
    """Test downloading batch results as ZIP"""
    response = client.get(f"/api/v1/faceswap/batch/{batch_id}/download")
    assert response.headers["content-type"] == "application/zip"
    assert len(extract_zip(response.content)) == 3
```

**Acceptance Criteria:**
- [ ] Batch processing creates multiple tasks
- [ ] Progress tracking works correctly
- [ ] ZIP download includes all results
- [ ] Failed tasks don't block others
- [ ] All tests pass

#### Checkpoint 1.5.5 - Auto Cleanup
**Duration:** 1 day

**Tasks:**
1. Implement cleanup Celery task
2. Add expiration logic for temp files
3. Create manual cleanup endpoint
4. Add cleanup monitoring

**Test Cases:**
```python
def test_auto_cleanup():
    """Test automatic cleanup of expired photos"""
    photo = upload_photo(...)
    set_expiry(photo, hours=1)

    run_cleanup_task()

    assert photo_exists(photo.id) == True  # Not expired

    set_expiry(photo, hours=-1)  # Expired
    run_cleanup_task()

    assert photo_exists(photo.id) == False  # Cleaned up
```

**Acceptance Criteria:**
- [ ] Expired photos deleted automatically
- [ ] Cleanup runs periodically
- [ ] Storage space reclaimed
- [ ] All tests pass

---

## Testing Strategy

### Unit Tests
- Each service function tested independently
- Mock external dependencies
- Test edge cases and error conditions

### Integration Tests
- Test complete workflows end-to-end
- Test API endpoints with real database
- Test file upload/download

### Test Coverage Target
- Minimum 80% code coverage
- 100% coverage for critical paths (face swap, preprocessing)

### Test Execution
```bash
# Run all tests
pytest backend/tests/ -v

# Run specific phase tests
pytest backend/tests/test_phase_1_5/ -v

# Run with coverage
pytest backend/tests/ --cov=app --cov-report=html

# Run only MVP tests
pytest backend/tests/ -m mvp
```

---

## Success Criteria for Phase 1.5

- [ ] All 5 checkpoints completed
- [ ] All tests passing (80%+ coverage)
- [ ] API documentation updated
- [ ] User can upload photos and templates separately
- [ ] Templates preprocessed automatically
- [ ] Batch processing works for multiple templates
- [ ] Temporary files cleaned up automatically
- [ ] Frontend can consume all new APIs
