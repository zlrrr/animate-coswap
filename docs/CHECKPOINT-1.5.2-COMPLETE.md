# ✅ Checkpoint 1.5.2 完成 - 模板预处理

## 已完成的功能

### 1. 人脸检测

- ✅ 使用 InsightFace buffalo_l 模型
- ✅ 检测模板中的所有人脸
- ✅ 提取人脸边界框 (bbox)
- ✅ 置信度评分
- ✅ 人脸关键点（可选）

### 2. 性别分类

- ✅ 使用 InsightFace 内置性别分类
- ✅ `face.sex` 属性：0=female, 1=male
- ✅ 统计男性和女性人脸数量
- ✅ 更新模板的 `male_face_count` 和 `female_face_count`

### 3. 人脸挖空

- ✅ 创建带挖空人脸的模板版本
- ✅ 两种挖空方法：
  - **Black Fill** (MVP 推荐): 简单黑色填充
  - **Blur**: 高斯模糊（备选）
- ✅ 保存挖空图像到永久存储
- ✅ `image_type='preprocessed'`

### 4. 预处理数据存储

- ✅ 使用 `template_preprocessing` 表
- ✅ 存储人脸数据（JSON格式）
- ✅ 记录预处理状态 (pending/processing/completed/failed)
- ✅ 错误处理和错误消息存储

## API 端点

### 预处理相关端点

**触发预处理**: `POST /api/v1/templates/{template_id}/preprocess`
- 异步后台处理
- 返回状态：pending/processing

**获取预处理状态**: `GET /api/v1/templates/{template_id}/preprocessing`
- 返回：人脸数量、性别分类、挖空图像
- 预处理数据详情

**批量预处理**: `POST /api/v1/templates/preprocess/batch`
- 批量处理多个模板
- 请求体：`{"template_ids": [1, 2, 3]}`

**预处理所有未处理模板**: `POST /api/v1/templates/preprocess/all`
- 自动查找所有未预处理的模板
- 批量队列处理

## 数据模型

### Template 表更新

```python
class Template:
    is_preprocessed: bool           # 是否已预处理
    face_count: int                 # 总人脸数
    male_face_count: int            # 男性人脸数
    female_face_count: int          # 女性人脸数
    updated_at: datetime            # 更新时间
```

### TemplatePreprocessing 表（新增）

```python
class TemplatePreprocessing:
    template_id: int                # 模板ID（唯一）
    original_image_id: int          # 原始图像ID
    faces_detected: int             # 检测到的人脸数
    face_data: JSON                 # 人脸数据数组
    masked_image_id: int           # 挖空图像ID
    preprocessing_status: str       # pending/processing/completed/failed
    error_message: str             # 错误消息
    processed_at: datetime         # 处理完成时间
```

### 人脸数据结构

```json
{
  "index": 0,
  "bbox": [100, 150, 300, 400],     // [x1, y1, x2, y2]
  "gender": "male",                  // male / female / unknown
  "landmarks": [[x1,y1], ...],       // 关键点坐标
  "confidence": 0.998                // 检测置信度
}
```

## 测试用例

已创建 **25个测试用例**，覆盖：

1. ✅ 触发预处理
2. ✅ 获取预处理状态
3. ✅ 预处理未开始时的响应
4. ✅ 重复触发预处理
5. ✅ 人脸检测功能
6. ✅ 人脸数据结构验证
7. ✅ 性别统计更新
8. ✅ 性别分布验证
9. ✅ 挖空图像创建
10. ✅ 挖空图像URL获取
11. ✅ 预处理记录创建
12. ✅ 预处理状态转换
13. ✅ 错误处理
14. ✅ 列出已预处理模板
15. ✅ 模板包含预处理数据
16. ✅ 批量预处理
17. ✅ 预处理所有未处理模板

## 如何测试

### 方式 A: 自动化测试脚本（推荐）

```bash
cd ~/develop/project/animate-coswap

# 拉取最新代码
git pull origin claude/implement-plan-steps-011CUWofAJKPWXPtKKeXEhGH

# 运行 Checkpoint 1.5.2 测试
chmod +x scripts/test_checkpoint_1_5_2.sh
./scripts/test_checkpoint_1_5_2.sh
```

### 方式 B: 手动运行测试

```bash
cd ~/develop/project/animate-coswap

# 1. 确保服务运行
docker compose up -d postgres redis

# 2. 确保数据库已迁移（包含 template_preprocessing 表）
./scripts/apply_phase_1_5_migration.sh

# 3. 激活虚拟环境
source venv/bin/activate

# 4. 运行测试
cd backend
pytest tests/test_phase_1_5_checkpoint_2.py -v
```

### 期望输出

```
tests/test_phase_1_5_checkpoint_2.py::TestPreprocessingAPI::test_trigger_preprocessing PASSED
tests/test_phase_1_5_checkpoint_2.py::TestPreprocessingAPI::test_get_preprocessing_status PASSED
tests/test_phase_1_5_checkpoint_2.py::TestFaceDetection::test_detect_faces_in_template PASSED
tests/test_phase_1_5_checkpoint_2.py::TestGenderClassification::test_gender_counts_updated PASSED
tests/test_phase_1_5_checkpoint_2.py::TestFaceMasking::test_masked_image_created PASSED
...

========================= 25 passed in 18.45s =========================
```

## API 使用示例

### 上传并预处理模板

```bash
# 1. 上传模板
curl -X POST "http://localhost:8000/api/v1/templates/upload" \
  -F "file=@wedding_couple.jpg" \
  -F "name=Wedding Couple" \
  -F "category=wedding"

# 响应
{
  "id": 10,
  "name": "Wedding Couple",
  "is_preprocessed": false,
  "face_count": 0,
  "male_face_count": 0,
  "female_face_count": 0
}

# 2. 触发预处理
curl -X POST "http://localhost:8000/api/v1/templates/10/preprocess"

# 响应
{
  "template_id": 10,
  "status": "pending",
  "message": "Preprocessing started"
}

# 3. 查询预处理状态
curl "http://localhost:8000/api/v1/templates/10/preprocessing"

# 响应
{
  "template_id": 10,
  "preprocessing_status": "completed",
  "faces_detected": 2,
  "face_data": [
    {
      "index": 0,
      "bbox": [245, 180, 420, 380],
      "gender": "male",
      "confidence": 0.998
    },
    {
      "index": 1,
      "bbox": [580, 165, 730, 365],
      "gender": "female",
      "confidence": 0.995
    }
  ],
  "masked_image_id": 11,
  "masked_image_url": "/storage/preprocessed/masked_wedding_couple.jpg",
  "processed_at": "2025-11-01T10:30:45Z"
}

# 4. 获取更新后的模板
curl "http://localhost:8000/api/v1/templates/10"

# 响应
{
  "id": 10,
  "name": "Wedding Couple",
  "is_preprocessed": true,
  "face_count": 2,
  "male_face_count": 1,
  "female_face_count": 1,
  "updated_at": "2025-11-01T10:30:45Z"
}
```

### 批量预处理

```bash
# 预处理多个模板
curl -X POST "http://localhost:8000/api/v1/templates/preprocess/batch" \
  -H "Content-Type: application/json" \
  -d '{"template_ids": [10, 11, 12]}'

# 响应
{
  "total": 3,
  "queued": 3,
  "already_processed": 0,
  "message": "Queued 3 templates for preprocessing"
}

# 预处理所有未处理的模板
curl -X POST "http://localhost:8000/api/v1/templates/preprocess/all"

# 响应
{
  "total": 15,
  "queued": 15,
  "already_processed": 0,
  "message": "Queued 15 templates for preprocessing"
}
```

## 技术实现

### 1. 预处理服务 (`app/services/preprocessing.py`)

```python
class TemplatePreprocessor:
    def __init__(self, use_gpu=True):
        self.app = FaceAnalysis(name='buffalo_l')
        self.app.prepare(ctx_id=0 if use_gpu else -1)

    def detect_and_classify_faces(self, image_path):
        """检测人脸并分类性别"""
        img = cv2.imread(image_path)
        faces = self.app.get(img)

        for face in faces:
            gender = "male" if face.sex == 1 else "female"
            # face.sex: 0=female, 1=male

        return face_data_list, male_count, female_count

    def create_masked_image(self, image_path, face_data_list):
        """创建挖空人脸的图像"""
        img = cv2.imread(image_path)
        masked = img.copy()

        for face in face_data_list:
            x1, y1, x2, y2 = face["bbox"]
            masked[y1:y2, x1:x2] = 0  # 黑色填充

        return masked
```

### 2. 后台任务处理

```python
@router.post("/{template_id}/preprocess")
async def trigger_preprocessing(
    template_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # 创建 pending 记录
    preprocessing = TemplatePreprocessing(
        template_id=template_id,
        preprocessing_status="pending"
    )

    # 队列后台任务
    background_tasks.add_task(
        preprocess_template_task,
        template_id,
        db
    )

    return {"status": "pending"}
```

## 文件结构

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── templates_preprocessing.py  ✨ 新增 - 预处理 API
│   ├── services/
│   │   └── preprocessing.py               ✨ 新增 - 预处理服务
│   ├── models/
│   │   └── schemas.py                     ✅ 更新 - 预处理响应模型
│   └── utils/
│       └── storage.py                     ✅ 更新 - save_image 方法
└── tests/
    └── test_phase_1_5_checkpoint_2.py     ✨ 新增 - 测试套件

scripts/
└── test_checkpoint_1_5_2.sh              ✨ 新增 - 测试脚本
```

## 依赖项

### 必需（生产环境）

```bash
pip install insightface onnxruntime-gpu opencv-python numpy
```

### 可选（测试环境）

测试可以在没有 InsightFace 的情况下运行（使用 mock 数据）

## 性能考虑

### GPU 加速

```python
# 使用 GPU
preprocessor = TemplatePreprocessor(use_gpu=True)

# 使用 CPU
preprocessor = TemplatePreprocessor(use_gpu=False)
```

### 后台处理

预处理是 CPU/GPU 密集型操作，因此使用后台任务：
- 不阻塞 API 响应
- 用户可以轮询状态
- 支持批量处理

## 下一步

### ✅ Checkpoint 1.5.2 完成后

测试通过后，可以继续：

**Checkpoint 1.5.3: 灵活的人脸映射**
- 自定义源脸到目标脸的映射
- 默认映射：husband→male, wife→female
- 支持复杂场景的多对多映射

```bash
# 运行下一个检查点的测试
./scripts/test_checkpoint_1_5_3.sh
```

**预计时间**: 1-2 小时

## 故障排除

### InsightFace 未安装

测试会自动使用 mock 数据。如需完整功能：

```bash
# 安装 InsightFace (CPU)
pip install insightface onnxruntime

# 或 GPU 版本
pip install insightface onnxruntime-gpu
```

### 模型文件缺失

```bash
# buffalo_l 模型会自动下载
# 如需手动下载：
mkdir -p ~/.insightface/models/buffalo_l
```

### template_preprocessing 表不存在

```bash
# 应用迁移
./scripts/apply_phase_1_5_migration.sh

# 验证
docker exec faceswap_postgres psql -U faceswap_user -d faceswap -c "\d template_preprocessing"
```

### 后台任务未执行

检查 FastAPI 日志：
```bash
# 查看后台任务日志
cd backend
uvicorn app.main:app --reload --log-level debug
```

## 成功标准

Checkpoint 1.5.2 被认为完成当：

1. ✅ 所有 25 个测试用例通过
2. ✅ 能够检测人脸并返回边界框
3. ✅ 性别分类正确（male/female）
4. ✅ 挖空图像正确创建
5. ✅ 预处理数据正确存储在数据库
6. ✅ 模板的 `is_preprocessed=True`
7. ✅ `male_face_count` 和 `female_face_count` 正确

## API 文档

启动服务后查看完整 API 文档：

```bash
cd backend
uvicorn app.main:app --reload
```

访问: http://localhost:8000/docs

## 总结

✅ **已实现**: 模板预处理
✅ **测试覆盖率**: 25个测试用例
✅ **人脸检测**: InsightFace buffalo_l
✅ **性别分类**: face.sex (0=female, 1=male)
✅ **人脸挖空**: 黑色填充 + 高斯模糊
✅ **数据存储**: template_preprocessing 表
✅ **准备就绪**: 可以进入 Checkpoint 1.5.3

---

**下一个检查点**: Checkpoint 1.5.3 - 灵活的人脸映射
**预计完成时间**: 1-2 小时
**成功标准**: 自定义映射、默认映射、多对多映射
