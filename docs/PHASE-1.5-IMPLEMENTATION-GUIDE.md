# MVP Phase 1.5 实施指南 | Implementation Guide

## 📋 需求总结

根据新的需求，我们需要在 MVP 阶段实现以下功能：

### 1. 分离上传 API
- ✅ Husband & Wife photos 和 template 使用不同的上传接口
- ✅ 已上传的图片支持删除接口
- ✅ Photos 存储在临时目录，处理后自动删除
- ✅ Templates 持久化到数据库

### 2. Template 预处理
- ✅ Template 数据需要预处理
- ✅ 识别并标注人脸性别（男性/女性）
- ✅ 生成挖空脸部的图像
- ✅ Gallery 显示原图和预处理后的图片

### 3. 灵活的脸部映射
- ✅ 支持自定义映射（任意脸部到任意脸部）
- ✅ 默认映射：Husband → 男性脸，Wife → 女性脸
- ✅ 在预处理后的挖空图像上执行实际处理

### 4. 批量处理
- ✅ 支持一次选中多个 templates
- ✅ 批量处理相同的 husband/wife photos
- ✅ 批量下载结果（ZIP）

---

## 🏗️ 已完成的工作

### 1. 数据库模型更新

已更新 `backend/app/models/database.py`，包含：

#### Image 模型更新
```python
class Image(Base):
    # 新增字段
    storage_type = Column(String(20), default='permanent')  # 'permanent' 或 'temporary'
    expires_at = Column(DateTime, nullable=True)  # 临时文件过期时间
    session_id = Column(String(100), index=True)  # 用于分组临时照片
```

#### Template 模型更新
```python
class Template(Base):
    # 更新字段
    name = Column(String(255))  # 从 title 重命名
    original_image_id = Column(Integer)  # 从 image_id 重命名
    is_preprocessed = Column(Boolean, default=False)
    male_face_count = Column(Integer, default=0)
    female_face_count = Column(Integer, default=0)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
```

#### 新增模型类

**TemplatePreprocessing** - 模板预处理数据
```python
class TemplatePreprocessing(Base):
    template_id = Column(Integer, unique=True)
    original_image_id = Column(Integer)
    faces_detected = Column(Integer)
    face_data = Column(JSON)  # 人脸信息：bbox, gender, landmarks
    masked_image_id = Column(Integer)  # 挖空图像
    preprocessing_status = Column(String(20))  # 'pending', 'completed', 'failed'
```

**BatchTask** - 批量处理任务
```python
class BatchTask(Base):
    batch_id = Column(String(100), unique=True)
    husband_photo_id = Column(Integer)
    wife_photo_id = Column(Integer)
    template_ids = Column(JSON)  # 模板ID数组
    total_tasks = Column(Integer)
    completed_tasks = Column(Integer, default=0)
    failed_tasks = Column(Integer, default=0)
```

#### FaceSwapTask 模型更新
```python
class FaceSwapTask(Base):
    # 新增字段
    task_id = Column(String(100), unique=True)
    batch_id = Column(String(100))  # 关联批量任务
    face_mappings = Column(JSON)  # 自定义脸部映射
    use_preprocessed = Column(Boolean, default=True)

    # 字段重命名
    husband_photo_id  # 从 husband_image_id 重命名
    wife_photo_id  # 从 wife_image_id 重命名
```

### 2. 计划文档更新

创建了 `docs/PLAN-PHASE-1.5.md`，包含：
- ✅ 详细的功能需求说明
- ✅ 数据库 schema 设计
- ✅ API 设计
- ✅ 5个检查点（Checkpoints）计划
- ✅ 测试策略
- ✅ 成功标准

---

## 📝 下一步实施计划

### 第 1 步：创建 API Schemas (1-2 小时)

在 `backend/app/models/schemas.py` 中添加新的 Pydantic 模型：

```python
# Photo Upload
class PhotoUploadResponse(BaseModel):
    id: int
    filename: str
    storage_path: str
    storage_type: str
    session_id: str
    expires_at: datetime

# Template Upload
class TemplateUploadRequest(BaseModel):
    name: str
    description: Optional[str]
    category: Optional[str]

class TemplateUploadResponse(BaseModel):
    id: int
    name: str
    original_image_id: int
    is_preprocessed: bool

# Preprocessing
class FaceDetectionResult(BaseModel):
    face_index: int
    bbox: List[float]  # [x1, y1, x2, y2]
    gender: str  # 'male' or 'female'
    confidence: float
    landmarks: List[List[float]]

class TemplatePreprocessingResponse(BaseModel):
    template_id: int
    faces_detected: int
    face_data: List[FaceDetectionResult]
    masked_image_id: int
    preprocessing_status: str

# Batch Processing
class BatchProcessRequest(BaseModel):
    husband_photo_id: int
    wife_photo_id: int
    template_ids: List[int]
    use_default_mapping: bool = True
    custom_mappings: Optional[List[FaceMapping]] = None

class BatchProcessResponse(BaseModel):
    batch_id: str
    total_tasks: int
    tasks: List[TaskInfo]
```

### 第 2 步：实现分离的上传 API (2-3 小时)

创建 `backend/app/api/v1/photos.py`:

```python
@router.post("/upload", response_model=PhotoUploadResponse)
async def upload_photo(
    file: UploadFile = File(...),
    photo_type: str = Query(..., regex="^(husband|wife)$"),
    session_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Upload husband or wife photo to temporary storage"""
    # 1. Generate session_id if not provided
    # 2. Save to temp directory: storage/temp/photos/{session_id}/
    # 3. Set expiry time (24 hours)
    # 4. Create Image record with storage_type='temporary'
    # 5. Return response with session_id
    pass

@router.delete("/{photo_id}")
async def delete_photo(
    photo_id: int,
    db: Session = Depends(get_db)
):
    """Delete a user photo"""
    # 1. Find photo by ID
    # 2. Delete file from storage
    # 3. Delete database record
    # 4. Return success
    pass
```

创建 `backend/app/api/v1/templates.py`:

```python
@router.post("/upload", response_model=TemplateUploadResponse)
async def upload_template(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Upload template to permanent storage and trigger preprocessing"""
    # 1. Save to permanent directory: storage/templates/originals/
    # 2. Create Image record with storage_type='permanent'
    # 3. Create Template record
    # 4. Trigger preprocessing task (async)
    # 5. Return response
    pass

@router.get("/{template_id}/preprocessing")
async def get_preprocessing_status(
    template_id: int,
    db: Session = Depends(get_db)
):
    """Get preprocessing status for a template"""
    # Return preprocessing data including face info
    pass
```

### 第 3 步：实现预处理逻辑 (4-5 小时)

创建 `backend/app/services/preprocessing/face_analyzer.py`:

```python
class FaceAnalyzer:
    """Face detection and gender classification"""

    def __init__(self):
        self.face_app = FaceAnalysis(name='buffalo_l')
        # Load gender classification model
        self.gender_classifier = self._load_gender_model()

    def detect_and_classify_faces(self, image_path: str):
        """
        Detect faces and classify gender

        Returns:
            List of face data with gender classification
        """
        img = cv2.imread(image_path)
        faces = self.face_app.get(img)

        results = []
        for idx, face in enumerate(faces):
            gender = self.classify_gender(face)
            results.append({
                "face_index": idx,
                "bbox": face.bbox.tolist(),
                "gender": gender,
                "confidence": face.det_score,
                "landmarks": face.landmark_2d_106.tolist(),
                "embedding": face.embedding.tolist()
            })

        return results

    def classify_gender(self, face):
        """Classify face gender"""
        # Use InsightFace gender attribute or custom model
        # Return 'male' or 'female'
        pass

    def generate_face_mask(self, image_path: str, faces):
        """Generate image with faces masked out"""
        img = cv2.imread(image_path)

        for face in faces:
            # Create mask for face region
            mask = self._create_face_mask(face["landmarks"])
            # Apply mask to image (black out face or use inpainting)
            img = cv2.bitwise_and(img, img, mask=~mask)

        return img
```

创建 `backend/app/services/preprocessing/processor.py`:

```python
class TemplatePreprocessor:
    """Template preprocessing service"""

    def __init__(self):
        self.face_analyzer = FaceAnalyzer()
        self.storage = StorageService()

    async def preprocess_template(self, template_id: int, db: Session):
        """
        Preprocess a template:
        1. Detect faces
        2. Classify gender
        3. Generate masked image
        4. Save results
        """
        template = db.query(Template).filter(Template.id == template_id).first()

        if not template:
            raise ValueError(f"Template {template_id} not found")

        # Get original image
        original_image = template.image
        image_path = self.storage.get_file_path(original_image.storage_path)

        # Detect and classify faces
        face_data = self.face_analyzer.detect_and_classify_faces(image_path)

        # Generate masked image
        masked_img = self.face_analyzer.generate_face_mask(image_path, face_data)
        masked_path = f"templates/preprocessed/template_{template_id}_masked.jpg"
        self.storage.save_image(masked_img, masked_path)

        # Save masked image to database
        masked_image = Image(
            filename=f"template_{template_id}_masked.jpg",
            storage_path=masked_path,
            image_type="preprocessed",
            storage_type="permanent",
            width=masked_img.shape[1],
            height=masked_img.shape[0]
        )
        db.add(masked_image)
        db.flush()

        # Count male/female faces
        male_count = sum(1 for f in face_data if f["gender"] == "male")
        female_count = sum(1 for f in face_data if f["gender"] == "female")

        # Update template
        template.is_preprocessed = True
        template.face_count = len(face_data)
        template.male_face_count = male_count
        template.female_face_count = female_count

        # Create preprocessing record
        preprocessing = TemplatePreprocessing(
            template_id=template_id,
            original_image_id=original_image.id,
            faces_detected=len(face_data),
            face_data=face_data,
            masked_image_id=masked_image.id,
            preprocessing_status="completed",
            processed_at=datetime.utcnow()
        )
        db.add(preprocessing)
        db.commit()

        return preprocessing
```

### 第 4 步：实现批量处理 (3-4 小时)

创建 `backend/app/api/v1/batch.py`:

```python
@router.post("/", response_model=BatchProcessResponse)
async def create_batch_process(
    request: BatchProcessRequest,
    db: Session = Depends(get_db)
):
    """Create batch processing task for multiple templates"""
    # 1. Generate batch_id
    # 2. Create BatchTask record
    # 3. Create FaceSwapTask for each template
    # 4. Trigger async processing
    # 5. Return batch info
    pass

@router.get("/{batch_id}/status")
async def get_batch_status(
    batch_id: str,
    db: Session = Depends(get_db)
):
    """Get batch processing status"""
    # Return progress and task statuses
    pass

@router.get("/{batch_id}/download")
async def download_batch_results(
    batch_id: str,
    db: Session = Depends(get_db)
):
    """Download all results as ZIP file"""
    # 1. Get all completed tasks
    # 2. Collect result images
    # 3. Create ZIP archive
    # 4. Return ZIP file
    pass
```

### 第 5 步：实现自动清理 (1-2 小时)

创建 `backend/app/services/cleanup/cleaner.py`:

```python
class TempFilesCleaner:
    """Cleanup service for temporary files"""

    @staticmethod
    async def cleanup_expired_photos(db: Session):
        """Delete expired temporary photos"""
        now = datetime.utcnow()

        expired_photos = db.query(Image).filter(
            Image.storage_type == 'temporary',
            Image.expires_at < now
        ).all()

        for photo in expired_photos:
            # Delete file
            storage = StorageService()
            storage.delete_file(photo.storage_path)

            # Delete database record
            db.delete(photo)

        db.commit()
        return len(expired_photos)

# Celery task
@celery_app.task
def cleanup_temp_files():
    """Periodic cleanup task"""
    db = SessionLocal()
    try:
        cleaner = TempFilesCleaner()
        count = cleaner.cleanup_expired_photos(db)
        logger.info(f"Cleaned up {count} expired photos")
    finally:
        db.close()
```

### 第 6 步：创建测试用例 (3-4 小时)

创建 `backend/tests/test_phase_1_5/`:

```python
# test_photo_upload.py
def test_upload_husband_photo():
    """Test uploading husband photo to temp storage"""
    pass

def test_upload_wife_photo():
    """Test uploading wife photo to temp storage"""
    pass

def test_delete_photo():
    """Test deleting photo"""
    pass

# test_template_preprocessing.py
def test_template_upload_triggers_preprocessing():
    """Test that uploading template triggers preprocessing"""
    pass

def test_face_detection_and_classification():
    """Test face detection and gender classification"""
    pass

def test_face_masking():
    """Test face masking generation"""
    pass

# test_batch_processing.py
def test_create_batch_task():
    """Test creating batch processing task"""
    pass

def test_batch_download():
    """Test downloading batch results as ZIP"""
    pass

# test_cleanup.py
def test_auto_cleanup_expired_photos():
    """Test automatic cleanup of expired photos"""
    pass
```

---

## 🚀 执行步骤（在您的 Mac 上）

### 1. 拉取最新代码

```bash
cd ~/develop/project/animate-coswap
git pull origin claude/implement-plan-steps-011CUWofAJKPWXPtKKeXEhGH
```

### 2. 运行数据库迁移

```bash
cd backend
source ../venv/bin/activate

# 创建新的迁移
alembic revision --autogenerate -m "Add Phase 1.5 features"

# 应用迁移
alembic upgrade head
```

### 3. 验证数据库结构

```bash
# 检查新表是否创建
docker exec faceswap_postgres psql -U faceswap_user -d faceswap -c "\dt"

# 应该看到新表：
# - template_preprocessing
# - batch_tasks

# 检查更新的字段
docker exec faceswap_postgres psql -U faceswap_user -d faceswap -c "\d images"
docker exec faceswap_postgres psql -U faceswap_user -d faceswap -c "\d templates"
docker exec faceswap_postgres psql -U faceswap_user -d faceswap -c "\d faceswap_tasks"
```

---

## 📊 开发进度

| 任务 | 状态 | 预计时间 | 说明 |
|------|------|----------|------|
| 计划文档 | ✅ 完成 | - | PLAN-PHASE-1.5.md |
| 数据库模型 | ✅ 完成 | - | 新增/更新所有模型 |
| API Schemas | 🔄 进行中 | 1-2 hours | 下一步 |
| Photo Upload API | ⏳ 待开始 | 2-3 hours | Checkpoint 1.5.1 |
| Template Upload API | ⏳ 待开始 | 2-3 hours | Checkpoint 1.5.1 |
| 预处理逻辑 | ⏳ 待开始 | 4-5 hours | Checkpoint 1.5.2 |
| 批量处理 | ⏳ 待开始 | 3-4 hours | Checkpoint 1.5.4 |
| 自动清理 | ⏳ 待开始 | 1-2 hours | Checkpoint 1.5.5 |
| 测试用例 | ⏳ 待开始 | 3-4 hours | 全程 |

**总预计时间：** 17-24 小时（2-3 天全职开发）

---

## ⚠️ 重要注意事项

### 1. 数据库迁移
- 当前代码包含数据库模型更新
- 必须运行 `alembic revision --autogenerate` 创建迁移
- 然后运行 `alembic upgrade head` 应用迁移

### 2. 性别分类模型
- InsightFace 的 buffalo_l 模型包含性别属性
- 可以直接使用：`face.sex` (0=female, 1=male)
- 如需更高精度，可以集成专门的性别分类模型

### 3. 人脸挖空策略
有两种方案：
- **方案 A（简单）：** 用黑色或白色填充人脸区域
- **方案 B（高级）：** 使用图像修复（inpainting）技术填充背景

推荐 MVP 阶段使用方案 A，后续优化可以采用方案 B。

### 4. 临时文件清理
- 实现 Celery 定时任务，每小时运行一次
- 删除超过 24 小时的临时文件
- 提供手动清理 API 端点

---

## 📖 相关文档

- [PLAN-PHASE-1.5.md](./PLAN-PHASE-1.5.md) - 详细计划
- [DATABASE SCHEMA](./PLAN-PHASE-1.5.md#updated-database-schema) - 数据库结构
- [API DESIGN](./PLAN-PHASE-1.5.md#new-featuresfor-mvp) - API 设计

---

## 🤝 下一步行动

建议按照以下顺序实施：

**Week 1 (基础功能):**
1. Day 1-2: 实现分离的上传 API 和删除功能
2. Day 2-3: 实现模板预处理逻辑

**Week 2 (高级功能):**
3. Day 4-5: 实现批量处理
4. Day 5: 实现自动清理
5. Day 5-7: 编写测试用例并调试

每完成一个 Checkpoint，运行测试确保功能正常，然后提交代码。

---

**创建时间：** 2025-10-31
**版本：** Phase 1.5 Initial Implementation Guide
**状态：** Database models completed, Ready for API implementation
